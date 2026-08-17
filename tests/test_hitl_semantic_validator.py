"""Focused unit tests for shared Gate semantic validation."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATORS = ROOT / ".agents" / "skills" / "00-news-driven-mi-orchestrator" / "scripts" / "validators"
sys.path.insert(0, str(VALIDATORS))
from validate_gate_status import evaluate_gate  # noqa: E402
from validate_hitl_sets import validate_hitl_sets  # noqa: E402

HITL_SCRIPT = ROOT / ".agents" / "skills" / "05-news-relevance-hitl" / "scripts" / "validate_decision.py"
spec = importlib.util.spec_from_file_location("gate1_validate_decision", HITL_SCRIPT)
assert spec and spec.loader
gate1_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate1_module)


def manifest(**overrides):
    value = {
        "review_gate": "news-relevance-hitl",
        "run_id": "20260809-030303-synthetic",
        "overall_status": "APPROVED",
        "reviewed_news_ids": ["A", "B"],
        "kept_news_ids": ["A"],
        "excluded_news_ids": ["B"],
        "revision_news_ids": [],
        "reviewer": "Human Reviewer",
        "reviewed_at": "2026-08-09T03:03:03+07:00",
        "reviewer_summary": "Synthetic test decision.",
        "synthetic": True,
    }
    value.update(overrides)
    return value


class HitlSemanticValidatorTests(unittest.TestCase):
    def test_valid_union_and_disjoint_sets_pass(self) -> None:
        result = validate_hitl_sets(manifest(), "reviewed_news_ids", ["kept_news_ids", "excluded_news_ids", "revision_news_ids"], {"A", "B"}, "kept_news_ids")
        self.assertEqual(result["status"], "PASS")

    def test_overlap_between_kept_and_excluded_fails(self) -> None:
        value = manifest(excluded_news_ids=["A", "B"])
        result = validate_hitl_sets(value, "reviewed_news_ids", ["kept_news_ids", "excluded_news_ids", "revision_news_ids"], {"A", "B"}, "kept_news_ids")
        self.assertIn("OVERLAPPING_DECISIONS", {error["code"] for error in result["errors"]})

    def test_unknown_news_id_fails(self) -> None:
        value = manifest(reviewed_news_ids=["A", "B", "X"], excluded_news_ids=["B", "X"])
        result = validate_hitl_sets(value, "reviewed_news_ids", ["kept_news_ids", "excluded_news_ids", "revision_news_ids"], {"A", "B"}, "kept_news_ids")
        self.assertIn("UNKNOWN_ID", {error["code"] for error in result["errors"]})

    def test_missing_reviewed_id_fails_when_approved(self) -> None:
        value = manifest(reviewed_news_ids=["A"], excluded_news_ids=[])
        result = validate_hitl_sets(value, "reviewed_news_ids", ["kept_news_ids", "excluded_news_ids", "revision_news_ids"], {"A", "B"}, "kept_news_ids")
        self.assertIn("MISSING_ID", {error["code"] for error in result["errors"]})

    def test_approved_with_revision_fails(self) -> None:
        value = manifest(excluded_news_ids=[], revision_news_ids=["B"])
        schema = json.loads((ROOT / ".agents" / "skills" / "05-news-relevance-hitl" / "schemas" / "review-decision.schema.json").read_text(encoding="utf-8"))
        artifacts = [{"run_id": value["run_id"], "synthetic": True, "items": [{"news_id": "A"}, {"news_id": "B"}]}]
        result = gate1_module.validate_decision(value, schema, artifacts)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("APPROVED_FORBIDS_REVISION", {error["code"] for error in result["errors"]})

    def test_pending_never_continues(self) -> None:
        result = evaluate_gate({"overall_status": "PENDING"}, True)
        self.assertFalse(result["pipeline_can_continue"])
        self.assertIn("HUMAN_REVIEW_PENDING", result["blocking_reasons"])


if __name__ == "__main__":
    unittest.main()
