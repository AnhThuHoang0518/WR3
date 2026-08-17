#!/usr/bin/env python3
"""Generate a non-gating Markdown inspection file for Product Gap quality."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    """Load one UTF-8 JSON object."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def _bullets(values: list[Any]) -> list[str]:
    return [f"  - {value}" for value in values] if values else ["  - Không có."]


def _evidence(refs: list[dict[str, Any]]) -> list[str]:
    if not refs:
        return ["  - Không có."]
    return [
        f"  - `{ref.get('product_code')}` → {', '.join(str(field) for field in ref.get('catalog_fields', []))}"
        for ref in refs
    ]


def generate_review(product_mapping: dict[str, Any], product_gap: dict[str, Any]) -> str:
    """Render every gap beside its immutable Product Mapping requirement."""
    if product_mapping.get("run_id") != product_gap.get("run_id"):
        raise ValueError("Product Mapping and Product Gap run_id values must match")
    mapping_by_id = {
        item.get("product_mapping_id"): item for item in product_mapping.get("items", [])
    }
    lines = [
        "---",
        "review_type: PRODUCT_GAP_MANUAL_INSPECTION",
        f"run_id: {product_gap['run_id']}",
        "status: READY_FOR_REVIEW",
        "reviewer: null",
        "reviewed_at: null",
        "formal_hitl_gate: false",
        "pipeline_contract_modified: false",
        "---",
        "",
        "# Kiểm tra thủ công Product Gap",
        "",
        "> Đây là bước kiểm tra chất lượng bắt buộc trước Action Recommendation, không phải cổng HITL chính thức và không tạo decision JSON.",
        "",
        f"Tổng số Product Gap: {len(product_gap.get('items', []))}",
        "",
    ]
    for gap in product_gap.get("items", []):
        parent = mapping_by_id.get(gap.get("product_mapping_id"), {})
        lines.extend([
            f"## {gap['gap_id']} — {gap['product_mapping_id']}",
            "",
            f"- Mã Product Mapping: `{gap['product_mapping_id']}`",
            f"- Mã Signal: `{gap['signal_id']}`",
            f"- Nhóm sản phẩm thị trường: {gap['market_product_category']}",
            "- Tính năng bắt buộc:",
            *_bullets(gap.get("required_capabilities", [])),
            f"- Sản phẩm VSF đối chiếu: `{gap.get('matched_vsf_product')}`" if gap.get("matched_vsf_product") else "- Sản phẩm VSF đối chiếu: `null`",
            "- Năng lực VSF hiện có:",
            *_bullets(gap.get("current_vsf_capabilities", [])),
            "- Tính năng còn thiếu:",
            *_bullets(gap.get("missing_capabilities", [])),
            f"- Trạng thái năng lực: `{gap['capability_status']}`",
            f"- Loại khoảng trống: `{gap['gap_type']}`",
            f"- Mức độ nghiêm trọng: `{gap['gap_severity']}`",
            f"- Cơ sở so sánh: {gap['comparison_rationale']}",
            "- Tham chiếu bằng chứng portfolio:",
            *_evidence(gap.get("portfolio_evidence_refs", [])),
            "- Nội dung cần xác minh:",
            *_bullets(gap.get("validation_needed", [])),
            "",
            "### Kiểm tra bảo toàn Product Mapping",
            "",
            f"- Nhóm sản phẩm khớp nguồn: {'Có' if gap.get('market_product_category') == parent.get('market_product_category') else 'Không'}",
            f"- Danh sách tính năng khớp nguồn: {'Có' if gap.get('required_capabilities') == parent.get('required_capabilities') else 'Không'}",
            "",
            "### Danh sách kiểm tra",
            "",
            "- [ ] Sản phẩm đối chiếu có đúng nhóm sản phẩm không?",
            "- [ ] Năng lực được xác nhận là đã có bằng chứng trong catalog không?",
            "- [ ] Tính năng được ghi là còn thiếu thực sự thiếu hay chỉ chưa được catalog mô tả?",
            "- [ ] NO_MATCH và UNKNOWN có được dùng đúng không?",
            "- [ ] Có suy diễn từ tên sản phẩm không?",
            "- [ ] FULL_MATCH có quá tự tin không?",
            "- [ ] Có Product Mapping nào bị thay đổi không?",
            "- [ ] Có đề xuất hành động nào bị đưa sớm vào Product Gap không?",
            "",
        ])
    lines.extend([
        "## Kết quả kiểm tra của người dùng",
        "",
        "Sau khi kiểm tra toàn bộ mục, cập nhật `status`, `reviewer` và `reviewed_at` trong frontmatter ở đầu file.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product-mapping", required=True, type=Path)
    parser.add_argument("--product-gap", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise ValueError(f"Refusing to overwrite existing manual review: {args.output}")
        rendered = generate_review(load_json(args.product_mapping), load_json(args.product_gap))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(json.dumps({"status": "PASS", "output": str(args.output)}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
