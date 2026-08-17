---
name: mi-quality-control
description: Audit a complete News-driven Market Intelligence run after human Gate 3 review for schema integrity, end-to-end lineage, HITL decisions, dependency boundaries, portfolio evidence, immutability and release readiness. Use only after Product Action HITL has been handled; report findings and remediation without modifying upstream artifacts or human decisions.
---

# MI Quality Control

## Purpose

Kiểm tra schema, completeness, lineage, HITL approval, dependency boundary, portfolio evidence, immutability và release readiness của toàn bộ pipeline. Chỉ kiểm tra và ghi remediation; không tự sửa.

## When to use

Chỉ chạy sau khi Product Action HITL Gate 3 đã được human reviewer xử lý. Gate 3 chưa `APPROVED` vẫn phải tạo QC report với `ERROR` và release eligibility `false`, nếu input còn parse an toàn.

## Required inputs

- Toàn bộ artifact stage 01–12, raw News input và approved/deferred bundles.
- Ba HITL review Markdown và ba decision manifests.
- Các validation/coverage/dependency reports và runtime manifest.
- Contract V1, dependency matrix, HITL policy và frozen schemas.
- `competitors.json` và `products.json` ở chế độ read-only để xác minh scope/provenance; không dùng để tạo lại phân tích portfolio.

Đọc [INPUT_OUTPUT_CONTRACT.md](references/INPUT_OUTPUT_CONTRACT.md) trước khi chạy. Giữ nguyên Contract V1 và mọi frozen schema.

## Output

- `validation/quality_control_report.json` theo frozen `schemas/output.schema.json`.
- `validation/final-artifact-integrity.json` với SHA-256 baseline/final.
- `reports/quality-control-summary.md` dành cho vận hành, không phải HITL gate hoặc MI report.
- `intermediate/qc_input_index.json` chỉ chứa index, metadata và hash ban đầu.

## Finding status

Chỉ dùng `ERROR`, `WARNING`, `PASS`.

### ERROR

Pipeline không hợp lệ, như schema fail, orphan ID, rejected/excluded leakage, boundary violation, unsupported capability claim, incomplete HITL, modified approved artifact hoặc bypassed stage. Có ERROR thì `pipeline_eligible_for_release = false`.

### WARNING

Rủi ro đáng chú ý nhưng không tự làm release fail, như single-source evidence, mechanical one-to-one mapping, adjacent portfolio category, weak catalog detail hoặc unresolved action dependency.

### PASS

Check đạt yêu cầu và không cần remediation.

## Overall status

Tuân thủ frozen output schema. Có ERROR → `ERROR`; không ERROR nhưng có WARNING → `WARNING`; không có ERROR/WARNING → `PASS`. Chỉ không có ERROR mới được đặt `pipeline_eligible_for_release = true`, trừ rule bắt buộc khác của Contract V1.

## Procedure

1. Thu thập input index và SHA-256 baseline trước khi tạo QC output.
2. Chạy file/schema, completeness, HITL, lineage, dependency, portfolio-evidence và Action checks.
3. Không dừng chỉ vì finding ERROR; tiếp tục build một report hợp lệ nếu input vẫn parse an toàn.
4. Tạo integrity manifest, build và validate QC report, rồi tạo summary Markdown.
5. So sánh lại hash của mọi immutable source; chỉ runtime manifest được thay đổi có chủ đích sau report.
6. Cập nhật runtime stage 13 sau khi QC execution hoàn tất. Không dùng `pipeline_can_continue` làm release decision; đọc `pipeline_eligible_for_release` trong QC report.
7. Dừng pipeline. Không tạo weekly/real Market Intelligence report và không bắt đầu real-data run.

## Required check groups

Thực hiện đủ: file/schema integrity, pipeline completeness, News/Gate 1, Signal, O/T/Gate 2, Product Mapping boundary, Product Gap evidence, Action quality, Gate 3 final portfolio, cross-stage lineage, dependencies, hash immutability, runtime consistency và release readiness.

## No auto-remediation

- Không sửa hoặc rebuild stage 01–12.
- Không thay human review/decision, không auto-approve/reject.
- Không xóa artifact lỗi, không tạo Action hoặc analysis mới.
- Không gọi internet.
- Mỗi ERROR/WARNING phải nêu affected IDs và remediation; chỉ báo cáo, không thực thi remediation.

## Runtime scripts

Chạy `collect_inputs.py`, các `run_*_checks.py`, `build_integrity_manifest.py`, `build_quality_control_report.py`, `validate_quality_control_report.py` và `generate_quality_control_summary.py` qua root driver `run_skill_13_quality_control.py`.

## End state

QC execution có thể `COMPLETED` dù report có ERROR. Release readiness chỉ thuộc QC report. Stage tiếp theo không tồn tại.
