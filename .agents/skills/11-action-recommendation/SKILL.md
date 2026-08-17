---
name: action-recommendation
description: Turn Gate 2-approved Opportunity/Threat items, reviewed Product Mapping and REVIEWED_ACCEPTED Product Gaps into specific, traceable action proposals for human review. Use only after Product Gap validation and manual review pass; validate full lineage and stop at Product Action HITL without treating proposals as final decisions.
---

# Action Recommendation

## Purpose

Chuyển approved O/T, Product Mapping và reviewed Product Gap thành action cụ thể để con người xem xét. Action chỉ là đề xuất, chưa phải quyết định cuối.

## Required inputs

- `signals.json`.
- `approved_opportunity_threat_bundle.json` và Gate 2 decision `APPROVED`.
- `product_mapping.json` đã COMPLETED.
- `product_gap.json` đã COMPLETED và validate PASS.
- `product-gap-review.md` có `REVIEWED_ACCEPTED`, reviewer và timestamp.

Đọc [INPUT_OUTPUT_CONTRACT.md](references/INPUT_OUTPUT_CONTRACT.md) và frozen [output.schema.json](schemas/output.schema.json) trước khi soạn draft.

## Forbidden inputs and behavior

- Không dùng rejected/revision O/T, excluded news, action ngoài pipeline hoặc catalog.
- Không sửa Signal, O/T, Product Mapping, Product Gap hoặc source artifact.
- Không tạo/khẳng định capability VSF ngoài evidence có trong Product Gap.
- Không tự tạo human approval, không đánh dấu action final và không bypass Gate 3.
- Không tạo action chung chung hoặc chỉ để coverage 100%.

## Procedure

1. Xác minh Gate 2, Mapping, Gap và manual-review preconditions.
2. Chạy `scripts/prepare_context.py`; lọc rejected O/T và giữ full lineage.
3. Chạy `scripts/build_action_matrix.py` để tạo candidate analysis, không phải final action.
4. Đọc trực tiếp context, matrix, approved O/T, Mapping và Gap; tự soạn `actions_draft.json` ngoài Python.
5. Gắn mỗi action với `source_signal_id`, `related_ot_ids`, `product_mapping_id`, `gap_ids` và target category.
6. Chọn response, priority, Build/Buy/Partner, Pilot/Productize theo evidence; ghi validation, next step, outcome và risks.
7. Build deterministic `ACTION-###`, validate schema/lineage/quality/duplicates, tạo coverage và summary.
8. Chuyển sang Product Action HITL với PENDING review; dừng.

## Core action logic

Mỗi Action phải tận dụng approved Opportunity, giảm approved Threat, đóng/xác thực Gap, kiểm chứng market requirement, chuẩn bị capability/partner/deployment, hoặc thực hiện pilot/productization khi evidence đủ. Không bắt buộc mỗi Gap sinh một Action và không gộp gap không liên quan.

## Recommended response

- `MONITOR`: evidence/tác động còn sớm; nêu đối tượng theo dõi, trigger và thời điểm review lại.
- `VALIDATE`: buyer requirement, capability, gap, regulatory hoặc procurement evidence chưa đủ; nêu giả định, phương pháp, output và pass/fail.
- `PREPARE`: signal quan trọng nhưng chưa nên triển khai đầy đủ; nêu deliverable, function liên quan và điều kiện chuyển `ACT`.
- `ACT`: evidence đủ mạnh, gap/requirement rõ và next step khả thi. Không chọn chỉ vì importance cao.

Khi Gap `UNKNOWN` hoặc evidence yếu, không chọn `ACT` trừ controlled pilot có risk/validation rõ.

## Build, Buy, Partner

Chỉ dùng frozen `BUILD`, `BUY`, `PARTNER`, `HYBRID`, `UNDECIDED`. Dựa trên gap type, current capability, time-to-market, dependency, evidence và strategic control; không mặc định `BUILD`. Thiếu căn cứ thì dùng `UNDECIDED` và ghi validation.

## Pilot or Productize

Chỉ dùng frozen `PILOT`, `PRODUCTIZE`, `BOTH`, `NEITHER`, `UNDECIDED`. Pilot kiểm chứng requirement/capability/deployment; Productize đóng gói khả năng lặp lại. Không chọn Productize khi buyer, gap, capability hoặc deployment model chưa rõ.

## Priority

Chỉ dùng `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`; cân importance, severity, confidence, urgency, feasibility và dependency. Không gán mọi action HIGH.

## Action content

- `proposed_action`: cụ thể, liên quan trực tiếp Gap.
- `next_step`: nói rõ việc cần làm và output cần thu được; không chỉ “nghiên cứu thêm/theo dõi thị trường”. Không ghi ngày, thời hạn, khoảng thời gian hoặc target timeline.
- `expected_outcome`: kết quả của action, không phải market opportunity.
- `decision_risks`: assumption, dependency, resource, capability, regulatory hoặc procurement uncertainty.
- `validation_required`: bằng chứng và tiêu chí cần trước quyết định tiếp theo.
- Không có trường owner trong Action. Không đề xuất cá nhân, nhóm hay function chịu trách nhiệm.
- Không giới hạn độ dài câu hoặc số câu. Tiêu chí tiên quyết là nội dung dễ hiểu, đầy đủ và không để reviewer phải đoán việc cần làm.

## Ngôn ngữ nội dung hướng tới reviewer

Tuân thủ [REVIEW_LANGUAGE_POLICY.md](../00-news-driven-mi-orchestrator/references/REVIEW_LANGUAGE_POLICY.md). Viết `proposed_action`, `rationale`, `validation_required`, `next_step`, `expected_outcome`, `decision_risks`, action summary và rationale trong coverage report bằng tiếng Việt. Giữ nguyên ID, field/schema, enum, tên riêng và thuật ngữ kỹ thuật khó dịch.

## Common mistakes

- Action không gắn Gap hoặc dùng rejected O/T.
- Chuyển Mapping thành Action ngay; mọi action đều ACT/BUILD/HIGH.
- Action chung chung, không có validation criterion hoặc next step dễ hiểu.
- Gộp gap không liên quan, tạo action chỉ để đủ coverage, hoặc tự coi action là final.

## Validation

Validate frozen schema; Signal/approved O/T/Mapping/Gap lineage; rejected leakage; specificity; enums; gap relevance; source immutability; duplicate actions; capability-claim boundary và non-final status.

Output là `artifacts/actions.json` và `artifacts/action_summary.json`. Stage kế tiếp là `12-product-action-hitl`; không chạy QC.
