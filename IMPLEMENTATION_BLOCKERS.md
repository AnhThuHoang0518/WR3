# Implementation Blockers — Step 4

Contract version: `1.0.0-contract`

Không file contract, schema, enum hoặc catalog freeze nào được sửa để xử lý các điểm dưới đây.

## BLOCKER-001 — Runtime manifest mở rộng không tương thích schema freeze

**Status:** RESOLVED in Step 5A. Lịch sử blocker được giữ lại bên dưới.

`pipeline_manifest.schema.json` đặt `additionalProperties: false` và chỉ cho phép sáu field gốc. Bước 4 đồng thời yêu cầu `started_at`, `completed_at`, `stage_statuses`, paths, `pipeline_can_continue` và `blocking_gate`. Schema cũng yêu cầu `current_stage` là canonical folder name như `05-news-relevance-hitl`, trong khi mô tả Bước 4 dùng `NEWS_RELEVANCE_HITL`.

**Safe implementation:** `workspace/runs/<run_id>/manifest.json` chứa đầy đủ runtime fields yêu cầu, giữ canonical `current_stage: 05-news-relevance-hitl`, và ghi `pipeline_manifest_schema_status: BLOCKED_BY_FROZEN_SCHEMA`. Manifest không được tuyên bố là PASS với schema freeze. `blocking_gate` vẫn dùng `NEWS_RELEVANCE_HITL`.

**Future contract decision required:** bổ sung version schema runtime manifest hoặc cho phép metadata mở rộng. Không xử lý trong Bước 4.

**Step 5A resolution:** tạo implementation schema độc lập `schemas/runtime-run-manifest.schema.json`. Driver validate `workspace/runs/<run_id>/manifest.json` bằng runtime schema này và chỉ ghi đường dẫn `pipeline_manifest.schema.json` vào log như Contract V1 reference. Hai schema không thay thế nhau; không file Contract V1 nào bị sửa.

## BLOCKER-002 — Frozen News schema không có lineage field

**Status:** RESOLVED in Step 5A. Lịch sử blocker được giữ lại bên dưới.

Schema của bốn News artifacts có `additionalProperties: false` và không có `raw_news_id`, `lineage` hoặc reference field tương đương.

**Safe implementation:** không thêm field trái schema. Mapping `raw_news_id` → `news_id` được ghi trong `validation/news-validation-report.json` của từng run. Quyết định bổ sung lineage vào contract để dành cho version sau.

**Step 5A resolution:** mapping được tách khỏi canonical validation report thành sidecar `validation/news-lineage.json`, validate bằng implementation schema `schemas/news-lineage.schema.json` và semantic validator `validate_news_lineage.py`. Canonical News schemas không thay đổi; Contract V1 lineage vẫn bắt đầu từ `news_id`.

## LIMITATION-001 — `content_status` không biểu diễn claim/unverified

**Status:** DOCUMENTED LIMITATION.

Enum freeze chỉ có `FULL_TEXT`, `PARTIAL_TEXT`, `METADATA_ONLY`, `UNAVAILABLE`; không có `CLAIM` hoặc `UNVERIFIED`. Runtime dùng `content_status` đúng nghĩa mức độ nội dung và dùng `evidence_quality: LOW/UNKNOWN` để phản ánh giới hạn bằng chứng. Nó không coi claim là sự kiện đã xác minh.
