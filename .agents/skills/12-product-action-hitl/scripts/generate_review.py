#!/usr/bin/env python3
"""Generate a deterministic, fully PENDING Product Action Gate 3 Markdown review."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PRIORITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
REVIEW_FIELDS = [
    "evidence_strength", "strategic_fit", "feasibility", "urgency", "expected_value",
    "required_resources", "review_decision",
    "revised_response", "revised_action", "reviewer_rationale", "final_next_step",
]
ACTION_FIELDS = [
    "action_id", "source_signal_id", "related_approved_ot", "target_product_or_category",
    "related_product_mapping", "related_product_gap", "proposed_response", "proposed_action",
    "rationale", "priority", "build_buy_partner", "pilot_or_productize", "validation_required",
    "next_step", "expected_outcome", "decision_risks",
]


def load_json(path: Path) -> dict[str, Any]:
    """Load one UTF-8 JSON object."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def _cell(value: Any) -> str:
    if isinstance(value, list):
        value = "<br>".join(str(item) for item in value)
    if value is None:
        value = "null"
    return str(value).replace("|", "&#124;").replace("\r", " ").replace("\n", " ").strip()


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def generate_review(
    signals: dict[str, Any], approved_bundle: dict[str, Any], product_mapping: dict[str, Any],
    product_gap: dict[str, Any], actions: dict[str, Any], source_paths: list[str],
) -> str:
    """Render every Action with upstream context and no machine decision."""
    run_ids = {source.get("run_id") for source in [signals, approved_bundle, product_mapping, product_gap, actions]}
    if len(run_ids) != 1 or None in run_ids:
        raise ValueError("Gate 3 sources must share one run_id")
    run_id = str(actions["run_id"])
    mappings = {item.get("product_mapping_id"): item for item in product_mapping.get("items", [])}
    gaps = {item.get("gap_id"): item for item in product_gap.get("items", [])}
    ots = {item.get("ot_id"): item for item in approved_bundle.get("approved_opportunity_threat", [])}
    items = sorted(actions.get("items", []), key=lambda item: (
        PRIORITY_ORDER.get(item.get("priority"), 99),
        str(item.get("target_product_or_category", "")).casefold(), str(item.get("action_id", "")),
    ))
    headers = ACTION_FIELDS + REVIEW_FIELDS
    lines = [
        "---", "review_gate: product-action-hitl", f"run_id: {_quote(run_id)}",
        f"synthetic: {str(bool(actions.get('synthetic'))).lower()}", "overall_status: PENDING",
        "reviewer: null", "reviewed_at: null", "reviewer_summary: null", "source_artifacts:",
        *[f"  - {_quote(path)}" for path in source_paths],
        "approved_ids: []", "rejected_ids: []", "revision_ids: []", "deferred_ids: []", "---", "",
        "# Cổng HITL 3 — Kiểm tra hành động sản phẩm", "",
        "> **Cảnh báo:** Pipeline đang dừng tại Gate 3. Không đổi `PENDING` thành `APPROVED` nếu chưa review đầy đủ mọi Action.", "",
        "Chọn đúng một quyết định cho từng Action: `APPROVE`, `REVISE`, `REJECT` hoặc `DEFER`.", "",
        "## Tóm tắt kiểm tra", "", f"- Tổng số Action: {len(items)}", "- Đã kiểm tra: 0",
        "- APPROVE: 0", "- REVISE: 0", "- REJECT: 0", "- DEFER: 0", "",
        "## Kiểm tra từng Action", "", "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for action in items:
        mapping = mappings.get(action.get("product_mapping_id"), {})
        related_gaps = [gaps.get(gap_id, {}) for gap_id in action.get("gap_ids", [])]
        related_ots = [ots.get(ot_id, {}) for ot_id in action.get("related_ot_ids", [])]
        row = [
            action.get("action_id"), action.get("source_signal_id"),
            [f"{item.get('ot_id')} ({item.get('type')}): {item.get('statement')}" for item in related_ots],
            action.get("target_product_or_category"),
            f"{action.get('product_mapping_id')}: {mapping.get('market_product_category', '')}",
            [f"{gap.get('gap_id')} ({gap.get('capability_status')}, {gap.get('gap_type')}, {gap.get('gap_severity')})" for gap in related_gaps],
            action.get("recommended_response"), action.get("proposed_action"), action.get("rationale"),
            action.get("priority"), action.get("build_buy_partner"), action.get("pilot_or_productize"),
            action.get("validation_required", []), action.get("next_step"),
            action.get("expected_outcome"), action.get("decision_risks", []),
            "Chưa đánh giá", "Chưa đánh giá", "Chưa đánh giá", "Chưa đánh giá", "Chưa đánh giá",
            "Chưa xác định", "PENDING", "", "", "Chờ reviewer.", "Chờ quyết định con người.",
        ]
        lines.append("| " + " | ".join(_cell(value) for value in row) + " |")
    lines.extend([
        "", "## Ghi chú của reviewer", "", "Chưa có quyết định của reviewer.", "",
        "## Quyết định cuối cùng", "", "- reviewer: null", "- reviewed_at: null",
        "- overall_status: `PENDING`", "- reviewer_summary: null", "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--signals", required=True, type=Path)
    parser.add_argument("--approved-ot-bundle", required=True, type=Path)
    parser.add_argument("--product-mapping", required=True, type=Path)
    parser.add_argument("--product-gap", required=True, type=Path)
    parser.add_argument("--actions", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise ValueError(f"Refusing to overwrite Gate 3 review: {args.output}")
        sources = [args.signals, args.approved_ot_bundle, args.product_mapping, args.product_gap, args.actions]
        review = generate_review(
            load_json(args.signals), load_json(args.approved_ot_bundle), load_json(args.product_mapping),
            load_json(args.product_gap), load_json(args.actions), [str(path) for path in sources],
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
