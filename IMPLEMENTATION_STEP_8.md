# Bước 8 — Action Recommendation và Product Action HITL Gate 3

## Trạng thái hậu-review

Ngày 2026-08-09, reviewer Thu đã đặt Gate 3 thành `APPROVED` và phê duyệt `ACTION-001` đến `ACTION-004`. Decision validation PASS, `pipeline_can_continue: true`, approved portfolio đã được tạo tại `artifacts/approved-actions.json`, deferred backlog rỗng tại `artifacts/deferred-actions.json`. Skill 13 vẫn `NOT_IN_SCOPE` và chưa được chạy.

## Phạm vi

Bước 8 hoàn thiện Skill 11 và Skill 12, chạy pipeline từ Product Gap đã được Thu chấp nhận tới Product Action HITL Gate 3. Bước này chỉ tạo đề xuất Action để con người review; không tự phê duyệt, không tạo final approved/deferred portfolio và chưa chạy Skill 13 Quality Control.

## Input

- `signals.json`.
- `approved_opportunity_threat_bundle.json` và Gate 2 decision `APPROVED`.
- `product_mapping.json` cùng manual review `REVIEWED_ACCEPTED`.
- `product_gap.json` cùng manual review `REVIEWED_ACCEPTED`.
- Frozen schemas, Contract V1 và read-only catalog dùng để kiểm tra provenance.

## Tạo Action

Skill 11 tạo `action_context.json` và `action_matrix.json`, sau đó Codex áp dụng logic semantic trực tiếp để soạn `actions_draft.json`. Mỗi Action bắt buộc truy vết qua:

`Signal → Gate 2-approved O/T → Product Mapping → Product Gap → Action`

`build_artifact.py` chỉ chuẩn hóa draft, cấp ID deterministic `ACTION-###` và validate theo frozen schema. Script không tự thêm kết luận semantic hoặc quyết định human.

### Recommended response

- `MONITOR`: bằng chứng/tác động còn sớm; phải có trigger và thời điểm review lại.
- `VALIDATE`: requirement, capability, gap hoặc buyer evidence chưa đủ; phải có phương pháp và pass/fail.
- `PREPARE`: đủ quan trọng để chuẩn bị deliverable/pilot nhưng chưa đủ căn cứ triển khai đầy đủ.
- `ACT`: chỉ dùng khi evidence, gap và next step đã đủ mạnh; không chọn chỉ vì urgency cao.

### Build / Buy / Partner

Chọn `BUILD`, `BUY`, `PARTNER`, `HYBRID` hoặc `UNDECIDED` dựa trên gap type, documented current capability, time-to-market, dependency, evidence và strategic control. Không mặc định BUILD; thiếu căn cứ thì giữ UNDECIDED và nêu validation cần thiết.

### Pilot / Productize

Chọn `PILOT`, `PRODUCTIZE`, `BOTH`, `NEITHER` hoặc `UNDECIDED`. PILOT kiểm chứng requirement/capability/deployment. PRODUCTIZE chỉ phù hợp khi buyer need, capability và repeatable operating model đã đủ rõ.

## Runtime outputs

- Action artifact: `workspace/runs/20260809-122107-synthetic/artifacts/actions.json`.
- Action summary: `workspace/runs/20260809-122107-synthetic/artifacts/action_summary.json`.
- Gate 3 review: `workspace/runs/20260809-122107-synthetic/reviews/03-product-action-review.md`.
- Gate 3 decision: `workspace/runs/20260809-122107-synthetic/reviews/03-product-action-decision.json`.
- Validation reports nằm trong `workspace/runs/20260809-122107-synthetic/validation/`.

## Cách Thu review Gate 3

Trong từng dòng của `03-product-action-review.md`, điền các đánh giá evidence, strategic fit, feasibility, urgency, expected value, resources, owner, timeline và chọn đúng một `review_decision`:

- `APPROVE`: chấp nhận Action vào final approved action portfolio sau khi overall gate được duyệt.
- `REVISE`: trả Action về Skill 11 để sửa.
- `REJECT`: loại khỏi final portfolio nhưng giữ lịch sử.
- `DEFER`: lưu backlog, không coi là immediate action.

Điền `reviewer`, `reviewed_at`, `reviewer_summary` và `overall_status` trong YAML frontmatter. Quy tắc status:

- Chưa review hết: `PENDING`.
- Có ít nhất một REVISE: `CHANGES_REQUIRED`.
- Review hết, không REVISE và có ít nhất một APPROVE: `APPROVED`.
- Dừng toàn batch: `REJECTED`.

Sau khi lưu review, build lại decision manifest:

```powershell
python .agents/skills/12-product-action-hitl/scripts/build_decision_manifest.py `
  --review workspace/runs/20260809-122107-synthetic/reviews/03-product-action-review.md `
  --output workspace/runs/20260809-122107-synthetic/reviews/03-product-action-decision.json `
  --overwrite
```

Sau đó validate:

```powershell
python .agents/skills/12-product-action-hitl/scripts/validate_decision.py `
  --decision workspace/runs/20260809-122107-synthetic/reviews/03-product-action-decision.json `
  --schema .agents/skills/12-product-action-hitl/schemas/review-decision.schema.json `
  --actions workspace/runs/20260809-122107-synthetic/artifacts/actions.json `
  --report workspace/runs/20260809-122107-synthetic/validation/gate-3-validation-report.json
```

Pipeline chỉ được tiếp tục khi decision có `overall_status: APPROVED`, mọi Action đã được review, các decision sets không chồng lặp, không có revision, reviewer metadata đầy đủ và semantic validation PASS.

## Driver

Chạy lại vertical slice bằng:

```powershell
python run_vertical_slice_04.py --run-dir workspace/runs/20260809-122107-synthetic
```

Driver revalidate toàn bộ input, build và validate Action, tạo/kiểm tra Gate 3 PENDING, cập nhật runtime manifest và xác minh hash các source, prior review, Contract V1 và catalog không đổi.

## Scope stop

Khi Gate 3 còn `PENDING`, runtime manifest phải là `BLOCKED`, `pipeline_can_continue: false`, `blocking_reasons: [HUMAN_REVIEW_PENDING]`. Không được tạo `approved-actions.json`, `deferred-actions.json` hoặc `quality_control_report.json`. Skill 13 chỉ được triển khai/chạy sau explicit human approval ở bước tiếp theo.
