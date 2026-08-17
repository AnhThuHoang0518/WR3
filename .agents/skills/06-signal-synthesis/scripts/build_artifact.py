#!/usr/bin/env python3
"""Synthesize deterministic change-mechanism Signals from an approved News bundle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


TYPE_ORDER = {"MARKET": 0, "COMPETITOR": 1, "TECHNOLOGY": 2, "POLICY": 3}
TOPIC_RULES = [
    {
        "keywords": ["procurement", "integrated urban operations", "incident-log", "incident log"],
        "title": "Integrated urban pilots are acquiring explicit operating controls",
        "statement": "Synthetic urban pilot demand is shifting toward integrated operating scope combined with explicit control requirements.",
        "what_changed": "Pilot evidence now combines integrated monitoring scope with stated operational-control requirements.",
        "from_state": "Synthetic pilots described isolated capabilities or general monitoring needs.",
        "to_state": "Synthetic procurement evidence describes integrated operations scope and explicit control obligations.",
        "why": "Buyers and implementers would need to evaluate integration and operating compliance together during pilot design.",
        "maturity": "DEVELOPING",
    },
    {
        "keywords": ["subscription", "service-fee", "service fee", "recurring"],
        "title": "Recurring service models are entering Smart City trials",
        "statement": "Synthetic Smart City projects are testing recurring fee and subscription proposals before adoption is proven.",
        "what_changed": "Commercial proposals now include recurring service fees or subscriptions in phased trials.",
        "from_state": "Synthetic project value was framed mainly around a pilot or installation.",
        "to_state": "Synthetic project operators are testing recurring service models alongside the pilot capability.",
        "why": "Commercial viability depends on validating willingness to pay and renewal, not only technical delivery.",
        "maturity": "EMERGING",
    },
    {
        "keywords": ["prototype", "sandbox", "edge-processing", "edge processing", "edge-aggregation", "sensor sandbox"],
        "title": "Edge urban analytics are progressing through non-commercial validation",
        "statement": "Synthetic edge and sensor capabilities are moving from laboratory concepts into limited sandbox validation without commercial deployment proof.",
        "what_changed": "Multiple synthetic items describe edge analytics or sensors at prototype and sandbox stages.",
        "from_state": "Capabilities were described as concepts or laboratory prototypes.",
        "to_state": "Capabilities are being framed for constrained sandbox validation while remaining non-commercial.",
        "why": "The change creates a clearer validation path but does not yet establish production readiness.",
        "maturity": "EMERGING",
    },
    {
        "keywords": ["interoperability", "data-sharing", "data sharing", "municipal data"],
        "title": "Municipal interoperability is moving into draft governance",
        "statement": "Synthetic municipal data interoperability is shifting from a technical concern toward draft clauses and data-sharing guidance.",
        "what_changed": "Interoperability and data sharing appear in synthetic draft consultation and guidance evidence.",
        "from_state": "Municipal interfaces and data sharing lacked a stated governance direction.",
        "to_state": "Synthetic authorities are consulting on draft interoperability and data-sharing expectations.",
        "why": "Technical interface choices may need to anticipate evolving governance requirements before they are final.",
        "maturity": "EMERGING",
    },
]


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load JSON {path}: {exc}") from exc


def _searchable(item: dict[str, Any]) -> str:
    """Return evidence content only; crawler query/provenance fields must never trigger a Signal."""
    return " ".join([
        str(item.get("title", "")), str(item.get("summary", "")),
    ]).casefold()


def _confidence(items: list[dict[str, Any]]) -> str:
    rank = {"UNKNOWN": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
    qualities = [rank.get(item.get("evidence_quality", "UNKNOWN"), 0) for item in items]
    if not qualities:
        return "UNKNOWN"
    weakest = min(qualities)
    return ["UNKNOWN", "LOW", "MEDIUM", "HIGH"][weakest]


def build_signals(bundle: dict[str, Any]) -> dict[str, Any]:
    """Apply frozen synthetic fixture rules; live Signals must be authored by the chat LLM."""
    if bundle.get("approval_status") != "APPROVED":
        raise ValueError("Approved News bundle must have approval_status APPROVED")
    if bundle.get("synthetic") is not True:
        raise ValueError(
            "Live Signal Synthesis must be authored by the current chat LLM; this script is synthetic-only"
        )
    approved = bundle.get("approved_news", [])
    signals: list[dict[str, Any]] = []
    for rule in TOPIC_RULES:
        evidence = [item for item in approved if any(keyword in _searchable(item) for keyword in rule["keywords"])]
        if not evidence:
            continue
        evidence_ids = [item["news_id"] for item in evidence]
        evidence_types = sorted({item["news_type"] for item in evidence}, key=lambda value: TYPE_ORDER[value])
        evidence_summary = " ".join(f"{item['news_id']}: {item['summary']}" for item in evidence)
        signals.append({
            "signal_id": f"SIGNAL-{len(signals) + 1:03d}",
            "signal_title": rule["title"],
            "signal_statement": rule["statement"],
            "what_changed": rule["what_changed"],
            "from_state": rule["from_state"],
            "to_state": rule["to_state"],
            "why_it_matters": rule["why"],
            "evidence_news_ids": evidence_ids,
            "evidence_types": evidence_types,
            "evidence_summary": evidence_summary,
            "signal_maturity": rule["maturity"],
            "evidence_confidence": _confidence(evidence),
        })
    return {"artifact_type": "signals", "run_id": bundle["run_id"], "synthetic": bundle["synthetic"], "items": signals}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-news", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        artifact = build_signals(load_json(args.approved_news))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "PASS", "output": str(args.output), "signal_count": len(artifact["items"])}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
