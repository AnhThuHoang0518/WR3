---
name: news-relevance-hitl
description: Require human review at the News Relevance HITL gate and block the pipeline unless its decision manifest is APPROVED.
---

# News Relevance HITL

## Purpose

Tạo hồ sơ để con người review từng News item và chặn pipeline cho đến khi decision manifest hợp lệ có `overall_status: APPROVED`.

## Khi nào sử dụng

Chỉ dùng sau khi cả bốn artifact Market, Competitor, Technology và Policy của cùng `run_id` đã build và validate thành công.

## Quy trình runtime

1. Chạy `scripts/generate_review.py` với bốn artifact và `REVIEW_TEMPLATE.md` để tạo Markdown `PENDING`.
2. Reviewer đọc toàn bộ bảng và điền `relevance_decision`, reason, correction, duplicate reference và note khi cần.
3. Reviewer cập nhật `reviewer`, `reviewed_at`, `overall_status` và `reviewer_summary` trong frontmatter.
4. Chạy `scripts/build_decision_manifest.py` để tạo decision JSON; parser không được đoán item lỗi.
5. Chạy `scripts/validate_decision.py`; chỉ kết quả schema và semantic `PASS` cùng status `APPROVED` mới cho phép đi tiếp.

## Ngôn ngữ nội dung hướng tới reviewer

Tuân thủ [REVIEW_LANGUAGE_POLICY.md](../00-news-driven-mi-orchestrator/references/REVIEW_LANGUAGE_POLICY.md). Hồ sơ review phải trình bày phần hướng dẫn và nội dung diễn giải bằng tiếng Việt. Xác nhận `summary`, `key_facts` và `relevance_rationale` nhận từ stage 01–04 đã bằng tiếng Việt; hướng dẫn reviewer viết `relevance_reason`, `reviewer_note` và `reviewer_summary` bằng tiếng Việt. Giữ nguyên ID, field, enum và decision token.

## Quyết định từng item

- `KEEP`: item đủ liên quan để stage sau sử dụng.
- `EXCLUDE`: item không liên quan hoặc không có intelligence value; ghi `relevance_reason`.
- `NEEDS_REVISION`: cần sửa dữ liệu, phân loại hoặc lineage trước khi review lại; manifest phải là `CHANGES_REQUIRED`.
- `corrected_news_type`: dùng khi type hiện tại sai; không sửa artifact âm thầm.
- `duplicate_of_news_id`: trỏ đến canonical candidate được reviewer chọn; duplicate không bị loại tự động.
- Quảng cáo: đánh giá intelligence value, không loại chỉ vì hình thức quảng cáo.
- Competitor ngoài `competitors.json`: đánh giá theo evidence và intelligence value như các item khác; không có catalog match không phải lý do tự động `EXCLUDE`, và reviewer có thể chọn `KEEP`.

## Quy tắc quyết định batch

`reviewed_news_ids` phải đúng bằng hợp rời nhau của `kept_news_ids`, `excluded_news_ids` và `revision_news_ids`. Chưa review hết phải `PENDING`. Có revision phải `CHANGES_REQUIRED`. `APPROVED` cần review toàn bộ, không revision, có ít nhất một kept item và có reviewer metadata. `REJECTED` cần reviewer metadata và summary giải thích dừng batch hoặc không có item dùng được.

## Cấm auto-approval

Generated review và generated decision ban đầu luôn `PENDING`, không có reviewer và không có item được tự động KEEP/EXCLUDE/NEEDS_REVISION. Script không được biến machine output thành human approval.

## Điều kiện dừng

Pipeline dừng khi status là `PENDING`, `CHANGES_REQUIRED`, `REJECTED`, hoặc khi semantic validation fail. Không gọi stage 06 trong vertical slice này.

## Allowed inputs

- workspace/artifacts/market_news.json
- workspace/artifacts/competitor_news.json
- workspace/artifacts/technology_news.json
- workspace/artifacts/policy_news.json

## Forbidden inputs

- Cross-run or incomplete artifacts.
- Machine-generated approval.

## Output artifact

- `workspace/reviews/01-news-relevance-review.md`
- `workspace/reviews/01-news-relevance-decision.json`

## Required previous approval

All immediately preceding automatic stages must complete successfully.

## Next stage

`06-signal-synthesis`

Human approval required. No auto-approval. Pipeline must stop when status is `PENDING`, `CHANGES_REQUIRED`, or `REJECTED`.

Read [INPUT_OUTPUT_CONTRACT.md](references/INPUT_OUTPUT_CONTRACT.md), [REVIEW_INSTRUCTIONS.md](references/REVIEW_INSTRUCTIONS.md), and [REVIEW_TEMPLATE.md](references/REVIEW_TEMPLATE.md).

Status: Gate 1 runtime implemented for synthetic vertical slice; Contract V1 remains frozen.
