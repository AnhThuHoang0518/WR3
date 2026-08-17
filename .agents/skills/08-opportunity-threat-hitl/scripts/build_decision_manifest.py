#!/usr/bin/env python3
"""Build the Gate 2 decision manifest from human-edited review Markdown."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

VALID_DECISIONS = {"APPROVE", "REJECT", "REVISE"}
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
        if not line.startswith(" ") and ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = _scalar(value)
    raise ValueError("YAML frontmatter is not closed")


def parse_review(text: str) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Parse deterministic Gate 2 rows; never infer an unreadable item decision."""
    lines = text.splitlines()
    meta, start = _frontmatter(lines)
    header_index = next((i for i in range(start, len(lines)) if lines[i].startswith("| ot_id |")), None)
    if header_index is None:
        raise ValueError("Gate 2 review table header not found")
    headers = [cell.strip() for cell in lines[header_index].strip().strip("|").split("|")]
    if not {"ot_id", "review_decision"}.issubset(headers):
        raise ValueError("Gate 2 review table lacks ot_id or review_decision")
    decisions = {"APPROVE": [], "REJECT": [], "REVISE": []}
    errors: list[dict[str, str]] = []
    seen: set[str] = set()
    for line in lines[header_index + 2:]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != len(headers):
            errors.append({"ot_id": "<unparsed>", "message": "table column count mismatch"})
            continue
        row = dict(zip(headers, cells))
        ot_id = row["ot_id"]
        if not ot_id or ot_id in seen:
            errors.append({"ot_id": ot_id or "<empty>", "message": "empty or duplicate ot_id"})
            continue
        seen.add(ot_id)
        decision = row["review_decision"].upper()
        if decision in {"", "PENDING", "NULL"}:
            continue
        if decision not in VALID_DECISIONS:
            errors.append({"ot_id": ot_id, "message": f"invalid decision {decision!r}"})
            continue
        decisions[decision].append(ot_id)
    status = str(meta.get("overall_status") or "PENDING").upper()
    if status not in VALID_STATUSES:
        errors.append({"ot_id": "<manifest>", "message": f"invalid overall_status {status!r}"})
        status = "PENDING"
    if errors:
        status = "PENDING"
    reviewed = decisions["APPROVE"] + decisions["REJECT"] + decisions["REVISE"]
    manifest = {
        "review_gate": "opportunity-threat-hitl",
        "run_id": str(meta.get("run_id") or ""),
        "overall_status": status,
        "reviewed_ot_ids": reviewed,
        "approved_ot_ids": decisions["APPROVE"],
        "rejected_ot_ids": decisions["REJECT"],
        "revision_ot_ids": decisions["REVISE"],
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
