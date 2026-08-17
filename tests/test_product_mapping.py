"""Tests for Skill 09 schema, approved lineage and non-forced coverage."""

from __future__ import annotations

import copy
import unittest

from pm_helpers import BUNDLE, CONTEXT, COVERAGE, DECISION, DRAFT, MAPPING, PREPARE, SCHEMA, SIGNALS, VALIDATOR


class ProductMappingTests(unittest.TestCase):
    def _validate(self, artifact):
        return VALIDATOR.validate_artifact(artifact, SCHEMA, SIGNALS, BUNDLE, DECISION)

    def test_gate2_must_be_approved_before_context_preparation(self) -> None:
        decision = copy.deepcopy(DECISION)
        decision["overall_status"] = "PENDING"
        with self.assertRaises(ValueError):
            PREPARE.prepare_context(SIGNALS, BUNDLE, decision)

    def test_bundle_contains_only_the_four_approved_ot_ids(self) -> None:
        ids = [item["ot_id"] for item in BUNDLE["approved_opportunity_threat"]]
        self.assertEqual(ids, ["OT-001", "OT-004", "OT-006", "OT-007"])

    def test_rejected_ot_is_absent_from_context(self) -> None:
        rendered = str(CONTEXT)
        for ot_id in DECISION["rejected_ot_ids"]:
            self.assertNotIn(ot_id, rendered)

    def test_mapping_uses_only_approved_ot(self) -> None:
        result = self._validate(MAPPING)
        self.assertEqual(result["status"], "PASS")
        approved = set(DECISION["approved_ot_ids"])
        self.assertTrue(all(set(item["related_ot_ids"]) <= approved for item in MAPPING["items"]))

    def test_rejected_ot_in_mapping_fails(self) -> None:
        artifact = copy.deepcopy(MAPPING)
        artifact["items"][0]["related_ot_ids"] = [DECISION["rejected_ot_ids"][0]]
        codes = {item["code"] for item in self._validate(artifact)["errors"]}
        self.assertIn("REJECTED_OT_LEAKAGE", codes)

    def test_unknown_signal_id_fails(self) -> None:
        artifact = copy.deepcopy(MAPPING)
        artifact["items"][0]["signal_id"] = "SIGNAL-999"
        codes = {item["code"] for item in self._validate(artifact)["errors"]}
        self.assertIn("UNKNOWN_SIGNAL_ID", codes)

    def test_unknown_ot_id_fails(self) -> None:
        artifact = copy.deepcopy(MAPPING)
        artifact["items"][0]["related_ot_ids"] = ["OT-999"]
        codes = {item["code"] for item in self._validate(artifact)["errors"]}
        self.assertIn("UNKNOWN_OR_UNAPPROVED_OT_ID", codes)

    def test_duplicate_product_mapping_id_fails(self) -> None:
        artifact = copy.deepcopy(MAPPING)
        duplicate = copy.deepcopy(artifact["items"][0])
        duplicate["related_ot_ids"] = ["OT-004"]
        duplicate["signal_id"] = "SIGNAL-002"
        artifact["items"].append(duplicate)
        codes = {item["code"] for item in self._validate(artifact)["errors"]}
        self.assertIn("DUPLICATE_PRODUCT_MAPPING_ID", codes)

    def test_empty_related_ot_ids_fails(self) -> None:
        artifact = copy.deepcopy(MAPPING)
        artifact["items"][0]["related_ot_ids"] = []
        result = self._validate(artifact)
        self.assertEqual(result["schema_status"], "FAIL")
        self.assertIn("MAPPING_WITHOUT_APPROVED_OT", {item["code"] for item in result["errors"]})

    def test_empty_required_capabilities_fails(self) -> None:
        artifact = copy.deepcopy(MAPPING)
        artifact["items"][0]["required_capabilities"] = []
        self.assertEqual(self._validate(artifact)["schema_status"], "FAIL")

    def test_more_than_five_capabilities_are_allowed(self) -> None:
        artifact = copy.deepcopy(MAPPING)
        artifact["items"][0]["required_capabilities"] = [f"Core feature {index}" for index in range(6)]
        result = self._validate(artifact)
        self.assertNotIn("TOO_MANY_CORE_FEATURES", {item["code"] for item in result["warnings"]})

    def test_two_capabilities_are_allowed(self) -> None:
        artifact = copy.deepcopy(MAPPING)
        artifact["items"][0]["required_capabilities"] = ["Core feature one", "Core feature two"]
        result = self._validate(artifact)
        self.assertNotIn("TOO_FEW_CORE_FEATURES", {item["code"] for item in result["warnings"]})

    def test_product_gap_and_action_fields_fail(self) -> None:
        artifact = copy.deepcopy(MAPPING)
        artifact["items"][0]["gap_type"] = "MISSING"
        artifact["items"][0]["proposed_action"] = "Build it"
        result = self._validate(artifact)
        self.assertEqual(result["boundary_status"], "FAIL")
        self.assertEqual(result["schema_status"], "FAIL")

    def test_external_market_examples_may_be_absent(self) -> None:
        self.assertTrue(all("external_market_examples" not in item for item in MAPPING["items"]))
        self.assertEqual(self._validate(MAPPING)["schema_status"], "PASS")

    def test_unmapped_approved_ot_with_rationale_is_not_error(self) -> None:
        artifact = copy.deepcopy(MAPPING)
        artifact["items"] = [item for item in artifact["items"] if "OT-007" not in item["related_ot_ids"]]
        draft = copy.deepcopy(DRAFT)
        draft["unmapped_approved_ot_rationales"] = {"OT-007": "Distinct requirement intentionally left for later validation."}
        draft["unmapped_signal_rationales"] = {"SIGNAL-004": "No mapping until the draft governance scope is validated."}
        report = COVERAGE.build_report(CONTEXT, artifact, draft)
        self.assertIn(report["validation_status"], {"PASS", "PASS_WITH_WARNINGS"})
        self.assertEqual(report["unmapped_approved_ot_ids"], ["OT-007"])


if __name__ == "__main__":
    unittest.main()
