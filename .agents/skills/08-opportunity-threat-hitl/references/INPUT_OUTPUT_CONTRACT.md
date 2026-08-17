# Input/Output Contract — Opportunity / Threat HITL

## Purpose

Con người review Opportunity/Threat trước khi Product Mapping sử dụng.

## Allowed inputs

- `workspace/artifacts/signals.json`
- `workspace/artifacts/opportunity_threat.json`

## Output artifacts

- `workspace/reviews/02-opportunity-threat-review.md`
- `workspace/reviews/02-opportunity-threat-decision.json`

## Item decisions and sets

- `APPROVE` → `approved_ot_ids`.
- `REVISE` → `revision_ot_ids`; quay lại stage 07.
- `REJECT` → `rejected_ot_ids`; không được đi tiếp.
- `reviewed_ot_ids` bằng hợp ba tập trên; các tập đôi một không chồng lặp.

Chỉ `approved_ot_ids` được Product Mapping sử dụng.

## Merge/split rule

Merge hoặc split phải được ghi trong Markdown bằng `structure_change`, `superseded_ot_ids`, `replacement_ot_ids`. Quyết định item phải là `REVISE`, overall status phải là `CHANGES_REQUIRED`, và stage 07 phải tạo ID mới. Không sửa âm thầm hoặc tái sử dụng ID cũ. ID mới phải đi qua Gate 2 lần nữa trước khi được APPROVE.

V1 không thêm merge/split mapping vào decision JSON; Markdown giữ đề xuất lineage và decision manifest giữ các ID cũ cần revision.

## Overall status

Áp dụng policy chung: chưa review hết → PENDING; có revision → CHANGES_REQUIRED; hoàn tất không revision → APPROVED; dừng batch → REJECTED.

## Next stage

Chỉ chạy `09-product-mapping` khi decision manifest do con người đặt `APPROVED`.

Status: Contract v1 frozen; detailed logic pending.
