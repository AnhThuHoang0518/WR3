#!/usr/bin/env python3
"""Validate Product Mapping schema, approved lineage, boundaries and quality."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

VALIDATORS = Path(__file__).resolve().parents[2] / "00-news-driven-mi-orchestrator" / "scripts" / "validators"
sys.path.insert(0, str(VALIDATORS))
from validate_json_schema import load_json, validate_instance  # noqa: E402
from validate_stage_lineage import validate_product_mapping_lineage  # noqa: E402

FORBIDDEN_FIELDS = {
    "matched_vsf_product", "current_vsf_capabilities", "missing_vsf_capabilities",
    "capability_status", "gap_type", "gap_severity", "recommended_response",
    "proposed_action", "build_buy_partner", "pilot_or_productize", "vsf_fit",
    "vsf_fit_score", "vsf_product_match", "portfolio_gap",
}
GENERIC_CAPABILITIES = {"ai", "data", "platform", "easy to use", "modern technology"}


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _find_forbidden(value: Any, path: str = "$") -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_FIELDS:
                findings.append({"code": "FORBIDDEN_DOWNSTREAM_FIELD", "path": f"{path}.{key}"})
            findings.extend(_find_forbidden(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_find_forbidden(child, f"{path}[{index}]"))
    return findings


def validate_artifact(
    artifact: dict[str, Any], schema: dict[str, Any], signals: dict[str, Any],
    bundle: dict[str, Any], decision: dict[str, Any],
) -> dict[str, Any]:
    """Return machine errors separately from semantic quality warnings."""
    schema_errors = validate_instance(artifact, schema)
    errors: list[dict[str, Any]] = [{"code": "SCHEMA_ERROR", **item} for item in schema_errors]
    lineage = validate_product_mapping_lineage(artifact, signals, bundle, decision)
    errors.extend(lineage["errors"])
    errors.extend(_find_forbidden(artifact))
    warnings: list[dict[str, Any]] = []
    signal_by_id = {item.get("signal_id"): item for item in signals.get("items", [])}
    approved_by_id = {item.get("ot_id"): item for item in bundle.get("approved_opportunity_threat", [])}
    duplicate_groups: dict[tuple[str, tuple[str, ...]], list[str]] = defaultdict(list)
    for item in artifact.get("items", []):
        mapping_id = item.get("product_mapping_id")
        if not re.fullmatch(r"PM-\d{3}", str(mapping_id)):
            errors.append({"code": "INVALID_PRODUCT_MAPPING_ID", "product_mapping_id": mapping_id})
        signal = signal_by_id.get(item.get("signal_id"), {})
        problem = _normalize(str(item.get("market_problem", "")))
        category = _normalize(str(item.get("market_product_category", "")))
        title = _normalize(str(signal.get("signal_title", "")))
        if problem and problem == title:
            warnings.append({"code": "MARKET_PROBLEM_REPEATS_SIGNAL_TITLE", "product_mapping_id": mapping_id})
        if category and category == title:
            warnings.append({"code": "CATEGORY_REPEATS_SIGNAL_TITLE", "product_mapping_id": mapping_id})
        capabilities = item.get("required_capabilities", [])
        for capability in capabilities:
            if _normalize(str(capability)) in GENERIC_CAPABILITIES:
                warnings.append({"code": "GENERIC_CAPABILITY", "product_mapping_id": mapping_id, "capability": capability})
        source_statements = {
            _normalize(str(approved_by_id.get(ot_id, {}).get("statement", "")))
            for ot_id in item.get("related_ot_ids", [])
        }
        if problem in source_statements or _normalize(str(item.get("fit_rationale", ""))) in source_statements:
            warnings.append({"code": "MAPPING_COPIES_OT_STATEMENT", "product_mapping_id": mapping_id})
        duplicate_groups[(category, tuple(sorted(_normalize(str(x)) for x in item.get("required_capabilities", []))))].append(str(mapping_id))
    for mapping_ids in duplicate_groups.values():
        if len(mapping_ids) > 1:
            warnings.append({"code": "DUPLICATE_MAPPING_CANDIDATE", "product_mapping_ids": mapping_ids})
    return {
        "status": "PASS" if not errors else "FAIL",
        "schema_status": "PASS" if not schema_errors else "FAIL",
        "lineage_status": lineage["status"],
        "boundary_status": "PASS" if not _find_forbidden(artifact) else "FAIL",
        "semantic_status": "PASS" if not warnings else "WARNING",
        "product_mapping_count": len(artifact.get("items", [])),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--signals", required=True, type=Path)
    parser.add_argument("--approved-ot-bundle", required=True, type=Path)
    parser.add_argument("--decision", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        result = validate_artifact(load_json(args.artifact), load_json(args.schema), load_json(args.signals), load_json(args.approved_ot_bundle), load_json(args.decision))
    except (OSError, ValueError, TypeError) as exc:
        result = {"status": "FAIL", "schema_status": "FAIL", "lineage_status": "FAIL", "boundary_status": "FAIL", "semantic_status": "UNKNOWN", "warning_count": 0, "errors": [{"code": "INPUT_ERROR", "message": str(exc)}], "warnings": []}
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
