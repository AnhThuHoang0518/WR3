---
review_gate: opportunity-threat-hitl
run_id: SYN-RUN-001
synthetic: true
overall_status: PENDING
reviewer: null
reviewed_at: null
source_artifacts:
  - workspace/artifacts/signals.json
  - workspace/artifacts/opportunity_threat.json
approved_ids: []
rejected_ids: []
revision_ids: []
---

# Opportunity / Threat HITL Review

> **Cảnh báo:** Pipeline phải dừng cho đến khi `overall_status: APPROVED` do con người xác nhận.

## Hướng dẫn review

- Chọn `APPROVE`, `REVISE` hoặc `REJECT`.
- Merge/split luôn là `REVISE`; không sửa âm thầm ID cũ.

## Tóm tắt review

- Tổng số item:
- Đã review:
- APPROVE:
- REVISE:
- REJECT:

## Review từng item

| ot_id | signal_id | proposed_type | proposed_statement | impacted_stakeholders | impact_mechanism | importance | alignment_with_signal | evidence_sufficiency | overlap_with_other_ot | review_decision | corrected_type | revised_statement | structure_change | superseded_ot_ids | replacement_ot_ids | reviewer_note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SYN-OT-001 | SYN-SIG-001 | OPPORTUNITY | Synthetic opportunity statement. | Synthetic buyer | Synthetic impact mechanism. | MEDIUM | Chưa xác minh | Chưa đủ | Không rõ | null |  |  | NONE | [] | [] | Chờ reviewer. |

## Ghi chú của reviewer

Chưa có quyết định của reviewer.

## Quyết định cuối cùng

- reviewer: null
- reviewed_at: null
- overall_status: `PENDING`
- reviewer_summary: Chưa review.
