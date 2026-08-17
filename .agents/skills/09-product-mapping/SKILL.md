---
name: product-mapping
description: Identify neutral market-fit product categories, solution types, and required capabilities from Signals and only Gate 2-approved Opportunity/Threat items. Use after Gate 2 is human-APPROVED and before any VSF portfolio comparison, Product Gap, or action analysis.
---

# Product Mapping

## Purpose

Chuyển Signal và O/T đã được Gate 2 phê duyệt thành loại sản phẩm hoặc giải pháp phù hợp với nhu cầu thị trường, cùng các capability cần có. Giữ góc nhìn outside-in và không đối chiếu với portfolio VSF.

## When to use

Chỉ dùng sau khi Gate 2 có human decision `overall_status: APPROVED`, validation PASS và `pipeline_can_continue: true`. Dừng trước Product Gap.

## Required inputs

- `signals.json` trong cùng `run_id`.
- `approved_opportunity_threat_bundle.json` chỉ chứa O/T đã APPROVE.
- Gate 2 decision manifest để xác nhận trạng thái và tập approved/rejected/revision.

Đọc [INPUT_OUTPUT_CONTRACT.md](references/INPUT_OUTPUT_CONTRACT.md) trước khi phân tích.

## Forbidden inputs

- `products.json` hoặc bất kỳ VSF product catalog/option list nào.
- Product Gap output, Action output hoặc code từ Skill 10–13.
- O/T bị REJECT, REVISE hoặc chưa review.
- Internet và ví dụ thị trường không có trong evidence hiện tại.

## Core distinction

- Product Mapping trả lời: thị trường cần loại sản phẩm, giải pháp, module, platform, service hay technology nào?
- Product Gap trả lời ở stage sau: portfolio VSF đáp ứng requirement đó đến đâu?

Không suy luận VSF đang có gì, không chấm VSF fit, không nêu portfolio gap và không đề xuất build/buy/partner hoặc action.

## Analysis procedure

1. Xác nhận Gate 2 APPROVED và chỉ lấy O/T trong `approved_ot_ids`.
2. Đọc nguyên văn Signal và approved O/T liên quan.
3. Xác định stakeholder đang gặp market problem cụ thể và bối cảnh phát sinh.
4. Xác định outcome vận hành hoặc business mà thị trường cần đạt.
5. Chọn market product category trung lập, không dùng thương hiệu hay tên sản phẩm VSF.
6. Chọn product/solution type phù hợp với frozen schema.
7. Viết đủ các required capability cần thiết dưới dạng tính năng mà sản phẩm phải cung cấp; mỗi tính năng phải dễ hiểu và đủ rõ để kiểm chứng ở Product Gap.
8. Xác định buyer/decision-maker chỉ khi Signal hoặc approved O/T hỗ trợ.
9. Ghi deployment context đúng mức evidence cho phép.
10. Giải thích fit rationale bằng quan hệ problem → capability → outcome → approved O/T.
11. Tách điều đã có evidence khỏi inference và ghi rõ buyer, technical, procurement hoặc regulatory validation còn thiếu.
12. Kiểm tra lại không có VSF mapping, rejected O/T, Product Gap field hoặc action.

Không tạo mapping chỉ để đạt coverage. Một approved O/T được phép không map nếu có rationale; nhiều approved O/T chỉ gộp khi thật sự có chung market problem/requirement.

## Market problem

Viết một vấn đề hoặc nhu cầu cụ thể: ai gặp vấn đề, vấn đề vận hành/business là gì, xảy ra trong bối cảnh nào và outcome nào cần đạt.

Không dùng chủ đề chung như “Smart City đang phát triển”, “AI quan trọng” hoặc “cần chuyển đổi số”. Không chép Signal title hoặc O/T statement làm market problem.

## Market product category

Dùng category trung lập theo ngôn ngữ thị trường, ví dụ về hình thức: integrated city operations platform, municipal data interoperability platform hoặc edge analytics assurance solution. Không dùng tên thương hiệu, tên sản phẩm VSF hay một action làm category.

### Đặt tên `market_product_category`

- Tên phải giúp reviewer hiểu loại offering này làm công việc chính gì; không biến category thành danh sách capability hoặc câu mô tả market problem.
- Không ép mọi category vào một công thức cố định. Có thể chọn các hướng như: loại offering + nhiệm vụ chính; outcome + bối cảnh triển khai; đối tượng được quản lý + chức năng; hoặc dịch vụ kiểm chứng/đảm bảo + đối tượng được kiểm chứng.
- Ưu tiên động từ hoặc danh từ hành động cụ thể như `điều phối`, `giám sát`, `đo lường`, `kiểm chứng`, `hợp nhất`; tránh chuỗi dài các danh từ chung như `tích hợp`, `giải pháp`, `hạ tầng`, `công nghệ` nếu không nói rõ công việc chính.
- Không giới hạn độ dài tên. Tên có thể dài nếu cần để reviewer hiểu đúng loại offering và công việc chính.
- Không dùng nhãn `Product N` như tên offering, không đưa thương hiệu/portfolio VSF, Product Gap hoặc Action vào category.

## Product or solution type

Tuân thủ frozen schema hiện tại. Khi schema không giới hạn enum, ưu tiên một loại rõ nghĩa như `PLATFORM`, `APPLICATION`, `MODULE`, `DEVICE`, `INFRASTRUCTURE`, `MANAGED_SERVICE`, `DATA_SERVICE`, `INTEGRATION_LAYER`, `AI_MODEL` hoặc `HYBRID_SOLUTION`; không sửa schema để hợp thức hóa output.

## Required capabilities

`required_capabilities` là danh sách **tính năng chính, nổi bật của loại sản phẩm**, không phải business outcome, nguyên tắc quản trị hoặc đặc tả kỹ thuật triển khai.

- Không ấn định số lượng tính năng. Ghi đủ để mô tả đúng sản phẩm, nhưng không thêm tính năng không liên quan chỉ để làm danh sách dài hơn.
- Viết theo cách người review có thể hình dung rõ sản phẩm nhận thông tin gì, xử lý hoặc hỗ trợ việc gì và tạo ra kết quả gì.
- Ưu tiên tính năng tạo nên giá trị và sự khác biệt chính của sản phẩm.
- Không liệt kê các chức năng hỗ trợ phổ biến như phân quyền, audit log, phê duyệt, metadata, lưu giữ dữ liệu hoặc cấu hình kỹ thuật, trừ khi chính chức năng đó là trọng tâm trực tiếp của Signal/O/T.
- Không mô tả cách hiện thực như giao thức, cấu trúc API, kiến trúc cloud/edge, cơ chế lưu trữ hoặc chi tiết tích hợp cấp thấp.
- Mỗi tính năng vẫn phải đủ cụ thể để Product Gap có thể đối chiếu với capability có bằng chứng trong portfolio.

Không chứa tên VSF, capability portfolio giả định hoặc action. Không dùng capability chung chung như “có AI”, “có data”, “dễ dùng”, “platform” hoặc “công nghệ hiện đại”.

## Target buyers

Chỉ ghi buyer hoặc decision-maker được evidence hỗ trợ. Phân biệt buyer với user, operator, regulator và beneficiary. Nếu evidence chỉ xác định operator, không tự nâng thành budget owner.

## Deployment context

Ghi nơi và điều kiện triển khai: thành phố, khu đô thị, cơ quan quản lý, trung tâm điều hành hoặc hệ thống tích hợp nhiều đơn vị. Chỉ ghi cloud, edge hoặc hybrid khi Signal/O/T hỗ trợ.

## External market examples

Field này optional. Với run synthetic không gọi internet và không bịa công ty/sản phẩm thật. Bỏ field nếu evidence hiện có không nêu ví dụ phù hợp.

## Evidence and validation needed

Ghi rõ requirement nào được Signal/O/T hỗ trợ, phần nào là inference, và điều gì còn cần buyer, technical, procurement hoặc regulatory validation. Không biến uncertainty thành fact.

## Ngôn ngữ nội dung hướng tới reviewer

Tuân thủ [REVIEW_LANGUAGE_POLICY.md](../00-news-driven-mi-orchestrator/references/REVIEW_LANGUAGE_POLICY.md). Viết `market_problem`, `required_capabilities`, `target_buyers`, `deployment_context`, `fit_rationale`, `evidence_or_validation_needed`, rationale trong coverage report và nội dung kiểm tra thủ công bằng tiếng Việt. `market_product_category`, `product_or_solution_type`, ID, enum, tên riêng và thuật ngữ kỹ thuật khó dịch có thể giữ nguyên; phần giải thích bao quanh phải bằng tiếng Việt.

## Runtime procedure

1. Dùng `prepare_context.py` để tạo context chỉ từ approved inputs.
2. Áp dụng trực tiếp hướng dẫn semantic trong file này để Codex tạo `product_mapping_draft.json`; không dùng keyword mapper.
3. Dùng `build_artifact.py` để chuẩn hóa, sinh ID `PM-NNN` và validate frozen schema.
4. Dùng `validate_artifact.py` và shared lineage validator để kiểm schema, lineage, boundary và semantic warnings.
5. Dùng `audit_forbidden_dependencies.py` để xác nhận runtime không phụ thuộc portfolio/Product Gap/Action.
6. Dùng `build_coverage_report.py` để ghi mapped/unmapped rationale mà không ép coverage 100%.
7. Dùng `generate_manual_review.py` để tạo file kiểm tra thủ công; file này không phải HITL gate và không có decision JSON.

## Common mistakes

- Map Signal trực tiếp sang sản phẩm VSF hoặc dùng tên sản phẩm VSF làm category/capability.
- Biến Opportunity thành category mà chưa xác định market problem.
- Liệt kê technology nhưng không giải thích solution và outcome.
- Viết capability quá chung, biến capability thành business outcome hoặc liệt kê quá nhiều chức năng phụ/chi tiết kỹ thuật.
- Dùng rejected/revision O/T.
- Đưa Product Gap, action hoặc build/buy/partner vào output.
- Bịa external example.
- Đọc `products.json` trong runtime Skill 09.

## Validation procedure

1. Kiểm JSON parse và frozen output schema.
2. Kiểm `product_mapping_id` unique, đúng dạng `PM-NNN`.
3. Kiểm `signal_id` tồn tại và `related_ot_ids` không rỗng.
4. Kiểm mọi related O/T thuộc approved bundle; không có rejected/revision leakage.
5. Kiểm O/T và Signal cùng lineage hoặc có cross-signal rationale rõ.
6. Kiểm không có field Product Gap, Action hay VSF fit.
7. Kiểm category trung lập; mỗi capability là một tính năng dễ hiểu, đủ nghĩa, unique và không phải generic token.
8. Kiểm không lặp Signal title hoặc chép nguyên O/T statement thành mapping.
9. Kiểm không có duplicate mapping/link set.
10. Kiểm coverage có rationale cho mọi approved O/T hoặc Signal chưa map.
11. Kiểm dependency audit PASS.

`ERROR` áp dụng cho schema, lineage hoặc boundary violation. `WARNING` áp dụng cho semantic quality cần người dùng xem lại. Manual inspection không thay đổi Pipeline Contract V1.

## Output and stop condition

Ghi `product_mapping.json`, validation/coverage/dependency reports và `product-mapping-review.md`. Đặt Product Mapping `COMPLETED`, giữ Skill 10–13 `NOT_IN_SCOPE`, rồi dừng trước Product Gap.
