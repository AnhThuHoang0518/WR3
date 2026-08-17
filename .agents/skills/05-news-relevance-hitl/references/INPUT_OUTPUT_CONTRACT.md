# Input/Output Contract — News Relevance HITL

## Purpose

Con người review từng news item trước khi Signal Synthesis sử dụng.

## Allowed inputs

- `workspace/artifacts/market_news.json`
- `workspace/artifacts/competitor_news.json`
- `workspace/artifacts/technology_news.json`
- `workspace/artifacts/policy_news.json`

## Output artifacts

- `workspace/reviews/01-news-relevance-review.md`: artifact review chính.
- `workspace/reviews/01-news-relevance-decision.json`: manifest điều khiển pipeline.

## Item decisions

- `KEEP`: có thể làm evidence cho Signal.
- `EXCLUDE`: không được làm evidence.
- `NEEDS_REVISION`: quay lại đúng News skill sở hữu item.

Reviewer có thể sửa `news_type`; `corrected_news_type` và `duplicate_of_news_id` nhận `null` khi không áp dụng.

## Decision-set invariants

- `reviewed_news_ids` bằng hợp của `kept_news_ids`, `excluded_news_ids`, `revision_news_ids`.
- Ba tập quyết định đôi một không chồng lặp.
- ID trong các tập phải tồn tại trong đúng bốn source artifacts và cùng `run_id`.
- Signal Synthesis chỉ được đọc ID trong `kept_news_ids`.

## Overall status

- Chưa review hết source IDs: `PENDING`.
- `revision_news_ids` không rỗng: `CHANGES_REQUIRED`.
- Review hoàn tất, không còn revision và batch có thể tiếp tục: `APPROVED`.
- Reviewer dừng hoặc loại toàn bộ batch: `REJECTED`.

Item-level `KEEP` không thay thế `overall_status = APPROVED`.

## Next stage

Chỉ chạy `06-signal-synthesis` khi con người đặt decision manifest thành `APPROVED`.

Status: Contract v1 frozen; detailed logic pending.
