"""Regression tests for the shared Vietnamese review-language policy."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".agents" / "skills"
POLICY = (
    SKILLS
    / "00-news-driven-mi-orchestrator"
    / "references"
    / "REVIEW_LANGUAGE_POLICY.md"
)


class ReviewLanguagePolicyTests(unittest.TestCase):
    def test_policy_preserves_required_technical_values(self) -> None:
        text = POLICY.read_text(encoding="utf-8")
        for required in (
            "bằng tiếng Việt",
            "`title`",
            "Giữ nguyên ID",
            "enum",
            "tên riêng",
            "thuật ngữ kỹ thuật khó dịch",
            "`PENDING`",
        ):
            self.assertIn(required, text)

    def test_stages_01_to_11_reference_the_shared_policy(self) -> None:
        expected_link = (
            "[REVIEW_LANGUAGE_POLICY.md]"
            "(../00-news-driven-mi-orchestrator/references/REVIEW_LANGUAGE_POLICY.md)"
        )
        for stage_number in range(1, 12):
            skill_dir = next(SKILLS.glob(f"{stage_number:02d}-*"))
            text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            with self.subTest(stage=skill_dir.name):
                self.assertIn(expected_link, text)
                self.assertIn("bằng tiếng Việt", text)


if __name__ == "__main__":
    unittest.main()
