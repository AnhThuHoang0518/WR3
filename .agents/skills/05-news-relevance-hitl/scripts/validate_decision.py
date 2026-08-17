#!/usr/bin/env python3
"""Validate Gate 1 decision schema, set semantics and continuation status."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

VALIDATORS = Path(__file__).resolve().parents[2] / "00-news-driven-mi-orchestrator" / "scripts" / "validators"
sys.path.insert(0, str(VALIDATORS))
from validate_gate_status import evaluate_gate  # noqa: E402
from validate_hitl_sets import validate_hitl_sets  # noqa: E402
from validate_json_schema import load_json, validate_instance  # noqa: E402


def validate_decision(
    decision: dict[str, Any], schema: dict[str, Any], artifacts: list[dict[str, Any]]
) -> dict[str, Any]:
    """Return one complete Gate 1 validation report."""
    errors: list[dict[str, Any]] = [
        {"code": "SCHEMA_ERROR", **error} for error in validate_instance(decision, schema)
    ]
    all_ids: list[str] = []
    run_ids: set[str] = set()
    for artifact in artifacts:
        run_ids.add(str(artifact.get("run_id")))
        all_ids.extend(str(item.get("news_id")) for item in artifact.get("items", []))
    duplicate_source_ids = sorted({value for value in all_ids if all_ids.count(value) > 1})
    if duplicate_source_ids:
        errors.append({"code": "DUPLICATE_SOURCE_ID", "ids": duplicate_source_ids})
    if len(run_ids) != 1 or decision.get("run_id") not in run_ids:
        errors.append({"code": "RUN_ID_MISMATCH", "artifact_run_ids": sorted(run_ids)})
    if any(artifact.get("synthetic") is not decision.get("synthetic") for artifact in artifacts):
        errors.append({"code": "SYNTHETIC_MISMATCH"})

    sets_report = validate_hitl_sets(
        decision,
        "reviewed_news_ids",
        ["kept_news_ids", "excluded_news_ids", "revision_news_ids"],
        set(all_ids),
        "kept_news_ids",
    )
    errors.extend(sets_report["errors"])
    status = decision.get("overall_status")
    reviewed = set(decision.get("reviewed_news_ids", []))
    revisions = decision.get("revision_news_ids", [])
    kept = decision.get("kept_news_ids", [])
    metadata_present = bool(decision.get("reviewer") and decision.get("reviewed_at"))
    if status != "PENDING" and not metadata_present:
        errors.append({"code": "REVIEWER_METADATA_REQUIRED"})
    if len(reviewed) < len(set(all_ids)) and status != "PENDING":
        errors.append({"code": "INCOMPLETE_REVIEW_MUST_BE_PENDING"})
    if revisions and status != "CHANGES_REQUIRED":
        errors.append({"code": "REVISION_REQUIRES_CHANGES_REQUIRED"})
    if status == "CHANGES_REQUIRED" and not revisions:
        errors.append({"code": "CHANGES_REQUIRED_NEEDS_REVISION_ID"})
    if status == "APPROVED":
        if reviewed != set(all_ids):
            errors.append({"code": "APPROVED_REQUIRES_COMPLETE_REVIEW"})
        if revisions:
            errors.append({"code": "APPROVED_FORBIDS_REVISION"})
        if not kept:
            errors.append({"code": "APPROVED_REQUIRES_KEPT_ITEM"})
    if status == "REJECTED":
        if kept and not decision.get("reviewer_summary"):
            errors.append({"code": "REJECTED_WITH_KEPT_REQUIRES_STOP_REASON"})
        if not decision.get("reviewer_summary"):
            errors.append({"code": "REJECTED_REQUIRES_SUMMARY"})

    semantic_pass = not errors
    gate = evaluate_gate(decision, semantic_pass)
    return {
        "status": "PASS" if semantic_pass else "FAIL",
        "schema_status": "PASS" if not any(error["code"] == "SCHEMA_ERROR" for error in errors) else "FAIL",
        "semantic_status": "PASS" if semantic_pass else "FAIL",
        "source_item_count": len(set(all_ids)),
        "reviewed_item_count": len(reviewed),
        "set_validation": sets_report,
        **gate,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--market", required=True, type=Path)
    parser.add_argument("--competitor", required=True, type=Path)
    parser.add_argument("--technology", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        artifacts = [load_json(path) for path in [args.market, args.competitor, args.technology, args.policy]]
        result = validate_decision(load_json(args.decision), load_json(args.schema), artifacts)
    except (OSError, ValueError, TypeError) as exc:
        result = {
            "status": "FAIL", "schema_status": "FAIL", "semantic_status": "FAIL",
            "gate_status": "UNKNOWN", "pipeline_can_continue": False,
            "blocking_reasons": ["VALIDATION_INPUT_ERROR"],
            "errors": [{"code": "INPUT_ERROR", "message": str(exc)}],
        }
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
