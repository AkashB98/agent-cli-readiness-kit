# agent-cli-readiness-kit

**The pre-flight audit to run before wrapping a customer's internal CLI as an agent tool.**

An **agent** — an AI program that acts by calling tools — is only as reliable as the command-line tools underneath it. In **forward deployed engineering** work, the tool is often a customer's existing internal **CLI** — command-line interface — that was built for a human at a terminal, not for a program. Humans forgive a CLI that prints prose instead of **JSON** — a machine-readable data format — asks a question mid-run, or reports success when it failed. Agents cannot. This kit is the **pre-flight audit** — a short, fixed checklist run *before* integration — that answers, per check and with evidence, whether a CLI is ready to be wrapped: parseable output, honest exit codes, discoverable help, a dry-run that truly changes nothing, no blocking prompts, and repeatable results.

> Proof-of-concept framing: this is a POC built against small in-repo fixture CLIs. It demonstrates the audit method and the failure modes; it is not a certified assessment of any real tool.

## What it proves

- **Per-check verdicts, never one weighted score.** A CLI that fails one check is not "83% ready" — it has one named problem to fix. Every check reports PASS/FAIL plus an evidence string.
- **Isolation, pinned by evals.** Each bad fixture fails *exactly* the check it was planted to fail and passes the rest, so a FAIL is attributable to a specific behaviour, not audit noise.
- **Sandboxed, deterministic auditing.** Every probe runs in a fresh temporary working directory, output is normalised (no temp paths, no timestamps), and the demo produces byte-identical output across runs.

## The six checks

| # | Check | Probe | Pass condition |
|---|---|---|---|
| 1 | `json_output` | `list --json` | exit 0 and stdout parses as JSON |
| 2 | `exit_code_discipline` | success probe (`list --json`) + failure probe (unknown command) | success exits 0, failure exits nonzero |
| 3 | `help_discoverability` | `--help` | exit 0 and the help text lists the declared subcommands (`create`, `list`). Narrow by design: no schema validation |
| 4 | `dry_run_no_mutation` | `create --name dryprobe --dry-run --yes --json`, with a file-hash + mtime snapshot of the sandbox tree before/after | no file created, changed, or touched |
| 5 | `non_interactive` | `create --name probe --json` with stdin set to DEVNULL and a hard 2s timeout | the probe completes; a timeout is a FAIL (blocked waiting for input) |
| 6 | `idempotency` | the same mutating probe (`create --name idem --yes --json`) run twice | same exit code, same `--json` stdout, and same filesystem state after run 2 as after run 1 |

## Fixtures

All fixtures are small Python scripts in `fixtures/`, declared in `fixtures/manifest.json`. They share one tiny interface (`create` / `list`, `--json`, `--dry-run`, `--yes`) and store items as files under `./data/` in the working directory.

| Fixture | Planted behaviour | Expected result |
|---|---|---|
| `good_cli` | correct on every axis | passes all 6 checks |
| `bad_json_cli` | accepts `--json` but always prints plain text | fails `json_output` only |
| `bad_exit_cli` | prints errors but exits 0 on failure | fails `exit_code_discipline` only |
| `bad_interactive_cli` | `create` without `--yes` prompts and loops forever on EOF | fails `non_interactive` only |
| `bad_dry_run_cli` | `--dry-run` writes the item file like a real run | fails `dry_run_no_mutation` only |
| `bad_idempotent_cli` | every `create` bumps a counter; output and stored content change per run | fails `idempotency` only |

## Quickstart

```bash
# one-command demo: audit all fixtures, print the markdown report (exits 0)
python3 demo.py

# audit everything as JSON
python3 cli.py audit-all --format json

# audit one fixture
python3 cli.py audit fixtures/good_cli.py

# tests and golden evals
python3 -m unittest discover -s tests
python3 evals/run_evals.py
```

Stdlib only — no dependencies, no network at runtime.

## How it works

```
fixtures/manifest.json ──► auditor.audit_all()
                              │  per fixture, per check:
                              │  fresh TemporaryDirectory (sandbox cwd)
                              │  subprocess probe (stdin=DEVNULL, timeout)
                              │  snapshot_tree(): sha256 (+mtime for dry-run)
                              ▼
                    report: {fixture, checks[{check, passed, evidence}],
                             passed_checks, failed_checks[]}
                              ▼
              demo.py / cli.py ──► markdown table or JSON
              evals/run_evals.py ──► isolation matrix vs golden_matrix.json
```

## Honest limits

- **In-repo fixture CLIs only.** The auditor is demonstrated and evaluated only against the fixture CLIs in this repository. It has never audited a real third-party CLI, and no claim is made about one.
- **POSIX only.** Probes assume a POSIX environment (DEVNULL stdin semantics, temp directories, `sys.executable` invocation). Windows behaviour is untested and undisclosed behaviour may differ.
- **The dry-run check only observes the sandbox working directory.** It snapshots the temp working dir's file tree (hashes + mtimes). It **cannot detect network calls or side effects outside that directory** — a `--dry-run` that phones home or writes elsewhere would pass this check.
- **Help discoverability is narrow.** It checks that `--help` exits 0 and names the declared subcommands. It does not validate any output schema, flag completeness, or help quality.
- **Idempotency is narrow.** It compares one mutating probe run twice (exit code, `--json` stdout, filesystem state). It does not prove idempotency for other commands, inputs, or concurrent runs.
- **Timeouts are evidence, not proof.** The non-interactive check uses a 2-second timeout; a very slow (but non-interactive) CLI could be misread as blocking, and a prompt that waits longer than the timeout in a different way could slip past a longer budget.

## Evals

`python3 evals/run_evals.py` runs 6 golden cases pinning the isolation matrix above: the good fixture passes all checks and each bad fixture fails exactly its planted check(s). The suite runs twice in-process and the reports must be identical; `evals/eval_report.json` is written with stable bytes (sorted keys, no timestamps).

## Verification

- Unit tests: `python3 -m unittest discover -s tests` (auditor helpers, per-check behaviour on the good fixture, the full isolation matrix, demo determinism across 3 runs).
- Golden evals: 6/6 pass (see `evals/eval_report.json`).
- Demo exits 0 and its output md5 is identical across 3 runs.
- Secret sweep: no keys, credentials, or personal data — all fixtures are synthetic and self-contained.

## Sample data

There is no sample *data* beyond the fixtures themselves: six small synthetic CLIs and the item files they create inside throwaway temp directories during probes. No real CLI, customer system, or personal data is involved.
