"""Read-only fixtures for Skill 10 Product Gap tests."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents" / "skills" / "10-product-gap"
RUN = ROOT / "workspace" / "runs" / "20260809-122107-synthetic"


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


PREPARE = module("pg_prepare", SKILL / "scripts" / "prepare_context.py")
MATRIX_BUILDER = module("pg_matrix", SKILL / "scripts" / "build_capability_matrix.py")
BUILDER = module("pg_builder", SKILL / "scripts" / "build_artifact.py")
EVIDENCE = module("pg_evidence", SKILL / "scripts" / "validate_portfolio_evidence.py")
VALIDATOR = module("pg_validator", SKILL / "scripts" / "validate_artifact.py")
COVERAGE = module("pg_coverage", SKILL / "scripts" / "build_coverage_report.py")
REVIEW = module("pg_review", SKILL / "scripts" / "generate_manual_review.py")

MAPPING = load(RUN / "artifacts" / "product_mapping.json")
SIGNALS = load(RUN / "artifacts" / "signals.json")
BUNDLE = load(RUN / "artifacts" / "approved_opportunity_threat_bundle.json")
DECISION = load(RUN / "reviews" / "02-opportunity-threat-decision.json")
CATALOG = load(SKILL / "references" / "products.json")
SCHEMA = load(SKILL / "schemas" / "output.schema.json")
CONTEXT = load(RUN / "intermediate" / "product_gap_context.json")
MATRIX = load(RUN / "intermediate" / "product_gap_capability_matrix.json")
DRAFT = load(RUN / "intermediate" / "product_gap_draft.json")
GAP = BUILDER.build_artifact(MAPPING, DRAFT, SCHEMA)

