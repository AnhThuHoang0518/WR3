#!/usr/bin/env python3
"""Build Product Gap coverage and unresolved-assessment reporting."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
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


def build_report(
    product_mapping: dict[str, Any], product_gap: dict[str, Any], draft: dict[str, Any]
) -> dict[str, Any]:
    """Require one assessment or an explicit unresolved rationale per mapping."""
    if not (product_mapping.get("run_id") == product_gap.get("run_id") == draft.get("run_id")):
        raise ValueError("Product Mapping, Product Gap and draft run_id values must match")
    mapping_ids = [item.get("product_mapping_id") for item in product_mapping.get("items", [])]
    links: dict[str, list[str]] = {mapping_id: [] for mapping_id in mapping_ids}
    statuses: Counter[str] = Counter()
    gap_types: Counter[str] = Counter()
    severities: Counter[str] = Counter()
    unresolved: set[str] = set()
    for gap in product_gap.get("items", []):
        mapping_id = gap.get("product_mapping_id")
        links.setdefault(mapping_id, []).append(gap.get("gap_id"))
        statuses[str(gap.get("capability_status"))] += 1
        gap_types[str(gap.get("gap_type"))] += 1
        severities[str(gap.get("gap_severity"))] += 1
        if gap.get("capability_status") == "UNKNOWN":
            unresolved.add(str(mapping_id))
    with_gap = [mapping_id for mapping_id in mapping_ids if links.get(mapping_id)]
    without_gap = [mapping_id for mapping_id in mapping_ids if not links.get(mapping_id)]
    rationales = draft.get("unresolved_mapping_rationales", {})
    findings: list[dict[str, Any]] = []
    for mapping_id in without_gap:
        unresolved.add(str(mapping_id))
        if not str(rationales.get(mapping_id, "")).strip():
            findings.append({
                "severity": "ERROR", "code": "MAPPING_WITHOUT_GAP_OR_RATIONALE",
                "product_mapping_id": mapping_id,
            })
        else:
            findings.append({
                "severity": "WARNING", "code": "MAPPING_WITHOUT_GAP_ASSESSMENT",
                "product_mapping_id": mapping_id, "rationale": rationales[mapping_id],
            })
    errors = [item for item in findings if item["severity"] == "ERROR"]
    warnings = [item for item in findings if item["severity"] == "WARNING"]
    status = "FAIL" if errors else ("PASS_WITH_WARNINGS" if warnings else "PASS")
    return {
        "run_id": product_mapping["run_id"],
        "product_mapping_ids": mapping_ids,
        "mapping_ids_with_gap": with_gap,
        "mapping_ids_without_gap": without_gap,
        "capability_status_counts": dict(sorted(statuses.items())),
        "gap_type_counts": dict(sorted(gap_types.items())),
        "gap_severity_counts": dict(sorted(severities.items())),
        "mapping_to_gap_links": [
            {
                "product_mapping_id": mapping_id,
                "gap_ids": links.get(mapping_id, []),
                "coverage_status": "ASSESSED" if links.get(mapping_id) else "UNRESOLVED",
                "rationale": "Đã được đánh giá trong các bản ghi Product Gap được liệt kê." if links.get(mapping_id) else rationales.get(mapping_id),
            }
            for mapping_id in mapping_ids
        ],
        "unresolved_mapping_ids": sorted(unresolved),
        "validation_status": status,
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product-mapping", required=True, type=Path)
    parser.add_argument("--product-gap", required=True, type=Path)
    parser.add_argument("--draft", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = build_report(
            load_json(args.product_mapping), load_json(args.product_gap), load_json(args.draft)
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({
            "status": report["validation_status"], "output": str(args.output),
            "mapping_ids_without_gap": report["mapping_ids_without_gap"],
            "unresolved_mapping_ids": report["unresolved_mapping_ids"],
        }, ensure_ascii=False))
        return 1 if report["validation_status"] == "FAIL" else 0
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
