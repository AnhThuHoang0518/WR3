---
name: market-news
description: Collect and structure general market news inputs for downstream market-intelligence analysis.
---

# Market News

## Purpose

Chọn và chuẩn hóa các bản tin phản ánh nhu cầu, hành vi mua, đầu tư, triển khai và mô hình thương mại Smart City. Stage này chỉ tạo News artifact, không tạo Signal hoặc Opportunity / Threat.

## Scope

- Nhu cầu thị trường, buyer behavior, procurement và adoption.
- Dự án, investment hoặc deployment pattern liên quan Smart City.
- Nhu cầu vận hành đô thị, khu đô thị và khu công nghiệp.
- Bất động sản hoặc quảng cáo dự án khi nội dung có intelligence value.

## Inclusion criteria

Giữ record khi raw input cung cấp ít nhất một thông tin có thể kiểm chứng về nhu cầu, người mua, cách mua, dự án, mô hình thương mại, đầu tư hoặc triển khai. Không tự loại chỉ vì nội dung mang tính quảng cáo.

## Exclusion criteria

Không tạo thêm fact; không suy luận Market Signal; không dùng `competitors.json` hay `products.json`; không đưa bài hoàn toàn ngoài phạm vi ra khỏi raw candidate nếu nó được cung cấp để HITL đánh giá.

## Classification rules

`expected_candidate_type: MARKET` được ánh xạ sang `news_type: MARKET`. Giữ nguyên thứ tự input và cấp `news_id` dạng `NEWS-MARKET-NNN`. Các candidate trùng hoặc gần trùng vẫn được giữ cho HITL quyết định.

## Required evidence handling

`summary`, `key_facts`, `evidence_quality` và `content_status` chỉ phản ánh raw input. Nội dung thiếu bằng chứng dùng `LOW` hoặc `UNKNOWN`; không nâng claim thành sự kiện đã xác nhận.

## Ngôn ngữ nội dung hướng tới reviewer

Tuân thủ [REVIEW_LANGUAGE_POLICY.md](../00-news-driven-mi-orchestrator/references/REVIEW_LANGUAGE_POLICY.md). Với nguồn không phải tiếng Việt, viết bản dịch đầy đủ bằng tiếng Việt cho `title`, `summary`, `key_facts` và `relevance_rationale` trước Gate 1; giữ nguyên ID, enum, URL, tên riêng, tên thương hiệu và thuật ngữ kỹ thuật khó dịch. Giữ tiêu đề/ngôn ngữ/trích đoạn gốc trong crawl evidence để bảo toàn provenance. Dừng trước Gate 1 nếu còn bản dịch `PENDING`.

## Output rules

Chạy `scripts/build_artifact.py` để tạo `market_news.json`, sau đó bắt buộc chạy `scripts/validate_artifact.py` với schema freeze. Output UTF-8, `synthetic: true` cho vertical slice synthetic.

## Common mistakes

- Biến bản tin thành Signal hoặc khuyến nghị.
- Loại quảng cáo tự động.
- Loại duplicate trước Gate 1.
- Bổ sung số liệu không có trong raw input.

## Validation procedure

Validator kiểm tra schema, required fields, `news_type`, format và uniqueness của `news_id`, URI, timestamps, `synthetic`, cùng `title`, `summary`, `key_facts` không rỗng. Mọi lỗi phải được sửa ở input/build logic trước khi tạo review.

## Allowed inputs

- Market news sources and run configuration.

## Forbidden inputs

- competitors.json.
- VSF portfolio catalog.

## Output artifact

`workspace/artifacts/market_news.json`

## Required previous approval

Không có; đây là stage đầu vào.

## Next stage

`05-news-relevance-hitl`

Read [INPUT_OUTPUT_CONTRACT.md](references/INPUT_OUTPUT_CONTRACT.md) before using this skill.

Status: Runtime implemented for synthetic vertical slice 01–05; Contract V1 remains frozen.
