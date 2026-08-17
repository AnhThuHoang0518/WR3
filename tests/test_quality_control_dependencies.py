"""Tests 13, 21-24 and 27: dependency and non-mutation boundaries."""

from __future__ import annotations

import copy
import unittest

from qc_helpers import DRIVER, HITL, ROOT, RUN, build_report, group, hitl_data, lineage_data


class QualityControlDependencyTests(unittest.TestCase):
    def test_13_product_mapping_products_read_is_error(self) -> None:
        from qc_helpers import DEPENDENCIES
        skill = ROOT / "tests" / "fixtures" / "qc-product-mapping-reads-products"
        self.assertEqual(DEPENDENCIES.audit_product_mapping(skill), ["runtime.py"])

    def test_21_qc_checks_do_not_mutate_source_artifacts(self) -> None:
        paths = sorted((RUN / "artifacts").glob("*.json"))
        before = {path: path.read_bytes() for path in paths}
        HITL.run_checks(hitl_data())
        from qc_helpers import LINEAGE
        LINEAGE.run_checks(lineage_data())
        self.assertEqual(before, {path: path.read_bytes() for path in paths})

    def test_22_qc_does_not_auto_fix_invalid_input(self) -> None:
        data = hitl_data()
        data["gate_3_decision"]["overall_status"] = "PENDING"
        HITL.run_checks(data)
        self.assertEqual(data["gate_3_decision"]["overall_status"], "PENDING")

    def test_23_qc_does_not_create_new_action(self) -> None:
        data = hitl_data()
        count = len(data["actions"]["items"])
        HITL.run_checks(data)
        self.assertEqual(len(data["actions"]["items"]), count)

    def test_24_qc_does_not_create_human_approval(self) -> None:
        data = hitl_data()
        pending = data["gate_1_decision"]
        pending.update({"overall_status": "PENDING", "reviewer": None, "reviewed_at": None})
        HITL.run_checks(data)
        self.assertIsNone(pending["reviewer"])
        self.assertEqual(pending["overall_status"], "PENDING")

    def test_27_manifest_marks_skill_13_only_after_report_build(self) -> None:
        from qc_helpers import pre_qc_manifest
        manifest = pre_qc_manifest()
        report = build_report([group("PASS")])
        self.assertEqual(manifest["stage_statuses"]["MI_QUALITY_CONTROL"], "NOT_IN_SCOPE")
        updated = DRIVER.update_runtime_manifest(
            manifest, RUN / "validation/quality_control_report.json",
            RUN / "validation/final-artifact-integrity.json",
            RUN / "reports/quality-control-summary.md",
            RUN / "validation/qc_checks/report-validation.json",
        )
        self.assertEqual(report["artifact_type"], "quality_control_report")
        self.assertEqual(updated["stage_statuses"]["MI_QUALITY_CONTROL"], "COMPLETED")
        self.assertEqual(manifest["stage_statuses"]["MI_QUALITY_CONTROL"], "NOT_IN_SCOPE")


if __name__ == "__main__":
    unittest.main()
