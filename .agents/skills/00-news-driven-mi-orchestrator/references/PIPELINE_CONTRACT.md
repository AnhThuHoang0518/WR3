# Pipeline Contract

Contract version: `1.0.0-contract`

## Canonical pipeline

Market News + Competitor News + Technology News + Policy News
→ News Relevance HITL
→ Signal Synthesis
→ Opportunity / Threat
→ Opportunity / Threat HITL
→ Product Mapping
→ Product Gap
→ Action Recommendation
→ Product Action HITL
→ Quality Control

Bốn News stage có thể chạy song song. Không stage hoặc HITL gate nào được bỏ qua.

## Stage contract

| # | Stage | Allowed input | Runtime output | Điều kiện chạy tiếp |
|---|---|---|---|---|
| 01 | Market News | Market sources | `market_news.json` | Schema hợp lệ |
| 02 | Competitor News | Competitor sources + `competitors.json` | `competitor_news.json` | Schema hợp lệ |
| 03 | Technology News | Technology sources | `technology_news.json` | Schema hợp lệ |
| 04 | Policy News | Policy sources | `policy_news.json` | Schema hợp lệ |
| 05 | News Relevance HITL | Bốn News artifacts | Review/decision 01 | Human overall APPROVED |
| 06 | Signal Synthesis | Chỉ news KEEP + decision 01 | `signals.json` | Evidence/lineage hợp lệ |
| 07 | Opportunity / Threat | `signals.json` | `opportunity_threat.json` | O/T gắn signal hợp lệ |
| 08 | O/T HITL | Signals + O/T | Review/decision 02 | Human overall APPROVED |
| 09 | Product Mapping | Signals + O/T APPROVE + decision 02 | `product_mapping.json` | Outside-in mapping hợp lệ |
| 10 | Product Gap | Mapping + `products.json` | `product_gap.json` | Capability có catalog evidence |
| 11 | Action Recommendation | O/T APPROVE + decision 02 + mapping + gap | `actions.json` | Action lineage hợp lệ |
| 12 | Product Action HITL | Signals + O/T duyệt + mapping + gap + actions | Review/decision 03 | Human overall APPROVED |
| 13 | Quality Control | Mọi artifacts, reviews, decisions, contracts | `quality_control_report.json` | Không ERROR |

Tất cả automatic artifacts nằm trong `workspace/artifacts`; review artifacts nằm trong `workspace/reviews`.

## Relationship invariants

1. News → Gate 1: mọi source `news_id` phải được review đúng một lần.
2. Gate 1 → Signal: chỉ `kept_news_ids`.
3. Signal → O/T: mọi O/T có `signal_id` tồn tại; một signal có thể có cả Opportunity và Threat.
4. Gate 2 → Product Mapping: chỉ `approved_ot_ids`.
5. Mapping → Gap: mọi gap có `product_mapping_id` và `signal_id` hợp lệ.
6. Gap + O/T → Action: action giữ signal, O/T, mapping và gap IDs.
7. Action → Gate 3: mọi action được review đúng một lần.
8. Gate 3 → QC: chỉ `approved_action_ids` là final; deferred IDs là backlog.

## ID lineage

`news_id → signal_id → ot_id → product_mapping_id → gap_id → action_id`

- Signal dùng array `evidence_news_ids`.
- Mapping và Action dùng array `related_ot_ids`.
- Action dùng array `gap_ids`.
- Downstream IDs phải tồn tại, cùng `run_id`, đúng approval state và không mồ côi.

## HITL transition

- PENDING: dừng chờ review.
- CHANGES_REQUIRED: quay lại stage tạo item, tạo lại downstream output bị ảnh hưởng và review lại.
- APPROVED: cho phép stage kế tiếp.
- REJECTED: dừng run.

Orchestrator không tạo nội dung phân tích, không tạo approval, không sửa Markdown thay reviewer và không bypass gate.

Status: FROZEN_FOR_IMPLEMENTATION. Runtime logic is not implemented.
