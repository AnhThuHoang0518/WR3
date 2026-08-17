#!/usr/bin/env python3
"""Build an exact Gate 1 KEEP-only News bundle without altering canonical content."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

VALID_TYPES = {"MARKET", "COMPETITOR", "TECHNOLOGY", "POLICY"}


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc


def parse_corrected_types(review_path: Path | None) -> dict[str, str]:
    """Read explicit corrected_news_type values from the Gate 1 Markdown table."""
    if review_path is None:
        return {}
    lines = review_path.read_text(encoding="utf-8").splitlines()
    header_index = next((i for i, line in enumerate(lines) if line.startswith("| news_id |")), None)
    if header_index is None:
        raise ValueError("Gate 1 review table header not found")
    headers = [cell.strip() for cell in lines[header_index].strip().strip("|").split("|")]
    required = {"news_id", "relevance_decision", "corrected_news_type"}
    if not required.issubset(headers):
        raise ValueError("Gate 1 review lacks corrected_news_type fields")
    corrections: dict[str, str] = {}
    for line in lines[header_index + 2:]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != len(headers):
            raise ValueError("Gate 1 review row has an invalid column count")
        row = dict(zip(headers, cells))
        corrected = row["corrected_news_type"].upper()
        if row["relevance_decision"].upper() == "KEEP" and corrected not in {"", "NULL", "PENDING"}:
            if corrected not in VALID_TYPES:
                raise ValueError(f"Invalid corrected_news_type for {row['news_id']}: {corrected}")
            corrections[row["news_id"]] = corrected
    return corrections


def build_bundle(
    decision: dict[str, Any],
    artifacts: list[dict[str, Any]],
    source_decision_path: str,
    corrected_types: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Return canonical items in Gate 1 kept_news_ids order."""
    if decision.get("overall_status") != "APPROVED":
        raise ValueError("Gate 1 decision must be APPROVED")
    if decision.get("revision_news_ids"):
        raise ValueError("Gate 1 decision must not contain revision_news_ids")
    corrected_types = corrected_types or {}
    canonical: dict[str, dict[str, Any]] = {}
    run_ids: set[str] = set()
    for artifact in artifacts:
        run_ids.add(str(artifact.get("run_id")))
        for item in artifact.get("items", []):
            news_id = item.get("news_id")
            if news_id in canonical:
                raise ValueError(f"Duplicate canonical news_id: {news_id}")
            canonical[news_id] = item
    if run_ids != {str(decision.get("run_id"))}:
        raise ValueError(f"Gate 1/artifact run_id mismatch: {sorted(run_ids)}")
    kept = decision.get("kept_news_ids", [])
    excluded = set(decision.get("excluded_news_ids", []))
    if set(kept) & excluded:
        raise ValueError("Gate 1 kept/excluded sets overlap")
    approved: list[dict[str, Any]] = []
    for news_id in kept:
        if news_id not in canonical:
            raise ValueError(f"Unknown kept news_id: {news_id}")
        item = copy.deepcopy(canonical[news_id])
        if news_id in corrected_types:
            item["news_type"] = corrected_types[news_id]
        approved.append(item)
    return {
        "run_id": decision["run_id"],
        "synthetic": bool(decision.get("synthetic")),
        "source_decision_path": source_decision_path,
        "approval_status": decision["overall_status"],
        "kept_news_count": len(kept),
        "excluded_news_count": len(excluded),
        "approved_news": approved,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision", required=True, type=Path)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--market", required=True, type=Path)
    parser.add_argument("--competitor", required=True, type=Path)
    parser.add_argument("--technology", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        decision = load_json(args.decision)
        artifacts = [load_json(path) for path in [args.market, args.competitor, args.technology, args.policy]]
        bundle = build_bundle(decision, artifacts, str(args.decision), parse_corrected_types(args.review))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "PASS", "output": str(args.output), "approved_news_count": len(bundle["approved_news"])}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
