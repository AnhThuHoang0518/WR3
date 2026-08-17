#!/usr/bin/env python3
"""Prepare approved, reviewed and immutable context for Action Recommendation."""

from __future__ import annotations

import argparse
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


def parse_frontmatter(path: Path) -> dict[str, str]:
    """Read scalar YAML frontmatter without an external dependency."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"Missing YAML frontmatter: {path}")
    result: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return result
        if line.startswith((" ", "\t", "-")) or ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip('"\'')
    raise ValueError(f"Unclosed YAML frontmatter: {path}")


def prepare_context(
    signals: dict[str, Any], approved_bundle: dict[str, Any], product_mapping: dict[str, Any],
    product_gap: dict[str, Any], gap_review: dict[str, str], decision: dict[str, Any],
) -> dict[str, Any]:
    """Return only approved O/T and their reviewed downstream lineage."""
    if decision.get("overall_status") != "APPROVED":
        raise ValueError("Gate 2 overall_status must be APPROVED")
    if decision.get("revision_ot_ids"):
        raise ValueError("Gate 2 must not contain revision O/T IDs")
    if gap_review.get("status") != "REVIEWED_ACCEPTED":
        raise ValueError("Product Gap manual review must be REVIEWED_ACCEPTED")
    if not gap_review.get("reviewer") or not gap_review.get("reviewed_at"):
        raise ValueError("Product Gap review requires reviewer and reviewed_at")
    sources = [signals, approved_bundle, product_mapping, product_gap, decision]
    run_ids = {source.get("run_id") for source in sources}
    if len(run_ids) != 1 or None in run_ids or gap_review.get("run_id") not in run_ids:
        raise ValueError("All action inputs must share one run_id")
    synthetic_values = {source.get("synthetic") for source in sources}
    if len(synthetic_values) != 1:
        raise ValueError("All action inputs must share one synthetic flag")
    approved_items = approved_bundle.get("approved_opportunity_threat", [])
    approved_ids = list(decision.get("approved_ot_ids", []))
    actual_ids = [item.get("ot_id") for item in approved_items if isinstance(item, dict)]
    if len(actual_ids) != len(set(actual_ids)) or set(actual_ids) != set(approved_ids):
        raise ValueError("Approved O/T bundle must exactly match Gate 2 approved IDs")
    rejected = set(decision.get("rejected_ot_ids", [])) | set(decision.get("revision_ot_ids", []))
    if set(actual_ids) & rejected:
        raise ValueError("Approved O/T bundle contains rejected or revision IDs")
    signal_by_id = {item.get("signal_id"): item for item in signals.get("items", [])}
    mapping_by_id = {item.get("product_mapping_id"): item for item in product_mapping.get("items", [])}
    links: list[dict[str, Any]] = []
    for gap in product_gap.get("items", []):
        mapping = mapping_by_id.get(gap.get("product_mapping_id"))
        if mapping is None:
            raise ValueError(f"Product Gap references unknown mapping: {gap.get('gap_id')}")
        if gap.get("signal_id") != mapping.get("signal_id") or gap.get("signal_id") not in signal_by_id:
            raise ValueError(f"Product Gap has invalid Signal lineage: {gap.get('gap_id')}")
        related = list(mapping.get("related_ot_ids", []))
        unknown = sorted(set(related) - set(approved_ids))
        if unknown:
            raise ValueError(f"Mapping contains non-approved O/T IDs: {unknown}")
        links.append({
            "source_signal_id": gap.get("signal_id"),
            "related_ot_ids": related,
            "product_mapping_id": mapping.get("product_mapping_id"),
            "gap_ids": [gap.get("gap_id")],
        })
    return {
        "run_id": signals["run_id"],
        "synthetic": signals["synthetic"],
        "gate_2_status": decision["overall_status"],
        "product_gap_review_status": gap_review["status"],
        "product_gap_reviewer": gap_review["reviewer"],
        "product_gap_reviewed_at": gap_review["reviewed_at"],
        "approved_ot_ids": approved_ids,
        "signals": signals.get("items", []),
        "approved_opportunity_threat": approved_items,
        "product_mappings": product_mapping.get("items", []),
        "product_gaps": product_gap.get("items", []),
        "lineage_links": links,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--signals", required=True, type=Path)
    parser.add_argument("--approved-ot-bundle", required=True, type=Path)
    parser.add_argument("--product-mapping", required=True, type=Path)
    parser.add_argument("--product-gap", required=True, type=Path)
    parser.add_argument("--product-gap-review", required=True, type=Path)
    parser.add_argument("--decision", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        if args.output.exists() and not args.overwrite:
            raise ValueError(f"Refusing to overwrite context: {args.output}")
        context = prepare_context(
            load_json(args.signals), load_json(args.approved_ot_bundle),
            load_json(args.product_mapping), load_json(args.product_gap),
            parse_frontmatter(args.product_gap_review), load_json(args.decision),
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({
            "status": "PASS", "output": str(args.output),
            "approved_ot_count": len(context["approved_ot_ids"]),
            "gap_count": len(context["product_gaps"]),
        }, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

