# Input/Output Contract — Product Action HITL

## Purpose

Con người đưa ra quyết định cuối cùng cho action được đề xuất.

## Allowed inputs

- `workspace/artifacts/signals.json`
- `workspace/artifacts/opportunity_threat.json` và decision 02; chỉ O/T đã APPROVE
- `workspace/artifacts/product_mapping.json`
- `workspace/artifacts/product_gap.json`
- `workspace/artifacts/actions.json`

## Output artifacts

- `workspace/reviews/03-product-action-review.md`
- `workspace/reviews/03-product-action-decision.json`

## Item decisions and sets

- APPROVE → `approved_action_ids`; đây là final action portfolio.
- REVISE → `revision_action_ids`; quay lại stage 11.
- REJECT → `rejected_action_ids`; bị loại.
- DEFER → `deferred_action_ids`; backlog riêng, không phải immediate action.
- `reviewed_action_ids` bằng hợp bốn tập; các tập đôi một không chồng lặp.

## Overall status

Chưa review hết → PENDING; có revision → CHANGES_REQUIRED; hoàn tất không revision → APPROVED; reviewer dừng batch → REJECTED. Item APPROVE không thay thế overall APPROVED.

## Next stage

Chỉ chạy `13-mi-quality-control` khi decision manifest do con người đặt `APPROVED`.

Status: Contract v1 frozen; Skill 12 runtime logic implemented without schema changes.
