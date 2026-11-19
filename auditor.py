#!/usr/bin/env python3
"""Pre-flight auditor for wrapping a CLI as an agent tool.

Runs a target CLI in a fresh temporary working directory per check and
reports pass/fail per check with evidence. There is deliberately NO
single weighted score: a CLI that fails one check is not "83% ready",
it has one named problem to fix.

Checks (see README for limits):
  1. json_output            probe with --json emits parseable JSON
  2. exit_code_discipline   success exits 0, failure exits nonzero
  3. help_discoverability   --help exits 0 and lists declared subcommands
  4. dry_run_no_mutation    --dry-run leaves the sandbox tree unchanged
  5. non_interactive        probe with stdin=DEVNULL finishes in time
  6. idempotency            same mutating probe twice = same result

Stdlib only. POSIX only. Fixture CLIs in this repo only.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile

CHECK_ORDER = [
    "json_output",
    "exit_code_discipline",
    "help_discoverability",
    "dry_run_no_mutation",
    "non_interactive",
    "idempotency",
]

DECLARED_SUBCOMMANDS = ["create", "list"]

# Probe commands (argument lists after the CLI itself).
JSON_PROBE = ["list", "--json"]
SUCCESS_PROBE = ["list", "--json"]
FAILURE_PROBE = ["bogus-command"]
HELP_PROBE = ["--help"]
DRY_RUN_PROBE = ["create", "--name", "dryprobe", "--dry-run", "--yes",
                 "--json"]
NONINTERACTIVE_PROBE = ["create", "--name", "probe", "--json"]
IDEMPOTENCY_PROBE = ["create", "--name", "idem", "--yes", "--json"]

DEFAULT_TIMEOUT = 5
NONINTERACTIVE_TIMEOUT = 2


def normalize(text, *paths):
    """Replace temp-dir paths so output is byte-stable across runs."""
    out = text
    for p in paths:
        if p:
            out = out.replace(p, "<TMP>")
    return out


def snapshot_tree(root, include_mtime=False):
    """Map relpath -> sha256 (and mtime_ns when requested), sorted."""
    snap = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            with open(full, "rb") as fh:
                digest = hashlib.sha256(fh.read()).hexdigest()
            if include_mtime:
                snap[rel] = [digest, os.stat(full).st_mtime_ns]
            else:
                snap[rel] = digest
    return snap


def run_probe(cli_path, args, cwd, timeout=DEFAULT_TIMEOUT):
    """Run one probe with stdin=DEVNULL. Returns a result dict.

    timed_out probes report exit_code=None.
    """
    try:
        proc = subprocess.run(
            [sys.executable, cli_path, *args],
            cwd=cwd, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, timeout=timeout)
        return {"exit_code": proc.returncode, "stdout": proc.stdout,
                "stderr": proc.stderr, "timed_out": False}
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) \
            else (exc.stdout or "")
        return {"exit_code": None, "stdout": stdout, "stderr": "",
                "timed_out": True}


def _result(check, passed, evidence):
    return {"check": check, "passed": bool(passed), "evidence": evidence}


def check_json_output(cli_path):
    with tempfile.TemporaryDirectory() as tmp:
        r = run_probe(cli_path, JSON_PROBE, tmp)
        if r["timed_out"]:
            return _result("json_output", False,
                           "probe timed out")
        try:
            json.loads(r["stdout"])
            parsed = True
        except (ValueError, TypeError):
            parsed = False
        evidence = (f"probe list --json exit={r['exit_code']} "
                    f"stdout_parseable_json={parsed}")
        return _result("json_output",
                       r["exit_code"] == 0 and parsed, evidence)


def check_exit_code_discipline(cli_path):
    with tempfile.TemporaryDirectory() as tmp:
        ok = run_probe(cli_path, SUCCESS_PROBE, tmp)
        bad = run_probe(cli_path, FAILURE_PROBE, tmp)
        passed = (ok["exit_code"] == 0 and bad["exit_code"] not in (0, None)
                  and not bad["timed_out"])
        evidence = (f"success probe exit={ok['exit_code']} (want 0); "
                    f"failure probe exit={bad['exit_code']} "
                    f"(want nonzero)")
        return _result("exit_code_discipline", passed, evidence)


def check_help_discoverability(cli_path, subcommands=DECLARED_SUBCOMMANDS):
    with tempfile.TemporaryDirectory() as tmp:
        r = run_probe(cli_path, HELP_PROBE, tmp)
        missing = [c for c in subcommands if c not in r["stdout"]]
        passed = r["exit_code"] == 0 and not missing
        evidence = (f"--help exit={r['exit_code']}; declared subcommands "
                    f"listed={sorted(set(subcommands) - set(missing))}; "
                    f"missing={missing}")
        return _result("help_discoverability", passed, evidence)


def check_dry_run_no_mutation(cli_path):
    with tempfile.TemporaryDirectory() as tmp:
        before = snapshot_tree(tmp, include_mtime=True)
        r = run_probe(cli_path, DRY_RUN_PROBE, tmp)
        after = snapshot_tree(tmp, include_mtime=True)
        changed = sorted(set(before) ^ set(after)) or \
            sorted(k for k in before if before[k] != after.get(k))
        passed = not changed and not r["timed_out"]
        evidence = (f"dry-run exit={r['exit_code']}; sandbox tree "
                    f"changed_files={changed} (hash+mtime snapshot, "
                    f"sandbox working dir only)")
        return _result("dry_run_no_mutation", passed, evidence)


def check_non_interactive(cli_path):
    with tempfile.TemporaryDirectory() as tmp:
        r = run_probe(cli_path, NONINTERACTIVE_PROBE, tmp,
                      timeout=NONINTERACTIVE_TIMEOUT)
        if r["timed_out"]:
            return _result(
                "non_interactive", False,
                f"probe timed out after {NONINTERACTIVE_TIMEOUT}s "
                f"with stdin=DEVNULL (blocked waiting for input)")
        return _result(
            "non_interactive", True,
            f"probe completed with stdin=DEVNULL, exit={r['exit_code']}")


def check_idempotency(cli_path):
    with tempfile.TemporaryDirectory() as tmp:
        r1 = run_probe(cli_path, IDEMPOTENCY_PROBE, tmp)
        snap1 = snapshot_tree(tmp)
        out1 = r1["stdout"]
        r2 = run_probe(cli_path, IDEMPOTENCY_PROBE, tmp)
        snap2 = snapshot_tree(tmp)
        same_exit = r1["exit_code"] == r2["exit_code"]
        same_out = out1 == r2["stdout"]
        same_fs = snap1 == snap2
        passed = same_exit and same_out and same_fs \
            and not r1["timed_out"] and not r2["timed_out"]
        evidence = (f"run1 exit={r1['exit_code']}, run2 "
                    f"exit={r2['exit_code']}; same_exit={same_exit}; "
                    f"same_stdout={same_out}; same_fs_state={same_fs}")
        return _result("idempotency", passed, evidence)


_CHECK_FUNCS = {
    "json_output": check_json_output,
    "exit_code_discipline": check_exit_code_discipline,
    "help_discoverability": check_help_discoverability,
    "dry_run_no_mutation": check_dry_run_no_mutation,
    "non_interactive": check_non_interactive,
    "idempotency": check_idempotency,
}


def audit_fixture(cli_path, name=None):
    """Audit one CLI; each check runs in its own fresh temp dir."""
    cli_path = os.path.abspath(cli_path)
    name = name or os.path.splitext(os.path.basename(cli_path))[0]
    checks = [_CHECK_FUNCS[c](cli_path) for c in CHECK_ORDER]
    return {
        "fixture": name,
        "checks": checks,
        "passed_checks": sum(1 for c in checks if c["passed"]),
        "failed_checks": [c["check"] for c in checks if not c["passed"]],
    }


def load_manifest(fixtures_dir):
    with open(os.path.join(fixtures_dir, "manifest.json"),
              encoding="utf-8") as fh:
        return json.load(fh)


def audit_all(fixtures_dir):
    manifest = load_manifest(fixtures_dir)
    results = []
    for entry in sorted(manifest["fixtures"], key=lambda e: e["name"]):
        results.append(audit_fixture(
            os.path.join(fixtures_dir, entry["file"]), entry["name"]))
    return {"suite": "agent-cli-readiness-kit audit",
            "fixtures": results}


def render_markdown(report):
    lines = ["# Agent CLI readiness audit", ""]
    for fx in report["fixtures"]:
        lines.append(f"## {fx['fixture']}: "
                     f"{fx['passed_checks']}/{len(fx['checks'])} checks passed")
        lines.append("")
        lines.append("| Check | Result | Evidence |")
        lines.append("|---|---|---|")
        for c in fx["checks"]:
            lines.append(f"| {c['check']} | "
                         f"{'PASS' if c['passed'] else 'FAIL'} | "
                         f"{c['evidence']} |")
        lines.append("")
    return "\n".join(lines)
