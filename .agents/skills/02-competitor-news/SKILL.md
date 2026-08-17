---
name: competitor-news
description: Collect and normalize Smart City competitor news for known companies and relevant companies not yet listed in competitors.json within the configured geographic scope. Use for Competitor News candidates discovered through both catalog-based tracking and catalog-independent capability/activity queries; treat competitors.json as a recognition aid, never a whitelist, and stop before Signal or Opportunity/Threat analysis.
---

# Competitor News

## Purpose

Chọn và chuẩn hóa bản tin về hoạt động, năng lực và định vị của đối thủ. Stage này chỉ tạo News artifact, không tạo Signal hoặc Opportunity / Threat.

## Scope

- Product launch, partnership, deal, deployment và expansion.
- Capability, positioning, business model và operational proof.
- Claim tiếp thị có thể được giữ nếu giới hạn bằng chứng được ghi rõ.
- Công ty ngoài `competitors.json` nếu có hoạt động cạnh tranh Smart City có giá trị intelligence trong phạm vi địa lý crawl đã cấu hình.

## Inclusion criteria

Giữ record `expected_candidate_type: COMPETITOR` có thông tin raw về công ty hoặc hoạt động cạnh tranh. Một công ty chưa có trong catalog vẫn được giữ nếu candidate có intelligence value. Không có catalog match không phải lý do tự động loại; reviewer Gate 1 có thể chọn `KEEP`.

## Exclusion criteria

Không dùng catalog để tạo hoặc xác nhận sự kiện; không loại bài chỉ vì entity ngoài catalog; không đọc `products.json`; không suy luận Signal hoặc Opportunity / Threat.

## Classification rules

Đọc `references/competitors.json` chỉ để nhận diện canonical name, alias, brand, company scope và theo dõi đối thủ đã biết. Không dùng catalog như whitelist. Discovery phải kết hợp truy vấn theo đối thủ đã biết với truy vấn mở theo năng lực/hoạt động Smart City trong phạm vi địa lý crawl đã cấu hình. Khi alias thực sự xuất hiện trong raw input, canonical competitor name có thể được thêm vào `entities`; với công ty ngoài catalog, giữ tên có bằng chứng trong raw input mà không tự gán canonical match. Cấp ID ổn định `NEWS-COMPETITOR-NNN`; giữ duplicate cho HITL.

## Required evidence handling

Claim chưa có operational proof vẫn có thể xuất hiện với `evidence_quality: LOW` hoặc `UNKNOWN`. Vì enum freeze của `content_status` mô tả mức độ nội dung chứ không có trạng thái “unverified”, chọn đúng mức `FULL_TEXT`, `PARTIAL_TEXT`, `METADATA_ONLY` hoặc `UNAVAILABLE` và không diễn giải nó như xác nhận claim.

## Ngôn ngữ nội dung hướng tới reviewer

Tuân thủ [REVIEW_LANGUAGE_POLICY.md](../00-news-driven-mi-orchestrator/references/REVIEW_LANGUAGE_POLICY.md). Với nguồn không phải tiếng Việt, viết bản dịch đầy đủ bằng tiếng Việt cho `title`, `summary`, `key_facts` và `relevance_rationale` trước Gate 1; giữ nguyên ID, enum, URL, tên công ty/thương hiệu và thuật ngữ kỹ thuật khó dịch. Giữ tiêu đề/ngôn ngữ/trích đoạn gốc trong crawl evidence để bảo toàn provenance. Dừng trước Gate 1 nếu còn bản dịch `PENDING`.

## Output rules

Chạy `scripts/build_artifact.py` với `--competitors`, rồi chạy `scripts/validate_artifact.py`. Không bổ sung fact ngoài raw input và không ghi runtime output vào thư mục skill.

## Common mistakes

- Coi catalog là bằng chứng sự kiện.
- Loại công ty ngoài catalog một cách tự động.
- Coi việc không match catalog là lý do tự động EXCLUDE tại Gate 1.
- Tin claim marketing như deployment đã xác minh.
- Đọc danh mục sản phẩm VSF.

## Validation procedure

Validator kiểm tra schema, required fields, `news_type`, deterministic ID, uniqueness, URI, timestamps, `synthetic`, và các trường nội dung không rỗng. Việc match catalog được báo trong lineage runtime, không thêm field trái schema vào artifact.

## Allowed inputs

- Competitor news sources.
- references/competitors.json.

## Forbidden inputs

- VSF portfolio catalog.

## Output artifact

`workspace/artifacts/competitor_news.json`

## Required previous approval

Không có; đây là stage đầu vào.

## Next stage

`05-news-relevance-hitl`

Read [INPUT_OUTPUT_CONTRACT.md](references/INPUT_OUTPUT_CONTRACT.md) before using this skill.

Status: Runtime implemented for synthetic vertical slice 01–05; Contract V1 remains frozen.
