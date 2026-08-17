"""Tests for Opportunity/Threat schema and parent Signal lineage."""

from __future__ import annotations

import copy
import unittest

from vs2_helpers import OT, OT_SCHEMA, OT_VALIDATOR, SIGNALS


class OpportunityThreatTests(unittest.TestCase):
    def _validate(self, artifact):
        return OT_VALIDATOR.validate_artifact(artifact, OT_SCHEMA, SIGNALS)

    def test_every_ot_has_a_valid_signal_id(self) -> None:
        self.assertEqual(self._validate(OT)["status"], "PASS")
        signal_ids = {item["signal_id"] for item in SIGNALS["items"]}
        self.assertTrue(all(item["signal_id"] in signal_ids for item in OT["items"]))

    def test_orphan_ot_fails(self) -> None:
        artifact = copy.deepcopy(OT)
        artifact["items"][0]["signal_id"] = "SIGNAL-999"
        result = self._validate(artifact)
        self.assertIn("ORPHAN_OT", {error["code"] for error in result["errors"]})

    def test_invalid_ot_type_fails(self) -> None:
        artifact = copy.deepcopy(OT)
        artifact["items"][0]["type"] = "BENEFIT"
        result = self._validate(artifact)
        self.assertEqual(result["schema_status"], "FAIL")

    def test_one_signal_can_have_opportunity_and_threat(self) -> None:
        first_signal = SIGNALS["items"][0]["signal_id"]
        types = {item["type"] for item in OT["items"] if item["signal_id"] == first_signal}
        self.assertEqual(types, {"OPPORTUNITY", "THREAT"})


if __name__ == "__main__":
    unittest.main()
