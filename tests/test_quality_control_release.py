"""Test 26: Markdown summary is a faithful view of QC JSON."""

from __future__ import annotations

import unittest

from qc_helpers import INDEX, RUN, SUMMARY, build_report, group, load, pre_qc_manifest


class QualityControlReleaseTests(unittest.TestCase):
    def test_26_summary_markdown_matches_qc_json(self) -> None:
        report = build_report([group("WARNING")])
        integrity = {"file_count": len(INDEX["file_index"]), "integrity_status": "PASS"}
        decisions = [load(RUN / "reviews" / name) for name in [
            "01-news-relevance-decision.json", "02-opportunity-threat-decision.json",
            "03-product-action-decision.json",
        ]]
        text = SUMMARY.generate_summary(
            report, integrity, pre_qc_manifest(), decisions,
            load(RUN / "artifacts" / "approved-actions.json"), "1.0.0-contract",
        )
        summary = report["summary"]
        self.assertIn(f"- Error count: {summary['error_count']}", text)
        self.assertIn(f"- Warning count: {summary['warning_count']}", text)
        self.assertIn(f"- Pass count: {summary['passed_count']}", text)
        self.assertIn("pipeline_eligible_for_release: true", text)


if __name__ == "__main__":
    unittest.main()
