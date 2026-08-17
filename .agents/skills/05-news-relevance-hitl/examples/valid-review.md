---
review_gate: news-relevance-hitl
run_id: SYN-RUN-001
synthetic: true
overall_status: PENDING
reviewer: null
reviewed_at: null
source_artifacts:
  - workspace/artifacts/market_news.json
  - workspace/artifacts/competitor_news.json
  - workspace/artifacts/technology_news.json
  - workspace/artifacts/policy_news.json
approved_ids: []
rejected_ids: []
revision_ids: []
---

# News Relevance HITL Review

> **Cảnh báo:** Pipeline phải dừng cho đến khi `overall_status: APPROVED` do con người xác nhận.

## Hướng dẫn review

- Chọn `KEEP`, `EXCLUDE` hoặc `NEEDS_REVISION` cho từng item.
- Quảng cáo không bị loại tự động; đánh giá giá trị intelligence của nội dung.
- Dùng `null` cho `corrected_news_type` hoặc `duplicate_of_news_id` khi không áp dụng.

## Tóm tắt review

- Tổng số item:
- Đã review:
- KEEP:
- EXCLUDE:
- NEEDS_REVISION:

## Review từng item

| news_id | current_news_type | title | source_name | source_url | published_at | collected_at | geography | language | summary | key_facts | entities | relevance_rationale | evidence_quality | content_status | relevance_decision | relevance_reason | corrected_news_type | duplicate_of_news_id | reviewer_note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SYN-NEWS-M-001 | MARKET | Synthetic market news | Synthetic source | https://example.invalid/market-news | 2026-01-01T00:00:00Z | 2026-01-01T01:00:00Z | SYNTHETIC_GEOGRAPHY | en | Synthetic example for contract validation. | Synthetic fact placeholder | SYNTHETIC_ENTITY | Synthetic rationale | UNKNOWN | METADATA_ONLY | null | Chưa review. | null | null | Chưa có phê duyệt. |

## Ghi chú của reviewer

Chưa có quyết định của reviewer.

## Quyết định cuối cùng

- reviewer: null
- reviewed_at: null
- overall_status: `PENDING`
- reviewer_summary: Chưa review.
