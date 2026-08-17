"""Tests 15-20: QC report status, counts and frozen schema."""

from __future__ import annotations

import unittest

from qc_helpers import QC_SCHEMA, VALIDATE_REPORT, build_report, group


class QualityControlSchemaTests(unittest.TestCase):
    def test_15_warning_does_not_fail_release(self) -> None:
        report = build_report([group("WARNING")])
        self.assertTrue(report["summary"]["pipeline_eligible_for_release"])
        self.assertEqual(report["summary"]["overall_status"], "WARNING")

    def test_16_error_makes_release_ineligible(self) -> None:
        self.assertFalse(build_report([group("ERROR")])["summary"]["pipeline_eligible_for_release"])

    def test_17_no_error_makes_release_eligible(self) -> None:
        self.assertTrue(build_report([group("PASS")])["summary"]["pipeline_eligible_for_release"])

    def test_18_summary_counts_match_findings(self) -> None:
        report = build_report([group("PASS"), group("WARNING"), group("ERROR")])
        checks = report["checks"]
        self.assertEqual(report["summary"]["error_count"], sum(x["status"] == "ERROR" for x in checks))
        self.assertEqual(report["summary"]["warning_count"], sum(x["status"] == "WARNING" for x in checks))
        self.assertEqual(report["summary"]["passed_count"], sum(x["status"] == "PASS" for x in checks))

    def test_19_report_validates_frozen_schema(self) -> None:
        validation = VALIDATE_REPORT.validate_report(build_report([group("WARNING")]), QC_SCHEMA)
        self.assertEqual(validation["schema_status"], "PASS")
        self.assertEqual(validation["semantic_status"], "PASS")

    def test_20_report_is_still_built_when_pipeline_has_error(self) -> None:
        report = build_report([group("ERROR", "Upstream pipeline error")])
        self.assertEqual(report["artifact_type"], "quality_control_report")
        self.assertGreater(report["summary"]["error_count"], 0)
        self.assertEqual(VALIDATE_REPORT.validate_report(report, QC_SCHEMA)["status"], "PASS")


if __name__ == "__main__":
    unittest.main()

