---
name: policy-news
description: Collect and structure policy news inputs for downstream market-intelligence analysis.
---

# Policy News

## Purpose

Chọn và chuẩn hóa bản tin luật, quy định, tiêu chuẩn, chương trình và yêu cầu compliance có liên quan Smart City. Stage này không tạo Signal hoặc Opportunity / Threat.

## Scope

- Law, regulation, standard và official guidance.
- Government program, public investment và procurement rule.
- Data governance, cybersecurity, privacy và environmental requirement.
- Draft, proposal và pilot program khi trạng thái được nêu rõ.

## Inclusion criteria

Giữ candidate chứa yêu cầu, cơ chế hoặc trạng thái chính sách có thể review. Phải phân biệt văn bản đã ban hành với draft, proposal, pilot hoặc guidance.

## Exclusion criteria

Không diễn giải nghĩa vụ vượt raw input; không cung cấp tư vấn pháp lý; không đọc catalog sản phẩm hoặc đối thủ; không tạo Signal hay O/T.

## Classification rules

`expected_candidate_type: POLICY` ánh xạ sang `news_type: POLICY`, với ID `NEWS-POLICY-NNN`. Candidate ngoài scope hoặc có thể phân loại sai vẫn được giữ cho HITL nếu đã có trong tập synthetic.

## Required evidence handling

Ghi đúng authority/source, thời điểm và trạng thái văn bản như raw input. Khi chưa đủ nội dung, hạ `evidence_quality` và dùng `content_status` tương ứng; không suy đoán phạm vi áp dụng.

## Ngôn ngữ nội dung hướng tới reviewer

Tuân thủ [REVIEW_LANGUAGE_POLICY.md](../00-news-driven-mi-orchestrator/references/REVIEW_LANGUAGE_POLICY.md). Với nguồn không phải tiếng Việt, viết bản dịch đầy đủ bằng tiếng Việt cho `title`, `summary`, `key_facts` và `relevance_rationale` trước Gate 1; giữ nguyên ID, enum, URL, tên cơ quan/văn bản, tên riêng và thuật ngữ pháp lý hoặc kỹ thuật khó dịch. Giữ tiêu đề/ngôn ngữ/trích đoạn gốc trong crawl evidence để bảo toàn provenance. Dừng trước Gate 1 nếu còn bản dịch `PENDING`.

## Output rules

Chạy `scripts/build_artifact.py` và `scripts/validate_artifact.py`. Artifact chỉ chứa canonical News fields và giữ nguyên giới hạn evidence.

## Common mistakes

- Gọi draft là quy định đã ban hành.
- Mở rộng compliance requirement ngoài nội dung raw.
- Tạo khuyến nghị hoặc market signal.
- Loại bài ngoài scope trước khi Gate 1 ghi quyết định.

## Validation procedure

Validator kiểm tra frozen schema, required fields, type, deterministic ID, uniqueness, URI, timestamps, `synthetic` và nội dung tối thiểu. Reviewer chịu trách nhiệm quyết định relevance và correction.

## Allowed inputs

- Policy news sources and run configuration.

## Forbidden inputs

- competitors.json.
- VSF portfolio catalog.

## Output artifact

`workspace/artifacts/policy_news.json`

## Required previous approval

Không có; đây là stage đầu vào.

## Next stage

`05-news-relevance-hitl`

Read [INPUT_OUTPUT_CONTRACT.md](references/INPUT_OUTPUT_CONTRACT.md) before using this skill.

Status: Runtime implemented for synthetic vertical slice 01–05; Contract V1 remains frozen.
