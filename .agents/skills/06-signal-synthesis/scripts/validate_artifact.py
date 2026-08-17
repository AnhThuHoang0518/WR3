#!/usr/bin/env python3
"""Validate Signal schema, lineage, live/synthetic separation and summary evidence."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

VALIDATORS = Path(__file__).resolve().parents[2] / "00-news-driven-mi-orchestrator" / "scripts" / "validators"
sys.path.insert(0, str(VALIDATORS))
from validate_json_schema import load_json, validate_instance  # noqa: E402
from validate_stage_lineage import validate_signal_lineage  # noqa: E402

ID_PATTERN = re.compile(r"^SIGNAL-[0-9]{3}$")
REVIEW_TEXT_FIELDS = (
    "signal_title", "signal_statement", "what_changed", "from_state",
    "to_state", "why_it_matters", "evidence_summary",
)


def validate_artifact(
    signals: dict[str, Any], schema: dict[str, Any], bundle: dict[str, Any], decision: dict[str, Any]
) -> dict[str, Any]:
    schema_errors = validate_instance(signals, schema)
    errors: list[dict[str, Any]] = [{"code": "SCHEMA_ERROR", **error} for error in schema_errors]
    for item in signals.get("items", []):
        if not isinstance(item.get("signal_id"), str) or ID_PATTERN.fullmatch(item["signal_id"]) is None:
            errors.append({"code": "INVALID_SIGNAL_ID", "signal_id": item.get("signal_id")})
    lineage = validate_signal_lineage(signals, bundle, set(decision.get("excluded_news_ids", [])))
    errors.extend(lineage["errors"])
    semantic_errors: list[dict[str, Any]] = []
    if signals.get("synthetic") is not bundle.get("synthetic"):
        semantic_errors.append({
            "code": "SYNTHETIC_FLAG_MISMATCH",
            "message": "Signal synthetic flag must match the approved News bundle",
        })
    if signals.get("synthetic") is False:
        evidence_by_id = {item["news_id"]: item for item in bundle.get("approved_news", [])}
        for signal in signals.get("items", []):
            rendered = " ".join(str(signal.get(field, "")) for field in REVIEW_TEXT_FIELDS).casefold()
            if "synthetic" in rendered:
                semantic_errors.append({
                    "code": "SYNTHETIC_CONTENT_IN_LIVE_SIGNAL",
                    "signal_id": signal.get("signal_id"),
                })
            missing_summary_ids = [
                news_id for news_id in signal.get("evidence_news_ids", [])
                if not str(evidence_by_id.get(news_id, {}).get("summary", "")).strip()
            ]
            if missing_summary_ids:
                semantic_errors.append({
                    "code": "MISSING_SUMMARY_EVIDENCE",
                    "signal_id": signal.get("signal_id"),
                    "evidence_news_ids": missing_summary_ids,
                })
    errors.extend(semantic_errors)
    return {
        "status": "PASS" if not errors else "FAIL",
        "schema_status": "PASS" if not schema_errors else "FAIL",
        "lineage_status": lineage["status"],
        "semantic_status": "PASS" if not semantic_errors else "FAIL",
        "signal_count": len(signals.get("items", [])),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--approved-news", required=True, type=Path)
    parser.add_argument("--decision", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        result = validate_artifact(load_json(args.artifact), load_json(args.schema), load_json(args.approved_news), load_json(args.decision))
    except (OSError, ValueError, TypeError) as exc:
        result = {"status": "FAIL", "schema_status": "FAIL", "lineage_status": "FAIL", "errors": [{"code": "INPUT_ERROR", "message": str(exc)}]}
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
