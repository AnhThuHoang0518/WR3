#!/usr/bin/env python3
"""Generate an unreviewed Gate 2 Markdown from Signals and Opportunity/Threat records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

FIELDS = [
    "ot_id", "signal_id", "proposed_type", "proposed_statement", "impacted_stakeholders",
    "impact_mechanism", "importance", "alignment_with_signal", "evidence_sufficiency",
    "overlap_with_other_ot", "review_decision", "corrected_type", "revised_statement",
    "structure_change", "superseded_ot_ids", "replacement_ot_ids", "reviewer_note",
]
TYPE_ORDER = {"OPPORTUNITY": 0, "THREAT": 1}


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load JSON {path}: {exc}") from exc


def _cell(value: Any) -> str:
    if isinstance(value, list):
        value = "<br>".join(str(item) for item in value)
    if value is None:
        value = "null"
    return str(value).replace("|", "&#124;").replace("\r", " ").replace("\n", " ").strip()


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def generate_review(
    signals: dict[str, Any], opportunity_threat: dict[str, Any], template: str,
    run_id: str, signal_path: str, ot_path: str,
) -> str:
    """Render every O/T as PENDING and include parent Signal/evidence context."""
    if "| ot_id | signal_id |" not in template or "overall_status: PENDING" not in template:
        raise ValueError("Gate 2 review template has an unexpected structure")
    if signals.get("run_id") != run_id or opportunity_threat.get("run_id") != run_id:
        raise ValueError("Gate 2 source run_id mismatch")
    synthetic = signals.get("synthetic")
    if synthetic is not opportunity_threat.get("synthetic"):
        raise ValueError("Gate 2 sources must share the same synthetic flag")
    if not isinstance(synthetic, bool):
        raise ValueError("Gate 2 sources must expose boolean synthetic")
    signal_map = {item["signal_id"]: item for item in signals.get("items", [])}
    items = sorted(
        opportunity_threat.get("items", []),
        key=lambda item: (item.get("signal_id", ""), TYPE_ORDER.get(item.get("type"), 99), item.get("ot_id", "")),
    )
    for item in items:
        if item.get("signal_id") not in signal_map:
            raise ValueError(f"Orphan O/T in review input: {item.get('ot_id')}")
    lines = [
        "---", "review_gate: opportunity-threat-hitl", f"run_id: {_quote(run_id)}",
        f"synthetic: {'true' if synthetic else 'false'}", "overall_status: PENDING", "reviewer: null", "reviewed_at: null",
        "reviewer_summary: null", "source_artifacts:", f"  - {_quote(signal_path)}", f"  - {_quote(ot_path)}",
        "approved_ids: []", "rejected_ids: []", "revision_ids: []", "---", "",
        "# Review HITL Cơ hội / Rủi ro (Opportunity / Threat)", "",
        "> **Cảnh báo:** Pipeline đang dừng tại Gate 2. Không đổi `PENDING` thành `APPROVED` nếu chưa có human review đầy đủ.", "",
        "Chọn `APPROVE`, `REVISE` hoặc `REJECT`. Merge/split luôn là `REVISE` và phải ghi lineage trong Markdown.", "",
        "Phạm vi đánh giá: Signal mô tả biến động thị trường; mọi O/T phải nêu tác động cụ thể đối với VSF/Vingroup. Signal không đủ căn cứ liên hệ có thể không sinh O/T.", "",
        "## Tóm tắt review", "", f"- Tổng số item: {len(items)}", "- Đã review: 0", "- APPROVE: 0", "- REVISE: 0", "- REJECT: 0", "",
        "## Ngữ cảnh Signal", "",
    ]
    for signal in signals.get("items", []):
        lines.extend([
            f"### {signal['signal_id']} — {signal['signal_title']}", "",
            f"- Tuyên bố: {signal['signal_statement']}",
            f"- ID bằng chứng: {', '.join(signal['evidence_news_ids'])}",
            f"- Tóm tắt bằng chứng: {signal['evidence_summary']}", "",
        ])
    lines.extend(["## Lý do O/T và khoảng trống bằng chứng", ""])
    for item in items:
        lines.extend([
            f"- `{item['ot_id']}` lý do: {item['rationale']}",
            f"  - Giả định: {'; '.join(item['assumptions']) or 'Không có'}",
            f"  - Khoảng trống bằng chứng: {'; '.join(item['evidence_gaps']) or 'Không có'}",
        ])
    lines.extend(["", "## Review từng item", "", "| " + " | ".join(FIELDS) + " |", "| " + " | ".join(["---"] * len(FIELDS)) + " |"])
    for item in items:
        row = [
            item["ot_id"], item["signal_id"], item["type"], item["statement"],
            item["impacted_stakeholders"], item["impact_mechanism"], item["importance"],
            "", "", "", "PENDING", "null", "null", "NONE", "[]", "[]", "",
        ]
        lines.append("| " + " | ".join(_cell(value) for value in row) + " |")
    lines.extend([
        "", "## Ghi chú của reviewer", "", "", "",
        "## Quyết định cuối cùng", "", "- reviewer: null", "- reviewed_at: null",
        "- overall_status: `PENDING`", "- reviewer_summary: null", "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--signals", required=True, type=Path)
    parser.add_argument("--opportunity-threat", required=True, type=Path)
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        review = generate_review(
            load_json(args.signals), load_json(args.opportunity_threat),
            args.template.read_text(encoding="utf-8"), args.run_id,
            str(args.signals), str(args.opportunity_threat),
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(review, encoding="utf-8")
        print(json.dumps({"status": "PASS", "output": str(args.output)}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
