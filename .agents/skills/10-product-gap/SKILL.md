---
name: product-gap
description: Compare reviewed Product Mapping market requirements with the read-only VSF products catalog, determine evidence-backed capability gaps, validate portfolio provenance and lineage, and prepare a non-gating manual inspection. Use only after Gate 2 is APPROVED, Product Mapping validation passes, and its manual inspection is REVIEWED_ACCEPTED; stop before Action Recommendation.
---

# Product Gap

## Purpose

So sánh market product requirement đã duyệt với portfolio và capability hiện tại của VSF. Chỉ xác nhận capability khi `references/products.json` cung cấp bằng chứng trực tiếp.

## Required inputs

- `product_mapping.json` đã validate PASS và được manual inspection `REVIEWED_ACCEPTED`.
- `references/products.json` ở chế độ chỉ đọc.
- `signals.json` để kiểm tra lineage.
- `approved_opportunity_threat_bundle.json` để kiểm tra lineage và chống rejected O/T leakage gián tiếp.
- Gate 2 decision và Product Mapping validation/dependency reports để kiểm tra precondition.

Đọc [INPUT_OUTPUT_CONTRACT.md](references/INPUT_OUTPUT_CONTRACT.md) và frozen [output.schema.json](schemas/output.schema.json) trước khi phân tích.

## Forbidden behavior

- Không sửa Product Mapping, category, required capabilities hoặc catalog.
- Không thêm capability VSF nếu catalog không ghi rõ; không suy diễn từ tên sản phẩm, thương hiệu hoặc kiến thức nền.
- Không kế thừa capability của ecosystem/enabling/legacy/historical product sang Core VSF.
- Không dùng competitor catalog, Signal hoặc O/T làm bằng chứng capability VSF.
- Không biến `NOT_DOCUMENTED` thành `CONFIRMED_ABSENT`.
- Không tạo Action, recommendation, Build/Buy/Partner, owner, priority hoặc next step.
- Không chạy Skill 11–13.

## Procedure

1. Xác minh Gate 2 `APPROVED`, Product Mapping `COMPLETED`, validation/dependency audit PASS và manual inspection `REVIEWED_ACCEPTED` có reviewer/timestamp.
2. Chụp hash các artifact, gate, contract và catalog được bảo vệ.
3. Chạy `scripts/prepare_context.py` để tạo context bất biến; không match portfolio ở bước này.
4. Chạy `scripts/build_capability_matrix.py` để tạo candidate aid và comparison scaffold. Candidate theo từ khóa chỉ hỗ trợ khám phá, không phải kết luận.
5. Đọc từng mapping, category, required capability, catalog record và catalog rule. Tự soạn `product_gap_draft.json`; không hard-code kết luận semantic trong script.
6. Phân loại category trong `comparison_rationale`: `EXACT_CATEGORY`, `ADJACENT_CATEGORY`, `NO_CATEGORY_MATCH` hoặc `UNCERTAIN_CATEGORY`.
7. So sánh từng capability trong intermediate analysis bằng `CONFIRMED_PRESENT`, `CONFIRMED_ABSENT`, `PARTIALLY_SUPPORTED`, `NOT_DOCUMENTED` hoặc `NOT_APPLICABLE`.
8. Chọn final `capability_status`, `gap_type`, `gap_severity`, evidence và validation cần thêm theo frozen schema.
9. Build artifact bằng `scripts/build_artifact.py`; script chỉ chuẩn hóa và gán `GAP-###`, không tạo kết luận mới.
10. Chạy schema/lineage/status/boundary validation, portfolio evidence validation và coverage report.
11. Tạo `product-gap-review.md` để người dùng kiểm tra thủ công; đây không phải formal HITL gate.
12. Xác minh hash protected không đổi và dừng trước Action Recommendation.

## Category matching

- `EXACT_CATEGORY`: catalog mô tả trực tiếp cùng loại sản phẩm/giải pháp.
- `ADJACENT_CATEGORY`: category gần nhưng scope khác; giải thích ranh giới và không coi là full match chỉ vì từ khóa giống.
- `NO_CATEGORY_MATCH`: catalog không có product category phù hợp; không tạo current capability claim.
- `UNCERTAIN_CATEGORY`: catalog chưa đủ thông tin để kết luận category.

Frozen schema không có field category match, vì vậy ghi đúng token và rationale trong `comparison_rationale`; không sửa schema.

## Capability comparison

Tiêu chí tiên quyết là reviewer phải hiểu rõ từng tính năng đang được so sánh. Mỗi capability cần lột tả tính năng là gì: hệ thống nhận hoặc dùng thông tin nào, thực hiện hoặc hỗ trợ việc gì, và kết quả mà người dùng hay đơn vị vận hành nhận được. Không dùng nhãn ngắn, chung chung như “AI analytics”, “dashboard”, “integration” hoặc “automation” nếu không giải thích chức năng cụ thể.

- Không giới hạn độ dài mô tả capability. Viết đủ dài khi cần để thể hiện trọn chức năng và ranh giới của nó.
- Với `current_vsf_capabilities`, vẫn phải giữ claim đúng bằng chứng catalog; nếu wording catalog ngắn, giải thích rõ phần đã có và chưa có trong `comparison_rationale`.
- Với `missing_capabilities`, mô tả rõ hành vi hoặc kết quả sản phẩm còn thiếu, không chỉ nêu tên công nghệ hay chủ đề.
- `comparison_rationale` phải giúp reviewer thấy trực tiếp required capability nào đã được hỗ trợ, hỗ trợ một phần, chưa được chứng minh hoặc chưa có category phù hợp.

- `CONFIRMED_PRESENT`: catalog ghi rõ capability và evidence ref truy được đến đúng record/field.
- `CONFIRMED_ABSENT`: chỉ dùng khi catalog cung cấp bằng chứng loại trừ rõ ràng; không suy ra từ việc không ghi.
- `PARTIALLY_SUPPORTED`: catalog capability hỗ trợ một phần requirement; nêu rõ phần được hỗ trợ và phần chưa chứng minh.
- `NOT_DOCUMENTED`: catalog không đủ nội dung để kết luận có hoặc không.
- `NOT_APPLICABLE`: capability không áp dụng với candidate đã đánh giá; không đồng nghĩa capability bị thiếu.

Giữ các giá trị chi tiết này trong capability matrix/draft; final artifact chỉ dùng enum frozen.

## Final capability status

- `FULL_MATCH`: có category phù hợp; mọi capability trọng yếu được evidence hỗ trợ; `matched_vsf_product` khác null, current/evidence không rỗng và missing rỗng.
- `PARTIAL_MATCH`: có product phù hợp hoặc adjacent; có ít nhất một capability được xác nhận và ít nhất một capability thiếu/chưa đủ; current, missing và evidence đều không rỗng.
- `NO_MATCH`: không có product cùng category phù hợp; `matched_vsf_product` null và current rỗng. Rationale phải ghi `NO_CATEGORY_MATCH`.
- `UNKNOWN`: catalog không đủ để kết luận; current rỗng, validation không rỗng, và không trình bày `NOT_DOCUMENTED` như missing đã xác nhận.

## Gap type and severity

Chỉ dùng frozen `gap_type`: `FEATURE`, `TECHNOLOGY`, `DATA`, `INTEGRATION`, `HARDWARE`, `OPERATION`, `PARTNER_ECOSYSTEM`, `COMMERCIAL_MODEL`, `COMPLIANCE`, `UNKNOWN`.

Chọn severity theo ảnh hưởng đến đáp ứng market requirement: capability bắt buộc có bị thiếu, có chặn deployment/procurement, có thể bổ sung hay chỉ cần validation. Chỉ dùng `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`, `UNKNOWN`. Không tách mọi capability thành gap riêng chỉ để tăng số record.

## Portfolio evidence

- Mọi `current_vsf_capabilities` phải trùng capability được ghi trong catalog record và có ref chứa `product_code` cùng `catalog_fields: [capabilities]`.
- Product dùng cho confirmed current capability phải có `allowed_gap_baseline=true`; các role khác chỉ là candidate cần validation.
- Evidence về category có thể dẫn `product_type` hoặc `smart_city_domains`, nhưng không thay thế capability evidence.
- Không dùng evidence ref không liên quan cho một claim khác.

## Ngôn ngữ nội dung hướng tới reviewer

Tuân thủ [REVIEW_LANGUAGE_POLICY.md](../00-news-driven-mi-orchestrator/references/REVIEW_LANGUAGE_POLICY.md). Viết `current_vsf_capabilities`, `missing_capabilities`, `comparison_rationale`, `validation_needed`, rationale trong coverage/evidence report và nội dung kiểm tra thủ công bằng tiếng Việt. Giữ nguyên ID, product code, field/schema, enum, tên sản phẩm, tên riêng và thuật ngữ kỹ thuật khó dịch.

Không áp đặt độ dài hoặc cấu trúc câu cố định. Chỉ yêu cầu nội dung dễ hiểu, đầy đủ và không làm mờ ranh giới giữa tính năng đã có, còn thiếu và chưa đủ bằng chứng.

## Common mistakes

- Coi không ghi trong catalog là không có.
- Match chỉ vì tên/từ khóa giống hoặc so sánh khác category mà không giải thích.
- Đổi Product Mapping để làm portfolio trông phù hợp hơn.
- Tạo `FULL_MATCH` khi evidence chưa bao phủ mọi capability trọng yếu.
- Dùng `UNKNOWN` và `NO_MATCH` lẫn nhau.
- Kế thừa capability ecosystem/enabling technology sang Core VSF.
- Đưa Action hoặc Build/Buy/Partner vào Product Gap.
- Tạo capability claim nhưng thiếu portfolio evidence.

## Validation

- Validate frozen schema và required enum/conditional rules.
- Validate Product Mapping, Signal và approved O/T lineage; phát hiện orphan/rejected leakage.
- So sánh nguyên vẹn `product_mapping_id`, `signal_id`, category và required capabilities.
- Resolve product/evidence refs với catalog và xác minh exact capability claims.
- Kiểm tra category rationale, missing/status consistency và forbidden Action fields.
- So sánh hash catalog, Product Mapping, gate và Contract V1 trước/sau.

Output cuối là `artifacts/product_gap.json`; review là `reviews/product-gap-review.md`. Stage tiếp theo theo contract là `11-action-recommendation`, nhưng skill này luôn dừng trước stage đó.
