---
name: opportunity-threat
description: Classify synthesized market signals as opportunities or threats.
---

# Opportunity Threat

## Purpose

Chuyển Signal hợp lệ thành Opportunity hoặc Threat cụ thể, có stakeholder và impact mechanism rõ. Stage này không thực hiện Product Mapping, Product Gap hoặc Action.

## Input bắt buộc

- `signals.json` đã validate schema và evidence lineage.
- `approved_news_bundle.json` chỉ dùng để kiểm tra evidence khi cần.
- Không đọc raw News, catalog hoặc portfolio VSF.

## Phân biệt Opportunity và Threat

- `OPPORTUNITY`: nêu cơ hội cụ thể, stakeholder có thể hưởng lợi/mua và cơ chế tạo giá trị.
- `THREAT`: nêu rủi ro cụ thể, stakeholder bị tác động và cơ chế gây rủi ro.
- Một Signal có thể sinh một loại, cả hai loại hoặc không sinh O/T khi chưa đủ căn cứ.
- Không tạo O/T trực tiếp từ News; mọi record phải có `signal_id` hợp lệ.

## Viết impact

- Tiêu chí tiên quyết là nội dung dễ hiểu và đầy đủ. Không giới hạn độ dài câu hoặc số câu nếu cần viết dài để giải thích đủ ý.
- `statement`: nói rõ đây là cơ hội hay rủi ro gì và gắn với thay đổi nào trong parent Signal.
- `impacted_stakeholders`: nêu những nhóm chịu tác động theo cách reviewer hiểu được vai trò của họ.
- `impact_mechanism`: giải thích dễ hiểu thay đổi dẫn đến giá trị hoặc rủi ro như thế nào.
- `importance`: chọn theo quy mô/tính cấp thiết evidence cho phép; không mặc định HIGH/CRITICAL.
- `rationale`: giải thích alignment với Signal.
- `assumptions`: ghi điều kiện đang giả định, không trình bày như fact.
- `evidence_gaps`: ghi dữ liệu còn thiếu để xác nhận impact.
- Không ép nội dung theo một công thức câu cố định. Chỉ viết lại khi còn mơ hồ, thiếu ý hoặc dễ bị hiểu sai.

## Ngôn ngữ nội dung hướng tới reviewer

Tuân thủ [REVIEW_LANGUAGE_POLICY.md](../00-news-driven-mi-orchestrator/references/REVIEW_LANGUAGE_POLICY.md). Viết `statement`, `impacted_stakeholders`, `impact_mechanism`, `rationale`, `assumptions`, `evidence_gaps` và rationale trong coverage report bằng tiếng Việt. Giữ nguyên ID, enum, tên riêng và thuật ngữ kỹ thuật khó dịch.

## Common mistakes

- Viết generic benefit hoặc generic threat.
- Suy diễn Threat vượt Signal.
- Tạo O/T không có stakeholder/cơ chế.
- Ép mỗi Signal có đủ Opportunity và Threat.
- Nhắc sản phẩm VSF như kết luận mapping.
- Dùng News ID thay `signal_id`.

## Validation procedure

Chạy `validate_artifact.py` để kiểm frozen schema, `OT-NNN`, required fields, type enum và Signal lineage. Chạy `build_coverage_report.py`; Signal không có O/T hợp lệ nếu có rationale. Orphan O/T hoặc invalid type phải fail trước Gate 2.

## Allowed inputs

- workspace/artifacts/signals.json.

## Forbidden inputs

- Raw news.
- Reference catalogs.

## Output artifact

`workspace/artifacts/opportunity_threat.json`

## Required previous approval

Signal Synthesis hoàn tất sau Gate 1 APPROVED.

## Next stage

`08-opportunity-threat-hitl`

Read [INPUT_OUTPUT_CONTRACT.md](references/INPUT_OUTPUT_CONTRACT.md) before using this skill.

Status: Runtime implemented for vertical slice 2; Contract V1 remains frozen.
