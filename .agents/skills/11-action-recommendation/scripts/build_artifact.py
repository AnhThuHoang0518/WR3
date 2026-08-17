#!/usr/bin/env python3
"""Normalize a Codex-authored semantic draft into frozen Action output."""

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
    """Load one UTF-8 JSON object."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def build_artifact(
    context: dict[str, Any], draft: dict[str, Any], schema: dict[str, Any]
) -> dict[str, Any]:
    """Preserve lineage, assign deterministic IDs and strip draft-only analysis."""
    if draft.get("run_id") != context.get("run_id") or draft.get("synthetic") is not context.get("synthetic"):
        raise ValueError("Draft and Action context metadata do not match")
    draft_items = draft.get("items")
    if not isinstance(draft_items, list):
        raise ValueError("Draft items must be an array")
    signals = {item.get("signal_id") for item in context.get("signals", [])}
    approved = set(context.get("approved_ot_ids", []))
    mappings = {item.get("product_mapping_id"): item for item in context.get("product_mappings", [])}
    gaps = {item.get("gap_id"): item for item in context.get("product_gaps", [])}
    mapping_order = {item.get("product_mapping_id"): index for index, item in enumerate(context.get("product_mappings", []))}
    sortable: list[tuple[int, int, dict[str, Any]]] = []
    for index, item in enumerate(draft_items):
        if not isinstance(item, dict):
            raise ValueError(f"Draft item {index} must be an object")
        signal_id = item.get("source_signal_id")
        mapping_id = item.get("product_mapping_id")
        related = item.get("related_ot_ids", [])
        gap_ids = item.get("gap_ids", [])
        mapping = mappings.get(mapping_id)
        if signal_id not in signals or mapping is None:
            raise ValueError(f"Draft item {index} has unknown Signal or Mapping")
        if signal_id != mapping.get("signal_id"):
            raise ValueError(f"Draft item {index} changes Mapping Signal lineage")
        if not related or set(related) - approved:
            raise ValueError(f"Draft item {index} contains non-approved O/T")
        if not gap_ids or any(gap_id not in gaps for gap_id in gap_ids):
            raise ValueError(f"Draft item {index} contains missing or unknown Gap IDs")
        if any(gaps[gap_id].get("product_mapping_id") != mapping_id for gap_id in gap_ids):
            raise ValueError(f"Draft item {index} links a Gap to the wrong Mapping")
        allowed_current = {
            capability for gap_id in gap_ids for capability in gaps[gap_id].get("current_vsf_capabilities", [])
        }
        unsupported_claims = sorted(set(item.get("existing_capability_claims", [])) - allowed_current)
        if unsupported_claims:
            raise ValueError(f"Draft item {index} claims unsupported current capabilities: {unsupported_claims}")
        sortable.append((mapping_order[mapping_id], index, item))
    sortable.sort(key=lambda entry: entry[:2])
    allowed_fields = set(schema["properties"]["items"]["items"]["properties"])
    output_items: list[dict[str, Any]] = []
    for number, (_, _, item) in enumerate(sortable, start=1):
        clean = {
            key: value for key, value in item.items()
            if key in allowed_fields and key not in {"action_id", "owner_suggestion"}
        }
        output_items.append({"action_id": f"ACTION-{number:03d}", **clean})
    artifact = {
        "artifact_type": "actions", "run_id": context["run_id"],
        "synthetic": context["synthetic"], "items": output_items,
    }
    schema_errors = validate_instance(artifact, schema)
    if schema_errors:
        raise ValueError(f"Built Action artifact fails frozen schema: {schema_errors}")
    if any(not re.fullmatch(r"ACTION-\d{3}", str(item.get("action_id"))) for item in output_items):
        raise ValueError("Deterministic Action ID generation failed")
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
            raise ValueError(f"Refusing to overwrite Action artifact: {args.output}")
        artifact = build_artifact(load_json(args.context), load_json(args.draft), load_json(args.schema))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "PASS", "output": str(args.output), "action_count": len(artifact["items"])}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
