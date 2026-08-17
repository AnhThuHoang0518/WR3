"""Integration tests for review generation and the initial PENDING manifest."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".agents" / "skills"
INPUT = ROOT / "workspace" / "inputs" / "news" / "synthetic_raw_news.json"
RUN_ID = "20260809-020202-synthetic"


class NewsRelevanceHitlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        test_temp_root = ROOT / "workspace" / "test-tmp"
        test_temp_root.mkdir(parents=True, exist_ok=True)
        cls.output_dir = test_temp_root / "news-relevance-hitl"
        cls.output_dir.mkdir(parents=True, exist_ok=True)
        cls.env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        cls.artifact_paths: dict[str, Path] = {}
        specs = [
            ("01-market-news", "market"),
            ("02-competitor-news", "competitor"),
            ("03-technology-news", "technology"),
            ("04-policy-news", "policy"),
        ]
        for folder, key in specs:
            skill = SKILLS / folder
            output = cls.output_dir / f"{key}_news.json"
            command = [sys.executable, str(skill / "scripts" / "build_artifact.py"), "--input", str(INPUT), "--output", str(output), "--run-id", RUN_ID]
            if key == "competitor":
                command.extend(["--competitors", str(skill / "references" / "competitors.json")])
            completed = subprocess.run(command, cwd=ROOT, env=cls.env, text=True, encoding="utf-8", capture_output=True, check=False)
            if completed.returncode != 0:
                raise AssertionError(completed.stderr)
            cls.artifact_paths[key] = output
        hitl = SKILLS / "05-news-relevance-hitl"
        cls.review = cls.output_dir / "review.md"
        cls.decision = cls.output_dir / "decision.json"
        cls.report = cls.output_dir / "gate-report.json"
        common_artifact_args = [argument for key in ["market", "competitor", "technology", "policy"] for argument in (f"--{key}", str(cls.artifact_paths[key]))]
        generated = subprocess.run([
            sys.executable, str(hitl / "scripts" / "generate_review.py"), *common_artifact_args,
            "--template", str(hitl / "references" / "REVIEW_TEMPLATE.md"), "--run-id", RUN_ID, "--output", str(cls.review),
        ], cwd=ROOT, env=cls.env, text=True, encoding="utf-8", capture_output=True, check=False)
        if generated.returncode != 0:
            raise AssertionError(generated.stderr)
        built = subprocess.run([
            sys.executable, str(hitl / "scripts" / "build_decision_manifest.py"), "--review", str(cls.review), "--output", str(cls.decision),
        ], cwd=ROOT, env=cls.env, text=True, encoding="utf-8", capture_output=True, check=False)
        if built.returncode != 0:
            raise AssertionError(built.stderr)
        validated = subprocess.run([
            sys.executable, str(hitl / "scripts" / "validate_decision.py"),
            "--decision", str(cls.decision), "--schema", str(hitl / "schemas" / "review-decision.schema.json"),
            *common_artifact_args, "--report", str(cls.report),
        ], cwd=ROOT, env=cls.env, text=True, encoding="utf-8", capture_output=True, check=False)
        if validated.returncode != 0:
            raise AssertionError(validated.stdout + validated.stderr)

    def test_review_is_pending_and_shows_all_items(self) -> None:
        review = self.review.read_text(encoding="utf-8")
        self.assertIn("overall_status: PENDING", review)
        self.assertIn("reviewer: null", review)
        self.assertIn("UrbanTech A", review)
        total = sum(len(json.loads(path.read_text(encoding="utf-8"))["items"]) for path in self.artifact_paths.values())
        self.assertEqual(review.count("| NEWS-"), total)

    def test_no_item_is_auto_kept(self) -> None:
        review = self.review.read_text(encoding="utf-8")
        decision = json.loads(self.decision.read_text(encoding="utf-8"))
        self.assertNotIn("| KEEP |", review)
        self.assertEqual(decision["kept_news_ids"], [])
        self.assertEqual(decision["reviewed_news_ids"], [])

    def test_pending_decision_manifest_validates(self) -> None:
        decision = json.loads(self.decision.read_text(encoding="utf-8"))
        report = json.loads(self.report.read_text(encoding="utf-8"))
        self.assertEqual(decision["overall_status"], "PENDING")
        self.assertEqual(report["schema_status"], "PASS")
        self.assertEqual(report["semantic_status"], "PASS")
        self.assertFalse(report["pipeline_can_continue"])


if __name__ == "__main__":
    unittest.main()
