# Input/Output Contract — Action Recommendation

## Purpose

Đề xuất response và next step có thể truy vết từ signal, O/T, mapping và gap.

## Allowed inputs

- `workspace/artifacts/approved_opportunity_threat_bundle.json`.
- `workspace/reviews/02-opportunity-threat-decision.json` với `overall_status = APPROVED`.
- `workspace/artifacts/product_mapping.json`.
- `workspace/artifacts/product_gap.json`.
- `workspace/reviews/product-gap-review.md` với `status = REVIEWED_ACCEPTED`.

## Output artifact

- `workspace/artifacts/actions.json`
- Validate bằng `../schemas/output.schema.json`.

## Semantic invariants

- Mỗi action giữ `source_signal_id`, một hoặc nhiều `related_ot_ids`, `product_mapping_id`, một hoặc nhiều `gap_ids`.
- `recommended_response` chỉ nhận `MONITOR`, `VALIDATE`, `PREPARE`, `ACT`.
- `proposed_action` không generic; `next_step` phải thực thi được.
- Action không có owner. `next_step` không ghi ngày, thời hạn, khoảng thời gian hoặc target timeline.
- Nội dung Action không bị giới hạn độ dài nhưng phải dễ hiểu và đầy đủ.
- Nếu response là ACT trong khi evidence yếu hoặc capability UNKNOWN, `rationale`, `validation_required` và `decision_risks` phải cảnh báo rõ.
- Action do AI đề xuất chưa phải final decision.
- Không sử dụng catalog hoặc claim capability ngoài Product Gap.
- Action phải dừng tại Gate 3 PENDING cho tới human review.

## Next stage

`12-product-action-hitl`

Status: Contract v1 frozen; Skill 11 runtime logic implemented without schema changes.
