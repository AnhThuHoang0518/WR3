---
name: product-action-hitl
description: Generate and validate Product Action HITL Gate 3 review artifacts for every proposed Action, supporting APPROVE, REVISE, REJECT and DEFER decisions. Use after validated Action Recommendation output; never auto-approve, keep PENDING runs blocked, and separate approved actions from deferred backlog only after explicit human review.
---

# Product Action HITL

## Purpose

Cho con người kiểm tra và quyết định cuối cùng đối với Action do AI đề xuất. `actions.json` không phải final portfolio.

## Required inputs

- `signals.json`.
- `approved_opportunity_threat_bundle.json`.
- `product_mapping.json`.
- `product_gap.json`.
- `actions.json` đã validate schema và lineage PASS.

Đọc [INPUT_OUTPUT_CONTRACT.md](references/INPUT_OUTPUT_CONTRACT.md), [REVIEW_INSTRUCTIONS.md](references/REVIEW_INSTRUCTIONS.md), [REVIEW_TEMPLATE.md](references/REVIEW_TEMPLATE.md) và frozen [review-decision.schema.json](schemas/review-decision.schema.json).

## Human decisions

- `APPROVE`: đưa Action vào final approved action portfolio sau khi overall gate APPROVED.
- `REVISE`: quay về Skill 11; không dùng làm final action.
- `REJECT`: loại khỏi final portfolio nhưng giữ artifact lịch sử.
- `DEFER`: lưu backlog, không coi là immediate action.

## Gate status

- Chưa review hết: `PENDING`.
- Có ít nhất một `REVISE`: `CHANGES_REQUIRED`.
- Review hết, không revision và có ít nhất một approved action theo frozen schema/rule: `APPROVED`.
- Reviewer dừng toàn batch: `REJECTED`.

`reviewed_action_ids` phải bằng hợp đôi một disjoint của approved, rejected, revision và deferred sets. Item approval không thay overall approval.

## Review criteria

Kiểm tra approved O/T lineage, đúng Mapping/Gap, response level, Build/Buy/Partner, Pilot/Productize, priority, evidence, feasibility, next step, defer suitability, specificity, duplicates và nhu cầu tách/gộp. Không yêu cầu owner hoặc timeline.

## Procedure

1. Chạy `scripts/generate_review.py` để hiển thị mọi Action với decision `PENDING`.
2. Chạy `scripts/build_decision_manifest.py`; review chưa chỉnh phải tạo decision PENDING với mọi ID set rỗng.
3. Chạy `scripts/validate_decision.py` để kiểm schema, set semantics, source IDs, status, reviewer metadata và continuation.
4. Khi PENDING, giữ pipeline BLOCKED tại `PRODUCT_ACTION_HITL`; không tạo approved/deferred bundle và không chạy QC.
5. Sau explicit human review, build approved/deferred bundles bằng script tương ứng; chỉ approved immediate actions được chuyển sang QC.

## No auto-approval

- Không tự điền decision, reviewer note, reviewer/timestamp hoặc `APPROVE`.
- Không sửa review thay reviewer và không coi actions.json là final.
- Không tạo bundle khi gate PENDING/CHANGES_REQUIRED/REJECTED.
- Không cho pipeline tiếp tục nếu overall status khác APPROVED hoặc semantic validation fail.

## Validation

Validate schema; duplicate/unknown IDs; reviewed union/disjoint sets; all actions reviewed for non-PENDING; overall status rules; reviewer/timestamp; revision routing; pipeline continuation và approved/deferred separation.

Output là `reviews/03-product-action-review.md` và `reviews/03-product-action-decision.json`. Chỉ chạy `13-mi-quality-control` sau explicit human `APPROVED`; Bước 8 dừng tại PENDING Gate 3.
