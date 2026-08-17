#!/usr/bin/env python3
"""Normalize a Codex-authored semantic draft into frozen Product Gap output."""

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
    product_mapping: dict[str, Any], draft: dict[str, Any], schema: dict[str, Any]
) -> dict[str, Any]:
    """Preserve market requirements, assign deterministic IDs and strip draft-only analysis."""
    if draft.get("run_id") != product_mapping.get("run_id"):
        raise ValueError("Draft and Product Mapping run_id values do not match")
    if draft.get("synthetic") is not product_mapping.get("synthetic"):
        raise ValueError("Draft and Product Mapping synthetic flags do not match")
    mappings = product_mapping.get("items")
    draft_items = draft.get("items")
    if not isinstance(mappings, list) or not isinstance(draft_items, list):
        raise ValueError("Product Mapping and draft items must be arrays")
    mapping_by_id = {item.get("product_mapping_id"): item for item in mappings if isinstance(item, dict)}
    mapping_order = {item.get("product_mapping_id"): index for index, item in enumerate(mappings)}
    sortable: list[tuple[int, int, dict[str, Any]]] = []
    for index, item in enumerate(draft_items):
        if not isinstance(item, dict):
            raise ValueError(f"Draft item {index} must be an object")
        mapping_id = item.get("product_mapping_id")
        parent = mapping_by_id.get(mapping_id)
        if parent is None:
            raise ValueError(f"Draft item {index} uses unknown product_mapping_id: {mapping_id}")
        for key in ["signal_id", "market_product_category", "required_capabilities"]:
            if item.get(key) != parent.get(key):
                raise ValueError(f"Draft item {index} changes Product Mapping field {key}")
        sortable.append((mapping_order[mapping_id], index, item))
    sortable.sort(key=lambda entry: entry[:2])
    item_schema = schema["properties"]["items"]["items"]
    allowed = set(item_schema["properties"])
    output_items: list[dict[str, Any]] = []
    for number, (_, _, draft_item) in enumerate(sortable, start=1):
        clean = {key: value for key, value in draft_item.items() if key in allowed and key != "gap_id"}
        clean = {"gap_id": f"GAP-{number:03d}", **clean}
        output_items.append(clean)
    artifact = {
        "artifact_type": "product_gap",
        "run_id": product_mapping["run_id"],
        "synthetic": product_mapping["synthetic"],
        "items": output_items,
    }
    schema_errors = validate_instance(artifact, schema)
    if schema_errors:
        raise ValueError(f"Built artifact fails frozen schema: {schema_errors}")
    if any(not re.fullmatch(r"GAP-\d{3}", str(item.get("gap_id"))) for item in output_items):
        raise ValueError("Deterministic Product Gap ID generation failed")
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product-mapping", required=True, type=Path)
    parser.add_argument("--draft", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        if args.output.exists() and not args.overwrite:
            raise ValueError(f"Refusing to overwrite existing artifact: {args.output}")
        artifact = build_artifact(load_json(args.product_mapping), load_json(args.draft), load_json(args.schema))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "PASS", "output": str(args.output), "product_gap_count": len(artifact["items"])}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

