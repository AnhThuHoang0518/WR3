#!/usr/bin/env python3
"""Generate a non-gating Markdown inspection file for Product Mapping quality."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def _bullets(values: list[str]) -> str:
    return "\n".join(f"  - {value}" for value in values) if values else "  - Không có."


def generate_review(context: dict[str, Any], mapping: dict[str, Any]) -> str:
    """Render every mapping beside its approved Signal/O-T evidence."""
    if context.get("run_id") != mapping.get("run_id"):
        raise ValueError("Context and Product Mapping run_id values must match")
    signals = {item.get("signal_id"): item for item in context.get("relevant_signals", [])}
    ots = {item.get("ot_id"): item for item in context.get("approved_opportunity_threat", [])}
    lines = [
        "---",
        "review_type: PRODUCT_MAPPING_MANUAL_INSPECTION",
        f"run_id: {context['run_id']}",
        "status: READY_FOR_REVIEW",
        "reviewer: null",
        "reviewed_at: null",
        "formal_hitl_gate: false",
        "pipeline_contract_modified: false",
        "---",
        "",
        "# Kiểm tra thủ công Product Mapping",
        "",
        "> Đây là file kiểm tra chất lượng bắt buộc trước Product Gap, không phải HITL gate và không tạo decision JSON.",
        "",
        f"Tổng số Product Mapping: {len(mapping.get('items', []))}",
        "",
    ]
    for item in mapping.get("items", []):
        signal = signals.get(item.get("signal_id"), {})
        related = [ots.get(ot_id, {}) for ot_id in item.get("related_ot_ids", [])]
        lines.extend([
            f"## {item['product_mapping_id']} — {item['market_product_category']}",
            "",
            f"- Mã Signal: `{item['signal_id']}`",
            f"- Nội dung Signal: {signal.get('signal_statement', '')}",
            f"- Mã O/T đã duyệt: {', '.join(item.get('related_ot_ids', []))}",
            "- Nội dung O/T:",
            *[f"  - `{ot.get('ot_id')}`: {ot.get('statement', '')}" for ot in related],
            f"- Vấn đề thị trường: {item['market_problem']}",
            f"- Nhóm sản phẩm thị trường: {item['market_product_category']}",
            f"- Loại sản phẩm/giải pháp: `{item['product_or_solution_type']}`",
            "- Năng lực bắt buộc:",
            _bullets(item.get("required_capabilities", [])),
            "- Nhóm khách hàng mục tiêu:",
            _bullets(item.get("target_buyers", [])),
            f"- Bối cảnh triển khai: {item['deployment_context']}",
            f"- Lý do phù hợp với nhu cầu thị trường: {item['fit_rationale']}",
            "- Bằng chứng/xác minh cần bổ sung:",
            _bullets(item.get("evidence_or_validation_needed", [])),
        ])
        if "external_market_examples" in item:
            lines.extend(["- Ví dụ thị trường bên ngoài:", _bullets(item.get("external_market_examples", []))])
        lines.extend([
            "", "### Danh sách kiểm tra", "",
            "- [ ] Không ánh xạ sang danh mục sản phẩm VSF.",
            "- [ ] Nhóm sản phẩm được mô tả trung lập từ nhu cầu thị trường.",
            "- [ ] Vấn đề thị trường đủ cụ thể.",
            "- [ ] Các tính năng được mô tả dễ hiểu, đầy đủ và cho thấy sản phẩm thực sự làm gì.",
            "- [ ] Không liệt kê chức năng hỗ trợ hoặc chi tiết kỹ thuật không cần thiết.",
            "- [ ] Chỉ dựa trên O/T đã được duyệt.",
            "- [ ] Không trùng với mapping khác.",
            "- [ ] Không tạo mapping chỉ để đạt coverage.",
            "- [ ] Không suy diễn quá bằng chứng.",
            "",
        ])
    lines.extend([
        "## Kết quả kiểm tra của người dùng", "",
        "Sau khi kiểm tra toàn bộ mục, cập nhật `status`, `reviewer` và `reviewed_at` trong frontmatter ở đầu file để cho phép chạy Product Gap.", "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", required=True, type=Path)
    parser.add_argument("--product-mapping", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        rendered = generate_review(load_json(args.context), load_json(args.product_mapping))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(json.dumps({"status": "PASS", "output": str(args.output)}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
