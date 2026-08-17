"""Test 9: Product Gap capability claims require catalog evidence."""

from __future__ import annotations

import unittest

from qc_helpers import INDEX, PORTFOLIO, ROOT


class QualityControlEvidenceTests(unittest.TestCase):
    def test_09_capability_claim_without_evidence_is_error(self) -> None:
        data = PORTFOLIO.load_inputs(INDEX, ROOT)
        data["product_gap"]["items"][3]["portfolio_evidence_refs"] = []
        report = PORTFOLIO.run_checks(**data, evidence_validator=PORTFOLIO._load_evidence_module(ROOT))
        finding = next(x for x in report["findings"] if x["check_name"] == "Product Gap portfolio evidence")
        self.assertEqual(finding["status"], "ERROR")


if __name__ == "__main__":
    unittest.main()
