#!/usr/bin/env python3
"""Validate Opportunity/Threat schema, IDs, content and Signal lineage."""

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
from validate_stage_lineage import validate_ot_lineage  # noqa: E402

ID_PATTERN = re.compile(r"^OT-[0-9]{3}$")
FORBIDDEN_FIELDS = {"product_mapping_id", "gap_id", "gap_ids", "action_id", "recommended_action"}


def validate_artifact(artifact: dict[str, Any], schema: dict[str, Any], signals: dict[str, Any]) -> dict[str, Any]:
    schema_errors = validate_instance(artifact, schema)
    errors: list[dict[str, Any]] = [{"code": "SCHEMA_ERROR", **error} for error in schema_errors]
    for item in artifact.get("items", []):
        if not isinstance(item.get("ot_id"), str) or ID_PATTERN.fullmatch(item["ot_id"]) is None:
            errors.append({"code": "INVALID_OT_ID", "ot_id": item.get("ot_id")})
        forbidden = sorted(FORBIDDEN_FIELDS & set(item))
        if forbidden:
            errors.append({"code": "FORBIDDEN_DOWNSTREAM_FIELD", "ot_id": item.get("ot_id"), "fields": forbidden})
    lineage = validate_ot_lineage(artifact, signals)
    errors.extend(lineage["errors"])
    return {
        "status": "PASS" if not errors else "FAIL",
        "schema_status": "PASS" if not schema_errors else "FAIL",
        "lineage_status": lineage["status"],
        "ot_count": len(artifact.get("items", [])),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--signals", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        result = validate_artifact(load_json(args.artifact), load_json(args.schema), load_json(args.signals))
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
