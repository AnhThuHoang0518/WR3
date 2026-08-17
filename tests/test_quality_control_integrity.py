"""Tests 14, 25, 28 and 29: baseline-driven source integrity."""

from __future__ import annotations

import hashlib
import unittest

from qc_helpers import HITL, INDEX, INTEGRITY, ROOT, RUN, hitl_data


class QualityControlIntegrityTests(unittest.TestCase):
    def test_14_changed_source_hash_is_error(self) -> None:
        path = ROOT / "tests" / "fixtures" / "qc-integrity-source.json"
        actual = hashlib.sha256(path.read_bytes()).hexdigest().upper()
        simulated_baseline = "0" * 64 if actual != "0" * 64 else "F" * 64
        index = {"run_id": "test", "contract_version": "1", "file_index": [{
            "logical_name": "source", "path": path.relative_to(ROOT).as_posix(),
            "role": "canonical_artifact", "sha256": simulated_baseline,
        }]}
        self.assertEqual(INTEGRITY.build_integrity(index, ROOT)["integrity_status"], "ERROR")

    def test_25_integrity_index_contains_all_required_artifacts(self) -> None:
        names = {item["logical_name"] for item in INDEX["file_index"]}
        required = {
            "market_news", "competitor_news", "technology_news", "policy_news",
            "approved_news_bundle", "signals", "opportunity_threat",
            "approved_opportunity_threat_bundle", "product_mapping", "product_gap",
            "actions", "approved_actions", "deferred_actions", "gate_1_decision",
            "gate_2_decision", "gate_3_decision", "pipeline_contract",
            "competitors_catalog", "products_catalog",
        }
        self.assertTrue(required <= names)
        self.assertEqual(INDEX["missing_paths"], [])

    def test_28_contract_and_catalog_hashes_are_unchanged(self) -> None:
        integrity = INTEGRITY.build_integrity(INDEX, ROOT)
        by_name = {item["logical_name"]: item for item in integrity["files"]}
        for name in ["pipeline_contract", "competitors_catalog", "products_catalog"]:
            self.assertEqual(by_name[name]["baseline_sha256"], by_name[name]["sha256"])

    def test_29_approved_actions_bundle_is_unchanged(self) -> None:
        path = RUN / "artifacts" / "approved-actions.json"
        before = path.read_bytes()
        HITL.run_checks(hitl_data())
        self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
