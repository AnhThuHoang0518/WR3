# Input/Output Contract — Signal Synthesis

## Purpose

Tổng hợp thay đổi thị trường từ news đã được Gate 1 KEEP; không biến từng bài thành một signal tóm tắt đơn thuần.

## Allowed inputs

- Bốn News artifacts, chỉ các ID thuộc `kept_news_ids`.
- `workspace/reviews/01-news-relevance-decision.json` với `overall_status = APPROVED`.

## Forbidden inputs

- News EXCLUDE, NEEDS_REVISION, chưa review hoặc khác `run_id`.
- Reference catalogs trực tiếp.

## Output artifact

- `workspace/artifacts/signals.json`
- Validate bằng `../schemas/output.schema.json`.

## Semantic invariants

- Signal của live run phải do LLM đang chạy skill trong phiên chat trực tiếp suy luận và viết; script không được gọi API model bên ngoài hoặc dùng rule deterministic để thay thế.
- Mỗi signal có ít nhất một `evidence_news_id` tồn tại và đã KEEP.
- `evidence_news_ids` là array và một news có thể hỗ trợ nhiều signal khi rationale giải thích được.
- `evidence_types` phải đúng với `news_type` thực tế của các evidence IDs; không bắt buộc đủ bốn type.
- Signal phải diễn đạt `what_changed`, `from_state`, `to_state` và `why_it_matters`, không chỉ tóm tắt bài báo.
- Signal không bị giới hạn độ dài, nhưng phải dễ hiểu và đầy đủ nội dung; không được rút gọn đến mức mất bối cảnh, logic, giới hạn evidence hoặc ý nghĩa của thay đổi.

## Next stage

`07-opportunity-threat`

Status: Contract v1 frozen; detailed logic pending.
