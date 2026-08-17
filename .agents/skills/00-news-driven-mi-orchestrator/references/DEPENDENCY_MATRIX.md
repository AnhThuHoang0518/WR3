# Dependency Matrix

| Skill | Được đọc | Bị cấm đọc | Output/next | Approval |
|---|---|---|---|---|
| 00 Orchestrator | Contracts, pipeline manifest, artifact metadata, HITL decisions | Catalogs, source content, tự tạo analysis/approval | Dispatch đúng stage | Mọi HITL transition |
| 01 Market News | Market sources | Cả hai catalogs | Gate 1 | Không |
| 02 Competitor News | Competitor sources, `competitors.json` | `products.json` | Gate 1 | Không |
| 03 Technology News | Technology sources | Cả hai catalogs | Gate 1 | Không |
| 04 Policy News | Policy sources | Cả hai catalogs | Gate 1 | Không |
| 05 News HITL | Bốn News artifacts | Catalogs | Signal | Human Gate 1 |
| 06 Signal | News KEEP, decision 01 | News khác, catalogs | O/T | Gate 1 APPROVED |
| 07 O/T | Signals | News thô, catalogs | Gate 2 | Gate 1 APPROVED |
| 08 O/T HITL | Signals, O/T | Catalogs | Mapping | Human Gate 2 |
| 09 Product Mapping | Signals, O/T APPROVE, decision 02 | `products.json`, VSF option list | Gap | Gate 2 APPROVED |
| 10 Product Gap | Mapping, `products.json` | News thô | Action | Gate 2 APPROVED |
| 11 Action | O/T APPROVE, decision 02, mapping, gap | Catalogs | Gate 3 | Gate 2 APPROVED |
| 12 Action HITL | Signals, O/T APPROVE, mapping, gap, actions | Catalogs | QC | Human Gate 3 |
| 13 QC | Mọi artifacts, reviews, decisions, contracts | Catalogs trực tiếp | Release eligibility | Gate 3 APPROVED |

Chỉ Competitor News đọc `competitors.json`. Chỉ Product Gap đọc `products.json`. QC kiểm capability provenance qua `portfolio_evidence_refs`.
