# Implementation Step 6 — Vertical Slice 2

## Phạm vi đã triển khai

Bước 6 hoàn thiện runtime cho ba stage:

- `06-signal-synthesis`: tạo approved News bundle, tổng hợp Signal, kiểm tra schema/lineage và lập coverage report.
- `07-opportunity-threat`: phân loại Opportunity/Threat từ Signal, kiểm tra schema/lineage và lập coverage report.
- `08-opportunity-threat-hitl`: tạo hồ sơ review Gate 2, build/validate decision manifest và chặn pipeline để chờ con người review.

Các validator lineage dùng chung nằm tại `.agents/skills/00-news-driven-mi-orchestrator/scripts/validators/validate_stage_lineage.py`.

## Điều kiện Gate 1

Driver chỉ chạy khi Gate 1 còn hợp lệ:

- `overall_status = APPROVED`.
- `pipeline_can_continue = true`.
- Có đúng 9 `kept_news_ids`, 5 `excluded_news_ids` và không có `revision_news_ids`.
- Gate 1 decision và bốn News artifact vượt qua validation.

Driver ghi nhận SHA-256 trước và sau khi chạy, đồng thời dừng nếu bất kỳ artifact Gate 1 được bảo vệ nào thay đổi.

## Cách chạy

Từ `C:\WR3`:

```powershell
python run_vertical_slice_02.py --run-dir workspace/runs/20260809-122107-synthetic
```

Với live run, Stage 06 phải do LLM trong phiên chat trực tiếp đọc approved News bundle, suy luận và viết `signals.json`. Script không gọi API model bên ngoài. `build_artifact.py` chỉ tạo synthetic fixture; sau khi LLM viết Signal, các script còn lại chỉ kiểm schema, lineage và coverage.

Luồng live chạy theo hai lượt: lượt đầu tạo và validate `approved_news_bundle.json`, sau đó dừng để LLM trong chat viết `signals.json`; lượt tiếp theo nhận artifact đã viết, validate và tiếp tục sang Opportunity/Threat. Driver không ghi đè bundle hoặc Signal đã có trong lượt tiếp theo.

Driver tiếp tục đúng run hiện tại, không tạo run mới và không ghi đè output Bước 6 đã tồn tại.

## Runtime output

- Approved News bundle: `workspace/runs/20260809-122107-synthetic/artifacts/approved_news_bundle.json`
- Signal: `workspace/runs/20260809-122107-synthetic/artifacts/signals.json`
- Opportunity/Threat: `workspace/runs/20260809-122107-synthetic/artifacts/opportunity_threat.json`
- Gate 2 review: `workspace/runs/20260809-122107-synthetic/reviews/02-opportunity-threat-review.md`
- Gate 2 decision: `workspace/runs/20260809-122107-synthetic/reviews/02-opportunity-threat-decision.json`
- Validation và coverage report: `workspace/runs/20260809-122107-synthetic/validation/`

## Review Gate 2

Reviewer chỉnh trực tiếp `02-opportunity-threat-review.md`:

1. Điền `reviewer`, `reviewed_at` và trạng thái tổng thể trong YAML frontmatter.
2. Với từng O/T, chọn đúng một quyết định: `APPROVE`, `REVISE` hoặc `REJECT`.
3. Khi `REVISE`, điền `corrected_type` và/hoặc `revised_statement` theo thay đổi cần thiết.
4. Ghi nhận xét merge/split tại trường ghi chú trong Markdown. Contract V1 không lưu mapping merge/split trong decision JSON.

Không được tự động điền quyết định thay reviewer hoặc tự động chuyển `REVISE` thành `APPROVE`.

## Build và validate decision manifest

Sau khi review được cập nhật, chạy:

```powershell
python .agents/skills/08-opportunity-threat-hitl/scripts/build_decision_manifest.py --review workspace/runs/20260809-122107-synthetic/reviews/02-opportunity-threat-review.md --opportunity-threat workspace/runs/20260809-122107-synthetic/artifacts/opportunity_threat.json --output workspace/runs/20260809-122107-synthetic/reviews/02-opportunity-threat-decision.json

python .agents/skills/08-opportunity-threat-hitl/scripts/validate_decision.py --decision workspace/runs/20260809-122107-synthetic/reviews/02-opportunity-threat-decision.json --opportunity-threat workspace/runs/20260809-122107-synthetic/artifacts/opportunity_threat.json --schema .agents/skills/08-opportunity-threat-hitl/schemas/decision.schema.json --report workspace/runs/20260809-122107-synthetic/validation/gate-2-validation-report.json
```

Validator kiểm tra schema, ID lineage, tính rời nhau và hợp của các decision set, điều kiện trạng thái tổng thể và quyền tiếp tục pipeline.

Pipeline chỉ được tiếp tục khi toàn bộ O/T đã được human review, Gate 2 có `overall_status = APPROVED`, không còn revision, có ít nhất một O/T được duyệt và semantic validation PASS. Ở trạng thái `PENDING`, pipeline luôn bị chặn với `pipeline_can_continue = false`.

## Chưa triển khai

Skill 09–13 không thuộc phạm vi Bước 6 và chưa được triển khai runtime. Bước này không đọc `products.json`, không gọi internet, không crawl dữ liệu thật và không chạy Market Intelligence thật.

> Gate 2 không bao giờ được auto-approve. Sau Bước 6, pipeline phải dừng tại `OPPORTUNITY_THREAT_HITL` để chờ reviewer.
