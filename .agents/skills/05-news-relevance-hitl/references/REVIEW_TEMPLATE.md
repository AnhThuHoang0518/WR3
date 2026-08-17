---
review_gate: news-relevance-hitl
run_id: <run id>
synthetic: false
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
- Competitor ngoài `competitors.json` vẫn có thể `KEEP`; không tự động loại chỉ vì không match catalog.
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
| <news_id> | <current_news_type> | <title> | <source_name> | <source_url> | <published_at> | <collected_at> | <geography> | <language> | <summary> | <key_facts> | <entities> | <relevance_rationale> | <evidence_quality> | <content_status> | <relevance_decision> | <relevance_reason> | null | null | <reviewer_note> |

## Ghi chú của reviewer

<Ghi chú của reviewer>

## Quyết định cuối cùng

- reviewer: <tên reviewer>
- reviewed_at: <ISO-8601 timestamp>
- overall_status: `PENDING`
- reviewer_summary: <tóm tắt quyết định>
