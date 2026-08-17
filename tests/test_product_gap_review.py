"""Tests for Product Gap manual review and protected-file integrity."""

from __future__ import annotations

import hashlib
import unittest

from product_gap_helpers import GAP, MAPPING, REVIEW, ROOT, RUN


class ProductGapReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.markdown = REVIEW.generate_review(MAPPING, GAP)

    def test_19_manual_review_markdown_is_generated(self) -> None:
        self.assertIn("review_type: PRODUCT_GAP_MANUAL_INSPECTION", self.markdown)
        for item in GAP["items"]:
            self.assertIn(item["gap_id"], self.markdown)
            self.assertIn(item["product_mapping_id"], self.markdown)
        self.assertIn("Tính năng được ghi là còn thiếu thực sự thiếu hay chỉ chưa được catalog mô tả?", self.markdown)

    def test_20_manual_review_is_not_formal_hitl(self) -> None:
        self.assertIn("status: READY_FOR_REVIEW", self.markdown)
        self.assertIn("formal_hitl_gate: false", self.markdown)
        self.assertNotIn("overall_status:", self.markdown)

    def test_23_gate_and_product_mapping_hashes_are_unchanged(self) -> None:
        expected = {
            RUN / "artifacts/signals.json": "CE0A0D4B59DE7350D95A9972F166C9ED1D02320FE026808B058A1B5D19F67E24",
            RUN / "artifacts/opportunity_threat.json": "E63B1DE96BFF6DC460850BDEE01DD4491277D8E4F44913FC06AA5C4CF67A086D",
            RUN / "artifacts/approved_opportunity_threat_bundle.json": "C66DB9DE8F192AC292D22EC9F026812E122FA3C5902945DB83A851F1ADC0425E",
            RUN / "artifacts/product_mapping.json": "78C78DE35EAC24B351E7B3ED69C6F8D6CCAE2B07CFA75775E39B0D3F326A44D4",
            RUN / "reviews/product-mapping-review.md": "A464667E1C8CC69FFF8B3D61A21239E17C8E1C3A749E89E2F5B963DC033FBC48",
            RUN / "reviews/01-news-relevance-review.md": "8C007834C307672B2136D47EB52DE91E8834D2C1D7502C43C766872340C97BDC",
            RUN / "reviews/01-news-relevance-decision.json": "22A042889307460660A46D65E381A837B09E4BCB001E8ECC0CD43E6A0D567293",
            RUN / "validation/gate-1-validation-report.json": "31D6CF9C590A5B852B2EE1DEDD81B3DAD72F10A0A827FF06BC070E5450E7E1D2",
            RUN / "reviews/02-opportunity-threat-review.md": "1C31BE79A1F34D976289116A149A77FC16E3427E54FDDE5B7CE1BE3B00214A1A",
            RUN / "reviews/02-opportunity-threat-decision.json": "104DE79B3F1CE171FD877093A93B0AEA152B57C7AA6F93BE613B1174D80FC3F8",
            RUN / "validation/gate-2-validation-report.json": "D0FA7770D7995C4B3DFF7885B07BA541B269BD44A37978C738D819DDE824A187",
        }
        for path, digest in expected.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest().upper(), digest)

    def test_24_contract_v1_and_catalog_hashes_are_unchanged(self) -> None:
        expected = {
            ROOT / "PIPELINE_VERSION.md": "8E4A0A59845507E8483F6EF96A7CC1F16DECC576761D907731C4C5D4AB2A7FEA",
            ROOT / ".agents/skills/00-news-driven-mi-orchestrator/references/PIPELINE_CONTRACT.md": "A954BEE344E126E969E4E4976A533DA84484C8D0C06EC088B9CD29145AC1EFA1",
            ROOT / ".agents/skills/00-news-driven-mi-orchestrator/references/DEPENDENCY_MATRIX.md": "1AFC5E309C4C750B19531DB413185CC4F7D31E2C8A3194A6087E779BE0D78917",
            ROOT / ".agents/skills/00-news-driven-mi-orchestrator/references/HITL_GATE_POLICY.md": "A094D4B1E56FA1BA6E48E444DB03EB9CFD07621476B6AA0739F717514AF37FFA",
            ROOT / ".agents/skills/02-competitor-news/references/competitors.json": "9391D4328DB5EB8C7A82ACE46A1C9D912267733AB433433D45D0A747E7868A31",
            ROOT / ".agents/skills/10-product-gap/references/products.json": "0AD8E4B0CAFE5CB6DBC9444FAD3CEABCE0D57B9F2BDF533D8F85C66DEE65F4E0",
        }
        for path, digest in expected.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest().upper(), digest)


if __name__ == "__main__":
    unittest.main()
