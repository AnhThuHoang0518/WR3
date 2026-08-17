---
name: writing-style
description: Apply natural Vietnamese business writing and approved terminology while preserving facts, evidence, lineage, structure, decision status, and release boundaries. MUST use for drafting, rewriting, summarizing, or fine-tuning Vietnamese business reports, Smart City content, Market Intelligence Markdown, Action copy, executive summaries, and slide copy; create and validate separate fine-tuned Markdown before building slides.
---

# Writing Style

## Objective

Produce Vietnamese business writing that is natural, clear, concise, professional without sounding academic, accurate in meaning, and ready for reports or slides.

Never optimize for elaborate wording at the expense of clarity.

## Reference loading

Before drafting or rewriting Vietnamese business content:

1. Read `references/glossary.md` and `references/terminology-rules.md` completely.
2. Read the routing guide at the top of `references/bad-good-examples.md`, then read the examples relevant to the requested content.
3. Read all examples when fine-tuning a complete Market Intelligence report or when several pipeline stages appear in one document.
4. Preserve the mandatory WR3 pipeline and HITL rules in `AGENTS.md`.

Treat direct user wording as authoritative when it conflicts with a style preference. Do not let editorial preferences override facts, reviewed decisions, official names, schema values, or pipeline boundaries.

## Core workflow

1. Determine the audience, output mode, source artifact, and whether the result is for review or release.
2. Lock facts, evidence, scope, IDs, citations, decisions, and certainty before changing wording.
3. Edit in three passes: terminology, sentence clarity, then supported business or user impact.
4. Apply the stage-specific rules below when the document contains Market Intelligence records.
5. Compare difficult passages with the routed BAD–GOOD examples.
6. Write a separate output unless the user explicitly requests an in-place edit.
7. Validate structural parity and report any release or source ambiguity outside the document.

## Market Intelligence delivery workflow

Use this delivery sequence after the Market Intelligence source Markdown is complete and its required HITL gates are approved:

```text
Completed/approved MI Markdown
→ writing-style editorial pass
→ <source-stem>-fine-tuned.md
→ VSF MI slide-generation skill
→ HTML/PDF presentation built from the fine-tuned Markdown
```

This is a post-analysis editorial workflow. It does not add, replace, approve, or skip any canonical WR3 stage or HITL gate.

### 1. Select the source

When the user requests the latest Markdown:

1. Search canonical `deliverables/markdown` locations first.
2. Exclude files whose stem already ends in `-fine-tuned`.
3. Sort candidates by modification time, then confirm the run ID and intended report type.
4. Prefer a completed summary artifact over review forms, QC reports, implementation notes, or slide copy.
5. Verify the required HITL decisions. Stop if a required gate is not `APPROVED`.
6. Check QC or release status separately. A Gate-approved run that fails QC may receive a clearly labeled review-only fine-tuned draft, but must not be described as release-ready.

If a sibling fine-tuned file already exists but is older than the source, regenerate it from the current source rather than incrementally trusting the stale copy.

### 2. Lock the source

Keep unchanged unless the user explicitly asks otherwise:

- Markdown heading hierarchy, tables, list nesting, anchors, and code blocks;
- News, Signal, Opportunity/Threat, Product Mapping, Product Gap, and Action IDs;
- `KEEP`, `APPROVE`, `REVISE`, `REJECT`, `DEFER`, `PENDING`, and other decision labels;
- company names, product names, source titles, URLs, citations, dates, numbers, units, and quoted text, except incidental quantities in fine-tuned Action copy when `references/terminology-rules.md` explicitly allows their removal;
- every `Liên hệ SIGNAL` explanation and its referenced Signal ID;
- evidence lineage, approval scope, and distinctions between fact, inference, recommendation, and decision;
- fixed template labels and schema keys unless the source explicitly treats them as display copy.

Do not add facts, causal claims, benefits, recommendations, or certainty unsupported by the source. Do not silently fix a suspected factual error; flag it separately.

### 3. Tune in three passes

- **Terminology pass:** normalize approved terms, capitalization, acronyms, and Vietnamese–English usage.
- **Sentence pass:** use active constructions, clear verbs, short sentences, and one main idea per sentence.
- **Business-impact pass:** foreground consequences for users, operators, cities, or the business only when supported by the source.

### 4. Apply stage-specific editing

- **Executive Summary:** mirror the underlying Signal and Action; lead with the finding and decision direction without creating a new conclusion.
- **Signal:** state the market change first, then the supported user or business implication. Calibrate certainty.
- **News:** preserve the exact record ID, source title, evidence figures, source link, and `Liên hệ SIGNAL` line. Improve readability without upgrading a source claim.
- **Opportunity / Threat:** express cause → consequence where useful. Keep `OPPORTUNITY`, `THREAT`, priority, and review status unchanged.
- **Product Mapping:** describe neutral market needs, solution categories, and target customers. Do not introduce VSF products or read `products.json` at this stage.
- **Product Gap:** distinguish a broad capability from an individual feature. Preserve catalog provenance, match status, and uncertainty.
- **Action:** start with a clear verb, preserve response type and approval status, then state the next step and decision outcome. Apply the Action quantity rule below.
- **Approach or methodology:** explain the process in plain language without adding analysis or implying approval.

### 5. Handle quantities in Action copy

Remove an Action quantity only when all of the following are true:

1. The user or approved house style allows removal.
2. The quantity merely narrows draft wording, such as a provisional count of venues, pain points, diagrams, flows, or processes.
3. Removing it does not change the approved intent, evidence, priority, acceptance criteria, or decision boundary.

Never remove a target, KPI, budget, date, threshold, approved scope, acceptance criterion, evidence figure, or auditable commitment. When uncertain, retain the quantity and flag it outside the document.

### 6. Preserve structural parity

Verify that every source section, record, ID, link, citation, decision status, and decision-critical numeric value remains present in the edited version. For Action copy, apply the incidental-quantity rule in `references/terminology-rules.md`; never remove an approved scope, target, KPI, budget, date, decision criterion, or auditable commitment.

For Markdown reports, run from any working directory by resolving the installed skill directory:

```text
python <skill-directory>/scripts/validate_fine_tuned.py <source.md> <fine-tuned.md> [--allow-action-incidental-number-removal]
```

Fix every validation error before delivery. Review each warning and mention any intentional Action quantity removal in the editing note.

### 7. Write a separate output

Unless the user requests an in-place edit, create a sibling file named `<source-stem>-fine-tuned.md`. Never overwrite the approved or canonical source by default.

Return a short editing note outside the document describing material terminology choices, ambiguities, or possible source issues. Do not add this note to the report unless requested.

Include the source path, output path, intentional Action quantity removals, material terminology choices, unresolved ambiguities, and QC/release status when relevant.

### 8. Hand off to slide generation

After the fine-tuned Markdown passes quality checks:

1. Treat the fine-tuned Markdown as the sole copy source for slide titles, subtitles, findings, implications, recommendations, and other narrative text.
2. Use `create-vsf-mi-finding-slides` for VSF MI slide creation.
3. Continue using canonical run artifacts for source images, evidence validation, exact citations, and lineage checks when the slide skill requires them.
4. Do not fall back to the pre-tuned Markdown for wording. If information is missing from the fine-tuned version, fix the parity issue in that version before building slides.
5. Preserve the fine-tuned meaning when shortening copy for slide fit; do not introduce a second, divergent editorial interpretation.

## Writing principles

### Prefer

- clear verbs and active sentences;
- short sentences with one main idea;
- wording a non-technical business reader can understand immediately;
- concrete subjects and outcomes;
- consistent terminology across headings, prose, tables, and slides;
- calibrated language such as “cho thấy”, “có thể”, or “nhiều khả năng” when evidence is not conclusive.

### Avoid

- literal translation from English;
- excessive nominalization and abstract nouns;
- buzzwords and inflated claims;
- long multi-clause sentences;
- technical terms when a precise plain-language expression works better;
- repeatedly using “nhằm”, “thông qua”, “qua đó”, “đồng thời”, and “được kỳ vọng”;
- unnecessary Vietnamese–English mixing;
- generic outcomes such as “nâng cao hiệu quả” without saying what becomes faster, safer, cheaper, or easier.

## Meaning preservation

Do not simplify so aggressively that technical distinctions disappear.

Bad:

> Kiểm tra interoperability của hệ thống.

Better:

> Kiểm tra các hệ thống có trao đổi đúng dữ liệu, trạng thái và lệnh xử lý hay không.

If `interoperability` is the subject being defined, retain the term once and explain it in Vietnamese. Apply the same rule to established terms such as Digital Twin, IoT, AI, API, and use case.

## Output modes

Choose the mode from the request; use **report** by default.

- **Report:** complete sentences, compact paragraphs, auditable nuance preserved.
- **Executive summary:** lead with the finding and business implication; remove secondary detail without dropping essential evidence.
- **Action copy:** use a verb-led instruction, concrete next step, expected decision outcome, and only the quantities needed to preserve scope or acceptance criteria.
- **Slide:** use compact phrases and strong verbs; preserve enough context for each point to stand alone.

## Final quality checks

Confirm all of the following before delivery:

- Meaning, confidence, and recommendation strength match the source.
- No facts, IDs, links, citations, decision-critical figures, or decisions were added, lost, or changed; any removed Action quantity satisfies the incidental-quantity rule.
- Every source News record still contains its source title, evidence text, `Liên hệ SIGNAL` explanation, and URL.
- Product Mapping remains portfolio-neutral; Product Gap remains the only stage that compares against VSF products.
- Terms comply with the glossary and terminology rules.
- Each sentence is readable on the first pass.
- Paragraphs and bullets do not repeat the same idea.
- English appears only when approved or needed for precision.
- The result sounds like professional Vietnamese written for business readers, not a translated English draft.
- The parity validator reports no errors, and every warning has been reviewed.
- The handoff distinguishes review-only output from release-ready output when QC is not eligible.
- If slides are requested, their copy source is the fine-tuned Markdown.

