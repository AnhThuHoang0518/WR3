---
review_gate: opportunity-threat-hitl
run_id: <run id>
synthetic: false
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
| <ot_id> | <signal_id> | <proposed_type> | <proposed_statement> | <impacted_stakeholders> | <impact_mechanism> | <importance> | <alignment_with_signal> | <evidence_sufficiency> | <overlap_with_other_ot> | <review_decision> | <corrected_type> | <revised_statement> | NONE | [] | [] | <reviewer_note> |

## Ghi chú của reviewer

<Ghi chú của reviewer>

## Quyết định cuối cùng

- reviewer: <tên reviewer>
- reviewed_at: <ISO-8601 timestamp>
- overall_status: `PENDING`
- reviewer_summary: <tóm tắt quyết định>
