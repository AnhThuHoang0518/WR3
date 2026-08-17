---
name: signal-synthesis
description: Synthesize structured news inputs into market-intelligence signals.
---

# Signal Synthesis

## Purpose

Tổng hợp News đã được Gate 1 KEEP thành thay đổi có ý nghĩa, có thể truy vết và đủ rõ để stage Opportunity / Threat đánh giá. Không tạo O/T, Product hoặc Action tại stage này.

## Điều kiện và input bắt buộc

- Gate 1 decision phải validate PASS và có `overall_status: APPROVED`.
- Chỉ đọc `approved_news_bundle.json`, được tạo nguyên văn từ `kept_news_ids`.
- Không đọc News EXCLUDE, catalog hoặc portfolio VSF.

## LLM trong phiên chat bắt buộc

- Agent đang chạy skill trong phiên chat phải trực tiếp đọc `approved_news_bundle.json`, suy luận và viết nội dung Signal.
- Không gọi OpenAI API hoặc một LLM bên ngoài từ script để viết Signal.
- Không dùng rule, keyword hay template deterministic để thay cho việc suy luận của LLM đối với News thật.
- `build_artifact.py` chỉ phục vụ synthetic fixture; không được dùng script này để tạo Signal cho live run.
- Temperature của model đang chạy trong phiên chat không phải tham số của skill. Không tự khai báo hoặc giả lập một giá trị temperature trong runtime.
- Sau khi LLM viết `signals.json`, dùng script chỉ để validate schema, lineage và coverage.

## Synthesis procedure

1. Xác định vấn đề, buyer shift, competitor movement, technology change, policy pressure hoặc deployment pattern trong từng News.
2. Nhóm News khi chúng có cùng change mechanism, không chỉ cùng từ khóa.
3. Chỉ tạo Signal khi trả lời được điều gì thay đổi, chuyển từ đâu sang đâu và vì sao quan trọng.
4. Cho phép một hoặc nhiều evidence; không bắt buộc đủ bốn `evidence_types`.
5. Cho phép một News hỗ trợ nhiều Signal khi từng liên kết có rationale và Signal không trùng lặp.
6. Không ép dùng toàn bộ News; ghi News chưa dùng và lý do trong coverage report.

## Viết Signal

- `signal_statement`: mô tả chuyển dịch, không chép title/summary.
- `what_changed`: nêu thay đổi quan sát được từ evidence.
- `from_state` và `to_state`: mô tả trạng thái trước/sau ở mức evidence cho phép.
- `why_it_matters`: nêu hệ quả cần đánh giá, chưa kết luận Opportunity/Threat.
- `signal_maturity`: dùng `EMERGING` cho evidence sớm/draft/prototype; `DEVELOPING` khi nhiều evidence cùng hướng; chỉ dùng `ESTABLISHED` khi evidence chứng minh trạng thái đã hình thành.
- `evidence_confidence`: phản ánh evidence yếu nhất và coverage; không nâng claim thành fact.
- `evidence_summary`: chỉ tóm tắt nội dung supplied evidence, không thêm fact.

### Yêu cầu tiên quyết: dễ hiểu và đầy đủ

- Không giới hạn độ dài câu, số vế, số câu hoặc độ dài tiêu đề. Có thể viết dài khi cần để truyền đạt đủ nội dung.
- Mỗi trường phải diễn đạt rõ nghĩa, có logic và giúp reviewer hiểu đúng mà không phải tự đoán phần còn thiếu.
- Ưu tiên đầy đủ nội dung hơn sự ngắn gọn. Không rút gọn nếu làm mất bối cảnh, quan hệ nguyên nhân–kết quả, giới hạn của evidence hoặc ý nghĩa của thay đổi.
- Phải nêu đủ chủ thể hoặc phạm vi liên quan, thay đổi quan sát được, trạng thái trước và sau, bằng chứng hỗ trợ và lý do thay đổi đó đáng chú ý.
- Có thể dùng thuật ngữ chuyên môn khi cần, nhưng cách diễn đạt tổng thể vẫn phải giúp reviewer hiểu thuật ngữ đang nói đến điều gì trong Signal cụ thể.
- Trước khi lưu, đọc lại toàn bộ Signal như một nội dung hoàn chỉnh. Viết lại nếu còn chỗ mơ hồ, thiếu ý, dễ hiểu sai hoặc chỉ có thể hiểu khi mở lại bài News gốc.

## Ngôn ngữ nội dung hướng tới reviewer

Tuân thủ [REVIEW_LANGUAGE_POLICY.md](../00-news-driven-mi-orchestrator/references/REVIEW_LANGUAGE_POLICY.md). Viết `signal_title`, `signal_statement`, `what_changed`, `from_state`, `to_state`, `why_it_matters`, `evidence_summary` và rationale trong coverage report bằng tiếng Việt. Giữ nguyên ID, enum, tên riêng và thuật ngữ kỹ thuật khó dịch.

### Đặt `signal_title`

- Không ép mọi Signal vào một công thức tiêu đề cố định. Chọn cấu trúc phù hợp nhất với cơ chế thay đổi và mức độ bằng chứng của từng Signal.
- Có thể dùng các hướng như: chuyển dịch từ A sang B; xu hướng trở thành yêu cầu mới; hành động quan sát được và hệ quả trực tiếp; sự hội tụ công nghệ hoặc lực thị trường; mâu thuẫn giữa kỳ vọng và bằng chứng; hoặc deployment pattern đang hình thành.
- Tạo 2–4 phương án tiêu đề nội bộ, sau đó chọn một phương án tốt nhất theo bốn tiêu chí: rõ thay đổi cốt lõi, đủ cụ thể, trung thành với evidence và khác biệt với các Signal còn lại.
- Tiêu đề phải đọc độc lập vẫn hiểu, nêu đúng thay đổi cốt lõi và không bỏ ý quan trọng chỉ để làm tiêu đề ngắn hơn.
- Không đưa kết luận Opportunity, Threat, Product, Product Gap hoặc Action vào tiêu đề. Không nâng mức khẳng định cao hơn `signal_maturity` và `evidence_confidence` cho phép.

## Evidence lineage

Mỗi Signal phải có ít nhất một `evidence_news_id` tồn tại trong bundle KEEP. `evidence_types` phải đúng bằng tập `news_type` thực tế của evidence. ID dùng `SIGNAL-NNN`, deterministic theo thứ tự output.

## Common mistakes

- Một News tương ứng máy móc với một Signal.
- Gộp News không chung cơ chế thay đổi.
- Viết lại headline thay vì nêu chuyển dịch.
- Dùng News EXCLUDE hoặc unknown ID.
- Suy diễn commercial readiness từ prototype.
- Tạo O/T, mapping, gap hoặc action trong Signal.

## Validation procedure

Chạy `validate_artifact.py` để kiểm frozen schema, ID, required fields, evidence lineage và type alignment. Chạy `build_coverage_report.py` để ghi mọi News USED/UNUSED cùng rationale. Validation fail thì không chạy stage 07.

## Allowed inputs

- Four news artifacts, restricted to Gate 1 KEEP items.
- workspace/reviews/01-news-relevance-decision.json with APPROVED status.

## Forbidden inputs

- EXCLUDE, NEEDS_REVISION, or unreviewed news.
- Reference catalogs.

## Output artifact

`workspace/artifacts/signals.json`

## Required previous approval

News Relevance HITL phải APPROVED.

## Next stage

`07-opportunity-threat`

Read [INPUT_OUTPUT_CONTRACT.md](references/INPUT_OUTPUT_CONTRACT.md) before using this skill.

Status: Runtime implemented for vertical slice 2; Contract V1 remains frozen.
