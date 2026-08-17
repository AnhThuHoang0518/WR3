---
name: technology-news
description: Collect and structure technology news inputs for downstream market-intelligence analysis.
---

# Technology News

## Purpose

Chọn và chuẩn hóa bản tin về capability, maturity, integration và constraint công nghệ Smart City. Stage này không map vào danh mục VSF và không tạo Signal hoặc Opportunity / Threat.

## Scope

- AI, IoT, sensor, platform và data architecture.
- Use case, integration method và technical constraint mới.
- Technology maturity, commercial readiness hoặc thiếu readiness.

## Inclusion criteria

Giữ candidate cung cấp thông tin kỹ thuật hoặc mức độ trưởng thành có thể hỗ trợ review. Prototype được giữ khi raw input nêu rõ trạng thái prototype.

## Exclusion criteria

Không đọc `products.json`; không map công nghệ vào VSF; không coi prototype là commercial deployment; không tạo market signal hoặc đánh giá O/T.

## Classification rules

`expected_candidate_type: TECHNOLOGY` ánh xạ sang `news_type: TECHNOLOGY`; ID ổn định dạng `NEWS-TECHNOLOGY-NNN`. Candidate có vẻ phân loại sai vẫn được đưa vào review để reviewer dùng `corrected_news_type`.

## Required evidence handling

Chỉ ánh xạ capability, maturity và constraint có trong raw input. Nguồn thiếu nội dung dùng `METADATA_ONLY` hoặc `UNAVAILABLE` và `evidence_quality` phù hợp; không tự hoàn thiện chi tiết kỹ thuật.

## Ngôn ngữ nội dung hướng tới reviewer

Tuân thủ [REVIEW_LANGUAGE_POLICY.md](../00-news-driven-mi-orchestrator/references/REVIEW_LANGUAGE_POLICY.md). Với nguồn không phải tiếng Việt, viết bản dịch đầy đủ bằng tiếng Việt cho `title`, `summary`, `key_facts` và `relevance_rationale` trước Gate 1; giữ nguyên ID, enum, URL, tên riêng và thuật ngữ kỹ thuật khó dịch. Giữ tiêu đề/ngôn ngữ/trích đoạn gốc trong crawl evidence để bảo toàn provenance. Dừng trước Gate 1 nếu còn bản dịch `PENDING`.

## Output rules

Chạy `scripts/build_artifact.py`, sau đó `scripts/validate_artifact.py`. Output tuân theo frozen schema, UTF-8 và không chứa portfolio linkage.

## Common mistakes

- Đánh đồng prototype với thương mại hóa.
- Suy đoán integration hoặc deployment.
- Đọc `products.json` hoặc map sang sản phẩm VSF.
- Loại candidate yếu trước HITL.

## Validation procedure

Validator kiểm tra schema, type, deterministic ID, uniqueness, URI, timestamps, `synthetic`, và nội dung tối thiểu. Lỗi phân loại ngữ nghĩa được đưa cho human reviewer thay vì tự sửa ngoài raw input.

## Allowed inputs

- Technology news sources and run configuration.

## Forbidden inputs

- competitors.json.
- VSF portfolio catalog.

## Output artifact

`workspace/artifacts/technology_news.json`

## Required previous approval

Không có; đây là stage đầu vào.

## Next stage

`05-news-relevance-hitl`

Read [INPUT_OUTPUT_CONTRACT.md](references/INPUT_OUTPUT_CONTRACT.md) before using this skill.

Status: Runtime implemented for synthetic vertical slice 01–05; Contract V1 remains frozen.
