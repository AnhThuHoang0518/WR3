# Terminology Rules

## 1. Priority order

Apply terminology in this order:

1. Direct wording required by the user for the current task.
2. Official names and exact values in the source artifact.
3. Mandatory WR3 pipeline and HITL terminology.
4. Preferred wording in `glossary.md`.
5. Natural Vietnamese appropriate to the intended audience.

Never change a source value merely to make it read more smoothly.

## 2. Vietnamese and English

- Prefer Vietnamese for normal business prose.
- Keep English for official names, pipeline stage names, schema fields, industry-standard abbreviations, or concepts that lose precision in translation.
- Avoid redundant mixtures such as “công nghệ AI technology”.
- At first use, add a Vietnamese explanation and the established English term in parentheses only when useful.
- After first use, choose one stable form and use it consistently.

## 3. Acronyms and capitalization

- Preserve official forms such as `AI`, `IoT`, `API`, `HITL`, `VSF`, and `Digital Twin`.
- Do not invent acronyms for phrases that appear only once or twice.
- Preserve capitalization in IDs, enum values, product names, and stage labels.
- Do not translate text inside code, YAML, JSON, Markdown link targets, or record identifiers.

## 4. Pipeline invariants

- Preserve `KEEP`, `APPROVE`, `REVISE`, `REJECT`, `DEFER`, `PENDING`, and any other status exactly.
- Preserve record IDs and lineage links exactly.
- Preserve every `Liên hệ SIGNAL` explanation and its referenced Signal ID; improve its wording only when the evidence-to-Signal relationship remains unchanged.
- Do not rewrite a proposed Action as an approved commitment.
- Do not describe a DEFER item as an immediate priority.
- Do not strengthen an Opportunity/Threat beyond its reviewed status.
- Do not use editorial polish to bypass or imply a HITL decision.

## 5. Evidence and certainty

Match verbs to evidence strength:

- Direct evidence: “ghi nhận”, “cho thấy”, “xác nhận” only when the source confirms it.
- Supported inference: “cho thấy xu hướng”, “gợi ý”, “nhiều khả năng”.
- Possibility: “có thể”, “mở ra khả năng”, “tiềm ẩn nguy cơ”.
- Recommendation: “nên xem xét”, “đề xuất”, “cần đánh giá”.
- Approved commitment: use decisive language only when the decision artifact is explicitly approved.

Avoid “chắc chắn”, “tất yếu”, “sẽ” or superlatives unless the source supports them.

## 6. Numbers, dates, and units

- Preserve numeric values, signs, currencies, percentages, ranges, dates, and units exactly unless the user requests normalization.
- In Action copy, remove incidental quantities only when the user or approved house style allows it and the count merely makes draft wording artificially narrow, such as a provisional number of venues, pain points, diagrams, flows, or processes.
- Preserve any number that defines approved scope, a target or KPI, budget, timing, decision criteria, evidence, or another auditable commitment.
- If it is unclear whether an Action number is incidental or decision-critical, retain it and flag the ambiguity instead of deleting it silently.
- Do not convert a percentage point into a percent or vice versa.
- Do not round values or infer a missing unit.
- Keep reporting period and geographic scope attached to the claim.

## 7. Business-readable sentences

- Name the actor before the action when known.
- Prefer “giảm thời gian xử lý” to “thực hiện tối ưu hóa thời gian xử lý”.
- Replace abstract nouns with verbs when meaning is preserved.
- Split a sentence when it contains more than one important finding or implication.
- Put the finding first, then the evidence or implication.
- Avoid strings of three or more nouns that make the relationship unclear.

## 8. Outcome language

Describe the affected outcome when it exists in the source:

- User: fewer steps, less waiting, safer movement, clearer information, smoother handoffs.
- Operator: faster detection, better coordination, fewer manual tasks, clearer accountability.
- Business: cost, revenue, adoption, retention, delivery risk, time to market.
- City: service quality, safety, mobility, environment, resilience, public trust.

Do not invent an outcome merely to make the copy sound strategic.

## 9. Headings, bullets, and slide copy

- Use parallel grammatical structures in sibling headings and bullets.
- Start bullets with the finding or action, not filler such as “Việc…”.
- Keep slide titles interpretive: state the message, not only the topic.
- Keep report headings stable when they belong to an approved template or schema.
- Preserve fixed field labels and machine-consumed schema keys. Translate or naturalize a label only when it is display copy and the change cannot affect parsing, parity, or lineage.
- Do not end every bullet with punctuation unless the bullets are full sentences.
- Build slide copy from the fine-tuned Markdown, not the pre-tuned source.

## 10. Quotations and citations

- Do not paraphrase text marked as an exact quote.
- Preserve citation placement when moving it could obscure which claim it supports.
- Preserve all Markdown links and URL targets exactly.
- If a sentence must be split, reposition a citation only when its coverage remains unambiguous.

## 11. Ambiguity handling

If a source phrase has multiple plausible meanings, do not choose one silently. Preserve the closest neutral wording and flag the ambiguity outside the edited document. If a suspected terminology issue affects facts, lineage, or decision status, stop editing that passage and request clarification.
