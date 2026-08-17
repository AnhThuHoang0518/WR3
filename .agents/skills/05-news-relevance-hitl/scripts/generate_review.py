#!/usr/bin/env python3
"""Generate a deterministic, unreviewed News Relevance HITL Markdown file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

TYPE_ORDER = {"MARKET": 0, "COMPETITOR": 1, "TECHNOLOGY": 2, "POLICY": 3}
FIELDS = [
    "news_id", "current_news_type", "title", "source_name", "source_url",
    "published_at", "collected_at", "geography", "language", "summary",
    "key_facts", "entities", "relevance_rationale", "evidence_quality",
    "content_status", "relevance_decision", "relevance_reason",
    "corrected_news_type", "duplicate_of_news_id", "reviewer_note",
]


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc


def _cell(value: Any) -> str:
    if isinstance(value, list):
        value = "<br>".join(str(item) for item in value)
    if value is None:
        value = "null"
    return str(value).replace("|", "&#124;").replace("\r", " ").replace("\n", " ").strip()


def _yaml_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def generate_review(
    artifact_paths: list[Path], template_path: Path, run_id: str, display_paths: list[str] | None = None
) -> str:
    """Combine validated artifacts into a PENDING review without decisions."""
    template = template_path.read_text(encoding="utf-8")
    if "| news_id | current_news_type |" not in template or "overall_status: PENDING" not in template:
        raise ValueError("REVIEW_TEMPLATE.md does not contain the expected Gate 1 structure")
    items: list[dict[str, Any]] = []
    synthetic_values: set[bool] = set()
    for artifact_path in artifact_paths:
        artifact = load_json(artifact_path)
        if artifact.get("run_id") != run_id:
            raise ValueError(f"Run ID mismatch in {artifact_path}")
        if not isinstance(artifact.get("synthetic"), bool):
            raise ValueError(f"synthetic must be boolean in {artifact_path}")
        synthetic_values.add(artifact["synthetic"])
        items.extend(artifact.get("items", []))
    if len(synthetic_values) != 1:
        raise ValueError("All News artifacts must use the same synthetic value")
    synthetic = synthetic_values.pop()
    items.sort(key=lambda item: (
        TYPE_ORDER.get(item.get("news_type"), 99),
        item.get("published_at", ""),
        item.get("news_id", ""),
    ))
    shown_paths = display_paths or [str(path) for path in artifact_paths]
    lines = [
        "---",
        "review_gate: news-relevance-hitl",
        f"run_id: {_yaml_quote(run_id)}",
        f"synthetic: {str(synthetic).lower()}",
        "overall_status: PENDING",
        "reviewer: null",
        "reviewed_at: null",
        "reviewer_summary: null",
        "source_artifacts:",
        *[f"  - {_yaml_quote(path)}" for path in shown_paths],
        "approved_ids: []",
        "rejected_ids: []",
        "revision_ids: []",
        "---",
        "",
        "# News Relevance HITL Review",
        "",
        "> **Cảnh báo:** Pipeline đang dừng tại Gate 1. Không đổi `PENDING` thành `APPROVED` nếu chưa có human review đầy đủ.",
        "",
        "Điền `KEEP`, `EXCLUDE` hoặc `NEEDS_REVISION` cho từng item. Quảng cáo và duplicate phải được đánh giá, không bị loại tự động.",
        "",
        "## Tóm tắt review",
        "",
        f"- Tổng số item: {len(items)}",
        "- Đã review: 0",
        "- KEEP: 0",
        "- EXCLUDE: 0",
        "- NEEDS_REVISION: 0",
        "",
        "## Review từng item",
        "",
        "| " + " | ".join(FIELDS) + " |",
        "| " + " | ".join(["---"] * len(FIELDS)) + " |",
    ]
    for item in items:
        row = [
            item.get("news_id"), item.get("news_type"), item.get("title"),
            item.get("source_name"), item.get("source_url"), item.get("published_at"),
            item.get("collected_at"), item.get("geography"), item.get("language"),
            item.get("summary"), item.get("key_facts"), item.get("entities"),
            item.get("relevance_rationale"), item.get("evidence_quality"),
            item.get("content_status"), "PENDING", "", "null", "null", "",
        ]
        lines.append("| " + " | ".join(_cell(value) for value in row) + " |")
    lines.extend([
        "", "## Ghi chú của reviewer", "", "", "",
        "## Quyết định cuối cùng", "",
        "- reviewer: null", "- reviewed_at: null", "- overall_status: `PENDING`",
        "- reviewer_summary: null", "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", required=True, type=Path)
    parser.add_argument("--competitor", required=True, type=Path)
    parser.add_argument("--technology", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    artifact_paths = [args.market, args.competitor, args.technology, args.policy]
    try:
        review = generate_review(artifact_paths, args.template, args.run_id)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(review, encoding="utf-8")
        print(json.dumps({"status": "PASS", "output": str(args.output)}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
