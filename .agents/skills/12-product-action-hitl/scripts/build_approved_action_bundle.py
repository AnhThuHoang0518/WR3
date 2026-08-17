#!/usr/bin/env python3
"""Build an approved Action bundle after a fully valid APPROVED Gate 3 decision."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def build_bundle(actions: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    """Copy only approved canonical records; never infer human approval."""
    if decision.get("overall_status") != "APPROVED":
        raise ValueError("Gate 3 must be APPROVED before building an approved Action bundle")
    if not (decision.get("reviewer") and decision.get("reviewed_at")):
        raise ValueError("Gate 3 reviewer metadata is required")
    if decision.get("revision_action_ids"):
        raise ValueError("An APPROVED Gate 3 decision cannot contain revision IDs")
    source = {item.get("action_id"): item for item in actions.get("items", []) if isinstance(item, dict)}
    all_ids = set(source)
    reviewed = set(decision.get("reviewed_action_ids", []))
    approved = decision.get("approved_action_ids", [])
    if reviewed != all_ids or not approved:
        raise ValueError("Every Action must be reviewed and at least one Action approved")
    unknown = sorted(set(approved) - all_ids)
    if unknown:
        raise ValueError(f"Unknown approved Action IDs: {unknown}")
    return {
        "artifact_type": "approved-actions", "run_id": actions.get("run_id"),
        "synthetic": actions.get("synthetic"), "gate_status": "APPROVED",
        "reviewer": decision.get("reviewer"), "reviewed_at": decision.get("reviewed_at"),
        "items": [source[action_id] for action_id in approved],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actions", required=True, type=Path)
    parser.add_argument("--decision", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise ValueError(f"Refusing to overwrite approved Action bundle: {args.output}")
        bundle = build_bundle(load_json(args.actions), load_json(args.decision))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "PASS", "approved_count": len(bundle["items"]), "output": str(args.output)}))
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

