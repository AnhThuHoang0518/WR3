#!/usr/bin/env python3
"""Validate the implementation-only raw-to-canonical News lineage sidecar."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

from validate_json_schema import load_json, validate_instance

ARTIFACT_SPECS = {
    "MARKET": "market_news.json",
    "COMPETITOR": "competitor_news.json",
    "TECHNOLOGY": "technology_news.json",
    "POLICY": "policy_news.json",
}


def _normalized_parts(value: str | Path) -> tuple[str, ...]:
    normalized = str(value).replace("\\", "/")
    return PurePosixPath(normalized).parts


def _path_matches(reported: str, actual: Path, expected_filename: str) -> bool:
    reported_parts = _normalized_parts(reported)
    actual_parts = _normalized_parts(actual.resolve())
    if not reported_parts or reported_parts[-1] != expected_filename:
        return False
    if len(reported_parts) == 1:
        return actual_parts[-1] == reported_parts[-1]
    return len(actual_parts) >= len(reported_parts) and actual_parts[-len(reported_parts):] == reported_parts


def validate_news_lineage(
    lineage: dict[str, Any],
    schema: dict[str, Any],
    artifacts: dict[str, tuple[Path, dict[str, Any]]],
    raw_input: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate schema, coverage, identity, type, path and optional raw-input lineage."""
    schema_errors = validate_instance(lineage, schema)
    errors: list[dict[str, Any]] = [
        {"code": "SCHEMA_ERROR", **error} for error in schema_errors
    ]
    canonical: dict[str, dict[str, Any]] = {}
    duplicate_canonical: set[str] = set()
    artifact_run_ids: set[str] = set()
    artifact_synthetic: set[Any] = set()
    for news_type, (artifact_path, artifact) in artifacts.items():
        artifact_run_ids.add(str(artifact.get("run_id")))
        artifact_synthetic.add(artifact.get("synthetic"))
        for item in artifact.get("items", []):
            news_id = str(item.get("news_id"))
            if news_id in canonical:
                duplicate_canonical.add(news_id)
            canonical[news_id] = {
                "news_type": news_type,
                "artifact_path": artifact_path,
                "filename": ARTIFACT_SPECS[news_type],
            }
    if duplicate_canonical:
        errors.append({"code": "DUPLICATE_CANONICAL_NEWS_ID", "news_ids": sorted(duplicate_canonical)})
    if len(artifact_run_ids) != 1 or lineage.get("run_id") not in artifact_run_ids:
        errors.append({"code": "RUN_ID_MISMATCH", "artifact_run_ids": sorted(artifact_run_ids)})
    if artifact_synthetic != {lineage.get("synthetic")}:
        errors.append({"code": "SYNTHETIC_MISMATCH"})

    mappings = lineage.get("mappings", []) if isinstance(lineage.get("mappings"), list) else []
    if lineage.get("mapping_count") != len(mappings):
        errors.append({
            "code": "MAPPING_COUNT_MISMATCH",
            "declared": lineage.get("mapping_count"),
            "actual": len(mappings),
        })
    pair_counts = Counter(
        (mapping.get("raw_news_id"), mapping.get("news_id"))
        for mapping in mappings if isinstance(mapping, dict)
    )
    duplicate_pairs = sorted(
        [{"raw_news_id": pair[0], "news_id": pair[1]} for pair, count in pair_counts.items() if count > 1],
        key=lambda item: (str(item["raw_news_id"]), str(item["news_id"])),
    )
    if duplicate_pairs:
        errors.append({"code": "DUPLICATE_MAPPING_PAIR", "pairs": duplicate_pairs})

    news_mapping_counts: Counter[str] = Counter()
    mapped_raw_ids: set[str] = set()
    for index, mapping in enumerate(mappings):
        if not isinstance(mapping, dict):
            continue
        news_id = str(mapping.get("news_id"))
        raw_news_id = str(mapping.get("raw_news_id"))
        mapped_raw_ids.add(raw_news_id)
        news_mapping_counts[news_id] += 1
        expected = canonical.get(news_id)
        if expected is None:
            errors.append({"code": "UNKNOWN_NEWS_ID", "mapping_index": index, "news_id": news_id})
            continue
        if mapping.get("news_type") != expected["news_type"]:
            errors.append({
                "code": "NEWS_TYPE_MISMATCH",
                "mapping_index": index,
                "news_id": news_id,
                "expected": expected["news_type"],
                "actual": mapping.get("news_type"),
            })
        if not _path_matches(str(mapping.get("artifact_path", "")), expected["artifact_path"], expected["filename"]):
            errors.append({
                "code": "ARTIFACT_PATH_MISMATCH",
                "mapping_index": index,
                "news_id": news_id,
                "expected_file": expected["filename"],
                "actual": mapping.get("artifact_path"),
            })

    missing_news_ids = sorted(set(canonical) - set(news_mapping_counts))
    if missing_news_ids:
        errors.append({"code": "MISSING_NEWS_LINEAGE", "news_ids": missing_news_ids})
    multiple_raw = sorted(news_id for news_id, count in news_mapping_counts.items() if news_id in canonical and count > 1)
    if multiple_raw:
        errors.append({"code": "MULTIPLE_RAW_FOR_NEWS_ID", "news_ids": multiple_raw})

    raw_input_status = "NOT_RUN"
    if raw_input is not None:
        raw_input_status = "PASS"
        records = raw_input.get("records", []) if isinstance(raw_input, dict) else []
        raw_positions: dict[str, int] = {}
        selected_raw_ids: set[str] = set()
        duplicate_raw_ids: set[str] = set()
        for position, record in enumerate(records):
            if not isinstance(record, dict) or "raw_news_id" not in record:
                continue
            raw_news_id = str(record["raw_news_id"])
            if raw_news_id in raw_positions:
                duplicate_raw_ids.add(raw_news_id)
            raw_positions[raw_news_id] = position
            if record.get("expected_candidate_type") in ARTIFACT_SPECS:
                selected_raw_ids.add(raw_news_id)
        if duplicate_raw_ids:
            errors.append({"code": "DUPLICATE_RAW_INPUT_ID", "raw_news_ids": sorted(duplicate_raw_ids)})
        missing_selected = sorted(selected_raw_ids - mapped_raw_ids)
        if missing_selected:
            errors.append({"code": "MISSING_SELECTED_RAW_LINEAGE", "raw_news_ids": missing_selected})
        unknown_raw = sorted(mapped_raw_ids - set(raw_positions))
        if unknown_raw:
            errors.append({"code": "UNKNOWN_RAW_NEWS_ID", "raw_news_ids": unknown_raw})
        for index, mapping in enumerate(mappings):
            if not isinstance(mapping, dict):
                continue
            raw_news_id = str(mapping.get("raw_news_id"))
            if raw_news_id in raw_positions and mapping.get("input_position") != raw_positions[raw_news_id]:
                errors.append({
                    "code": "INPUT_POSITION_MISMATCH",
                    "mapping_index": index,
                    "raw_news_id": raw_news_id,
                    "expected": raw_positions[raw_news_id],
                    "actual": mapping.get("input_position"),
                })
        if any(error["code"] in {
            "DUPLICATE_RAW_INPUT_ID", "MISSING_SELECTED_RAW_LINEAGE",
            "UNKNOWN_RAW_NEWS_ID", "INPUT_POSITION_MISMATCH"
        } for error in errors):
            raw_input_status = "FAIL"

    semantic_errors = [error for error in errors if error["code"] != "SCHEMA_ERROR"]
    return {
        "status": "PASS" if not errors else "FAIL",
        "schema_status": "PASS" if not schema_errors else "FAIL",
        "semantic_status": "PASS" if not semantic_errors else "FAIL",
        "raw_input_validation": raw_input_status,
        "canonical_news_count": len(canonical),
        "mapping_count": len(mappings),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lineage", required=True, type=Path)
    parser.add_argument("--market", required=True, type=Path)
    parser.add_argument("--competitor", required=True, type=Path)
    parser.add_argument("--technology", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--schema", type=Path, default=Path(__file__).resolve().parents[2] / "schemas" / "news-lineage.schema.json")
    parser.add_argument("--input", type=Path, help="Optional raw input for selected-record and input_position validation")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        artifacts = {
            "MARKET": (args.market, load_json(args.market)),
            "COMPETITOR": (args.competitor, load_json(args.competitor)),
            "TECHNOLOGY": (args.technology, load_json(args.technology)),
            "POLICY": (args.policy, load_json(args.policy)),
        }
        raw_input = load_json(args.input) if args.input else None
        result = validate_news_lineage(load_json(args.lineage), load_json(args.schema), artifacts, raw_input)
    except (OSError, ValueError, TypeError) as exc:
        result = {
            "status": "FAIL", "schema_status": "FAIL", "semantic_status": "FAIL",
            "raw_input_validation": "FAIL", "errors": [{"code": "INPUT_ERROR", "message": str(exc)}],
        }
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
