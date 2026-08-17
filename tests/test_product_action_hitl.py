"""Gate 3 review, set semantics, status and bundle guards."""

from __future__ import annotations

import copy
import unittest

from action_helpers import (
    ACTIONS, APPROVED_BUILDER, BUNDLE, GAP, MAPPING, PENDING_GATE3,
    REVIEW_GENERATOR, RUN, SIGNALS, validate_gate3,
)


class ProductActionHitlTests(unittest.TestCase):
    def test_18_gate_3_review_markdown_is_pending(self) -> None:
        text = REVIEW_GENERATOR.generate_review(
            SIGNALS, BUNDLE, MAPPING, GAP, ACTIONS,
            ["signals.json", "approved_ot.json", "mapping.json", "gap.json", "actions.json"],
        )
        self.assertIn("overall_status: PENDING", text)
        self.assertIn("reviewer: null", text)
        self.assertIn("reviewed_at: null", text)
        self.assertNotIn("owner_suggestion", text)
        self.assertNotIn("action_owner", text)
        self.assertNotIn("target_timeline", text)

    def test_19_no_action_is_auto_approved(self) -> None:
        self.assertEqual(PENDING_GATE3["reviewed_action_ids"], [])
        self.assertEqual(PENDING_GATE3["approved_action_ids"], [])
        self.assertEqual(PENDING_GATE3["rejected_action_ids"], [])
        self.assertEqual(PENDING_GATE3["revision_action_ids"], [])
        self.assertEqual(PENDING_GATE3["deferred_action_ids"], [])

    def test_20_pending_decision_manifest_validates_pass(self) -> None:
        self.assertEqual(validate_gate3(PENDING_GATE3)["status"], "PASS")

    def test_21_approved_rejected_overlap_fails(self) -> None:
        decision = copy.deepcopy(PENDING_GATE3)
        decision["reviewed_action_ids"] = ["ACTION-001"]
        decision["approved_action_ids"] = ["ACTION-001"]
        decision["rejected_action_ids"] = ["ACTION-001"]
        self.assertEqual(validate_gate3(decision)["status"], "FAIL")

    def test_22_approved_deferred_overlap_fails(self) -> None:
        decision = copy.deepcopy(PENDING_GATE3)
        decision["reviewed_action_ids"] = ["ACTION-001"]
        decision["approved_action_ids"] = ["ACTION-001"]
        decision["deferred_action_ids"] = ["ACTION-001"]
        self.assertEqual(validate_gate3(decision)["status"], "FAIL")

    def test_23_unknown_action_id_fails(self) -> None:
        decision = copy.deepcopy(PENDING_GATE3)
        decision["reviewed_action_ids"] = ["ACTION-999"]
        decision["approved_action_ids"] = ["ACTION-999"]
        codes = {item["code"] for item in validate_gate3(decision)["errors"]}
        self.assertIn("UNKNOWN_ID", codes)

    def test_24_approved_with_incomplete_review_fails(self) -> None:
        decision = copy.deepcopy(PENDING_GATE3)
        decision.update({
            "overall_status": "APPROVED", "reviewed_action_ids": ["ACTION-001"],
            "approved_action_ids": ["ACTION-001"], "reviewer": "Thu",
            "reviewed_at": "2026-08-09T12:00:00Z", "reviewer_summary": "Approved reviewed subset.",
        })
        self.assertEqual(validate_gate3(decision)["status"], "FAIL")

    def test_25_approved_with_revision_ids_fails(self) -> None:
        ids = [item["action_id"] for item in ACTIONS["items"]]
        decision = copy.deepcopy(PENDING_GATE3)
        decision.update({
            "overall_status": "APPROVED", "reviewed_action_ids": ids,
            "approved_action_ids": ids[:-1], "revision_action_ids": [ids[-1]],
            "reviewer": "Thu", "reviewed_at": "2026-08-09T12:00:00Z",
            "reviewer_summary": "Contains revision and must fail.",
        })
        self.assertEqual(validate_gate3(decision)["status"], "FAIL")

    def test_26_pending_gate_blocks_pipeline(self) -> None:
        report = validate_gate3(PENDING_GATE3)
        self.assertFalse(report["pipeline_can_continue"])
        self.assertEqual(report["blocking_reasons"], ["HUMAN_REVIEW_PENDING"])

    def test_27_pending_gate_cannot_build_approved_bundle(self) -> None:
        with self.assertRaises(ValueError):
            APPROVED_BUILDER.build_bundle(ACTIONS, PENDING_GATE3)


if __name__ == "__main__":
    unittest.main()
