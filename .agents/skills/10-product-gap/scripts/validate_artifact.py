#!/usr/bin/env python3
"""Validate Product Gap schema, lineage, status semantics, evidence and stage boundaries."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
VALIDATORS = Path(__file__).resolve().parents[2] / "00-news-driven-mi-orchestrator" / "scripts" / "validators"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(VALIDATORS))
from validate_json_schema import load_json, validate_instance  # noqa: E402
from validate_portfolio_evidence import validate_portfolio_evidence  # noqa: E402
from validate_stage_lineage import validate_product_gap_lineage  # noqa: E402

FORBIDDEN_FIELDS = {
    "recommended_response", "proposed_action", "build_buy_partner", "pilot_or_productize",
    "owner", "priority", "next_step",
}
CATEGORY_MARKERS = {
    "EXACT_CATEGORY", "ADJACENT_CATEGORY", "NO_CATEGORY_MATCH", "UNCERTAIN_CATEGORY",
}


def _find_forbidden(value: Any, path: str = "$") -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_FIELDS:
                findings.append({"code": "FORBIDDEN_ACTION_FIELD", "path": f"{path}.{key}"})
            findings.extend(_find_forbidden(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_find_forbidden(child, f"{path}[{index}]"))
    return findings


def _status_errors(item: dict[str, Any]) -> list[dict[str, Any]]:
    gap_id = item.get("gap_id")
    status = item.get("capability_status")
    matched = item.get("matched_vsf_product")
    current = item.get("current_vsf_capabilities", [])
    missing = item.get("missing_capabilities", [])
    refs = item.get("portfolio_evidence_refs", [])
    validation = item.get("validation_needed", [])
    rationale = str(item.get("comparison_rationale", ""))
    errors: list[dict[str, Any]] = []
    markers = sorted(marker for marker in CATEGORY_MARKERS if marker in rationale)
    if len(markers) != 1:
        errors.append({"code": "CATEGORY_MATCH_RATIONALE_INVALID", "gap_id": gap_id, "markers": markers})
    required = item.get("required_capabilities", [])
    unexpected_missing = [capability for capability in missing if capability not in required]
    if unexpected_missing:
        errors.append({
            "code": "MISSING_CAPABILITY_NOT_IN_REQUIREMENT", "gap_id": gap_id,
            "capabilities": unexpected_missing,
        })
    if status == "FULL_MATCH":
        if matched is None or not current or missing or not refs:
            errors.append({"code": "INVALID_FULL_MATCH", "gap_id": gap_id})
        if markers and markers[0] not in {"EXACT_CATEGORY", "ADJACENT_CATEGORY"}:
            errors.append({"code": "FULL_MATCH_CATEGORY_INCONSISTENT", "gap_id": gap_id})
    elif status == "PARTIAL_MATCH":
        if matched is None or not current or not missing or not refs:
            errors.append({"code": "INVALID_PARTIAL_MATCH", "gap_id": gap_id})
        if markers and markers[0] not in {"EXACT_CATEGORY", "ADJACENT_CATEGORY"}:
            errors.append({"code": "PARTIAL_MATCH_CATEGORY_INCONSISTENT", "gap_id": gap_id})
    elif status == "NO_MATCH":
        if matched is not None or current or "NO_CATEGORY_MATCH" not in rationale:
            errors.append({"code": "INVALID_NO_MATCH", "gap_id": gap_id})
    elif status == "UNKNOWN":
        if current or not validation:
            errors.append({"code": "INVALID_UNKNOWN", "gap_id": gap_id})
        if missing:
            errors.append({"code": "UNKNOWN_WITH_CONFIRMED_MISSING_CLAIM", "gap_id": gap_id})
        if not ({"UNCERTAIN_CATEGORY", "ADJACENT_CATEGORY"} & set(markers)):
            errors.append({"code": "UNKNOWN_CATEGORY_RATIONALE_INCONSISTENT", "gap_id": gap_id})
    return errors


def validate_artifact(
    artifact: dict[str, Any],
    schema: dict[str, Any],
    product_mapping: dict[str, Any],
    catalog: dict[str, Any],
    signals: dict[str, Any],
    approved_bundle: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    """Return machine errors separately from catalog-quality warnings."""
    schema_errors = validate_instance(artifact, schema)
    errors: list[dict[str, Any]] = [{"code": "SCHEMA_ERROR", **item} for item in schema_errors]
    lineage = validate_product_gap_lineage(
        artifact, product_mapping, signals, approved_bundle, decision
    )
    errors.extend(lineage["errors"])
    boundary_errors = _find_forbidden(artifact)
    errors.extend(boundary_errors)
    for item in artifact.get("items", []):
        if not re.fullmatch(r"GAP-\d{3}", str(item.get("gap_id"))):
            errors.append({"code": "INVALID_GAP_ID", "gap_id": item.get("gap_id")})
        errors.extend(_status_errors(item))
    evidence = validate_portfolio_evidence(catalog, artifact)
    errors.extend({key: value for key, value in item.items() if key != "severity"} for item in evidence["errors"])
    warnings = [{key: value for key, value in item.items() if key != "severity"} for item in evidence["warnings"]]
    return {
        "status": "PASS" if not errors else "FAIL",
        "schema_status": "PASS" if not schema_errors else "FAIL",
        "lineage_status": lineage["status"],
        "capability_status_rules": "PASS" if not any(
            error.get("code", "").startswith(("INVALID_", "UNKNOWN_", "FULL_MATCH_", "PARTIAL_MATCH_", "MISSING_", "CATEGORY_"))
            for error in errors
        ) else "FAIL",
        "boundary_status": "PASS" if not boundary_errors else "FAIL",
        "portfolio_evidence_status": evidence["status"],
        "product_gap_count": len(artifact.get("items", [])),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--product-mapping", required=True, type=Path)
    parser.add_argument("--products", required=True, type=Path)
    parser.add_argument("--signals", required=True, type=Path)
    parser.add_argument("--approved-ot-bundle", required=True, type=Path)
    parser.add_argument("--decision", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        result = validate_artifact(
            load_json(args.artifact), load_json(args.schema), load_json(args.product_mapping),
            load_json(args.products), load_json(args.signals), load_json(args.approved_ot_bundle),
            load_json(args.decision),
        )
    except (OSError, ValueError, TypeError) as exc:
        result = {
            "status": "FAIL", "schema_status": "FAIL", "lineage_status": "FAIL",
            "capability_status_rules": "FAIL", "boundary_status": "FAIL",
            "portfolio_evidence_status": "FAIL", "error_count": 1, "warning_count": 0,
            "errors": [{"code": "INPUT_ERROR", "message": str(exc)}], "warnings": [],
        }
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

