---
review_gate: product-action-hitl
run_id: <run id>
synthetic: false
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
| <action_id> | <source_signal_id> | <target_product_or_category> | <proposed_response> | <proposed_action> | <related_opportunity> | <related_threat> | <key_product_gap> | <evidence_strength> | <strategic_fit> | <feasibility> | <urgency> | <expected_value> | <required_resources> | <review_decision> | <revised_response> | <revised_action> | <reviewer_rationale> | <final_next_step> |

## Ghi chú của reviewer

<Ghi chú của reviewer>

## Quyết định cuối cùng

- reviewer: <tên reviewer>
- reviewed_at: <ISO-8601 timestamp>
- overall_status: `PENDING`
- reviewer_summary: <tóm tắt quyết định>
