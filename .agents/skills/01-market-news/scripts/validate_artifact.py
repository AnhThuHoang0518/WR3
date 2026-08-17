#!/usr/bin/env python3
"""Validate a MARKET News artifact against schema and runtime invariants."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

VALIDATORS = Path(__file__).resolve().parents[2] / "00-news-driven-mi-orchestrator" / "scripts" / "validators"
sys.path.insert(0, str(VALIDATORS))
from validate_json_schema import load_json, validate_instance  # noqa: E402

NEWS_TYPE = "MARKET"
ARTIFACT_TYPE = "market_news"
ID_PATTERN = re.compile(r"^NEWS-MARKET-[0-9]{3}$")


def _valid_datetime(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return "T" in value
    except ValueError:
        return False


def validate_artifact(artifact: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    """Combine frozen-schema validation with deterministic stage checks."""
    errors = validate_instance(artifact, schema)
    ids: list[str] = []
    if artifact.get("artifact_type") != ARTIFACT_TYPE:
        errors.append({"path": "$.artifact_type", "message": f"expected {ARTIFACT_TYPE}"})
    if not isinstance(artifact.get("synthetic"), bool):
        errors.append({"path": "$.synthetic", "message": "must be boolean"})
    for index, item in enumerate(artifact.get("items", [])):
        news_id = item.get("news_id", f"item[{index}]")
        ids.append(news_id)
        prefix = f"$.items[{index}] ({news_id})"
        if not isinstance(news_id, str) or ID_PATTERN.fullmatch(news_id) is None:
            errors.append({"path": f"{prefix}.news_id", "message": f"expected NEWS-{type}-NNN"})
        if item.get("news_type") != NEWS_TYPE:
            errors.append({"path": f"{prefix}.news_type", "message": f"expected {NEWS_TYPE}"})
        for field in ("title", "summary", "source_url"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append({"path": f"{prefix}.{field}", "message": "must be a non-empty string"})
        if item.get("source_url") and not urlparse(item["source_url"]).scheme:
            errors.append({"path": f"{prefix}.source_url", "message": "must be a URI"})
        for field in ("published_at", "collected_at"):
            if not _valid_datetime(item.get(field)):
                errors.append({"path": f"{prefix}.{field}", "message": "must be an ISO-8601 date-time"})
        facts = item.get("key_facts")
        if not isinstance(facts, list) or not facts or any(not isinstance(fact, str) or not fact.strip() for fact in facts):
            errors.append({"path": f"{prefix}.key_facts", "message": "must contain at least one non-empty fact"})
    duplicate_ids = sorted({value for value in ids if ids.count(value) > 1})
    if duplicate_ids:
        errors.append({"path": "$.items[*].news_id", "message": f"duplicate IDs: {duplicate_ids}"})
    return {"status": "PASS" if not errors else "FAIL", "artifact_type": ARTIFACT_TYPE, "item_count": len(ids), "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        result = validate_artifact(load_json(args.artifact), load_json(args.schema))
    except (OSError, ValueError, TypeError) as exc:
        result = {"status": "FAIL", "artifact_type": ARTIFACT_TYPE, "errors": [{"path": "$", "message": str(exc)}]}
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
