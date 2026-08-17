#!/usr/bin/env python3
"""Generate a machine-readable, non-approval Action summary."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    """Load one UTF-8 JSON object."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def build_summary(actions: dict[str, Any]) -> dict[str, Any]:
    """Aggregate proposal metadata without creating final approved actions."""
    responses: Counter[str] = Counter()
    priorities: Counter[str] = Counter()
    choices: Counter[str] = Counter()
    packaging: Counter[str] = Counter()
    by_category: dict[str, list[str]] = defaultdict(list)
    validation_count = 0
    for action in actions.get("items", []):
        responses[str(action.get("recommended_response"))] += 1
        priorities[str(action.get("priority"))] += 1
        choices[str(action.get("build_buy_partner"))] += 1
        packaging[str(action.get("pilot_or_productize"))] += 1
        if action.get("validation_required"):
            validation_count += 1
        by_category[str(action.get("target_product_or_category"))].append(action.get("action_id"))
    return {
        "artifact_type": "action_summary", "run_id": actions.get("run_id"),
        "synthetic": actions.get("synthetic"), "approval_status": "NOT_REVIEWED",
        "action_count": len(actions.get("items", [])),
        "response_counts": dict(sorted(responses.items())),
        "priority_counts": dict(sorted(priorities.items())),
        "build_buy_partner_counts": dict(sorted(choices.items())),
        "pilot_or_productize_counts": dict(sorted(packaging.items())),
        "validation_required_count": validation_count,
        "actions_by_target_category": [
            {"target_product_or_category": category, "action_ids": ids}
            for category, ids in sorted(by_category.items())
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actions", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        if args.output.exists() and not args.overwrite:
            raise ValueError(f"Refusing to overwrite Action summary: {args.output}")
        summary = build_summary(load_json(args.actions))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "PASS", "output": str(args.output), "action_count": summary["action_count"]}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
