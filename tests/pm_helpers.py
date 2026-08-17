"""Read-only reusable fixtures for Skill 09 Product Mapping tests."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents" / "skills" / "09-product-mapping"
RUN = ROOT / "workspace" / "runs" / "20260809-122107-synthetic"


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


PREPARE = module("pm_prepare", SKILL / "scripts" / "prepare_context.py")
BUILDER = module("pm_builder", SKILL / "scripts" / "build_artifact.py")
VALIDATOR = module("pm_validator", SKILL / "scripts" / "validate_artifact.py")
COVERAGE = module("pm_coverage", SKILL / "scripts" / "build_coverage_report.py")
REVIEW = module("pm_review", SKILL / "scripts" / "generate_manual_review.py")
AUDIT = module("pm_audit", SKILL / "scripts" / "audit_forbidden_dependencies.py")

SIGNALS = load(RUN / "artifacts" / "signals.json")
OPPORTUNITY_THREAT = load(RUN / "artifacts" / "opportunity_threat.json")
DECISION = load(RUN / "reviews" / "02-opportunity-threat-decision.json")
BUNDLE = load(RUN / "artifacts" / "approved_opportunity_threat_bundle.json")
CONTEXT = load(RUN / "intermediate" / "product_mapping_context.json")
DRAFT = load(RUN / "intermediate" / "product_mapping_draft.json")
SCHEMA = load(SKILL / "schemas" / "output.schema.json")
MAPPING = BUILDER.build_artifact(CONTEXT, DRAFT, SCHEMA)
