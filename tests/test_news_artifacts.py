"""Tests for deterministic synthetic News artifact builders and validators."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".agents" / "skills"
INPUT = ROOT / "workspace" / "inputs" / "news" / "synthetic_raw_news.json"
RUN_ID = "20260809-010101-synthetic"


class NewsArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        test_temp_root = ROOT / "workspace" / "test-tmp"
        test_temp_root.mkdir(parents=True, exist_ok=True)
        cls.output_dir = test_temp_root / "news-artifacts"
        cls.output_dir.mkdir(parents=True, exist_ok=True)
        cls.artifacts: dict[str, dict] = {}
        cls.build_results: dict[str, dict] = {}
        cls.validation_results: dict[str, dict] = {}
        specs = [
            ("01-market-news", "MARKET", "market_news.json"),
            ("02-competitor-news", "COMPETITOR", "competitor_news.json"),
            ("03-technology-news", "TECHNOLOGY", "technology_news.json"),
            ("04-policy-news", "POLICY", "policy_news.json"),
        ]
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        for folder, news_type, filename in specs:
            skill = SKILLS / folder
            output = cls.output_dir / filename
            command = [
                sys.executable, str(skill / "scripts" / "build_artifact.py"),
                "--input", str(INPUT), "--output", str(output), "--run-id", RUN_ID,
            ]
            if news_type == "COMPETITOR":
                command.extend(["--competitors", str(skill / "references" / "competitors.json")])
            built = subprocess.run(command, cwd=ROOT, env=env, text=True, encoding="utf-8", capture_output=True, check=False)
            if built.returncode != 0:
                raise AssertionError(built.stderr)
            cls.build_results[news_type] = json.loads(built.stdout)
            cls.artifacts[news_type] = json.loads(output.read_text(encoding="utf-8"))
            validated = subprocess.run([
                sys.executable, str(skill / "scripts" / "validate_artifact.py"),
                "--artifact", str(output), "--schema", str(skill / "schemas" / "output.schema.json"),
            ], cwd=ROOT, env=env, text=True, encoding="utf-8", capture_output=True, check=False)
            if validated.returncode != 0:
                raise AssertionError(validated.stdout + validated.stderr)
            cls.validation_results[news_type] = json.loads(validated.stdout)

    def test_four_news_artifacts_validate(self) -> None:
        self.assertEqual(set(self.validation_results), {"MARKET", "COMPETITOR", "TECHNOLOGY", "POLICY"})
        self.assertTrue(all(result["status"] == "PASS" for result in self.validation_results.values()))

    def test_news_ids_are_unique_across_run(self) -> None:
        ids = [item["news_id"] for artifact in self.artifacts.values() for item in artifact["items"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_news_types_match_artifacts(self) -> None:
        for news_type, artifact in self.artifacts.items():
            self.assertTrue(artifact["items"])
            self.assertTrue(all(item["news_type"] == news_type for item in artifact["items"]))

    def test_competitor_builder_reads_catalog_and_retains_non_catalog_company(self) -> None:
        matches = [entry["catalog_matches"] for entry in self.build_results["COMPETITOR"]["lineage"]]
        self.assertTrue(any("Becamex IDC" in values for values in matches))
        titles = [item["title"] for item in self.artifacts["COMPETITOR"]["items"]]
        self.assertTrue(any("UrbanTech A" in title for title in titles))

    def test_technology_scripts_do_not_read_products_catalog(self) -> None:
        technology_scripts = (SKILLS / "03-technology-news" / "scripts").glob("*.py")
        self.assertTrue(all("products.json" not in path.read_text(encoding="utf-8") for path in technology_scripts))

    def test_market_retains_advertisement_with_intelligence_value(self) -> None:
        titles = [item["title"] for item in self.artifacts["MARKET"]["items"]]
        self.assertTrue(any("phased smart-utility service fees" in title for title in titles))

    def test_duplicate_candidate_remains_for_hitl(self) -> None:
        raw_ids = {entry["raw_news_id"] for entry in self.build_results["MARKET"]["lineage"]}
        self.assertTrue({"RAW-SYN-001", "RAW-SYN-004"}.issubset(raw_ids))

    def test_skills_01_to_05_scripts_never_reference_products_catalog(self) -> None:
        for number in range(1, 6):
            skill_dir = next(SKILLS.glob(f"{number:02d}-*"))
            for script in (skill_dir / "scripts").glob("*.py"):
                self.assertNotIn("products.json", script.read_text(encoding="utf-8"), str(script))

    def test_frozen_catalog_hashes_match(self) -> None:
        expected = {
            SKILLS / "02-competitor-news" / "references" / "competitors.json": "9391D4328DB5EB8C7A82ACE46A1C9D912267733AB433433D45D0A747E7868A31",
            SKILLS / "10-product-gap" / "references" / "products.json": "0AD8E4B0CAFE5CB6DBC9444FAD3CEABCE0D57B9F2BDF533D8F85C66DEE65F4E0",
        }
        for path, digest in expected.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest().upper(), digest)


if __name__ == "__main__":
    unittest.main()
