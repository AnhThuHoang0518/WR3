"""Tests for Skill 10 preconditions, lineage, preservation and status semantics."""

from __future__ import annotations

import copy
import hashlib
import unittest

from product_gap_helpers import (
    BUNDLE, CATALOG, CONTEXT, DECISION, DRAFT, GAP, MAPPING, MATRIX, ROOT, RUN, SCHEMA, SIGNALS, VALIDATOR,
)


class ProductGapTests(unittest.TestCase):
    def _validate(self, artifact):
        return VALIDATOR.validate_artifact(
            artifact, SCHEMA, MAPPING, CATALOG, SIGNALS, BUNDLE, DECISION
        )

    def test_01_product_mapping_review_is_reviewed_accepted(self) -> None:
        text = (RUN / "reviews" / "product-mapping-review.md").read_text(encoding="utf-8")
        self.assertIn("status: REVIEWED_ACCEPTED", text)
        self.assertIn("reviewer: Thu", text)
        self.assertRegex(text, r"reviewed_at: \d{4}-\d{2}-\d{2}T")

    def test_02_skill_reads_the_frozen_products_catalog(self) -> None:
        self.assertEqual(CONTEXT["portfolio_catalog_metadata"]["dataset_name"], "VSF Smart City Product Master")
        self.assertEqual(CONTEXT["portfolio_catalog_metadata"]["product_count"], len(CATALOG["products"]))
        self.assertEqual(CONTEXT["portfolio_products"], CATALOG["products"])

    def test_03_products_catalog_is_not_modified(self) -> None:
        digest = hashlib.sha256((ROOT / ".agents/skills/10-product-gap/references/products.json").read_bytes()).hexdigest().upper()
        self.assertEqual(digest, "0AD8E4B0CAFE5CB6DBC9444FAD3CEABCE0D57B9F2BDF533D8F85C66DEE65F4E0")

    def test_04_product_mapping_ids_are_preserved(self) -> None:
        source = {item["product_mapping_id"] for item in MAPPING["items"]}
        self.assertTrue(all(item["product_mapping_id"] in source for item in GAP["items"]))

    def test_05_signal_ids_are_preserved(self) -> None:
        parents = {item["product_mapping_id"]: item for item in MAPPING["items"]}
        self.assertTrue(all(item["signal_id"] == parents[item["product_mapping_id"]]["signal_id"] for item in GAP["items"]))

    def test_06_market_categories_are_preserved(self) -> None:
        parents = {item["product_mapping_id"]: item for item in MAPPING["items"]}
        self.assertTrue(all(item["market_product_category"] == parents[item["product_mapping_id"]]["market_product_category"] for item in GAP["items"]))

    def test_07_required_capabilities_are_preserved(self) -> None:
        parents = {item["product_mapping_id"]: item for item in MAPPING["items"]}
        self.assertTrue(all(item["required_capabilities"] == parents[item["product_mapping_id"]]["required_capabilities"] for item in GAP["items"]))

    def test_08_unknown_product_mapping_id_fails(self) -> None:
        artifact = copy.deepcopy(GAP)
        artifact["items"][0]["product_mapping_id"] = "PM-999"
        codes = {item["code"] for item in self._validate(artifact)["errors"]}
        self.assertIn("UNKNOWN_PRODUCT_MAPPING_ID", codes)

    def test_09_wrong_signal_id_fails(self) -> None:
        artifact = copy.deepcopy(GAP)
        artifact["items"][0]["signal_id"] = "SIGNAL-999"
        codes = {item["code"] for item in self._validate(artifact)["errors"]}
        self.assertIn("GAP_SIGNAL_ID_MISMATCH", codes)

    def test_14_partial_match_has_current_and_missing_capabilities(self) -> None:
        partial = next(item for item in GAP["items"] if item["capability_status"] == "PARTIAL_MATCH")
        self.assertTrue(partial["current_vsf_capabilities"])
        self.assertTrue(partial["missing_capabilities"])
        self.assertEqual(self._validate(GAP)["status"], "PASS")

    def test_15_no_match_has_null_matched_product(self) -> None:
        no_matches = [item for item in GAP["items"] if item["capability_status"] == "NO_MATCH"]
        self.assertTrue(no_matches)
        self.assertTrue(all(item["matched_vsf_product"] is None for item in no_matches))

    def test_16_unknown_has_validation_needed(self) -> None:
        unknown = next(item for item in GAP["items"] if item["capability_status"] == "UNKNOWN")
        self.assertTrue(unknown["validation_needed"])
        self.assertEqual(unknown["current_vsf_capabilities"], [])

    def test_17_not_documented_is_not_confirmed_absent(self) -> None:
        pm001 = next(item for item in MATRIX["items"] if item["product_mapping_id"] == "PM-001")
        self.assertTrue(all(item["support_status"] == "NOT_DOCUMENTED" for item in pm001["capability_comparisons"]))
        gap = next(item for item in GAP["items"] if item["product_mapping_id"] == "PM-001")
        self.assertEqual(gap["capability_status"], "UNKNOWN")
        self.assertEqual(gap["missing_capabilities"], [])

    def test_18_no_action_fields_exist(self) -> None:
        rendered = str(DRAFT) + str(GAP)
        for field in ["recommended_response", "proposed_action", "build_buy_partner", "pilot_or_productize", "owner", "priority", "next_step"]:
            self.assertNotIn(field, rendered)

    def test_21_product_gap_remains_free_of_action_fields_after_gate_3(self) -> None:
        rendered = str(GAP)
        self.assertNotIn("recommended_response", rendered)
        self.assertNotIn("proposed_action", rendered)

    def test_22_quality_control_is_not_created_before_gate_3_approval(self) -> None:
        self.assertFalse((RUN / "artifacts" / "quality_control_report.json").exists())


if __name__ == "__main__":
    unittest.main()
