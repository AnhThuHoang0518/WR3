"""Tests for exact Gate 1 KEEP-only bundle creation."""

from __future__ import annotations

import unittest

from vs2_helpers import BUNDLE, CORRECTIONS, DECISION, NEWS_ARTIFACTS
from validate_stage_lineage import validate_approved_news_bundle


class ApprovedNewsBundleTests(unittest.TestCase):
    def test_bundle_contains_exactly_nine_kept_news(self) -> None:
        self.assertEqual(BUNDLE["kept_news_count"], 9)
        self.assertEqual(len(BUNDLE["approved_news"]), 9)
        self.assertEqual({item["news_id"] for item in BUNDLE["approved_news"]}, set(DECISION["kept_news_ids"]))

    def test_bundle_contains_no_excluded_news(self) -> None:
        bundle_ids = {item["news_id"] for item in BUNDLE["approved_news"]}
        self.assertFalse(bundle_ids & set(DECISION["excluded_news_ids"]))

    def test_every_bundle_item_matches_canonical_news(self) -> None:
        result = validate_approved_news_bundle(BUNDLE, DECISION, NEWS_ARTIFACTS, CORRECTIONS)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["actual_bundle_count"], result["expected_kept_count"])


if __name__ == "__main__":
    unittest.main()
