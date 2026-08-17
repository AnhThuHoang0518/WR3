#!/usr/bin/env python3
"""Validate Action schema, full lineage, specificity, evidence boundaries and duplicates."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

VALIDATORS = Path(__file__).resolve().parents[2] / "00-news-driven-mi-orchestrator" / "scripts" / "validators"
sys.path.insert(0, str(VALIDATORS))
from validate_json_schema import load_json, validate_instance  # noqa: E402
from validate_stage_lineage import validate_action_lineage  # noqa: E402

RESPONSES = {"MONITOR", "VALIDATE", "PREPARE", "ACT"}
GENERIC_NEXT_STEPS = {"research more", "nghiên cứu thêm", "monitor the market", "theo dõi thị trường", "follow up", "tìm hiểu thêm"}
FINAL_DECISION_PHRASES = {"final approved action", "already approved", "human approved", "final decision is approved"}


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9à-ỹ]+", " ", value.casefold()).strip()


def validate_artifact(
    artifact: dict[str, Any], schema: dict[str, Any], signals: dict[str, Any],
    approved_bundle: dict[str, Any], product_mapping: dict[str, Any],
    product_gap: dict[str, Any], decision: dict[str, Any],
) -> dict[str, Any]:
    """Return hard errors separately from semantic quality warnings."""
    schema_errors = validate_instance(artifact, schema)
    errors: list[dict[str, Any]] = [{"code": "SCHEMA_ERROR", **item} for item in schema_errors]
    lineage = validate_action_lineage(
        artifact, signals, approved_bundle, product_mapping, product_gap, decision
    )
    errors.extend(lineage["errors"])
    warnings: list[dict[str, Any]] = []
    mappings = {item.get("product_mapping_id"): item for item in product_mapping.get("items", [])}
    gaps = {item.get("gap_id"): item for item in product_gap.get("items", [])}
    duplicate_groups: dict[tuple[str, tuple[str, ...], str], list[str]] = defaultdict(list)
    responses: Counter[str] = Counter()
    priorities: Counter[str] = Counter()
    for action in artifact.get("items", []):
        action_id = action.get("action_id")
        proposed = str(action.get("proposed_action", "")).strip()
        next_step = str(action.get("next_step", "")).strip()
        rationale = str(action.get("rationale", "")).strip()
        response = action.get("recommended_response")
        if not proposed:
            errors.append({"code": "EMPTY_PROPOSED_ACTION", "action_id": action_id})
        if not next_step:
            errors.append({"code": "EMPTY_NEXT_STEP", "action_id": action_id})
        if not action.get("gap_ids"):
            errors.append({"code": "ACTION_WITHOUT_GAP", "action_id": action_id})
        if response not in RESPONSES:
            errors.append({"code": "INVALID_RECOMMENDED_RESPONSE", "action_id": action_id, "value": response})
        combined = " ".join(str(action.get(field, "")) for field in ["proposed_action", "rationale", "next_step", "expected_outcome"]).casefold()
        if any(phrase in combined for phrase in FINAL_DECISION_PHRASES):
            errors.append({"code": "ACTION_CLAIMS_FINAL_APPROVAL", "action_id": action_id})
        allowed_current = {
            capability.casefold() for gap_id in action.get("gap_ids", [])
            for capability in gaps.get(gap_id, {}).get("current_vsf_capabilities", [])
            if isinstance(capability, str)
        }
        explicit_claims = re.findall(r"\[CURRENT_CAPABILITY:\s*([^\]]+)\]", combined, flags=re.IGNORECASE)
        unsupported = [claim.strip() for claim in explicit_claims if claim.strip() not in allowed_current]
        if unsupported:
            errors.append({"code": "UNSUPPORTED_CAPABILITY_CLAIM", "action_id": action_id, "claims": unsupported})
        mapping = mappings.get(action.get("product_mapping_id"), {})
        target = action.get("target_product_or_category")
        if mapping and target != mapping.get("market_product_category"):
            warnings.append({"code": "TARGET_DIFFERS_FROM_MAPPING_CATEGORY", "action_id": action_id})
        normalized_next = _normalize(next_step)
        if not next_step or normalized_next in GENERIC_NEXT_STEPS:
            warnings.append({"code": "GENERIC_NEXT_STEP", "action_id": action_id})
        referenced_gaps = [gaps.get(gap_id, {}) for gap_id in action.get("gap_ids", [])]
        if response == "ACT" and any(gap.get("capability_status") == "UNKNOWN" for gap in referenced_gaps):
            warnings.append({"code": "ACT_WITH_UNKNOWN_GAP", "action_id": action_id})
        if action.get("pilot_or_productize") in {"PRODUCTIZE", "BOTH"} and any(
            gap.get("capability_status") in {"UNKNOWN", "NO_MATCH"} for gap in referenced_gaps
        ):
            warnings.append({"code": "PRODUCTIZE_WITH_UNCLEAR_GAP", "action_id": action_id})
        duplicate_groups[(str(target).casefold(), tuple(sorted(action.get("gap_ids", []))), _normalize(proposed))].append(str(action_id))
        responses[str(response)] += 1
        priorities[str(action.get("priority"))] += 1
    action_count = len(artifact.get("items", []))
    if action_count > 1 and len(responses) == 1:
        warnings.append({"code": "ALL_ACTIONS_SAME_RESPONSE", "response": next(iter(responses))})
    if action_count > 1 and len(priorities) == 1:
        warnings.append({"code": "ALL_ACTIONS_SAME_PRIORITY", "priority": next(iter(priorities))})
    for ids in duplicate_groups.values():
        if len(ids) > 1:
            warnings.append({"code": "DUPLICATE_ACTION_CANDIDATE", "action_ids": ids})
    return {
        "status": "PASS" if not errors else "FAIL",
        "schema_status": "PASS" if not schema_errors else "FAIL",
        "lineage_status": lineage["status"],
        "semantic_status": "PASS" if not errors else "FAIL",
        "quality_status": "PASS" if not warnings else "WARNING",
        "action_count": action_count,
        "error_count": len(errors), "warning_count": len(warnings),
        "errors": errors, "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--signals", required=True, type=Path)
    parser.add_argument("--approved-ot-bundle", required=True, type=Path)
    parser.add_argument("--product-mapping", required=True, type=Path)
    parser.add_argument("--product-gap", required=True, type=Path)
    parser.add_argument("--decision", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        result = validate_artifact(
            load_json(args.artifact), load_json(args.schema), load_json(args.signals),
            load_json(args.approved_ot_bundle), load_json(args.product_mapping),
            load_json(args.product_gap), load_json(args.decision),
        )
    except (OSError, ValueError, TypeError) as exc:
        result = {
            "status": "FAIL", "schema_status": "FAIL", "lineage_status": "FAIL",
            "semantic_status": "FAIL", "quality_status": "UNKNOWN", "error_count": 1,
            "warning_count": 0, "errors": [{"code": "INPUT_ERROR", "message": str(exc)}], "warnings": [],
        }
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
