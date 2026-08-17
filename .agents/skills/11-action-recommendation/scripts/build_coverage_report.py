#!/usr/bin/env python3
"""Build Action coverage without forcing every approved input to have an Action."""

from __future__ import annotations

import argparse
import json
import re
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


def _norm(value: str) -> str:
    return re.sub(r"\W+", " ", value.casefold()).strip()


def build_report(context: dict[str, Any], actions: dict[str, Any], draft: dict[str, Any]) -> dict[str, Any]:
    """Report action links and require rationale only for uncovered items."""
    if not (context.get("run_id") == actions.get("run_id") == draft.get("run_id")):
        raise ValueError("Context, Actions and draft run_id values must match")
    ot_ids = list(context.get("approved_ot_ids", []))
    mapping_ids = [item.get("product_mapping_id") for item in context.get("product_mappings", [])]
    gap_ids = [item.get("gap_id") for item in context.get("product_gaps", [])]
    ot_links: dict[str, list[str]] = {item_id: [] for item_id in ot_ids}
    mapping_links: dict[str, list[str]] = {item_id: [] for item_id in mapping_ids}
    gap_links: dict[str, list[str]] = {item_id: [] for item_id in gap_ids}
    responses: Counter[str] = Counter()
    priorities: Counter[str] = Counter()
    duplicates: dict[tuple[str, tuple[str, ...], str], list[str]] = defaultdict(list)
    for action in actions.get("items", []):
        action_id = action.get("action_id")
        for ot_id in action.get("related_ot_ids", []):
            ot_links.setdefault(ot_id, []).append(action_id)
        mapping_links.setdefault(action.get("product_mapping_id"), []).append(action_id)
        for gap_id in action.get("gap_ids", []):
            gap_links.setdefault(gap_id, []).append(action_id)
        responses[str(action.get("recommended_response"))] += 1
        priorities[str(action.get("priority"))] += 1
        duplicates[(str(action.get("target_product_or_category")).casefold(), tuple(sorted(action.get("gap_ids", []))), _norm(str(action.get("proposed_action"))))].append(action_id)
    without_ot = [item_id for item_id in ot_ids if not ot_links.get(item_id)]
    without_mapping = [item_id for item_id in mapping_ids if not mapping_links.get(item_id)]
    without_gap = [item_id for item_id in gap_ids if not gap_links.get(item_id)]
    rationale_sets = {
        "ot": draft.get("uncovered_approved_ot_rationales", {}),
        "mapping": draft.get("uncovered_mapping_rationales", {}),
        "gap": draft.get("uncovered_gap_rationales", {}),
    }
    findings: list[dict[str, Any]] = []
    for kind, values in [("ot", without_ot), ("mapping", without_mapping), ("gap", without_gap)]:
        for item_id in values:
            rationale = str(rationale_sets[kind].get(item_id, "")).strip()
            findings.append({
                "severity": "WARNING" if rationale else "ERROR",
                "code": "UNCOVERED_ITEM_WITH_RATIONALE" if rationale else "UNCOVERED_ITEM_RATIONALE_MISSING",
                "item_type": kind.upper(), "item_id": item_id, "rationale": rationale or None,
            })
    duplicate_groups = [ids for ids in duplicates.values() if len(ids) > 1]
    for ids in duplicate_groups:
        findings.append({"severity": "WARNING", "code": "DUPLICATE_ACTION_CANDIDATE", "action_ids": ids})
    errors = [item for item in findings if item["severity"] == "ERROR"]
    warnings = [item for item in findings if item["severity"] == "WARNING"]
    status = "FAIL" if errors else ("PASS_WITH_WARNINGS" if warnings else "PASS")
    return {
        "run_id": context["run_id"],
        "approved_ot_ids": ot_ids, "product_mapping_ids": mapping_ids, "gap_ids": gap_ids,
        "action_ids": [item.get("action_id") for item in actions.get("items", [])],
        "ot_ids_with_action": [item_id for item_id in ot_ids if ot_links.get(item_id)],
        "ot_ids_without_action": without_ot,
        "mapping_ids_with_action": [item_id for item_id in mapping_ids if mapping_links.get(item_id)],
        "mapping_ids_without_action": without_mapping,
        "gap_ids_with_action": [item_id for item_id in gap_ids if gap_links.get(item_id)],
        "gap_ids_without_action": without_gap,
        "response_counts": dict(sorted(responses.items())),
        "priority_counts": dict(sorted(priorities.items())),
        "mapping_to_action_links": [{"product_mapping_id": item_id, "action_ids": mapping_links.get(item_id, [])} for item_id in mapping_ids],
        "gap_to_action_links": [{"gap_id": item_id, "action_ids": gap_links.get(item_id, [])} for item_id in gap_ids],
        "duplicate_candidate_groups": duplicate_groups,
        "validation_status": status, "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", required=True, type=Path)
    parser.add_argument("--actions", required=True, type=Path)
    parser.add_argument("--draft", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = build_report(load_json(args.context), load_json(args.actions), load_json(args.draft))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({
            "status": report["validation_status"], "output": str(args.output),
            "ot_ids_without_action": report["ot_ids_without_action"],
            "gap_ids_without_action": report["gap_ids_without_action"],
        }, ensure_ascii=False))
        return 1 if report["validation_status"] == "FAIL" else 0
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

