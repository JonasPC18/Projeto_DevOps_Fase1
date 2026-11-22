import unittest
from scripts.security_gate import summarize


class SecurityGateTests(unittest.TestCase):
    def report(self, severity, fixed):
        return {"SchemaVersion": 2, "Results": [{"Vulnerabilities": [
            {"Severity": severity, "FixedVersion": fixed, "VulnerabilityID": "CVE-TEST",
             "PkgName": "example"}]}]}

    def test_fixable_high_is_blocked(self):
        self.assertEqual(len(summarize(self.report("HIGH", "2.0"))["blocked"]), 1)

    def test_fixable_critical_is_blocked(self):
        self.assertEqual(len(summarize(self.report("CRITICAL", "2.0"))["blocked"]), 1)

    def test_unfixed_is_reported_without_blocking(self):
        result = summarize(self.report("HIGH", ""))
        self.assertEqual(result["counts"], {"HIGH": 1})
        self.assertEqual(result["blocked"], [])

    def test_medium_is_reported(self):
        self.assertEqual(summarize(self.report("MEDIUM", "2.0"))["counts"], {"MEDIUM": 1})

    def test_invalid_report_is_rejected(self):
        with self.assertRaises(ValueError):
            summarize({})
