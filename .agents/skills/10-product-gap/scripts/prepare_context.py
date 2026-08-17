#!/usr/bin/env python3
"""Prepare immutable Product Mapping and portfolio context for Product Gap analysis."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
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


def parse_review_frontmatter(path: Path) -> dict[str, str]:
    """Read scalar YAML frontmatter without adding a PyYAML dependency."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"Cannot read Product Mapping review {path}: {exc}") from exc
    if not lines or lines[0].strip() != "---":
        raise ValueError("Product Mapping review is missing YAML frontmatter")
    result: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith((" ", "\t", "-")) or ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip('"\'')
    return result


def prepare_context(
    product_mapping: dict[str, Any],
    catalog: dict[str, Any],
    signals: dict[str, Any],
    approved_bundle: dict[str, Any],
    review: dict[str, str],
    catalog_sha256: str,
) -> dict[str, Any]:
    """Copy required inputs without performing portfolio matching."""
    if review.get("status") != "REVIEWED_ACCEPTED":
        raise ValueError("Product Mapping manual inspection must be REVIEWED_ACCEPTED")
    if not review.get("reviewer") or not review.get("reviewed_at"):
        raise ValueError("Product Mapping review requires reviewer and reviewed_at")
    run_ids = {product_mapping.get("run_id"), signals.get("run_id"), approved_bundle.get("run_id")}
    if len(run_ids) != 1 or None in run_ids:
        raise ValueError("Product Mapping, Signals and approved O/T bundle must share one run_id")
    if review.get("run_id") != product_mapping.get("run_id"):
        raise ValueError("Product Mapping review run_id does not match")
    if not (
        product_mapping.get("synthetic") is signals.get("synthetic")
        and signals.get("synthetic") is approved_bundle.get("synthetic")
    ):
        raise ValueError("Synthetic flags do not match")
    mappings = product_mapping.get("items")
    products = catalog.get("products")
    if not isinstance(mappings, list) or not isinstance(products, list):
        raise ValueError("Product Mapping items and catalog products must be arrays")
    if catalog.get("product_count") != len(products):
        raise ValueError("Catalog product_count does not match products array")
    signal_by_id = {item.get("signal_id"): item for item in signals.get("items", []) if isinstance(item, dict)}
    relevant_ids = {item.get("signal_id") for item in mappings if isinstance(item, dict)}
    unknown = sorted(relevant_ids - set(signal_by_id))
    if unknown:
        raise ValueError(f"Product Mapping references unknown Signal IDs: {unknown}")
    approved_ids = {
        item.get("ot_id") for item in approved_bundle.get("approved_opportunity_threat", []) if isinstance(item, dict)
    }
    leaked = sorted(
        {
            ot_id
            for item in mappings if isinstance(item, dict)
            for ot_id in item.get("related_ot_ids", [])
        }
        - approved_ids
    )
    if leaked:
        raise ValueError(f"Product Mapping contains non-approved O/T IDs: {leaked}")
    metadata = {key: value for key, value in catalog.items() if key != "products"}
    metadata["catalog_sha256"] = catalog_sha256.upper()
    return {
        "run_id": product_mapping["run_id"],
        "synthetic": product_mapping["synthetic"],
        "product_mapping_review_status": review["status"],
        "product_mapping_reviewer": review["reviewer"],
        "product_mapping_reviewed_at": review["reviewed_at"],
        "product_mappings": mappings,
        "relevant_signals": [item for item in signals.get("items", []) if item.get("signal_id") in relevant_ids],
        "approved_opportunity_threat": approved_bundle.get("approved_opportunity_threat", []),
        "portfolio_catalog_metadata": metadata,
        "portfolio_products": products,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product-mapping", required=True, type=Path)
    parser.add_argument("--products", required=True, type=Path)
    parser.add_argument("--signals", required=True, type=Path)
    parser.add_argument("--approved-ot-bundle", required=True, type=Path)
    parser.add_argument("--product-mapping-review", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        if args.output.exists() and not args.overwrite:
            raise ValueError(f"Refusing to overwrite existing context: {args.output}")
        context = prepare_context(
            load_json(args.product_mapping),
            load_json(args.products),
            load_json(args.signals),
            load_json(args.approved_ot_bundle),
            parse_review_frontmatter(args.product_mapping_review),
            hashlib.sha256(args.products.read_bytes()).hexdigest(),
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({
            "status": "PASS",
            "output": str(args.output),
            "product_mapping_count": len(context["product_mappings"]),
            "portfolio_product_count": len(context["portfolio_products"]),
        }, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

