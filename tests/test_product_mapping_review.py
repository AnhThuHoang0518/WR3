"""Tests for the non-gating Product Mapping manual inspection file."""

from __future__ import annotations

import unittest

from pm_helpers import CONTEXT, MAPPING, REVIEW, RUN


class ProductMappingReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.markdown = REVIEW.generate_review(CONTEXT, MAPPING)

    def test_manual_review_markdown_is_ready_and_not_formal_gate(self) -> None:
        self.assertIn("review_type: PRODUCT_MAPPING_MANUAL_INSPECTION", self.markdown)
        self.assertIn("status: READY_FOR_REVIEW", self.markdown)
        self.assertIn("formal_hitl_gate: false", self.markdown)
        self.assertIn("pipeline_contract_modified: false", self.markdown)

    def test_manual_review_contains_every_mapping_and_checklist(self) -> None:
        for item in MAPPING["items"]:
            self.assertIn(item["product_mapping_id"], self.markdown)
            self.assertIn(item["market_product_category"], self.markdown)
        self.assertIn("Không ánh xạ sang danh mục sản phẩm VSF", self.markdown)
        self.assertIn("Không tạo mapping chỉ để đạt coverage", self.markdown)
        self.assertIn("Các tính năng được mô tả dễ hiểu, đầy đủ", self.markdown)

    def test_manual_review_does_not_create_a_decision_manifest(self) -> None:
        self.assertNotIn("overall_status:", self.markdown)
        self.assertFalse((RUN / "reviews" / "product-mapping-decision.json").exists())


if __name__ == "__main__":
    unittest.main()
