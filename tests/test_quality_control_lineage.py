"""Tests 4-8: negative cross-stage lineage cases."""

from __future__ import annotations

import unittest

from qc_helpers import LINEAGE, lineage_data


def errors(data):
    return [x for x in LINEAGE.run_checks(data)["findings"] if x["status"] == "ERROR"]


class QualityControlLineageTests(unittest.TestCase):
    def test_04_excluded_news_used_by_signal_is_error(self) -> None:
        data = lineage_data()
        excluded = data["gate_1_decision"]["excluded_news_ids"][0]
        data["signals"]["items"][0]["evidence_news_ids"].append(excluded)
        self.assertTrue(errors(data))

    def test_05_rejected_ot_used_by_mapping_is_error(self) -> None:
        data = lineage_data()
        rejected = data["gate_2_decision"]["rejected_ot_ids"][0]
        data["product_mapping"]["items"][0]["related_ot_ids"] = [rejected]
        self.assertTrue(errors(data))

    def test_06_rejected_ot_used_by_action_is_error(self) -> None:
        data = lineage_data()
        rejected = data["gate_2_decision"]["rejected_ot_ids"][0]
        data["actions"]["items"][0]["related_ot_ids"] = [rejected]
        self.assertTrue(errors(data))

    def test_07_unknown_product_mapping_id_is_error(self) -> None:
        data = lineage_data()
        data["product_gap"]["items"][0]["product_mapping_id"] = "PM-999"
        self.assertTrue(errors(data))

    def test_08_gap_with_wrong_signal_id_is_error(self) -> None:
        data = lineage_data()
        data["product_gap"]["items"][0]["signal_id"] = "SIGNAL-999"
        self.assertTrue(errors(data))


if __name__ == "__main__":
    unittest.main()

