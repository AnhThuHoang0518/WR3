---
name: news-driven-mi-orchestrator
description: Coordinate the mandatory News-driven Market Intelligence pipeline, enforce three human-review gates, and continue only on APPROVED decision manifests.
---

# News-driven MI Orchestrator

## Purpose

Điều phối đúng thứ tự 14 stage, bảo toàn ID lineage và cưỡng chế ba HITL gate.

## Ngôn ngữ nội dung review

Bắt buộc các stage 01–11 tuân thủ [REVIEW_LANGUAGE_POLICY.md](references/REVIEW_LANGUAGE_POLICY.md): mọi nội dung diễn giải hướng tới reviewer phải bằng tiếng Việt; giữ nguyên ID, field/schema, enum, status token, URL, tên riêng, tên thương hiệu và thuật ngữ kỹ thuật khó dịch.

## Allowed inputs

- Stage artifact metadata thuộc cùng `run_id`.
- Ba HITL decision manifests.
- Pipeline contract, dependency matrix và HITL policy.

## Forbidden inputs

- Approval do AI hoặc orchestrator tự tạo.
- Artifact từ run khác.
- Runtime output bỏ qua stage hoặc HITL gate.
- Tự tạo nội dung news, signal, O/T, mapping, gap hoặc action.

## Output artifact

`workspace/artifacts/pipeline_manifest.json`

## Required previous approval

Mỗi downstream transition sau HITL chỉ chạy khi manifest tương ứng có `overall_status = APPROVED`.

## Next stage

Chỉ dispatch stage kế tiếp theo [PIPELINE_CONTRACT.md](references/PIPELINE_CONTRACT.md).

## Runtime implementation resources

- Validate partial/full run metadata with `schemas/runtime-run-manifest.schema.json`; never use it to replace `schemas/pipeline_manifest.schema.json`.
- Persist pre-canonical `raw_news_id` provenance in the `schemas/news-lineage.schema.json` sidecar.
- Validate the sidecar with `scripts/validators/validate_news_lineage.py` before Gate 1 review.
- Treat runtime manifest status as operational metadata, never as a HITL decision or human approval.

Không tự tạo approval, không bypass HITL, không sửa Markdown thay reviewer và không tự tạo analysis content.

Read [PIPELINE_CONTRACT.md](references/PIPELINE_CONTRACT.md), [DEPENDENCY_MATRIX.md](references/DEPENDENCY_MATRIX.md), [HITL_GATE_POLICY.md](references/HITL_GATE_POLICY.md), and [REVIEW_LANGUAGE_POLICY.md](references/REVIEW_LANGUAGE_POLICY.md).

Status: Runtime manifest and News lineage support implemented; Contract V1 remains frozen.
