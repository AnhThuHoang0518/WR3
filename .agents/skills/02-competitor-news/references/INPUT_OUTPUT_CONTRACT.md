# Input/Output Contract — Competitor News

## Purpose

Thu thập và chuẩn hóa competitor news cho đối thủ đã biết và công ty liên quan chưa có trong catalog, trong phạm vi địa lý crawl đã cấu hình.

## Allowed inputs

- Nguồn competitor news và cấu hình run, gồm truy vấn theo catalog và truy vấn mở theo năng lực/hoạt động Smart City.
- `references/competitors.json` chỉ để nhận diện canonical name/alias và theo dõi đối thủ đã biết; không phải whitelist. Quy tắc này không tự mở rộng phạm vi địa lý crawl.

## Forbidden inputs

- products.json.
- Sử dụng competitors.json ngoài mục đích Competitor News.

## Required previous approval

Không có; đây là stage đầu vào.

## Output artifact

- `workspace/artifacts/competitor_news.json`
- `news_type` phải là `COMPETITOR`.
- Validate bằng `../schemas/output.schema.json`.

## Common news fields

- `news_id`
- `news_type`
- `title`
- `source_name`
- `source_url`
- `published_at`
- `collected_at`
- `geography`
- `language`
- `summary`
- `key_facts`
- `entities`
- `relevance_rationale`
- `evidence_quality`
- `content_status`

Bốn News skill phải dùng cùng tên và cùng semantic cho các field chung. `key_facts` và `entities` có thể là array rỗng; không được tạo fact giả để lấp field.

Với nguồn không phải tiếng Việt, `title`, `summary`, `key_facts` và `relevance_rationale` trong artifact phải được dịch sang tiếng Việt trước Gate 1. Bản gốc được giữ trong raw crawl evidence; bản dịch `PENDING` là stop condition.

## Next stage

`05-news-relevance-hitl`

## Stop conditions

Dừng khi input lỗi, artifact sai `run_id`, schema không hợp lệ, URL/thời gian không parse được, hoặc không thể tạo `news_id` ổn định.

Status: Contract v1 frozen; detailed logic pending.
