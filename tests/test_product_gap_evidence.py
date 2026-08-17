"""Tests for Product Gap portfolio evidence and frozen conditional rules."""

from __future__ import annotations

import copy
import unittest

from product_gap_helpers import BUNDLE, CATALOG, DECISION, EVIDENCE, GAP, MAPPING, SCHEMA, SIGNALS, VALIDATOR


class ProductGapEvidenceTests(unittest.TestCase):
    def _validate(self, artifact):
        return VALIDATOR.validate_artifact(
            artifact, SCHEMA, MAPPING, CATALOG, SIGNALS, BUNDLE, DECISION
        )

    def test_10_nonexistent_evidence_ref_fails(self) -> None:
        artifact = copy.deepcopy(GAP)
        partial = next(item for item in artifact["items"] if item["capability_status"] == "PARTIAL_MATCH")
        partial["portfolio_evidence_refs"][0]["product_code"] = "DOES-NOT-EXIST"
        result = EVIDENCE.validate_portfolio_evidence(CATALOG, artifact)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("EVIDENCE_PRODUCT_NOT_FOUND", {item["code"] for item in result["errors"]})

    def test_11_capability_claim_without_evidence_fails(self) -> None:
        artifact = copy.deepcopy(GAP)
        partial = next(item for item in artifact["items"] if item["capability_status"] == "PARTIAL_MATCH")
        partial["portfolio_evidence_refs"] = []
        codes = {item["code"] for item in self._validate(artifact)["errors"]}
        self.assertIn("CAPABILITY_CLAIM_WITHOUT_EVIDENCE", codes)

    def test_12_full_match_without_evidence_fails(self) -> None:
        artifact = copy.deepcopy(GAP)
        partial = next(item for item in artifact["items"] if item["capability_status"] == "PARTIAL_MATCH")
        partial["capability_status"] = "FULL_MATCH"
        partial["missing_capabilities"] = []
        partial["portfolio_evidence_refs"] = []
        codes = {item["code"] for item in self._validate(artifact)["errors"]}
        self.assertTrue({"FULL_MATCH_WITHOUT_EVIDENCE", "INVALID_FULL_MATCH"} & codes)

    def test_13_full_match_with_missing_capability_fails(self) -> None:
        artifact = copy.deepcopy(GAP)
        partial = next(item for item in artifact["items"] if item["capability_status"] == "PARTIAL_MATCH")
        partial["capability_status"] = "FULL_MATCH"
        result = self._validate(artifact)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("INVALID_FULL_MATCH", {item["code"] for item in result["errors"]})


if __name__ == "__main__":
    unittest.main()

