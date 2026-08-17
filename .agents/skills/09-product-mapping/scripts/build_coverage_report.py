#!/usr/bin/env python3
"""Build Product Mapping coverage without forcing approved O/T to be mapped."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def build_report(context: dict[str, Any], mapping: dict[str, Any], draft: dict[str, Any]) -> dict[str, Any]:
    """Report mapped and intentionally unmapped approved inputs with rationales."""
    if not (context.get("run_id") == mapping.get("run_id") == draft.get("run_id")):
        raise ValueError("Context, mapping and draft run_id values must match")
    approved_ids = list(context.get("approved_ot_ids", []))
    signal_ids = [item.get("signal_id") for item in context.get("relevant_signals", [])]
    ot_links: dict[str, list[str]] = {ot_id: [] for ot_id in approved_ids}
    signal_links: dict[str, list[str]] = {signal_id: [] for signal_id in signal_ids}
    duplicate_index: dict[tuple[str, tuple[str, ...]], list[str]] = defaultdict(list)
    for item in mapping.get("items", []):
        mapping_id = item.get("product_mapping_id")
        signal_links.setdefault(item.get("signal_id"), []).append(mapping_id)
        for ot_id in item.get("related_ot_ids", []):
            ot_links.setdefault(ot_id, []).append(mapping_id)
        duplicate_index[(str(item.get("market_product_category", "")).strip().lower(), tuple(sorted(str(x).strip().lower() for x in item.get("required_capabilities", []))))].append(mapping_id)
    mapped_ot = [ot_id for ot_id in approved_ids if ot_links.get(ot_id)]
    unmapped_ot = [ot_id for ot_id in approved_ids if not ot_links.get(ot_id)]
    mapped_signals = [signal_id for signal_id in signal_ids if signal_links.get(signal_id)]
    unmapped_signals = [signal_id for signal_id in signal_ids if not signal_links.get(signal_id)]
    ot_rationales = draft.get("unmapped_approved_ot_rationales", {})
    signal_rationales = draft.get("unmapped_signal_rationales", {})
    findings: list[dict[str, Any]] = []
    for ot_id in unmapped_ot:
        if not str(ot_rationales.get(ot_id, "")).strip():
            findings.append({"severity": "ERROR", "code": "UNMAPPED_OT_RATIONALE_MISSING", "ot_id": ot_id})
    for signal_id in unmapped_signals:
        if not str(signal_rationales.get(signal_id, "")).strip():
            findings.append({"severity": "ERROR", "code": "UNMAPPED_SIGNAL_RATIONALE_MISSING", "signal_id": signal_id})
    duplicate_groups = [ids for ids in duplicate_index.values() if len(ids) > 1]
    for ids in duplicate_groups:
        findings.append({"severity": "WARNING", "code": "DUPLICATE_MAPPING_CANDIDATE", "product_mapping_ids": ids})
    has_error = any(item["severity"] == "ERROR" for item in findings)
    has_warning = any(item["severity"] == "WARNING" for item in findings)
    return {
        "run_id": context["run_id"],
        "approved_ot_ids": approved_ids,
        "mapped_ot_ids": mapped_ot,
        "unmapped_approved_ot_ids": unmapped_ot,
        "signal_ids": signal_ids,
        "mapped_signal_ids": mapped_signals,
        "unmapped_signal_ids": unmapped_signals,
        "product_mapping_ids": [item.get("product_mapping_id") for item in mapping.get("items", [])],
        "ot_to_mapping_links": [
            {"ot_id": ot_id, "product_mapping_ids": ot_links.get(ot_id, []), "coverage_status": "MAPPED" if ot_links.get(ot_id) else "UNMAPPED", "rationale": "Đã được liên kết với các bản ghi yêu cầu thị trường được liệt kê." if ot_links.get(ot_id) else ot_rationales.get(ot_id)}
            for ot_id in approved_ids
        ],
        "signal_to_mapping_links": [
            {"signal_id": signal_id, "product_mapping_ids": signal_links.get(signal_id, []), "coverage_status": "MAPPED" if signal_links.get(signal_id) else "UNMAPPED", "rationale": "Đã được liên kết với các bản ghi yêu cầu thị trường được liệt kê." if signal_links.get(signal_id) else signal_rationales.get(signal_id)}
            for signal_id in signal_ids
        ],
        "duplicate_candidate_groups": duplicate_groups,
        "validation_status": "FAIL" if has_error else ("PASS_WITH_WARNINGS" if has_warning else "PASS"),
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", required=True, type=Path)
    parser.add_argument("--product-mapping", required=True, type=Path)
    parser.add_argument("--draft", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = build_report(load_json(args.context), load_json(args.product_mapping), load_json(args.draft))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": report["validation_status"], "output": str(args.output), "unmapped_approved_ot_ids": report["unmapped_approved_ot_ids"], "unmapped_signal_ids": report["unmapped_signal_ids"]}, ensure_ascii=False))
        return 1 if report["validation_status"] == "FAIL" else 0
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
