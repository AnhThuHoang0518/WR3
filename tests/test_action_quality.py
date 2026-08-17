"""Action schema, semantic-warning and coverage behavior tests."""

from __future__ import annotations

import copy
import unittest

from action_helpers import ACTIONS, CONTEXT, COVERAGE, DRAFT, validate_action


class ActionQualityTests(unittest.TestCase):
    def test_10_invalid_recommended_response_enum_fails(self) -> None:
        artifact = copy.deepcopy(ACTIONS)
        artifact["items"][0]["recommended_response"] = "SHIP"
        self.assertEqual(validate_action(artifact)["status"], "FAIL")

    def test_11_act_with_unknown_gap_warns(self) -> None:
        artifact = copy.deepcopy(ACTIONS)
        artifact["items"][0]["recommended_response"] = "ACT"
        codes = {item["code"] for item in validate_action(artifact)["warnings"]}
        self.assertIn("ACT_WITH_UNKNOWN_GAP", codes)

    def test_12_build_does_not_require_a_fixed_rationale_phrase(self) -> None:
        artifact = copy.deepcopy(ACTIONS)
        build = next(item for item in artifact["items"] if item["build_buy_partner"] == "BUILD")
        build["rationale"] = build["rationale"].replace("BUILD rationale:", "Reason:")
        codes = {item["code"] for item in validate_action(artifact)["warnings"]}
        self.assertNotIn("BUILD_WITHOUT_RATIONALE", codes)

    def test_13_productize_with_unclear_gap_warns(self) -> None:
        artifact = copy.deepcopy(ACTIONS)
        artifact["items"][2]["pilot_or_productize"] = "PRODUCTIZE"
        codes = {item["code"] for item in validate_action(artifact)["warnings"]}
        self.assertIn("PRODUCTIZE_WITH_UNCLEAR_GAP", codes)

    def test_14_empty_proposed_action_fails(self) -> None:
        artifact = copy.deepcopy(ACTIONS)
        artifact["items"][0]["proposed_action"] = ""
        codes = {item["code"] for item in validate_action(artifact)["errors"]}
        self.assertIn("EMPTY_PROPOSED_ACTION", codes)

    def test_15_empty_next_step_fails(self) -> None:
        artifact = copy.deepcopy(ACTIONS)
        artifact["items"][0]["next_step"] = ""
        codes = {item["code"] for item in validate_action(artifact)["errors"]}
        self.assertIn("EMPTY_NEXT_STEP", codes)

    def test_16_generic_next_step_warns(self) -> None:
        artifact = copy.deepcopy(ACTIONS)
        artifact["items"][0]["next_step"] = "nghiên cứu thêm"
        codes = {item["code"] for item in validate_action(artifact)["warnings"]}
        self.assertIn("GENERIC_NEXT_STEP", codes)

    def test_17_coverage_below_100_with_rationales_is_not_error(self) -> None:
        artifact = copy.deepcopy(ACTIONS)
        artifact["items"] = artifact["items"][:-1]
        draft = copy.deepcopy(DRAFT)
        draft["uncovered_approved_ot_rationales"] = {"OT-007": "Deferred pending clearer policy scope."}
        draft["uncovered_mapping_rationales"] = {"PM-004": "Deferred pending clearer policy scope."}
        draft["uncovered_gap_rationales"] = {"GAP-004": "Deferred pending clearer policy scope."}
        report = COVERAGE.build_report(CONTEXT, artifact, draft)
        self.assertEqual(report["validation_status"], "PASS_WITH_WARNINGS")
        self.assertFalse(any(item["severity"] == "ERROR" for item in report["findings"]))


if __name__ == "__main__":
    unittest.main()
