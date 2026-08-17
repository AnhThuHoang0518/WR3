# Input/Output Contract — Opportunity / Threat

## Purpose

Chuyển signal hợp lệ thành Opportunity hoặc Threat có impact mechanism rõ.

## Allowed inputs

- `workspace/artifacts/signals.json` thuộc run hiện tại.

## Forbidden inputs

- News thô.
- Reference catalogs.
- Signal ID không tồn tại.

## Output artifact

- `workspace/artifacts/opportunity_threat.json`
- Validate bằng `../schemas/output.schema.json`.

## Semantic invariants

- Mỗi `ot_id` tham chiếu đúng một `signal_id` tồn tại.
- `type` chỉ nhận `OPPORTUNITY` hoặc `THREAT`.
- Một signal có thể sinh cả Opportunity và Threat; mỗi record vẫn phải có ID riêng, rationale và impact mechanism riêng.
- Không được tạo generic benefit hoặc threat suy diễn quá mức.
- Nội dung không bị giới hạn độ dài nhưng phải dễ hiểu và đầy đủ để reviewer nhận ra tác động, stakeholder và cơ chế tạo giá trị/rủi ro.

## Next stage

`08-opportunity-threat-hitl`

Status: Contract v1 frozen; detailed logic pending.
