---
review_gate: product-action-hitl
run_id: SYN-RUN-001
synthetic: true
overall_status: PENDING
reviewer: null
reviewed_at: null
source_artifacts:
  - workspace/artifacts/signals.json
  - workspace/artifacts/opportunity_threat.json
  - workspace/artifacts/product_mapping.json
  - workspace/artifacts/product_gap.json
  - workspace/artifacts/actions.json
approved_ids: []
rejected_ids: []
revision_ids: []
deferred_ids: []
---

# Product Action HITL Review

> **Cảnh báo:** Pipeline phải dừng cho đến khi `overall_status: APPROVED` do con người xác nhận.

## Hướng dẫn review

- Chọn APPROVE, REVISE, REJECT hoặc DEFER.
- APPROVE là final action; DEFER chỉ vào backlog.

## Tóm tắt review

- Tổng số item:
- Đã review:
- APPROVE:
- REVISE:
- REJECT:
- DEFER:

## Review từng item

| action_id | source_signal_id | target_product_or_category | proposed_response | proposed_action | related_opportunity | related_threat | key_product_gap | evidence_strength | strategic_fit | feasibility | urgency | expected_value | required_resources | review_decision | revised_response | revised_action | reviewer_rationale | final_next_step |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SYN-ACT-001 | SYN-SIG-001 | Synthetic market category | VALIDATE | Validate the synthetic capability requirement. | SYN-OT-001 |  | SYN-GAP-001 | Chưa xác minh | Chưa đánh giá | Chưa đánh giá | Chưa đánh giá | Chưa đánh giá | Chưa đánh giá |  |  | null |  |  | Chờ reviewer. | Đợi quyết định con người. |

## Ghi chú của reviewer

Chưa có quyết định của reviewer.

## Quyết định cuối cùng

- reviewer: null
- reviewed_at: null
- overall_status: `PENDING`
- reviewer_summary: Chưa review.
