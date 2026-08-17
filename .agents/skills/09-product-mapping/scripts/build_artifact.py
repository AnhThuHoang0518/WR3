#!/usr/bin/env python3
"""Normalize a human/Codex semantic draft into frozen Product Mapping output."""

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


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def build_artifact(context: dict[str, Any], draft: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    """Assign deterministic IDs and strip non-schema draft metadata without new analysis."""
    if draft.get("run_id") != context.get("run_id") or draft.get("synthetic") is not context.get("synthetic"):
        raise ValueError("Draft and context run metadata do not match")
    draft_items = draft.get("items")
    if not isinstance(draft_items, list):
        raise ValueError("Draft items must be an array")
    approved_order = {ot_id: index for index, ot_id in enumerate(context.get("approved_ot_ids", []))}
    signal_order = {
        item.get("signal_id"): index for index, item in enumerate(context.get("relevant_signals", []))
    }
    sortable: list[tuple[int, int, int, dict[str, Any]]] = []
    for index, item in enumerate(draft_items):
        if not isinstance(item, dict):
            raise ValueError(f"Draft item {index} must be an object")
        signal_id = item.get("signal_id")
        related = item.get("related_ot_ids")
        if signal_id not in signal_order:
            raise ValueError(f"Draft item {index} uses unknown signal_id: {signal_id}")
        if not isinstance(related, list) or not related:
            raise ValueError(f"Draft item {index} must contain related_ot_ids")
        unknown = sorted(set(related) - set(approved_order))
        if unknown:
            raise ValueError(f"Draft item {index} uses unapproved O/T IDs: {unknown}")
        normalized_related = sorted(set(related), key=approved_order.get)
        copied = dict(item)
        copied["related_ot_ids"] = normalized_related
        sortable.append((signal_order[signal_id], min(approved_order[x] for x in normalized_related), index, copied))
    sortable.sort(key=lambda entry: entry[:3])

    item_schema = schema["properties"]["items"]["items"]
    allowed = set(item_schema["properties"])
    output_items: list[dict[str, Any]] = []
    for number, (_, _, _, draft_item) in enumerate(sortable, start=1):
        clean = {key: value for key, value in draft_item.items() if key in allowed and key != "product_mapping_id"}
        clean = {"product_mapping_id": f"PM-{number:03d}", **clean}
        output_items.append(clean)
    artifact = {
        "artifact_type": "product_mapping",
        "run_id": context["run_id"],
        "synthetic": context["synthetic"],
        "items": output_items,
    }
    schema_errors = validate_instance(artifact, schema)
    if schema_errors:
        raise ValueError(f"Built artifact fails frozen schema: {schema_errors}")
    for item in output_items:
        if not re.fullmatch(r"PM-\d{3}", item["product_mapping_id"]):
            raise ValueError("Deterministic Product Mapping ID generation failed")
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", required=True, type=Path)
    parser.add_argument("--draft", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        if args.output.exists() and not args.overwrite:
            raise ValueError(f"Refusing to overwrite existing artifact: {args.output}")
        artifact = build_artifact(load_json(args.context), load_json(args.draft), load_json(args.schema))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "PASS", "output": str(args.output), "product_mapping_count": len(artifact["items"])}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
