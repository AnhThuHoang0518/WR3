---
name: summarize-mi-run
description: Create one concise Vietnamese Markdown report with auditable News source links and an explicit evidence-to-Signal explanation for every News item from a completed WR3 News-driven Market Intelligence run. Use when the user asks to summarize a run, consolidate approved market-intelligence outputs, generate the final MD report, or prepare Markdown content for later HTML slides. Include only approved or reviewed-accepted items and preserve the WR3 HITL and lineage boundaries.
---

# Summarize MI Run

Create a concise, executive-readable report from one WR3 run without adding analysis or changing any upstream pipeline artifact.

## Select the run

1. Use the `run_id` supplied by the user.
2. If no `run_id` is supplied, select the most recently modified directory under `workspace/runs/` that contains `manifest.json`.
3. Read only files belonging to that run.

## Require approved inputs

Before writing the report, verify:

- `reviews/01-news-relevance-decision.json` has `overall_status: APPROVED`.
- `reviews/02-opportunity-threat-decision.json` has `overall_status: APPROVED`.
- `reviews/product-mapping-review.md` has `status: REVIEWED_ACCEPTED`.
- `reviews/product-gap-review.md` has `status: REVIEWED_ACCEPTED`.
- `reviews/03-product-action-decision.json` has `overall_status: APPROVED`.

Stop without creating the report when a required decision is missing or not approved. Never auto-approve or edit a review.

## Read the approved content

- Use `artifacts/approved_news_bundle.json` as the sole authority for which News items and final News types may appear.
- Read each included News title and substantive summary from the corresponding approved Gate 1 review row. Use `reviews/01-news-source-summaries.md` only when that row lacks a substantive summary, and the approved bundle summary only as the final fallback.
- Read `source_name` and exact `source_url` from the approved News bundle. Never substitute a search URL or infer a source.
- Never display RSS placeholders, crawler notes, reviewer instructions, or unverified-content boilerplate. If no substantive summary exists, write `Chưa có tóm tắt nội dung đầy đủ đã được xác minh.`
- Read Signals from `artifacts/signals.json`, but include only Signals referenced by an approved O/T. For each included Signal, preserve its `evidence_news_ids` exactly and use that field as the sole authority for which News records may appear under the Signal.
- Read O/T only from `artifacts/approved_opportunity_threat_bundle.json`.
- Read Product Mapping from `artifacts/product_mapping.json` only after its manual review is accepted.
- Read Product Gap from `artifacts/product_gap.json` only after its manual review is accepted.
- Read Actions only from `artifacts/approved-actions.json`.
- Preserve every Action's exact `recommended_response` enum: `PREPARE`, `VALIDATE`, `MONITOR`, or `ACT`.
- Never read `products.json` or redo the portfolio comparison.

Preserve lineage one step at a time using exact stored IDs: Signal → News, O/T → Signal, Product Mapping → O/T, Product Gap → Product Mapping, Action → Product Gap. Display Map before Gap even when both are visually grouped. Never infer or invent a relationship. Verify that every News ID under a Signal is `KEEP` in the approved News bundle.

Exclude every `EXCLUDE`, `REJECT`, `REVISE`, `NEEDS_REVISION`, `DEFER`, or otherwise unapproved item. Do not mention excluded-item counts or histories.

## Write the deliverable

Write `deliverables/markdown/market-intelligence-summary.md` inside the selected run. Reserve `deliverables/slides/` for the HTML deck.

## Use exactly three report sections

```markdown
# Market Intelligence Report

- Run ID: `...`
- Thời gian: ...
- Crawl 1 tuần: DD/MM/YYYY – DD/MM/YYYY

## 1. Executive Summary

### SIGNAL-... → ACTION-...
- Signal: one concise approved signal statement
- Action: one concise approved action statement
- Hướng phản hồi: `PREPARE|VALIDATE|MONITOR|ACT`
- Priority: `...`

## 2. Findings

### SIGNAL-... — Signal title
- Signal: concise approved signal statement

#### News
- **NEWS-... — Title**
  Liên hệ `SIGNAL-...`: One concise sentence explaining which part of the Signal this News supports.
  Concise substantive summary.
  Nguồn: [source_name](exact-source-url)

#### Opportunity / Threat
- **OT-... — OPPORTUNITY|THREAT**
  - Nội dung: concise approved statement
  - Mức độ quan trọng: `...`
  - Signal liên quan: `SIGNAL-...`

#### Product Mapping
- **PM-... — Neutral market solution title**
  - O/T liên quan: `OT-...`
  - Vấn đề thị trường: concise approved statement
  - Khách hàng mục tiêu: concise approved statement

#### Product Gap
- **GAP-...**
  - Product Mapping liên quan: `PM-...`
  - Sản phẩm VSF liên quan: ...
  - Trạng thái capability: `...`
  - Capability còn thiếu: concise semicolon-separated list
  - Mức độ gap: `...`

#### Action
- **ACTION-... — Priority**
  - Product Gap liên quan: `GAP-...`
  - Hướng phản hồi: `...`
  - Hành động đề xuất: concise approved statement
  - Bước tiếp theo: concise approved statement
  - Kết quả mong đợi: concise approved statement

## 3. Approach

### Từ Signal đến Action
- Signal: ...
- Opportunity / Threat: ...
- Product Mapping: ...
- Product Gap: ...
- Action: ...

### Cách đọc hướng phản hồi
- PREPARE: **Chuẩn bị** — ...
- VALIDATE: **Kiểm chứng** — ...
- MONITOR: **Theo dõi** — ...
- ACT: **Thực thi** — ...
```

## Compression rules

- Executive Summary must contain exactly one approved Action for each included Signal. If lineage does not resolve to exactly one Action, stop and report the ambiguity instead of choosing.
- Findings are Signal-centric. Put each Signal and its complete approved lineage in one H3 block.
- Under every News title, before its summary, add exactly one `Liên hệ SIGNAL-...` sentence. State concretely which change, result, capability, or operating implication in that News supports the Signal. Derive the sentence only from the approved News content and the approved Signal statement; do not add facts, causality, certainty, or recommendations. Avoid generic wording that merely says the News is related.
- Keep each connection sentence concise and presentation-ready, with at most 180 characters after the colon. Use the exact containing Signal ID. The News records expanded under a Signal must match all and only that Signal's `evidence_news_ids`, in stored order; stop and report a lineage mismatch when the ID, membership, or order differs.
- Keep every related approved News and O/T item, but reduce each prose field to its decision-relevant core using only facts already present in approved inputs.
- In Product Mapping, keep O/T lineage, market problem, and target customer; omit `Năng lực bắt buộc` because the capability detail is retained in Product Gap.
- In Product Gap, retain the complete missing-capability meaning; merge closely related clauses only when no meaning is lost.
- In Action, keep response, priority, action, next step, and expected outcome. Do not add an owner field. Keep the next step easy to understand and complete, but omit dates, deadlines, durations, and target timelines.
- Attach exactly one compact source link immediately under every News summary. Do not create a separate source section.
- Write Executive Summary first for reader priority, Findings second for evidence and lineage, and Approach last for methodology.
- Do not include pipeline status, HITL status, validation/QC tables, raw JSON, collection metadata, or a second concluding Summary section.
