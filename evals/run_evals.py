#!/usr/bin/env python3
"""Golden evals: pin the isolation matrix.

The good fixture must pass ALL checks; each bad fixture must fail
EXACTLY its planted check(s) and pass every other check. Any spillover
(a bad fixture failing a check it was not planted to fail, or passing
its planted one) fails the eval.

The suite runs twice in-process; the reports must be identical
(determinism). evals/eval_report.json is written with stable bytes
(sorted keys, no timestamps).

Stdlib only.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auditor import audit_all  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_FIXTURES = os.path.join(_ROOT, "fixtures")


def load_cases():
    with open(os.path.join(_HERE, "golden_matrix.json"),
              encoding="utf-8") as fh:
        return json.load(fh)["cases"]


def run_once(cases):
    report = audit_all(_FIXTURES)
    by_name = {fx["fixture"]: fx for fx in report["fixtures"]}
    results = []
    for case in sorted(cases, key=lambda c: c["fixture"]):
        got = sorted(by_name[case["fixture"]]["failed_checks"])
        results.append({
            "fixture": case["fixture"],
            "expected_failed": sorted(case["expected_failed"]),
            "got_failed": got,
            "passed": got == sorted(case["expected_failed"]),
        })
    return results


def main():
    cases = load_cases()
    first = run_once(cases)
    second = run_once(cases)
    deterministic = (json.dumps(first, sort_keys=True)
                     == json.dumps(second, sort_keys=True))
    passed = sum(1 for r in first if r["passed"])
    report = {
        "suite": "agent-cli-readiness-kit golden evals",
        "case_count": len(cases),
        "passed": passed,
        "failed": len(cases) - passed,
        "deterministic": deterministic,
        "all_passed": passed == len(cases) and deterministic,
        "cases": first,
    }
    with open(os.path.join(_HERE, "eval_report.json"), "w",
              encoding="utf-8") as fh:
        fh.write(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(f"{passed}/{len(cases)} golden cases passed; "
          f"deterministic={deterministic}")
    for r in first:
        if not r["passed"]:
            print(f"  FAIL {r['fixture']}: expected failed="
                  f"{r['expected_failed']}, got {r['got_failed']}")
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
