# Input/Output Contract — MI Quality Control

## Purpose

Kiểm tra schema, lineage, HITL, dependency và release eligibility của toàn pipeline.

## Allowed inputs

- Toàn bộ automatic-stage artifacts cùng `run_id`.
- Ba Markdown reviews và ba decision manifests.
- PIPELINE_CONTRACT.md, DEPENDENCY_MATRIX.md và HITL_GATE_POLICY.md.

QC không đọc catalog trực tiếp. Capability provenance được kiểm qua `product_gap.json.portfolio_evidence_refs`.

## Required previous approval

Product Action HITL phải có `overall_status = APPROVED`.

## Required checks

- JSON Schema, required fields và enums.
- ID lineage và orphan IDs.
- HITL status; decision sets phải disjoint và reviewed set phải bằng union.
- Signal chỉ dùng news KEEP.
- Product Mapping và Action chỉ dùng O/T APPROVE.
- Final action chỉ thuộc approved IDs; DEFER tách khỏi immediate action.
- Chỉ Product Gap được đọc products catalog.
- Capability claim có portfolio evidence refs.
- Không stage hoặc gate nào bị bypass.

## Output artifact

`workspace/artifacts/quality_control_report.json`

Mỗi check gồm `check_id`, `check_name`, `status`, `severity`, `affected_ids`, `message`, `remediation`. Status chỉ nhận `ERROR`, `WARNING`, `PASS`.

Summary gồm `overall_status`, `error_count`, `warning_count`, `passed_count`, `pipeline_eligible_for_release`. Có ERROR thì release eligibility phải false.

Status: Contract v1 frozen; detailed logic pending.
