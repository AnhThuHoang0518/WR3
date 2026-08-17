"""Negative Action lineage tests."""

from __future__ import annotations

import copy
import unittest

from action_helpers import ACTIONS, validate_action


class ActionLineageTests(unittest.TestCase):
    def test_07_gap_linked_to_wrong_product_mapping_fails(self) -> None:
        artifact = copy.deepcopy(ACTIONS)
        artifact["items"][0]["gap_ids"] = ["GAP-002"]
        codes = {item["code"] for item in validate_action(artifact)["errors"]}
        self.assertIn("ACTION_GAP_MAPPING_MISMATCH", codes)

    def test_08_action_without_gap_fails(self) -> None:
        artifact = copy.deepcopy(ACTIONS)
        artifact["items"][0]["gap_ids"] = []
        codes = {item["code"] for item in validate_action(artifact)["errors"]}
        self.assertIn("ACTION_WITHOUT_GAP", codes)

    def test_09_duplicate_action_id_fails(self) -> None:
        artifact = copy.deepcopy(ACTIONS)
        duplicate = copy.deepcopy(artifact["items"][0])
        artifact["items"].append(duplicate)
        codes = {item["code"] for item in validate_action(artifact)["errors"]}
        self.assertIn("DUPLICATE_ACTION_ID", codes)


if __name__ == "__main__":
    unittest.main()

