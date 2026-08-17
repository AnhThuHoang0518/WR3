#!/usr/bin/env python3
"""Build the POLICY canonical News artifact from deterministic raw input."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

NEWS_TYPE = "POLICY"
ARTIFACT_TYPE = "policy_news"
READ_COMPETITOR_CATALOG = False
RAW_REQUIRED = {
    "synthetic", "raw_news_id", "title", "source_name", "source_url",
    "published_at", "collected_at", "raw_content", "expected_candidate_type",
}


def load_json(path: Path) -> Any:
    """Load UTF-8 JSON with clear diagnostics."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc


def _catalog_aliases(path: Path | None) -> dict[str, str]:
    if not READ_COMPETITOR_CATALOG:
        return {}
    if path is None:
        raise ValueError("--competitors is required for the COMPETITOR stage")
    payload = load_json(path)
    aliases: dict[str, str] = {}
    for item in payload.get("competitors", []):
        if not item.get("active", True):
            continue
        canonical = item.get("name")
        for alias in [canonical, *item.get("aliases", [])]:
            if canonical and alias:
                aliases[str(alias).casefold()] = str(canonical)
    if not aliases:
        raise ValueError("Competitor catalog has no active names or aliases")
    return aliases


def build_artifact(raw_payload: dict[str, Any], run_id: str, competitors: Path | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Select this stage's candidates and map only supplied facts to the frozen schema."""
    if not isinstance(raw_payload.get("synthetic"), bool):
        raise ValueError("Input root must contain boolean synthetic")
    records = raw_payload.get("records")
    if not isinstance(records, list):
        raise ValueError("Input root must contain a records array")
    aliases = _catalog_aliases(competitors)
    items: list[dict[str, Any]] = []
    lineage: list[dict[str, Any]] = []
    for raw in records:
        if not isinstance(raw, dict):
            raise ValueError("Every records item must be an object")
        if raw.get("expected_candidate_type") != NEWS_TYPE:
            continue
        missing = sorted(RAW_REQUIRED - raw.keys())
        if missing:
            raise ValueError(f"{raw.get('raw_news_id', '<unknown>')}: missing {missing}")
        if not isinstance(raw["synthetic"], bool):
            raise ValueError(f"{raw['raw_news_id']}: synthetic must be boolean")
        if raw["synthetic"] is not bool(raw_payload.get("synthetic")):
            raise ValueError(f"{raw['raw_news_id']}: synthetic does not match input root")
        entities = list(raw.get("entities", []))
        catalog_matches: list[str] = []
        if READ_COMPETITOR_CATALOG:
            searchable = " ".join([
                str(raw.get("title", "")),
                str(raw.get("raw_content", "")),
                *[str(value) for value in entities],
            ]).casefold()
            catalog_matches = sorted({canonical for alias, canonical in aliases.items() if alias in searchable})
            for canonical in catalog_matches:
                if canonical not in entities:
                    entities.append(canonical)
        news_id = f"NEWS-{NEWS_TYPE}-{len(items) + 1:03d}"
        item = {
            "news_id": news_id,
            "news_type": NEWS_TYPE,
            "title": raw["title"],
            "source_name": raw["source_name"],
            "source_url": raw["source_url"],
            "published_at": raw["published_at"],
            "collected_at": raw["collected_at"],
            "geography": raw.get("geography", ["Chưa xác định"]),
            "language": raw.get("language", "vi"),
            "summary": raw.get("summary", raw["raw_content"]),
            "key_facts": raw.get("key_facts", [raw["raw_content"]]),
            "entities": entities,
            "relevance_rationale": raw.get("relevance_rationale", "Ứng viên được giữ lại để con người đánh giá mức liên quan."),
            "evidence_quality": raw.get("evidence_quality", "UNKNOWN"),
            "content_status": raw.get("content_status", "PARTIAL_TEXT"),
        }
        items.append(item)
        lineage.append({
            "raw_news_id": raw["raw_news_id"],
            "news_id": news_id,
            "catalog_matches": catalog_matches,
        })
    return {
        "artifact_type": ARTIFACT_TYPE,
        "run_id": run_id,
        "synthetic": bool(raw_payload.get("synthetic")),
        "items": items,
    }, lineage


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        raw_payload = load_json(args.input)
        artifact, lineage = build_artifact(raw_payload, args.run_id, None)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "PASS", "output": str(args.output), "count": len(artifact["items"]), "lineage": lineage}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
