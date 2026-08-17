"""Tests 1-3, 10-12 and 30: human-gate and final-portfolio semantics."""

from __future__ import annotations

import unittest

from qc_helpers import HITL, hitl_data


def error_names(data):
    return {x["check_name"] for x in HITL.run_checks(data)["findings"] if x["status"] == "ERROR"}


class QualityControlHitlTests(unittest.TestCase):
    def test_01_gate_1_must_be_approved(self) -> None:
        data = hitl_data()
        data["gate_1_decision"]["overall_status"] = "PENDING"
        self.assertIn("Gate 1 human approval and decision sets", error_names(data))

    def test_02_gate_2_must_be_approved(self) -> None:
        data = hitl_data()
        data["gate_2_decision"]["overall_status"] = "PENDING"
        self.assertIn("Gate 2 human approval and decision sets", error_names(data))

    def test_03_gate_3_must_be_approved(self) -> None:
        data = hitl_data()
        data["gate_3_decision"]["overall_status"] = "PENDING"
        self.assertIn("Gate 3 human approval and decision sets", error_names(data))

    def test_10_unknown_approved_action_is_error(self) -> None:
        data = hitl_data()
        data["gate_3_decision"]["approved_action_ids"][0] = "ACTION-999"
        data["gate_3_decision"]["reviewed_action_ids"][0] = "ACTION-999"
        self.assertTrue(error_names(data) & {"Gate 3 human approval and decision sets", "Approved Action portfolio"})

    def test_11_decision_set_overlap_is_error(self) -> None:
        data = hitl_data()
        action_id = data["gate_3_decision"]["approved_action_ids"][0]
        data["gate_3_decision"]["rejected_action_ids"].append(action_id)
        self.assertIn("Gate 3 human approval and decision sets", error_names(data))

    def test_12_missing_review_item_is_error(self) -> None:
        data = hitl_data()
        data["gate_2_decision"]["reviewed_ot_ids"].pop()
        self.assertIn("Gate 2 human approval and decision sets", error_names(data))

    def test_30_empty_deferred_bundle_is_accepted(self) -> None:
        data = hitl_data()
        self.assertEqual(data["gate_3_decision"]["deferred_action_ids"], [])
        self.assertEqual(data["deferred_actions"]["items"], [])
        finding = next(x for x in HITL.run_checks(data)["findings"] if x["check_name"] == "Deferred Action backlog")
        self.assertEqual(finding["status"], "PASS")


if __name__ == "__main__":
    unittest.main()

