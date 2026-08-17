---
name: opportunity-threat-hitl
description: Require human review at the Opportunity / Threat HITL gate and block the pipeline unless its decision manifest is APPROVED.
---

# Opportunity / Threat HITL

## Purpose

Tạo hồ sơ để con người review mọi Opportunity/Threat và chặn pipeline cho đến khi Gate 2 decision hợp lệ có `overall_status: APPROVED`.

## Điều kiện và input

Chỉ chạy sau khi `signals.json`, `opportunity_threat.json` và lineage/coverage validation đều PASS trong cùng `run_id`.

## Quy trình runtime

1. `generate_review.py` hiển thị O/T, parent Signal và evidence summary trong Markdown `PENDING`.
2. Reviewer chọn đúng một `APPROVE`, `REVISE` hoặc `REJECT` cho mỗi `ot_id`.
3. Reviewer có thể điền `corrected_type`, `revised_statement` và note.
4. `build_decision_manifest.py` parse bảng deterministic; không đoán row lỗi.
5. `validate_decision.py` kiểm schema, union/disjoint, ID existence và gate status.

## Ngôn ngữ nội dung hướng tới reviewer

Tuân thủ [REVIEW_LANGUAGE_POLICY.md](../00-news-driven-mi-orchestrator/references/REVIEW_LANGUAGE_POLICY.md). Hồ sơ review phải trình bày phần hướng dẫn, Signal context, rationale, assumptions và evidence gaps bằng tiếng Việt. Xác nhận nội dung nhận từ stage 06–07 đã bằng tiếng Việt; hướng dẫn reviewer viết `revised_statement`, `reviewer_note` và `reviewer_summary` bằng tiếng Việt. Giữ nguyên ID, field, enum và decision token.

## Item decisions

- `APPROVE`: O/T được phép dùng sau khi overall status cũng APPROVED.
- `REJECT`: O/T bị loại khỏi downstream.
- `REVISE`: quay lại skill 07 để tạo lại O/T và review lại ID mới.

## Merge/split lineage

Merge/split luôn dùng `REVISE`. Ghi `structure_change`, `superseded_ot_ids`, `replacement_ot_ids` và reviewer note trong Markdown. Không mở rộng Gate 2 decision JSON và không tái sử dụng ID cũ âm thầm.

## Overall status

- Chưa review đủ: `PENDING`.
- Có `revision_ot_ids`: `CHANGES_REQUIRED`.
- Review đủ, không revision, có ít nhất một approved item và human metadata: `APPROVED`.
- Reviewer dừng batch hoặc không cho O/T nào đi tiếp: `REJECTED`.

## Cấm auto-approval

Review và decision ban đầu luôn `PENDING`, reviewer/timestamp null và mọi decision set rỗng. Item APPROVE không thay thế overall APPROVED. Pipeline chỉ tiếp tục khi schema và semantic validation PASS cùng human overall APPROVED.

## Validation procedure

Kiểm `reviewed_ot_ids = approved ∪ rejected ∪ revision`, ba tập rời nhau, mọi ID tồn tại và không trùng. PENDING, CHANGES_REQUIRED, REJECTED hoặc validation fail đều phải dừng.

## Allowed inputs

- workspace/artifacts/signals.json
- workspace/artifacts/opportunity_threat.json

## Forbidden inputs

- Cross-run or incomplete artifacts.
- Machine-generated approval.

## Output artifact

- `workspace/reviews/02-opportunity-threat-review.md`
- `workspace/reviews/02-opportunity-threat-decision.json`

## Required previous approval

All immediately preceding automatic stages must complete successfully.

## Next stage

`09-product-mapping`

Human approval required. No auto-approval. Pipeline must stop when status is `PENDING`, `CHANGES_REQUIRED`, or `REJECTED`.

Read [INPUT_OUTPUT_CONTRACT.md](references/INPUT_OUTPUT_CONTRACT.md), [REVIEW_INSTRUCTIONS.md](references/REVIEW_INSTRUCTIONS.md), and [REVIEW_TEMPLATE.md](references/REVIEW_TEMPLATE.md).

Status: Gate 2 runtime implemented for vertical slice 2; Contract V1 remains frozen.
