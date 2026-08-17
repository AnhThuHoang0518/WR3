"""Tests for initial Gate 2 review and decision semantics."""

from __future__ import annotations

import copy
import hashlib
import unittest
from pathlib import Path

from vs2_helpers import (
    GATE2_BUILDER, GATE2_REVIEW, GATE2_SCHEMA, GATE2_VALIDATOR,
    OT, RUN, SIGNALS, SKILLS,
)

ROOT = Path(__file__).resolve().parents[1]


def pending_decision():
    return {
        "review_gate": "opportunity-threat-hitl", "run_id": OT["run_id"], "overall_status": "PENDING",
        "reviewed_ot_ids": [], "approved_ot_ids": [], "rejected_ot_ids": [], "revision_ot_ids": [],
        "reviewer": None, "reviewed_at": None, "reviewer_summary": None, "synthetic": True,
    }


class OpportunityThreatHitlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        template = (SKILLS / "08-opportunity-threat-hitl" / "references" / "REVIEW_TEMPLATE.md").read_text(encoding="utf-8")
        cls.review = GATE2_REVIEW.generate_review(SIGNALS, OT, template, OT["run_id"], "signals.json", "opportunity_threat.json")
        cls.decision, cls.parse_errors = GATE2_BUILDER.parse_review(cls.review)

    def test_gate2_review_is_pending_and_has_no_auto_approve(self) -> None:
        self.assertIn("overall_status: PENDING", self.review)
        self.assertNotIn("| APPROVE |", self.review)
        self.assertEqual(self.review.count("| OT-"), len(OT["items"]))

    def test_pending_gate2_decision_validates(self) -> None:
        result = GATE2_VALIDATOR.validate_decision(self.decision, GATE2_SCHEMA, OT)
        self.assertEqual(self.parse_errors, [])
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["pipeline_can_continue"])

    def test_approved_rejected_overlap_fails(self) -> None:
        decision = pending_decision()
        decision.update({"reviewed_ot_ids": ["OT-001"], "approved_ot_ids": ["OT-001"], "rejected_ot_ids": ["OT-001"]})
        result = GATE2_VALIDATOR.validate_decision(decision, GATE2_SCHEMA, OT)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("OVERLAPPING_DECISIONS", {error["code"] for error in result["errors"]})

    def test_unknown_ot_id_fails(self) -> None:
        decision = pending_decision()
        decision.update({"reviewed_ot_ids": ["OT-999"], "approved_ot_ids": ["OT-999"]})
        result = GATE2_VALIDATOR.validate_decision(decision, GATE2_SCHEMA, OT)
        self.assertIn("UNKNOWN_ID", {error["code"] for error in result["errors"]})

    def test_approved_incomplete_review_fails(self) -> None:
        decision = pending_decision()
        decision.update({
            "overall_status": "APPROVED", "reviewed_ot_ids": ["OT-001"], "approved_ot_ids": ["OT-001"],
            "reviewer": "Human", "reviewed_at": "2026-08-09T12:00:00+07:00", "reviewer_summary": "Partial",
        })
        result = GATE2_VALIDATOR.validate_decision(decision, GATE2_SCHEMA, OT)
        self.assertIn("APPROVED_REQUIRES_COMPLETE_REVIEW", {error["code"] for error in result["errors"]})

    def test_approved_with_revision_fails(self) -> None:
        all_ids = [item["ot_id"] for item in OT["items"]]
        decision = pending_decision()
        decision.update({
            "overall_status": "APPROVED", "reviewed_ot_ids": all_ids,
            "approved_ot_ids": all_ids[:-1], "revision_ot_ids": [all_ids[-1]],
            "reviewer": "Human", "reviewed_at": "2026-08-09T12:00:00+07:00", "reviewer_summary": "Invalid revision",
        })
        result = GATE2_VALIDATOR.validate_decision(decision, GATE2_SCHEMA, OT)
        self.assertIn("APPROVED_FORBIDS_REVISION", {error["code"] for error in result["errors"]})

    def test_stage_06_to_08_scripts_do_not_read_products_catalog(self) -> None:
        for number in range(6, 9):
            skill_dir = next(SKILLS.glob(f"{number:02d}-*"))
            for script in (skill_dir / "scripts").glob("*.py"):
                self.assertNotIn("products.json", script.read_text(encoding="utf-8"), str(script))

    def test_gate1_approval_artifact_hashes_are_unchanged(self) -> None:
        expected = {
            RUN / "reviews" / "01-news-relevance-review.md": "8C007834C307672B2136D47EB52DE91E8834D2C1D7502C43C766872340C97BDC",
            RUN / "reviews" / "01-news-relevance-decision.json": "22A042889307460660A46D65E381A837B09E4BCB001E8ECC0CD43E6A0D567293",
            RUN / "validation" / "gate-1-validation-report.json": "31D6CF9C590A5B852B2EE1DEDD81B3DAD72F10A0A827FF06BC070E5450E7E1D2",
        }
        for path, digest in expected.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest().upper(), digest)

    def test_contract_and_catalog_hashes_are_unchanged(self) -> None:
        expected = {
            ROOT / "PIPELINE_VERSION.md": "8E4A0A59845507E8483F6EF96A7CC1F16DECC576761D907731C4C5D4AB2A7FEA",
            SKILLS / "00-news-driven-mi-orchestrator" / "references" / "PIPELINE_CONTRACT.md": "A954BEE344E126E969E4E4976A533DA84484C8D0C06EC088B9CD29145AC1EFA1",
            SKILLS / "00-news-driven-mi-orchestrator" / "references" / "DEPENDENCY_MATRIX.md": "1AFC5E309C4C750B19531DB413185CC4F7D31E2C8A3194A6087E779BE0D78917",
            SKILLS / "00-news-driven-mi-orchestrator" / "references" / "HITL_GATE_POLICY.md": "A094D4B1E56FA1BA6E48E444DB03EB9CFD07621476B6AA0739F717514AF37FFA",
            SKILLS / "00-news-driven-mi-orchestrator" / "schemas" / "pipeline_manifest.schema.json": "616D89BFDFBC3325FAC9E1E12D49060B38718D0C371083B7FF1EAFD47352F175",
            SKILLS / "02-competitor-news" / "references" / "competitors.json": "9391D4328DB5EB8C7A82ACE46A1C9D912267733AB433433D45D0A747E7868A31",
            SKILLS / "10-product-gap" / "references" / "products.json": "0AD8E4B0CAFE5CB6DBC9444FAD3CEABCE0D57B9F2BDF533D8F85C66DEE65F4E0",
        }
        for path, digest in expected.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest().upper(), digest)


if __name__ == "__main__":
    unittest.main()
