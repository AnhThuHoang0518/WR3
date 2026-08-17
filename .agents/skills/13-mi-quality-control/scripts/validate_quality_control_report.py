#!/usr/bin/env python3
"""Validate frozen QC schema, deterministic IDs, counts and release semantics."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

VALIDATORS = Path(__file__).resolve().parents[2] / "00-news-driven-mi-orchestrator" / "scripts" / "validators"
sys.path.insert(0, str(VALIDATORS))
from validate_json_schema import validate_instance  # noqa: E402

from qc_common import load_json, write_json


def validate_report(report: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    """Return structural/semantic validation independent of release eligibility."""
    schema_errors = validate_instance(report, schema)
    errors: list[dict[str, Any]] = [{"code": "SCHEMA_ERROR", **item} for item in schema_errors]
    checks = report.get("checks", []) if isinstance(report.get("checks"), list) else []
    actual_ids = [item.get("check_id") for item in checks if isinstance(item, dict)]
    expected_ids = [f"QC-{index:03d}" for index in range(1, len(checks) + 1)]
    if actual_ids != expected_ids or any(not re.fullmatch(r"QC-\d{3}", str(item)) for item in actual_ids):
        errors.append({"code": "NON_DETERMINISTIC_CHECK_IDS"})
    counts = {
        "error_count": sum(item.get("status") == "ERROR" for item in checks if isinstance(item, dict)),
        "warning_count": sum(item.get("status") == "WARNING" for item in checks if isinstance(item, dict)),
        "passed_count": sum(item.get("status") == "PASS" for item in checks if isinstance(item, dict)),
    }
    summary = report.get("summary", {})
    for field, value in counts.items():
        if summary.get(field) != value:
            errors.append({"code": "SUMMARY_COUNT_MISMATCH", "field": field, "expected": value, "actual": summary.get(field)})
    expected_overall = "ERROR" if counts["error_count"] else ("WARNING" if counts["warning_count"] else "PASS")
    if summary.get("overall_status") != expected_overall:
        errors.append({"code": "OVERALL_STATUS_MISMATCH", "expected": expected_overall})
    if summary.get("pipeline_eligible_for_release") is not (counts["error_count"] == 0):
        errors.append({"code": "RELEASE_ELIGIBILITY_MISMATCH"})
    invalid_remediation = [
        item.get("check_id") for item in checks
        if item.get("status") in {"ERROR", "WARNING"} and not item.get("remediation")
    ]
    if invalid_remediation:
        errors.append({"code": "MISSING_REMEDIATION", "check_ids": invalid_remediation})
    return {
        "status": "PASS" if not errors else "FAIL",
        "schema_status": "PASS" if not schema_errors else "FAIL",
        "semantic_status": "PASS" if not errors else "FAIL",
        "check_count": len(checks), **counts, "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        validation = validate_report(load_json(args.report), load_json(args.schema))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        validation = {"status": "FAIL", "schema_status": "FAIL", "semantic_status": "FAIL", "errors": [{"code": "INPUT_ERROR", "message": str(exc)}]}
    if args.output:
        write_json(args.output, validation)
    print(json.dumps(validation, ensure_ascii=False, indent=2))
    return 0 if validation["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

