"""Step 8 scope-stop and protected-file integrity tests."""

from __future__ import annotations

import hashlib
import unittest

from action_helpers import ROOT, RUN


class ProductActionReviewTests(unittest.TestCase):
    def test_28_approved_and_deferred_bundles_match_gate_3(self) -> None:
        approved = (RUN / "artifacts" / "approved-actions.json")
        deferred = (RUN / "artifacts" / "deferred-actions.json")
        self.assertTrue(approved.exists())
        self.assertTrue(deferred.exists())
        self.assertFalse((RUN / "artifacts" / "quality_control_report.json").exists())

    def test_29_product_mapping_and_gap_hashes_are_unchanged(self) -> None:
        expected = {
            RUN / "artifacts/product_mapping.json": "78C78DE35EAC24B351E7B3ED69C6F8D6CCAE2B07CFA75775E39B0D3F326A44D4",
            RUN / "artifacts/product_gap.json": "8BD4BEEC0F1F09777B643DFC16C95A1B874DA5015CFC0992D1ED6147B8F0A580",
        }
        for path, digest in expected.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest().upper(), digest)

    def test_30_contract_catalog_and_prior_reviews_are_unchanged(self) -> None:
        expected = {
            ROOT / "PIPELINE_VERSION.md": "8E4A0A59845507E8483F6EF96A7CC1F16DECC576761D907731C4C5D4AB2A7FEA",
            ROOT / ".agents/skills/00-news-driven-mi-orchestrator/references/PIPELINE_CONTRACT.md": "A954BEE344E126E969E4E4976A533DA84484C8D0C06EC088B9CD29145AC1EFA1",
            ROOT / ".agents/skills/00-news-driven-mi-orchestrator/references/DEPENDENCY_MATRIX.md": "1AFC5E309C4C750B19531DB413185CC4F7D31E2C8A3194A6087E779BE0D78917",
            ROOT / ".agents/skills/00-news-driven-mi-orchestrator/references/HITL_GATE_POLICY.md": "A094D4B1E56FA1BA6E48E444DB03EB9CFD07621476B6AA0739F717514AF37FFA",
            ROOT / ".agents/skills/02-competitor-news/references/competitors.json": "9391D4328DB5EB8C7A82ACE46A1C9D912267733AB433433D45D0A747E7868A31",
            ROOT / ".agents/skills/10-product-gap/references/products.json": "0AD8E4B0CAFE5CB6DBC9444FAD3CEABCE0D57B9F2BDF533D8F85C66DEE65F4E0",
            RUN / "reviews/01-news-relevance-decision.json": "22A042889307460660A46D65E381A837B09E4BCB001E8ECC0CD43E6A0D567293",
            RUN / "reviews/02-opportunity-threat-decision.json": "104DE79B3F1CE171FD877093A93B0AEA152B57C7AA6F93BE613B1174D80FC3F8",
            RUN / "reviews/product-mapping-review.md": "A464667E1C8CC69FFF8B3D61A21239E17C8E1C3A749E89E2F5B963DC033FBC48",
            RUN / "reviews/product-gap-review.md": "86655322CDF3039A2820AED056F3B2D2A28BCE9F624EBDD5C95BE6C2CE25CF55",
        }
        for path, digest in expected.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest().upper(), digest)


if __name__ == "__main__":
    unittest.main()
