"""Read-only reusable fixtures for vertical slice 2 unit tests."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".agents" / "skills"
RUN = ROOT / "workspace" / "runs" / "20260809-122107-synthetic"
VALIDATORS = SKILLS / "00-news-driven-mi-orchestrator" / "scripts" / "validators"
sys.path.insert(0, str(VALIDATORS))


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


BUNDLE_BUILDER = module("vs2_bundle_builder", SKILLS / "06-signal-synthesis" / "scripts" / "build_approved_news_bundle.py")
SIGNAL_BUILDER = module("vs2_signal_builder", SKILLS / "06-signal-synthesis" / "scripts" / "build_artifact.py")
SIGNAL_VALIDATOR = module("vs2_signal_validator", SKILLS / "06-signal-synthesis" / "scripts" / "validate_artifact.py")
OT_BUILDER = module("vs2_ot_builder", SKILLS / "07-opportunity-threat" / "scripts" / "build_artifact.py")
OT_VALIDATOR = module("vs2_ot_validator", SKILLS / "07-opportunity-threat" / "scripts" / "validate_artifact.py")
GATE2_REVIEW = module("vs2_gate2_review", SKILLS / "08-opportunity-threat-hitl" / "scripts" / "generate_review.py")
GATE2_BUILDER = module("vs2_gate2_builder", SKILLS / "08-opportunity-threat-hitl" / "scripts" / "build_decision_manifest.py")
GATE2_VALIDATOR = module("vs2_gate2_validator", SKILLS / "08-opportunity-threat-hitl" / "scripts" / "validate_decision.py")

DECISION = load(RUN / "reviews" / "01-news-relevance-decision.json")
NEWS_PATHS = [
    RUN / "artifacts" / "market_news.json",
    RUN / "artifacts" / "competitor_news.json",
    RUN / "artifacts" / "technology_news.json",
    RUN / "artifacts" / "policy_news.json",
]
NEWS_ARTIFACTS = [load(path) for path in NEWS_PATHS]
CORRECTIONS = BUNDLE_BUILDER.parse_corrected_types(RUN / "reviews" / "01-news-relevance-review.md")
BUNDLE = BUNDLE_BUILDER.build_bundle(DECISION, NEWS_ARTIFACTS, str(RUN / "reviews" / "01-news-relevance-decision.json"), CORRECTIONS)
SIGNALS = SIGNAL_BUILDER.build_signals(BUNDLE)
OT = OT_BUILDER.build_opportunity_threat(SIGNALS, BUNDLE)
SIGNAL_SCHEMA = load(SKILLS / "06-signal-synthesis" / "schemas" / "output.schema.json")
OT_SCHEMA = load(SKILLS / "07-opportunity-threat" / "schemas" / "output.schema.json")
GATE2_SCHEMA = load(SKILLS / "08-opportunity-threat-hitl" / "schemas" / "review-decision.schema.json")
