#!/usr/bin/env python3
"""Build a Gate 1 decision manifest from a human-editable Markdown review."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

VALID_DECISIONS = {"KEEP", "EXCLUDE", "NEEDS_REVISION"}
VALID_STATUSES = {"PENDING", "APPROVED", "CHANGES_REQUIRED", "REJECTED"}


def _scalar(value: str) -> Any:
    value = value.strip()
    if value.lower() in {"null", "~", ""}:
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1].replace("''", "'")
    return value


def _frontmatter(lines: list[str]) -> tuple[dict[str, Any], int]:
    if not lines or lines[0].strip() != "---":
        raise ValueError("Review must start with YAML frontmatter")
    data: dict[str, Any] = {}
    for index in range(1, len(lines)):
        line = lines[index]
        if line.strip() == "---":
            return data, index + 1
        if line.startswith(" ") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = _scalar(value)
    raise ValueError("YAML frontmatter is not closed")


def parse_review(text: str) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Parse the deterministic Gate 1 table; never infer an unreadable decision."""
    lines = text.splitlines()
    meta, start = _frontmatter(lines)
    header_index = next((i for i in range(start, len(lines)) if lines[i].startswith("| news_id |")), None)
    if header_index is None:
        raise ValueError("Review table header not found")
    headers = [cell.strip() for cell in lines[header_index].strip().strip("|").split("|")]
    required = {"news_id", "relevance_decision"}
    if not required.issubset(headers):
        raise ValueError("Review table lacks news_id or relevance_decision")
    decisions = {"KEEP": [], "EXCLUDE": [], "NEEDS_REVISION": []}
    errors: list[dict[str, str]] = []
    seen: set[str] = set()
    for line in lines[header_index + 2:]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != len(headers):
            errors.append({"news_id": "<unparsed>", "message": "table column count mismatch"})
            continue
        row = dict(zip(headers, cells))
        news_id = row["news_id"]
        if not news_id:
            errors.append({"news_id": "<empty>", "message": "news_id is empty"})
            continue
        if news_id in seen:
            errors.append({"news_id": news_id, "message": "duplicate review row"})
            continue
        seen.add(news_id)
        decision = row["relevance_decision"].strip().upper()
        if decision in {"", "PENDING", "NULL"}:
            continue
        if decision not in VALID_DECISIONS:
            errors.append({"news_id": news_id, "message": f"invalid decision {decision!r}"})
            continue
        decisions[decision].append(news_id)
    status = str(meta.get("overall_status") or "PENDING").upper()
    if status not in VALID_STATUSES:
        errors.append({"news_id": "<manifest>", "message": f"invalid overall_status {status!r}"})
        status = "PENDING"
    if errors:
        status = "PENDING"
    reviewed = decisions["KEEP"] + decisions["EXCLUDE"] + decisions["NEEDS_REVISION"]
    manifest = {
        "review_gate": "news-relevance-hitl",
        "run_id": str(meta.get("run_id") or ""),
        "overall_status": status,
        "reviewed_news_ids": reviewed,
        "kept_news_ids": decisions["KEEP"],
        "excluded_news_ids": decisions["EXCLUDE"],
        "revision_news_ids": decisions["NEEDS_REVISION"],
        "reviewer": meta.get("reviewer"),
        "reviewed_at": meta.get("reviewed_at"),
        "reviewer_summary": meta.get("reviewer_summary"),
        "synthetic": str(meta.get("synthetic", "false")).lower() == "true",
    }
    return manifest, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        manifest, parse_errors = parse_review(args.review.read_text(encoding="utf-8"))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "PASS" if not parse_errors else "FAIL", "output": str(args.output), "parse_errors": parse_errors}, ensure_ascii=False))
        return 0 if not parse_errors else 1
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
