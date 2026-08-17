"""Tests for Signal schema and Gate 1 evidence lineage."""

from __future__ import annotations

import copy
import unittest

from vs2_helpers import (
    BUNDLE, DECISION, SIGNALS, SIGNAL_BUILDER, SIGNAL_SCHEMA, SIGNAL_VALIDATOR, SKILLS,
)


class SignalSynthesisTests(unittest.TestCase):
    def _validate(self, signals):
        return SIGNAL_VALIDATOR.validate_artifact(signals, SIGNAL_SCHEMA, BUNDLE, DECISION)

    def test_signals_validate_and_only_use_kept_news(self) -> None:
        result = self._validate(SIGNALS)
        used = {news_id for signal in SIGNALS["items"] for news_id in signal["evidence_news_ids"]}
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(used.issubset(set(DECISION["kept_news_ids"])))

    def test_excluded_news_evidence_fails(self) -> None:
        signals = copy.deepcopy(SIGNALS)
        signals["items"][0]["evidence_news_ids"] = [DECISION["excluded_news_ids"][0]]
        signals["items"][0]["evidence_types"] = ["MARKET"]
        result = self._validate(signals)
        codes = {error["code"] for error in result["errors"]}
        self.assertIn("EXCLUDED_EVIDENCE", codes)

    def test_unknown_news_evidence_fails(self) -> None:
        signals = copy.deepcopy(SIGNALS)
        signals["items"][0]["evidence_news_ids"] = ["NEWS-MARKET-999"]
        signals["items"][0]["evidence_types"] = []
        result = self._validate(signals)
        self.assertIn("EVIDENCE_NOT_KEPT", {error["code"] for error in result["errors"]})

    def test_signal_without_evidence_fails(self) -> None:
        signals = copy.deepcopy(SIGNALS)
        signals["items"][0]["evidence_news_ids"] = []
        signals["items"][0]["evidence_types"] = []
        result = self._validate(signals)
        self.assertIn("SIGNAL_WITHOUT_EVIDENCE", {error["code"] for error in result["errors"]})

    def test_evidence_types_mismatch_fails(self) -> None:
        signals = copy.deepcopy(SIGNALS)
        signals["items"][0]["evidence_types"] = ["TECHNOLOGY"]
        result = self._validate(signals)
        self.assertIn("EVIDENCE_TYPES_MISMATCH", {error["code"] for error in result["errors"]})

    def test_duplicate_signal_id_fails(self) -> None:
        signals = copy.deepcopy(SIGNALS)
        signals["items"][1]["signal_id"] = signals["items"][0]["signal_id"]
        result = self._validate(signals)
        self.assertIn("DUPLICATE_SIGNAL_ID", {error["code"] for error in result["errors"]})

    def test_live_bundle_must_be_authored_by_current_chat_llm(self) -> None:
        bundle = copy.deepcopy(BUNDLE)
        bundle["synthetic"] = False
        with self.assertRaisesRegex(ValueError, "current chat LLM"):
            SIGNAL_BUILDER.build_signals(bundle)

    def test_query_provenance_cannot_trigger_topic_rule(self) -> None:
        item = {
            "title": "Thông báo phát triển đô thị",
            "summary": "Bản tin chưa cung cấp nội dung về cơ chế mua sắm.",
            "relevance_rationale": "Được phát hiện qua market-vn-procurement.",
            "key_facts": ["Query ID: market-vn-procurement"],
        }
        searchable = SIGNAL_BUILDER._searchable(item)
        self.assertNotIn("market-vn-procurement", searchable)
        self.assertNotIn("query id", searchable)

    def test_stage_06_scripts_do_not_call_external_model_api(self) -> None:
        scripts = SKILLS / "06-signal-synthesis" / "scripts"
        rendered = "\n".join(path.read_text(encoding="utf-8") for path in scripts.glob("*.py"))
        for forbidden in ("api.openai.com", "OPENAI_API_KEY", "chat/completions"):
            self.assertNotIn(forbidden, rendered)

    def test_skill_requires_current_chat_llm_and_plain_language(self) -> None:
        skill = (SKILLS / "06-signal-synthesis" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("LLM trong phiên chat bắt buộc", skill)
        self.assertIn("Yêu cầu tiên quyết: dễ hiểu và đầy đủ", skill)
        self.assertIn("Không giới hạn độ dài câu, số vế, số câu hoặc độ dài tiêu đề", skill)
        self.assertIn("Ưu tiên đầy đủ nội dung hơn sự ngắn gọn", skill)
        self.assertNotIn("Mỗi câu chỉ nên truyền đạt một ý chính", skill)
        self.assertNotIn("Khoảng 8–16 từ", skill)

    def test_validator_rejects_synthetic_content_in_live_signal(self) -> None:
        bundle = copy.deepcopy(BUNDLE)
        bundle["synthetic"] = False
        signals = copy.deepcopy(SIGNALS)
        signals["synthetic"] = False
        result = SIGNAL_VALIDATOR.validate_artifact(signals, SIGNAL_SCHEMA, bundle, DECISION)
        self.assertEqual(result["semantic_status"], "FAIL")
        self.assertIn(
            "SYNTHETIC_CONTENT_IN_LIVE_SIGNAL",
            {error["code"] for error in result["errors"]},
        )

    def test_validator_accepts_metadata_only_live_evidence_with_summary(self) -> None:
        bundle = copy.deepcopy(BUNDLE)
        bundle["synthetic"] = False
        signals = copy.deepcopy(SIGNALS)
        signals["synthetic"] = False
        for signal in signals["items"]:
            for field in (
                "signal_title", "signal_statement", "what_changed", "from_state",
                "to_state", "why_it_matters", "evidence_summary",
            ):
                signal[field] = signal[field].replace("Synthetic", "Mô phỏng").replace("synthetic", "mô phỏng")
        evidence_id = signals["items"][0]["evidence_news_ids"][0]
        next(item for item in bundle["approved_news"] if item["news_id"] == evidence_id)[
            "content_status"
        ] = "METADATA_ONLY"
        result = SIGNAL_VALIDATOR.validate_artifact(signals, SIGNAL_SCHEMA, bundle, DECISION)
        self.assertNotIn("MISSING_SUMMARY_EVIDENCE", {error["code"] for error in result["errors"]})

    def test_validator_rejects_live_evidence_without_summary(self) -> None:
        bundle = copy.deepcopy(BUNDLE)
        bundle["synthetic"] = False
        signals = copy.deepcopy(SIGNALS)
        signals["synthetic"] = False
        for signal in signals["items"]:
            for field in (
                "signal_title", "signal_statement", "what_changed", "from_state",
                "to_state", "why_it_matters", "evidence_summary",
            ):
                signal[field] = signal[field].replace("Synthetic", "Mô phỏng").replace("synthetic", "mô phỏng")
        evidence_id = signals["items"][0]["evidence_news_ids"][0]
        next(item for item in bundle["approved_news"] if item["news_id"] == evidence_id)["summary"] = ""
        result = SIGNAL_VALIDATOR.validate_artifact(signals, SIGNAL_SCHEMA, bundle, DECISION)
        self.assertIn("MISSING_SUMMARY_EVIDENCE", {error["code"] for error in result["errors"]})


if __name__ == "__main__":
    unittest.main()
