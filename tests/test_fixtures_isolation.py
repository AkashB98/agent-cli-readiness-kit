"""Isolation matrix: each bad fixture fails EXACTLY its planted check."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auditor  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXPECTED_FAILED = {
    "good_cli": [],
    "bad_json_cli": ["json_output"],
    "bad_exit_cli": ["exit_code_discipline"],
    "bad_interactive_cli": ["non_interactive"],
    "bad_dry_run_cli": ["dry_run_no_mutation"],
    "bad_idempotent_cli": ["idempotency"],
}


class TestIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        report = auditor.audit_all(os.path.join(ROOT, "fixtures"))
        cls.by_name = {fx["fixture"]: fx for fx in report["fixtures"]}

    def _check(self, fixture, expected):
        got = sorted(self.by_name[fixture]["failed_checks"])
        self.assertEqual(got, sorted(expected),
                         f"{fixture}: failed={got}, want {expected}")

    def test_good_passes_all(self):
        self._check("good_cli", EXPECTED_FAILED["good_cli"])

    def test_bad_json_fails_only_json_output(self):
        self._check("bad_json_cli", EXPECTED_FAILED["bad_json_cli"])

    def test_bad_exit_fails_only_exit_code(self):
        self._check("bad_exit_cli", EXPECTED_FAILED["bad_exit_cli"])

    def test_bad_interactive_fails_only_non_interactive(self):
        self._check("bad_interactive_cli",
                    EXPECTED_FAILED["bad_interactive_cli"])

    def test_bad_dry_run_fails_only_dry_run(self):
        self._check("bad_dry_run_cli", EXPECTED_FAILED["bad_dry_run_cli"])

    def test_bad_idempotent_fails_only_idempotency(self):
        self._check("bad_idempotent_cli",
                    EXPECTED_FAILED["bad_idempotent_cli"])

    def test_every_fixture_reports_six_checks(self):
        for fx in self.by_name.values():
            self.assertEqual(len(fx["checks"]), 6)

    def test_check_names_match_order(self):
        for fx in self.by_name.values():
            self.assertEqual([c["check"] for c in fx["checks"]],
                             auditor.CHECK_ORDER)


if __name__ == "__main__":
    unittest.main()
