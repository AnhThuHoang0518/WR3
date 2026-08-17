"""Read-only fixtures and modules for Step 8 Action and Gate 3 tests."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "workspace" / "runs" / "20260809-122107-synthetic"
SKILL11 = ROOT / ".agents" / "skills" / "11-action-recommendation"
SKILL12 = ROOT / ".agents" / "skills" / "12-product-action-hitl"
SHARED = ROOT / ".agents" / "skills" / "00-news-driven-mi-orchestrator" / "scripts" / "validators"


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


ACTION_VALIDATOR = module("step8_action_validator", SKILL11 / "scripts" / "validate_artifact.py")
ACTION_BUILDER = module("step8_action_builder", SKILL11 / "scripts" / "build_artifact.py")
COVERAGE = module("step8_action_coverage", SKILL11 / "scripts" / "build_coverage_report.py")
GATE3_VALIDATOR = module("step8_gate3_validator", SKILL12 / "scripts" / "validate_decision.py")
APPROVED_BUILDER = module("step8_approved_builder", SKILL12 / "scripts" / "build_approved_action_bundle.py")
REVIEW_GENERATOR = module("step8_review_generator", SKILL12 / "scripts" / "generate_review.py")

SIGNALS = load(RUN / "artifacts" / "signals.json")
BUNDLE = load(RUN / "artifacts" / "approved_opportunity_threat_bundle.json")
MAPPING = load(RUN / "artifacts" / "product_mapping.json")
GAP = load(RUN / "artifacts" / "product_gap.json")
ACTIONS = load(RUN / "artifacts" / "actions.json")
GATE2 = load(RUN / "reviews" / "02-opportunity-threat-decision.json")
GATE3 = load(RUN / "reviews" / "03-product-action-decision.json")
PENDING_GATE3 = {
    "review_gate": "product-action-hitl",
    "run_id": ACTIONS["run_id"],
    "overall_status": "PENDING",
    "reviewed_action_ids": [],
    "approved_action_ids": [],
    "rejected_action_ids": [],
    "revision_action_ids": [],
    "deferred_action_ids": [],
    "reviewer": None,
    "reviewed_at": None,
    "reviewer_summary": None,
    "synthetic": True,
}
ACTION_SCHEMA = load(SKILL11 / "schemas" / "output.schema.json")
GATE3_SCHEMA = load(SKILL12 / "schemas" / "review-decision.schema.json")
CONTEXT = load(RUN / "intermediate" / "action_context.json")
DRAFT = load(RUN / "intermediate" / "actions_draft.json")


def validate_action(artifact):
    return ACTION_VALIDATOR.validate_artifact(
        artifact, ACTION_SCHEMA, SIGNALS, BUNDLE, MAPPING, GAP, GATE2
    )


def validate_gate3(decision):
    return GATE3_VALIDATOR.validate_decision(decision, GATE3_SCHEMA, ACTIONS)
