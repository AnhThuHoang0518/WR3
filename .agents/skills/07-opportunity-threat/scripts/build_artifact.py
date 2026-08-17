#!/usr/bin/env python3
"""Derive specific Opportunity/Threat mechanisms from validated Signals."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

THEME_RULES = [
    {
        "keywords": ["procurement", "integrated urban", "operating controls"],
        "opportunity": {
            "statement": "Synthetic municipal buyers and integrators can define integrated pilot scopes that include operating-control requirements from the start.",
            "stakeholders": ["Municipal buyers", "Urban operations integrators"],
            "mechanism": "Jointly specifying integration and controls during pilot procurement can reduce late-stage scope reconciliation.",
            "importance": "HIGH",
            "rationale": "The parent Signal combines integrated operations demand with an explicit control requirement.",
            "assumptions": ["Synthetic pilot requirements remain in scope during procurement design."],
            "gaps": ["No synthetic award, budget, or production deployment evidence is available."],
        },
        "threat": {
            "statement": "Providers that cannot demonstrate integrated operations and required controls may be screened out of synthetic urban pilots.",
            "stakeholders": ["Urban technology providers", "Implementation partners"],
            "mechanism": "Combined functional and control requirements raise the evidence threshold for pilot qualification.",
            "importance": "MEDIUM",
            "rationale": "The parent Signal indicates that capability and operating controls may be assessed together.",
            "assumptions": ["Synthetic control requirements are applied during supplier evaluation."],
            "gaps": ["Supplier evaluation criteria and enforcement details are not stated."],
        },
    },
    {
        "keywords": ["recurring", "subscription", "service models"],
        "opportunity": {
            "statement": "Synthetic project operators can test recurring Smart City service models alongside technical pilots.",
            "stakeholders": ["Project operators", "Municipal service buyers"],
            "mechanism": "A phased trial can connect service usage with fee or subscription validation before broader adoption.",
            "importance": "MEDIUM",
            "rationale": "The parent Signal identifies recurring commercial proposals in multiple synthetic trials.",
            "assumptions": ["Trial participants are allowed to evaluate recurring commercial terms."],
            "gaps": ["Willingness to pay, renewal, and adoption evidence are unavailable."],
        },
        "threat": {
            "statement": "Recurring fees may fail to gain synthetic buyer acceptance when adoption and renewal remain unproven.",
            "stakeholders": ["Project operators", "Service subscribers"],
            "mechanism": "A recurring charge without demonstrated ongoing value can limit conversion after a pilot.",
            "importance": "MEDIUM",
            "rationale": "The parent Signal explicitly notes recurring proposals before adoption is proven.",
            "assumptions": ["Buyers compare recurring fees with observed pilot value."],
            "gaps": ["No pricing, usage, conversion, or renewal data is supplied."],
        },
    },
    {
        "keywords": ["edge urban", "prototype", "sandbox"],
        "opportunity": {
            "statement": "Synthetic city operators and technology integrators can use constrained sandboxes to validate edge analytics before production procurement.",
            "stakeholders": ["City operators", "Technology integrators"],
            "mechanism": "Limited environments can test capability, integration, and readiness while containing deployment risk.",
            "importance": "MEDIUM",
            "rationale": "The parent Signal shows related capabilities progressing through prototype and sandbox stages.",
            "assumptions": ["Sandbox conditions can represent relevant operating constraints."],
            "gaps": ["Production reliability, scale, and commercial readiness are not demonstrated."],
        },
        "threat": {
            "statement": "Treating synthetic edge prototypes as production-ready could create performance and integration failures.",
            "stakeholders": ["City operators", "Procurement teams", "Technology providers"],
            "mechanism": "Premature scaling bypasses evidence needed for reliability, integration, and operational support.",
            "importance": "HIGH",
            "rationale": "The parent Signal explicitly lacks commercial deployment proof.",
            "assumptions": ["Stakeholders may extrapolate sandbox results to production use."],
            "gaps": ["No production-scale test or operational service evidence is available."],
        },
    },
    {
        "keywords": ["interoperability", "data-sharing", "data sharing", "draft governance"],
        "opportunity": {
            "statement": "Synthetic authorities and platform teams can prepare interoperable municipal data interfaces while governance remains in draft.",
            "stakeholders": ["Municipal authorities", "Platform architects", "Data governance teams"],
            "mechanism": "Early interface and governance design can reduce later adaptation when draft expectations mature.",
            "importance": "MEDIUM",
            "rationale": "The parent Signal links technical interoperability with emerging draft guidance.",
            "assumptions": ["Draft direction remains relevant to future requirements."],
            "gaps": ["Final scope, compliance dates, and enforcement are not available."],
        },
        "threat": {
            "statement": "Synthetic platform implementations may require rework if draft interoperability and data-sharing expectations change.",
            "stakeholders": ["Platform implementers", "Municipal data owners"],
            "mechanism": "Interfaces designed before requirements stabilize can diverge from final governance expectations.",
            "importance": "MEDIUM",
            "rationale": "The parent Signal is based on consultation and draft evidence rather than issued requirements.",
            "assumptions": ["Implementation begins before governance is finalized."],
            "gaps": ["Final wording and implementation guidance are unknown."],
        },
    },
]


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load JSON {path}: {exc}") from exc


def _rule_for(signal: dict[str, Any]) -> dict[str, Any] | None:
    text = " ".join([signal.get("signal_title", ""), signal.get("signal_statement", ""), signal.get("what_changed", "")]).casefold()
    return next((rule for rule in THEME_RULES if any(keyword in text for keyword in rule["keywords"])), None)


def build_opportunity_threat(signals: dict[str, Any], approved_news: dict[str, Any]) -> dict[str, Any]:
    """Create O/T only for Signals with a supported reusable impact mechanism."""
    approved_ids = {item["news_id"] for item in approved_news.get("approved_news", [])}
    if signals.get("run_id") != approved_news.get("run_id"):
        raise ValueError("Signal and approved News run_id mismatch")
    items: list[dict[str, Any]] = []
    for signal in signals.get("items", []):
        if not set(signal.get("evidence_news_ids", [])).issubset(approved_ids):
            raise ValueError(f"Signal {signal.get('signal_id')} contains non-approved evidence")
        rule = _rule_for(signal)
        if rule is None:
            continue
        for ot_type, key in [("OPPORTUNITY", "opportunity"), ("THREAT", "threat")]:
            definition = rule[key]
            items.append({
                "ot_id": f"OT-{len(items) + 1:03d}",
                "signal_id": signal["signal_id"],
                "type": ot_type,
                "statement": definition["statement"],
                "impacted_stakeholders": definition["stakeholders"],
                "impact_mechanism": definition["mechanism"],
                "importance": definition["importance"],
                "rationale": definition["rationale"],
                "assumptions": definition["assumptions"],
                "evidence_gaps": definition["gaps"],
            })
    return {"artifact_type": "opportunity_threat", "run_id": signals["run_id"], "synthetic": signals["synthetic"], "items": items}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--signals", required=True, type=Path)
    parser.add_argument("--approved-news", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        artifact = build_opportunity_threat(load_json(args.signals), load_json(args.approved_news))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        opportunity_count = sum(item["type"] == "OPPORTUNITY" for item in artifact["items"])
        threat_count = sum(item["type"] == "THREAT" for item in artifact["items"])
        print(json.dumps({"status": "PASS", "output": str(args.output), "opportunity_count": opportunity_count, "threat_count": threat_count}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
