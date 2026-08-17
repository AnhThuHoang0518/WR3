"""Tests for the implementation runtime manifest and News lineage sidecar."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".agents" / "skills"
ORCHESTRATOR = SKILLS / "00-news-driven-mi-orchestrator"
VALIDATORS = ORCHESTRATOR / "scripts" / "validators"
sys.path.insert(0, str(VALIDATORS))
from validate_json_schema import validate_instance  # noqa: E402
from validate_news_lineage import validate_news_lineage  # noqa: E402

INPUT = ROOT / "workspace" / "inputs" / "news" / "synthetic_raw_news.json"
RUN_ID = "20260809-050505-synthetic"


class RuntimeManifestAndLineageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.output_dir = ROOT / "workspace" / "test-tmp" / "runtime-manifest-lineage"
        cls.output_dir.mkdir(parents=True, exist_ok=True)
        cls.env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        cls.raw_input = json.loads(INPUT.read_text(encoding="utf-8"))
        raw_positions = {
            record["raw_news_id"]: position
            for position, record in enumerate(cls.raw_input["records"])
        }
        specs = [
            ("01-market-news", "MARKET", "market_news.json"),
            ("02-competitor-news", "COMPETITOR", "competitor_news.json"),
            ("03-technology-news", "TECHNOLOGY", "technology_news.json"),
            ("04-policy-news", "POLICY", "policy_news.json"),
        ]
        cls.artifacts: dict[str, tuple[Path, dict]] = {}
        mappings: list[dict] = []
        for folder, news_type, filename in specs:
            skill = SKILLS / folder
            output = cls.output_dir / filename
            command = [
                sys.executable, str(skill / "scripts" / "build_artifact.py"),
                "--input", str(INPUT), "--output", str(output), "--run-id", RUN_ID,
            ]
            if news_type == "COMPETITOR":
                command.extend(["--competitors", str(skill / "references" / "competitors.json")])
            completed = subprocess.run(
                command, cwd=ROOT, env=cls.env, text=True, encoding="utf-8",
                capture_output=True, check=False,
            )
            if completed.returncode != 0:
                raise AssertionError(completed.stderr)
            build_result = json.loads(completed.stdout)
            cls.artifacts[news_type] = (output, json.loads(output.read_text(encoding="utf-8")))
            for mapping in build_result["lineage"]:
                mappings.append({
                    "raw_news_id": mapping["raw_news_id"],
                    "news_id": mapping["news_id"],
                    "news_type": news_type,
                    "artifact_path": str(output),
                    "input_position": raw_positions[mapping["raw_news_id"]],
                })
        cls.lineage_schema = json.loads((ORCHESTRATOR / "schemas" / "news-lineage.schema.json").read_text(encoding="utf-8"))
        cls.valid_lineage = {
            "run_id": RUN_ID,
            "synthetic": True,
            "mapping_count": len(mappings),
            "mappings": mappings,
        }

    def _validate(self, lineage: dict, include_raw: bool = True) -> dict:
        return validate_news_lineage(
            lineage,
            self.lineage_schema,
            self.artifacts,
            self.raw_input if include_raw else None,
        )

    def test_runtime_partial_manifest_example_validates(self) -> None:
        schema = json.loads((ORCHESTRATOR / "schemas" / "runtime-run-manifest.schema.json").read_text(encoding="utf-8"))
        example = json.loads((ORCHESTRATOR / "examples" / "valid-runtime-run-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(validate_instance(example, schema), [])

    def test_pending_gate_runtime_manifest_is_blocked(self) -> None:
        example = json.loads((ORCHESTRATOR / "examples" / "valid-runtime-run-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(example["pipeline_status"], "BLOCKED")
        self.assertFalse(example["pipeline_can_continue"])
        self.assertEqual(example["blocking_reasons"], ["HUMAN_REVIEW_PENDING"])
        self.assertEqual(example["stage_statuses"]["NEWS_RELEVANCE_HITL"], "BLOCKED")

    def test_contract_pipeline_manifest_schema_hash_is_unchanged(self) -> None:
        path = ORCHESTRATOR / "schemas" / "pipeline_manifest.schema.json"
        self.assertEqual(
            hashlib.sha256(path.read_bytes()).hexdigest().upper(),
            "616D89BFDFBC3325FAC9E1E12D49060B38718D0C371083B7FF1EAFD47352F175",
        )

    def test_every_canonical_news_id_has_lineage(self) -> None:
        result = self._validate(self.valid_lineage)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["canonical_news_count"], result["mapping_count"])
        self.assertEqual(result["raw_input_validation"], "PASS")

    def test_unknown_news_id_in_lineage_fails(self) -> None:
        lineage = copy.deepcopy(self.valid_lineage)
        lineage["mappings"][0]["news_id"] = "NEWS-MARKET-999"
        result = self._validate(lineage)
        self.assertIn("UNKNOWN_NEWS_ID", {error["code"] for error in result["errors"]})

    def test_missing_news_id_lineage_fails(self) -> None:
        lineage = copy.deepcopy(self.valid_lineage)
        lineage["mappings"].pop()
        lineage["mapping_count"] = len(lineage["mappings"])
        result = self._validate(lineage)
        self.assertIn("MISSING_NEWS_LINEAGE", {error["code"] for error in result["errors"]})

    def test_duplicate_mapping_pair_fails(self) -> None:
        lineage = copy.deepcopy(self.valid_lineage)
        lineage["mappings"].append(copy.deepcopy(lineage["mappings"][0]))
        lineage["mapping_count"] = len(lineage["mappings"])
        result = self._validate(lineage)
        self.assertIn("DUPLICATE_MAPPING_PAIR", {error["code"] for error in result["errors"]})

    def test_news_type_mismatch_fails(self) -> None:
        lineage = copy.deepcopy(self.valid_lineage)
        lineage["mappings"][0]["news_type"] = "POLICY"
        result = self._validate(lineage)
        self.assertIn("NEWS_TYPE_MISMATCH", {error["code"] for error in result["errors"]})

    def test_artifact_path_mismatch_fails(self) -> None:
        lineage = copy.deepcopy(self.valid_lineage)
        lineage["mappings"][0]["artifact_path"] = "artifacts/policy_news.json"
        result = self._validate(lineage)
        self.assertIn("ARTIFACT_PATH_MISMATCH", {error["code"] for error in result["errors"]})

    def test_one_raw_news_id_may_map_to_multiple_news_ids(self) -> None:
        lineage = copy.deepcopy(self.valid_lineage)
        lineage["mappings"][1]["raw_news_id"] = lineage["mappings"][0]["raw_news_id"]
        lineage["mappings"][1]["input_position"] = lineage["mappings"][0]["input_position"]
        result = self._validate(lineage, include_raw=False)
        self.assertEqual(result["status"], "PASS")

    def test_driver_does_not_auto_approve_gate_1(self) -> None:
        driver = (ROOT / "run_vertical_slice_01.py").read_text(encoding="utf-8")
        self.assertNotIn('"overall_status": "APPROVED"', driver)
        self.assertNotIn("06-signal-synthesis", driver)


if __name__ == "__main__":
    unittest.main()
