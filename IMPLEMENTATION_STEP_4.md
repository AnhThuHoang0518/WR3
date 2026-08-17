# Step 4 — Vertical Slice 01–05

## Phạm vi đã triển khai

- Runtime deterministic cho `01-market-news`, `02-competitor-news`, `03-technology-news`, `04-policy-news`.
- Build và validate bốn canonical News artifacts theo schema V1 freeze.
- Gate 1 `05-news-relevance-hitl`: tạo review Markdown, build decision manifest và validate schema/semantic sets.
- Shared validators cho JSON Schema subset, HITL union/disjoint/ID rules và gate continuation.
- Synthetic dataset 14 records, driver, log, validation reports và 18 unittest.

Không triển khai runtime stage 06–13, không crawl/search internet, không tạo Market Intelligence thật và không auto-approve.

## Dependency

Yêu cầu Python 3.11+. Implementation chỉ dùng Python standard library nên không cần `pip install` hoặc `requirements.txt`.

## Chạy synthetic vertical slice

Từ `C:\WR3`:

```powershell
python run_vertical_slice_01.py --input workspace/inputs/news/synthetic_raw_news.json
```

Có thể truyền run ID chưa tồn tại:

```powershell
python run_vertical_slice_01.py --input workspace/inputs/news/synthetic_raw_news.json --run-id 20260809-120000-synthetic
```

Driver từ chối ghi đè `workspace/runs/<run_id>` cũ. Output nằm tại:

```text
workspace/runs/<run_id>/
├── manifest.json
├── artifacts/
├── reviews/
└── validation/
```

Log nằm tại `workspace/logs/<run_id>.log`.

## Review Gate 1

Mở `workspace/runs/<run_id>/reviews/01-news-relevance-review.md`. Ban đầu file luôn có:

- `overall_status: PENDING`
- `reviewer: null`
- `reviewed_at: null`
- mọi `relevance_decision` là `PENDING`

Reviewer điền từng row bằng một trong `KEEP`, `EXCLUDE`, `NEEDS_REVISION`; ghi `relevance_reason`, `corrected_news_type`, `duplicate_of_news_id`, `reviewer_note` khi phù hợp. Sau khi review, cập nhật frontmatter `reviewer`, `reviewed_at`, `overall_status`, `reviewer_summary`.

Không đổi `PENDING` thành `APPROVED` nếu chưa review toàn bộ item. Generated Markdown không phải human approval.

## Build decision sau human review

```powershell
python .agents/skills/05-news-relevance-hitl/scripts/build_decision_manifest.py `
  --review workspace/runs/<run_id>/reviews/01-news-relevance-review.md `
  --output workspace/runs/<run_id>/reviews/01-news-relevance-decision.json
```

Parser không đoán item lỗi; lỗi parse khiến status không được `APPROVED`.

## Validate Gate 1

```powershell
python .agents/skills/05-news-relevance-hitl/scripts/validate_decision.py `
  --decision workspace/runs/<run_id>/reviews/01-news-relevance-decision.json `
  --schema .agents/skills/05-news-relevance-hitl/schemas/review-decision.schema.json `
  --market workspace/runs/<run_id>/artifacts/market_news.json `
  --competitor workspace/runs/<run_id>/artifacts/competitor_news.json `
  --technology workspace/runs/<run_id>/artifacts/technology_news.json `
  --policy workspace/runs/<run_id>/artifacts/policy_news.json `
  --report workspace/runs/<run_id>/validation/gate-1-validation-report.json
```

Pipeline chỉ có thể đi tiếp khi:

- schema và semantic validation đều PASS;
- tất cả source IDs đã được review;
- ba decision sets rời nhau và hợp đúng bằng `reviewed_news_ids`;
- không có unknown/duplicate ID;
- `overall_status: APPROVED`;
- không có `revision_news_ids`;
- có ít nhất một `kept_news_id`;
- có human reviewer metadata.

Trong synthetic run đầu tiên, Gate 1 hợp lệ ở trạng thái `PENDING` nhưng `pipeline_can_continue` luôn `false`.

## Contract manifest và runtime manifest

`pipeline_manifest.schema.json` thuộc Contract V1 và giữ nguyên semantics freeze. `runtime-run-manifest.schema.json` là implementation schema dùng để theo dõi partial/full run, runtime paths, trạng thái stage và lý do block. Hai schema không thay thế nhau.

Driver `run_vertical_slice_01.py` chỉ validate runtime `manifest.json` bằng `runtime-run-manifest.schema.json`; nó không cố validate runtime manifest bằng Contract schema. Log ghi rõ đường dẫn cả hai schema để audit.

Với partial vertical slice hiện tại:

- `run_mode: PARTIAL`;
- `current_stage: NEWS_RELEVANCE_HITL`;
- `pipeline_status: BLOCKED` khi chờ human review;
- stage 06–13 được ghi `NOT_IN_SCOPE`;
- runtime manifest không chứa hoặc thay thế HITL decision.

## Raw-to-canonical lineage

`raw_news_id` được giữ trong `workspace/runs/<run_id>/validation/news-lineage.json`. Mỗi mapping ghi `news_id`, `news_type`, `artifact_path` và `input_position`.

Canonical News schemas không bị thêm field. Contract lineage tiếp tục bắt đầu từ `news_id`; sidecar chỉ cung cấp implementation provenance trước canonical boundary.

Các file tách biệt:

- `news-validation-report.json`: validation bốn canonical News artifacts.
- `news-lineage.json`: raw-to-canonical mappings.
- `news-lineage-validation-report.json`: schema và semantic validation của sidecar.

## Contract limitations

Xem `IMPLEMENTATION_BLOCKERS.md`. Hai blocker runtime manifest và raw lineage đã được giải quyết bằng implementation artifacts riêng; enum `content_status` freeze vẫn được giữ nguyên.

## Chạy test

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m unittest discover -s tests -v
```
