import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hy3cli.safety import analyze, describe  # noqa: E402


class TestSafety(unittest.TestCase):
    def test_low_risk(self):
        r = analyze("ls -lh")
        self.assertEqual(r["risk"], "low")
        self.assertTrue(r["safe_to_auto"])

    def test_high_risk_rm_rf(self):
        r = analyze("rm -rf /tmp/foo")
        self.assertEqual(r["risk"], "high")
        self.assertFalse(r["safe_to_auto"])
        self.assertTrue(any("rm -rf" in x for x in r["reasons"]))

    def test_high_risk_dd(self):
        r = analyze("dd if=/dev/zero of=/dev/sda")
        self.assertEqual(r["risk"], "high")

    def test_medium_risk_sudo(self):
        r = analyze("sudo apt update")
        self.assertEqual(r["risk"], "medium")

    def test_medium_risk_kill(self):
        r = analyze("kill -9 1234")
        self.assertEqual(r["risk"], "medium")

    def test_high_risk_git_force(self):
        r = analyze("git push --force origin main")
        self.assertEqual(r["risk"], "high")

    def test_high_risk_fork_bomb(self):
        r = analyze(":(){ :|:& };:")
        self.assertEqual(r["risk"], "high")

    def test_describe(self):
        self.assertIn("低风险", describe("low"))
        self.assertIn("高风险", describe("high"))


if __name__ == "__main__":
    unittest.main()
