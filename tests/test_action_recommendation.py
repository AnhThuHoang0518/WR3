"""Action Recommendation precondition and approved-lineage tests."""

from __future__ import annotations

import copy
import unittest

from action_helpers import (
    ACTIONS, ACTION_BUILDER, ACTION_SCHEMA, BUNDLE, CONTEXT, DRAFT, GAP,
    GATE2, MAPPING, RUN, SIGNALS, validate_action,
)


class ActionRecommendationTests(unittest.TestCase):
    def test_01_product_gap_review_is_reviewed_accepted(self) -> None:
        text = (RUN / "reviews" / "product-gap-review.md").read_text(encoding="utf-8")
        self.assertIn("status: REVIEWED_ACCEPTED", text)
        self.assertIn("reviewer: Thu", text)
        self.assertRegex(text, r"reviewed_at: \d{4}-\d{2}-\d{2}T")

    def test_02_actions_use_only_approved_opportunity_threat_items(self) -> None:
        approved = {item["ot_id"] for item in BUNDLE["approved_opportunity_threat"]}
        self.assertEqual(approved, set(GATE2["approved_ot_ids"]))
        self.assertTrue(all(set(item["related_ot_ids"]) <= approved for item in ACTIONS["items"]))

    def test_03_rejected_opportunity_threat_leakage_fails(self) -> None:
        artifact = copy.deepcopy(ACTIONS)
        artifact["items"][0]["related_ot_ids"] = [GATE2["rejected_ot_ids"][0]]
        codes = {item["code"] for item in validate_action(artifact)["errors"]}
        self.assertIn("ACTION_REJECTED_OT_LEAKAGE", codes)

    def test_04_every_action_source_signal_exists(self) -> None:
        signal_ids = {item["signal_id"] for item in SIGNALS["items"]}
        self.assertTrue(all(item["source_signal_id"] in signal_ids for item in ACTIONS["items"]))

    def test_05_every_action_product_mapping_exists(self) -> None:
        mapping_ids = {item["product_mapping_id"] for item in MAPPING["items"]}
        self.assertTrue(all(item["product_mapping_id"] in mapping_ids for item in ACTIONS["items"]))

    def test_06_every_action_gap_exists(self) -> None:
        gap_ids = {item["gap_id"] for item in GAP["items"]}
        self.assertTrue(all(set(item["gap_ids"]) <= gap_ids for item in ACTIONS["items"]))

    def test_new_action_schema_does_not_require_owner(self) -> None:
        required = set(ACTION_SCHEMA["properties"]["items"]["items"]["required"])
        self.assertNotIn("owner_suggestion", required)

    def test_action_builder_removes_legacy_owner(self) -> None:
        draft = copy.deepcopy(DRAFT)
        for item in draft["items"]:
            item["owner_suggestion"] = "Product"
        artifact = ACTION_BUILDER.build_artifact(CONTEXT, draft, ACTION_SCHEMA)
        self.assertTrue(all("owner_suggestion" not in item for item in artifact["items"]))


if __name__ == "__main__":
    unittest.main()
