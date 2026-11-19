"""Unit tests for auditor helpers and single-check behaviour."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auditor  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOOD = os.path.join(ROOT, "fixtures", "good_cli.py")


class TestHelpers(unittest.TestCase):
    def test_snapshot_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(auditor.snapshot_tree(tmp), {})

    def test_snapshot_hashes_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "a.txt"), "w") as fh:
                fh.write("hello")
            snap = auditor.snapshot_tree(tmp)
            self.assertIn("a.txt", snap)
            with open(os.path.join(tmp, "a.txt"), "w") as fh:
                fh.write("changed")
            self.assertNotEqual(snap, auditor.snapshot_tree(tmp))

    def test_snapshot_detects_new_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            before = auditor.snapshot_tree(tmp)
            with open(os.path.join(tmp, "b.txt"), "w") as fh:
                fh.write("x")
            self.assertNotEqual(before, auditor.snapshot_tree(tmp))

    def test_normalize_replaces_temp_path(self):
        self.assertEqual(auditor.normalize("at /tmp/xyz/file", "/tmp/xyz"),
                         "at <TMP>/file")

    def test_check_order_is_fixed(self):
        self.assertEqual(auditor.CHECK_ORDER,
                         ["json_output", "exit_code_discipline",
                          "help_discoverability", "dry_run_no_mutation",
                          "non_interactive", "idempotency"])


class TestGoodFixtureChecks(unittest.TestCase):
    def test_json_output_passes(self):
        self.assertTrue(auditor.check_json_output(GOOD)["passed"])

    def test_exit_code_discipline_passes(self):
        self.assertTrue(auditor.check_exit_code_discipline(GOOD)["passed"])

    def test_help_discoverability_passes(self):
        self.assertTrue(auditor.check_help_discoverability(GOOD)["passed"])

    def test_dry_run_no_mutation_passes(self):
        self.assertTrue(auditor.check_dry_run_no_mutation(GOOD)["passed"])

    def test_non_interactive_passes(self):
        self.assertTrue(auditor.check_non_interactive(GOOD)["passed"])

    def test_idempotency_passes(self):
        self.assertTrue(auditor.check_idempotency(GOOD)["passed"])

    def test_every_check_has_evidence(self):
        result = auditor.audit_fixture(GOOD, "good_cli")
        for c in result["checks"]:
            self.assertTrue(c["evidence"])

    def test_report_has_no_single_score(self):
        result = auditor.audit_fixture(GOOD, "good_cli")
        self.assertNotIn("score", result)
        for c in result["checks"]:
            self.assertNotIn("score", c)

    def test_audit_all_covers_six_fixtures(self):
        report = auditor.audit_all(os.path.join(ROOT, "fixtures"))
        self.assertEqual(len(report["fixtures"]), 6)

    def test_markdown_lists_every_check(self):
        report = auditor.audit_all(os.path.join(ROOT, "fixtures"))
        md = auditor.render_markdown(report)
        for check in auditor.CHECK_ORDER:
            self.assertIn(check, md)

    def test_manifest_declares_subcommands(self):
        manifest = auditor.load_manifest(os.path.join(ROOT, "fixtures"))
        self.assertEqual(manifest["declared_subcommands"],
                         ["create", "list"])


if __name__ == "__main__":
    unittest.main()
