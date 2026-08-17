#!/usr/bin/env python3
"""Build the Gate 3 decision manifest from human-edited review Markdown."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

VALID_DECISIONS = {"APPROVE", "REVISE", "REJECT", "DEFER"}
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
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return data, index + 1
        if not line.startswith(" ") and ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = _scalar(value)
    raise ValueError("YAML frontmatter is not closed")


def parse_review(text: str) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Parse deterministic Gate 3 rows without inferring human decisions."""
    lines = text.splitlines()
    meta, start = _frontmatter(lines)
    header_index = next((i for i in range(start, len(lines)) if lines[i].startswith("| action_id |")), None)
    if header_index is None:
        raise ValueError("Gate 3 review table header not found")
    headers = [cell.strip() for cell in lines[header_index].strip().strip("|").split("|")]
    if not {"action_id", "review_decision"}.issubset(headers):
        raise ValueError("Gate 3 table lacks action_id or review_decision")
    decisions = {name: [] for name in VALID_DECISIONS}
    errors: list[dict[str, str]] = []
    seen: set[str] = set()
    for line in lines[header_index + 2:]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != len(headers):
            errors.append({"action_id": "<unparsed>", "message": "table column count mismatch"})
            continue
        row = dict(zip(headers, cells))
        action_id = row["action_id"]
        if not action_id or action_id in seen:
            errors.append({"action_id": action_id or "<empty>", "message": "empty or duplicate action_id"})
            continue
        seen.add(action_id)
        choice = row["review_decision"].upper()
        if choice in {"", "PENDING", "NULL"}:
            continue
        if choice not in VALID_DECISIONS:
            errors.append({"action_id": action_id, "message": f"invalid decision {choice!r}"})
            continue
        decisions[choice].append(action_id)
    status = str(meta.get("overall_status") or "PENDING").upper()
    if status not in VALID_STATUSES:
        errors.append({"action_id": "<manifest>", "message": f"invalid overall_status {status!r}"})
        status = "PENDING"
    if errors:
        status = "PENDING"
    reviewed = decisions["APPROVE"] + decisions["REJECT"] + decisions["REVISE"] + decisions["DEFER"]
    manifest = {
        "review_gate": "product-action-hitl", "run_id": str(meta.get("run_id") or ""),
        "overall_status": status, "reviewed_action_ids": reviewed,
        "approved_action_ids": decisions["APPROVE"], "rejected_action_ids": decisions["REJECT"],
        "revision_action_ids": decisions["REVISE"], "deferred_action_ids": decisions["DEFER"],
        "reviewer": meta.get("reviewer"), "reviewed_at": meta.get("reviewed_at"),
        "reviewer_summary": meta.get("reviewer_summary"),
        "synthetic": str(meta.get("synthetic", "false")).lower() == "true",
    }
    return manifest, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        if args.output.exists() and not args.overwrite:
            raise ValueError(f"Refusing to overwrite Gate 3 decision: {args.output}")
        manifest, errors = parse_review(args.review.read_text(encoding="utf-8"))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "PASS" if not errors else "FAIL", "output": str(args.output), "parse_errors": errors}, ensure_ascii=False))
        return 0 if not errors else 1
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
