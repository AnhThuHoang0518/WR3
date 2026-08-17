#!/usr/bin/env python3
"""Validate Gate 3 decision schema, set semantics and continuation status."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

VALIDATORS = Path(__file__).resolve().parents[2] / "00-news-driven-mi-orchestrator" / "scripts" / "validators"
sys.path.insert(0, str(VALIDATORS))
from validate_gate_status import evaluate_gate  # noqa: E402
from validate_json_schema import load_json, validate_instance  # noqa: E402
from validate_stage_lineage import validate_gate3_lineage  # noqa: E402


def validate_decision(decision: dict[str, Any], schema: dict[str, Any], actions: dict[str, Any]) -> dict[str, Any]:
    """Return schema, semantic, set and gate validation without changing the decision."""
    schema_errors = validate_instance(decision, schema)
    errors: list[dict[str, Any]] = [{"code": "SCHEMA_ERROR", **error} for error in schema_errors]
    sets_report = validate_gate3_lineage(decision, actions)
    errors.extend(sets_report.get("errors", []))
    all_ids = {item.get("action_id") for item in actions.get("items", []) if isinstance(item, dict)}
    reviewed = set(decision.get("reviewed_action_ids", []))
    approved = decision.get("approved_action_ids", [])
    revisions = decision.get("revision_action_ids", [])
    status = decision.get("overall_status")
    if status != "PENDING" and not (decision.get("reviewer") and decision.get("reviewed_at")):
        errors.append({"code": "REVIEWER_METADATA_REQUIRED"})
    if reviewed != all_ids and status != "PENDING":
        errors.append({"code": "INCOMPLETE_REVIEW_MUST_BE_PENDING"})
    if revisions and status != "CHANGES_REQUIRED":
        errors.append({"code": "REVISION_REQUIRES_CHANGES_REQUIRED"})
    if status == "CHANGES_REQUIRED" and not revisions:
        errors.append({"code": "CHANGES_REQUIRED_NEEDS_REVISION_ID"})
    if status == "APPROVED":
        if reviewed != all_ids:
            errors.append({"code": "APPROVED_REQUIRES_COMPLETE_REVIEW"})
        if revisions:
            errors.append({"code": "APPROVED_FORBIDS_REVISION"})
        if not approved:
            errors.append({"code": "APPROVED_REQUIRES_APPROVED_ITEM"})
        if not decision.get("reviewer_summary"):
            errors.append({"code": "APPROVED_REQUIRES_SUMMARY"})
    if status == "REJECTED" and not decision.get("reviewer_summary"):
        errors.append({"code": "REJECTED_REQUIRES_SUMMARY"})
    semantic_pass = not errors
    gate = evaluate_gate(decision, semantic_pass)
    return {
        "status": "PASS" if semantic_pass else "FAIL",
        "schema_status": "PASS" if not schema_errors else "FAIL",
        "semantic_status": "PASS" if semantic_pass else "FAIL",
        "source_item_count": len(all_ids),
        "reviewed_item_count": len(reviewed),
        "set_validation": sets_report,
        **gate,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--actions", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        result = validate_decision(load_json(args.decision), load_json(args.schema), load_json(args.actions))
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

