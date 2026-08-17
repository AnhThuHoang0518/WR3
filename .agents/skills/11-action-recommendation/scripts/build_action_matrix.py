#!/usr/bin/env python3
"""Build generic candidate Action analysis from approved O/T, Mapping and reviewed Gaps."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    """Load one UTF-8 JSON object."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def _candidate_response(gap: dict[str, Any]) -> str:
    status = gap.get("capability_status")
    return {"UNKNOWN": "VALIDATE", "NO_MATCH": "VALIDATE", "PARTIAL_MATCH": "PREPARE", "FULL_MATCH": "ACT"}.get(status, "MONITOR")


def _evidence_strength(gap: dict[str, Any]) -> str:
    return {"UNKNOWN": "LOW", "NO_MATCH": "MEDIUM", "PARTIAL_MATCH": "MEDIUM", "FULL_MATCH": "HIGH"}.get(gap.get("capability_status"), "LOW")


def _urgency(ots: list[dict[str, Any]], gap: dict[str, Any]) -> str:
    levels = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3, "UNKNOWN": 0}
    score = max([levels.get(str(item.get("importance")), 0) for item in ots] + [levels.get(str(gap.get("gap_severity")), 0)])
    return ["LOW", "MEDIUM", "HIGH", "CRITICAL"][score]


def build_matrix(context: dict[str, Any]) -> dict[str, Any]:
    """Create one non-final candidate per reviewed gap without forcing final coverage."""
    mappings = {item.get("product_mapping_id"): item for item in context.get("product_mappings", [])}
    ots = {item.get("ot_id"): item for item in context.get("approved_opportunity_threat", [])}
    items: list[dict[str, Any]] = []
    for gap in context.get("product_gaps", []):
        mapping = mappings.get(gap.get("product_mapping_id"))
        if mapping is None:
            raise ValueError(f"Unknown mapping for gap {gap.get('gap_id')}")
        related = [ots[ot_id] for ot_id in mapping.get("related_ot_ids", []) if ot_id in ots]
        opportunity = [item.get("statement") for item in related if item.get("type") == "OPPORTUNITY"]
        threat = [item.get("statement") for item in related if item.get("type") == "THREAT"]
        status = gap.get("capability_status")
        candidate_pilot = "UNDECIDED" if status == "UNKNOWN" else ("PRODUCTIZE" if status == "FULL_MATCH" else "PILOT")
        items.append({
            "source_signal_id": gap.get("signal_id"),
            "related_ot_ids": list(mapping.get("related_ot_ids", [])),
            "product_mapping_id": mapping.get("product_mapping_id"),
            "gap_ids": [gap.get("gap_id")],
            "opportunity_to_capture": opportunity,
            "threat_to_mitigate": threat,
            "market_requirement": mapping.get("market_problem"),
            "gap_summary": {
                "capability_status": status,
                "gap_type": gap.get("gap_type"),
                "gap_severity": gap.get("gap_severity"),
                "missing_capabilities": gap.get("missing_capabilities", []),
            },
            "evidence_strength": _evidence_strength(gap),
            "urgency": _urgency(related, gap),
            "feasibility": "UNCERTAIN" if status in {"UNKNOWN", "NO_MATCH"} else "PARTIALLY_SUPPORTED",
            "candidate_response": _candidate_response(gap),
            "candidate_build_buy_partner": "UNDECIDED",
            "candidate_pilot_or_productize": candidate_pilot,
            "validation_questions": [*gap.get("validation_needed", []), *[question for item in related for question in item.get("evidence_gaps", [])]],
            "action_dependencies": [
                "Retain Product Mapping and Product Gap lineage.",
                "Obtain explicit Gate 3 human decision before treating any action as final.",
            ],
            "unresolved_questions": [
                "What pass/fail threshold should govern escalation to ACT or Productize?",
            ],
        })
    return {"run_id": context.get("run_id"), "synthetic": context.get("synthetic"), "items": items}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        if args.output.exists() and not args.overwrite:
            raise ValueError(f"Refusing to overwrite action matrix: {args.output}")
        matrix = build_matrix(load_json(args.context))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "PASS", "output": str(args.output), "candidate_count": len(matrix["items"])}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
