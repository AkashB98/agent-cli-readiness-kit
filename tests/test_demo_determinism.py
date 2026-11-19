"""Demo smoke + determinism tests (subprocess, 3 runs)."""
import hashlib
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_demo():
    return subprocess.run([sys.executable, os.path.join(ROOT, "demo.py")],
                          capture_output=True, text=True, timeout=120)


class TestDemo(unittest.TestCase):
    def test_demo_exits_zero(self):
        self.assertEqual(run_demo().returncode, 0)

    def test_demo_mentions_all_fixtures(self):
        out = run_demo().stdout
        for name in ("good_cli", "bad_json_cli", "bad_exit_cli",
                     "bad_interactive_cli", "bad_dry_run_cli",
                     "bad_idempotent_cli"):
            self.assertIn(name, out)

    def test_demo_deterministic_across_three_runs(self):
        outs = [run_demo().stdout for _ in range(3)]
        self.assertEqual(outs[0], outs[1])
        self.assertEqual(outs[1], outs[2])
        digests = {hashlib.md5(o.encode()).hexdigest() for o in outs}
        self.assertEqual(len(digests), 1)

    def test_demo_output_has_no_temp_paths(self):
        out = run_demo().stdout
        self.assertNotIn("/tmp/", out)

    def test_cli_audit_all_json(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, "cli.py"), "audit-all",
             "--format", "json"],
            capture_output=True, text=True, timeout=120)
        self.assertEqual(proc.returncode, 0)
        import json
        report = json.loads(proc.stdout)
        self.assertEqual(len(report["fixtures"]), 6)


if __name__ == "__main__":
    unittest.main()
