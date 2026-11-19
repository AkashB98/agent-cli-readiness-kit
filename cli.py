#!/usr/bin/env python3
"""CLI for the readiness auditor.

Usage:
  python3 cli.py audit-all [--format md|json]
  python3 cli.py audit <fixture-file> [--format md|json]
  python3 cli.py demo

Exit code: 0 when the audit ran (per-check results are in the report),
2 on usage errors.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auditor import audit_all, audit_fixture, render_markdown  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
FIXTURES_DIR = os.path.join(ROOT, "fixtures")


def emit(report, fmt):
    if fmt == "json":
        print(json.dumps(report, sort_keys=True, indent=2))
    else:
        print(render_markdown(report), end="")


def main(argv):
    fmt = "md"
    args = []
    i = 0
    while i < len(argv):
        if argv[i] == "--format" and i + 1 < len(argv):
            fmt = argv[i + 1]
            i += 2
        else:
            args.append(argv[i])
            i += 1
    if fmt not in ("md", "json"):
        print("error: --format must be md or json", file=sys.stderr)
        return 2
    if not args:
        print(__doc__, file=sys.stderr)
        return 2
    if args[0] == "audit-all":
        emit(audit_all(FIXTURES_DIR), fmt)
        return 0
    if args[0] == "audit" and len(args) == 2:
        path = args[1] if os.path.isabs(args[1]) else os.path.join(ROOT, args[1])
        if not os.path.isfile(path):
            print("error: no such fixture: " + args[1], file=sys.stderr)
            return 2
        emit({"suite": "agent-cli-readiness-kit audit",
              "fixtures": [audit_fixture(path)]}, fmt)
        return 0
    if args[0] == "demo":
        emit(audit_all(FIXTURES_DIR), fmt)
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
