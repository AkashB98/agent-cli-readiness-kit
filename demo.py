#!/usr/bin/env python3
"""One-command demo: audit every in-repo fixture CLI and print the report.

Exits 0: the demo reports readiness, it does not gate on it (the bad
fixtures are *supposed* to fail their planted checks). Output is
deterministic: fixtures and checks are sorted/fixed-order, evidence
strings carry no timestamps or temp paths.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auditor import audit_all, render_markdown  # noqa: E402

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "fixtures")


def main():
    report = audit_all(FIXTURES_DIR)
    print(render_markdown(report), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
