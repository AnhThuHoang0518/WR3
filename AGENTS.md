# WR3 News-driven Market Intelligence

Status: Contract v1 frozen for implementation; detailed runtime logic pending.

Canonical pipeline:

Market News
+ Competitor News
+ Technology News
+ Policy News
→ News Relevance HITL
→ Signal
→ Opportunity / Threat
→ Opportunity / Threat HITL
→ Product Mapping
→ Product Gap
→ Action
→ Product Action HITL
→ Quality Control

Mandatory rules:

1. Do not skip any pipeline stage.
2. Do not bypass any HITL Gate.
3. Never auto-approve HITL.
4. Only news marked KEEP may be used for Signal Synthesis.
5. Only O/T marked APPROVE may be used for Product Mapping or Action Recommendation.
6. Only actions marked APPROVE are final actions.
7. DEFER actions are backlog items, not immediate actions.
8. Product Mapping must not read products.json or map directly to the VSF list.
9. Product Gap is the only stage allowed to read and compare against products.json.
10. competitors.json is used only for Competitor News scope and analysis.
11. Orchestrator must not generate analysis content or human approvals.
12. Do not modify reference catalogs unless the user explicitly requests it.
13. Stop whenever a required HITL decision is not APPROVED.

# Language & Writing Rules

For all Vietnamese business, Market Intelligence, Smart City, and presentation content:

- Write natural professional Vietnamese, not literal translations from English.
- Prioritize clarity for non-technical business readers.
- Avoid unnecessary technical jargon.
- Avoid mixing Vietnamese and English unless the English term is an approved domain term.
- Preserve the exact business meaning when simplifying language.
- Prefer concise, presentation-friendly wording.
- Do not invent Vietnamese translations for established technical terms if the translation sounds unnatural.

When drafting, rewriting, summarizing, or polishing Vietnamese business content, use the `writing-style` skill and follow its glossary, terminology rules, and examples.

For Market Intelligence deliverables, preserve the approved source Markdown, create a separate fine-tuned Markdown with `writing-style`, and build slides from that fine-tuned Markdown. Do not use the pre-tuned Markdown as the slide copy source after a fine-tuned version exists.

If the user corrects terminology or phrasing repeatedly, treat the correction as a candidate update to the writing-style glossary. Do not update the glossary unless the user explicitly requests the change.
