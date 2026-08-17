#!/usr/bin/env python3
"""Evaluate whether a HITL gate permits pipeline continuation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from validate_json_schema import load_json


def evaluate_gate(manifest: dict[str, Any], semantic_pass: bool) -> dict[str, Any]:
    """Return gate status, continuation flag and deterministic blocking reasons."""
    status = manifest.get("overall_status", "PENDING")
    reasons: list[str] = []
    can_continue = status == "APPROVED" and semantic_pass
    if status == "PENDING":
        reasons.append("HUMAN_REVIEW_PENDING")
    elif status == "CHANGES_REQUIRED":
        reasons.append("RETURN_TO_PREVIOUS_STAGE")
    elif status == "REJECTED":
        reasons.append("BATCH_REJECTED")
    elif status != "APPROVED":
        reasons.append("INVALID_GATE_STATUS")
    if not semantic_pass:
        reasons.append("SEMANTIC_VALIDATION_FAILED")
    return {"gate_status": status, "pipeline_can_continue": can_continue, "blocking_reasons": reasons}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--semantic-report", type=Path)
    args = parser.parse_args()
    try:
        manifest = load_json(args.manifest)
        semantic_pass = True
        if args.semantic_report:
            semantic_pass = load_json(args.semantic_report).get("status") == "PASS"
        result = evaluate_gate(manifest, semantic_pass)
    except ValueError as exc:
        result = {"gate_status": "UNKNOWN", "pipeline_can_continue": False, "blocking_reasons": [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["pipeline_can_continue"] else 1


if __name__ == "__main__":
    sys.exit(main())
