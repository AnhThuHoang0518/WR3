#!/usr/bin/env python3
"""Validate generic HITL reviewed/decision ID set semantics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from validate_json_schema import load_json


def _duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def validate_hitl_sets(
    manifest: dict[str, Any],
    reviewed_field: str,
    decision_fields: list[str],
    all_source_ids: set[str] | None = None,
    approved_field: str | None = None,
) -> dict[str, Any]:
    """Validate union, disjointness, duplicates, unknown and missing IDs."""
    errors: list[dict[str, Any]] = []
    reviewed = manifest.get(reviewed_field, [])
    if not isinstance(reviewed, list):
        return {"status": "FAIL", "errors": [{"code": "INVALID_FIELD", "field": reviewed_field}]}

    decision_lists: dict[str, list[str]] = {}
    for field in decision_fields:
        values = manifest.get(field, [])
        if not isinstance(values, list):
            errors.append({"code": "INVALID_FIELD", "field": field})
            values = []
        decision_lists[field] = values

    for field, values in [(reviewed_field, reviewed), *decision_lists.items()]:
        duplicates = _duplicates(values)
        if duplicates:
            errors.append({"code": "DUPLICATE_ID", "field": field, "ids": duplicates})

    membership: dict[str, list[str]] = {}
    for field, values in decision_lists.items():
        for value in values:
            membership.setdefault(value, []).append(field)
    overlaps = {value: fields for value, fields in membership.items() if len(fields) > 1}
    if overlaps:
        errors.append({"code": "OVERLAPPING_DECISIONS", "items": overlaps})

    union = set(membership)
    reviewed_set = set(reviewed)
    if union != reviewed_set:
        errors.append({
            "code": "UNION_MISMATCH",
            "missing_from_reviewed": sorted(union - reviewed_set),
            "missing_from_decisions": sorted(reviewed_set - union),
        })

    if all_source_ids is not None:
        used_ids = union | reviewed_set
        unknown = sorted(used_ids - all_source_ids)
        if unknown:
            errors.append({"code": "UNKNOWN_ID", "ids": unknown})
        missing = sorted(all_source_ids - reviewed_set)
        if missing and manifest.get("overall_status") != "PENDING":
            errors.append({"code": "MISSING_ID", "ids": missing})
    else:
        missing = []

    if manifest.get("overall_status") == "APPROVED":
        approved_name = approved_field or (decision_fields[0] if decision_fields else None)
        if not approved_name or not decision_lists.get(approved_name):
            errors.append({"code": "EMPTY_APPROVED_SET", "field": approved_name})

    return {
        "status": "PASS" if not errors else "FAIL",
        "reviewed_count": len(reviewed_set),
        "source_count": len(all_source_ids) if all_source_ids is not None else None,
        "unreviewed_ids": missing,
        "errors": errors,
    }


def _load_source_ids(path: Path) -> set[str]:
    payload = load_json(path)
    if isinstance(payload, list):
        return set(payload)
    if isinstance(payload, dict):
        for field in ("all_source_ids", "news_ids", "ids"):
            if isinstance(payload.get(field), list):
                return set(payload[field])
    raise ValueError("all-source-ids-file must be a JSON list or contain all_source_ids/news_ids/ids")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--reviewed-field", required=True)
    parser.add_argument("--decision-field", action="append", dest="decision_fields", required=True)
    parser.add_argument("--approved-field")
    parser.add_argument("--all-source-ids-file", type=Path)
    args = parser.parse_args()
    try:
        manifest = load_json(args.manifest)
        all_ids = _load_source_ids(args.all_source_ids_file) if args.all_source_ids_file else None
        result = validate_hitl_sets(
            manifest,
            args.reviewed_field,
            args.decision_fields,
            all_ids,
            args.approved_field,
        )
    except ValueError as exc:
        result = {"status": "FAIL", "errors": [{"code": "INPUT_ERROR", "message": str(exc)}]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
