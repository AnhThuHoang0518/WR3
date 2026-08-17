---
name: create-vsf-mi-finding-slides
description: Create the sole self-contained VSF-branded Finding Board HTML Market Intelligence presentation from approved WR3 summary Markdown, including explicit evidence-to-Signal explanations, one blank real-world reference template per Signal, blank verified-technology placeholders, and editable reference cells beside Product Gap features. Optionally transfer extractive News presentation metadata from an explicitly supplied approved HTML deck. Use when Codex needs to generate or refresh the clean white three-page Finding design while preserving every approved field, exact lineage, citations, images, and presentation emphasis.
---

# Create VSF MI Finding Slides

Turn the newest approved three-section WR3 Markdown summary into the sole executive-ready standalone `.html` deck. Apply the bundled white Finding-board visual system without shortening or omitting approved content.

## Preserve approval boundaries

1. Select the newest validated `workspace/runs/*/deliverables/markdown/market-intelligence-summary-fine-tuned.md` unless the user names a run. If a fine-tuned sibling exists, never use the pre-tuned Markdown as slide copy. Use the canonical run artifacts separately for gate, evidence, image, citation, and lineage checks.
2. Require all five review artifacts to be approved or reviewed-accepted. Let the generator enforce this check.
3. Stop when any required decision is missing or not approved. Never auto-approve or edit a review.
4. Treat the Markdown as the authority for substantive analysis, lineage, and every News-to-Signal connection sentence. Use an explicitly supplied approved source HTML only as a presentation overlay for News subtitles and exact extractive highlights. Always render the fixed cover copy `VSF MARKET INTELLIGENCE`, `Market Intelligence Report`, and the unit line split across two lines: `Phòng Nghiên cứu thị trường và Trải nghiệm khách hàng` then `• Khối Smart City`. Change only the period label, derived as `Tuần N - Tháng M (dd/mm/yyyy – dd/mm/yyyy)`. Do not let the overlay change cover copy, facts, lineage, News-to-Signal connections, O/T, Map, Gap, or Action content.
5. Write only under the selected run's `deliverables/slides/` directory unless the user explicitly chooses another output path.

## Read the supporting references

Read [references/input-contract.md](references/input-contract.md) when validating or changing parsing. Read [references/design-system.md](references/design-system.md) whenever changing composition, styling, typography, density, image treatment, or responsive behavior. Inspect [assets/finding-layout-reference.png](assets/finding-layout-reference.png) before any visual redesign.

## Select source images

- Require at least one suitable local source image for each Signal, matched to a related News ID.
- Give text priority over imagery. Never place an image before or beside the text in a News card. When a News card is the only card in its Evidence column, center its own source image in the available space after the summary and before the source/date footer. When two News cards are stacked in a column, keep both text-only and move their available source images to the right-side media gallery. If all related images are already used inline and the O/T column would otherwise leave a large empty lower area, reuse one of the same Signal's source images beneath the O/T cards. Never add a generic or unrelated image.
- Prefer the article's own `og:image` or `twitter:image`; never use unrelated stock imagery or AI-generated substitutes.
- Save each image as `deliverables/slides/assets/<NEWS-ID>.<ext>` and record retrieval provenance in `deliverables/slides/assets/news-image-sources.json`.
- Keep the News article URL clickable on both image and citation.
- If a Signal has no suitable source image, report its ID and related News IDs before generating the final deck.

## Generate the deck

Run the bundled generator:

```powershell
$latestSummary = Get-ChildItem C:\WR3\workspace\runs -Recurse -Filter market-intelligence-summary-fine-tuned.md | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName
python scripts/generate_vsf_mi_finding_slides.py --input $latestSummary
```

The default output is `<run>/deliverables/slides/market-intelligence-finding-board.html`.

When the user explicitly requests an editable PowerPoint, first generate and validate the HTML above, then use `html-to-editable-pptx` on that HTML. The HTML is the visual source of truth and carries the blank fill-in regions through `data-ppt-placeholder` annotations:

```powershell
powershell -File C:\WR3\.agents\skills\html-to-editable-pptx\scripts\html2ppt.ps1 <run>/deliverables/slides/market-intelligence-finding-board.html --output <run>/deliverables/slides/market-intelligence-finding-board-editable.pptx --debug
```

The editable export must use native PowerPoint text boxes, rounded rectangles, lines, pictures, hyperlinks, and named blank fill-in text boxes. Never use a screenshot or full-slide raster as the slide background. Keep all text and card geometry editable, keep source images individually movable and croppable, and never auto-fill any annotated placeholder.

Use `--output <path>` only when the user requests a specific destination. Use `--logo <path>` only for an approved replacement logo. Use `--exclude-news-id NEWS-...` only when the user explicitly requests omission of an exact News record; never change the Markdown or upstream reviews.

Use `--source-deck <approved-html>` only when the user identifies an existing approved deck whose News presentation copy must carry forward. When omitted, generate directly from the approved Markdown. Transfer only:

- each visible News article title and the publication date beside the source link in the News footer; validate its visible evidence-to-Signal explanation against the Markdown instead of importing it; accept the legacy `Liên hệ SIGNAL-…:` prefix but do not require or reproduce that prefix;
- every exact underlined evidence phrase, validated as a literal substring of the approved Markdown summary.

Reject missing News records, title mismatches, broken Signal lineage, non-extractive highlights, overlapping highlights, or more than three highlights per News item.

## Required slide order

1. Cover: use `assets/backgrounds1.png` as the full-slide background, then place the VSF logo at upper-right; thin red top rule and double red left rule; eyebrow `VSF MARKET INTELLIGENCE`; two-line heading `Market Intelligence Report`; fixed unit copy on two lines with `• Khối Smart City` on the second line; red separator; and only the dynamic period label `Tuần N - Tháng M (dd/mm/yyyy – dd/mm/yyyy)`. Do not show Run ID, report time, stage cards, or `FROM SIGNAL TO ACTION`.
2. Executive Summary: title it `Điểm nhấn thị trường và Đề xuất hành động`, with exactly one Signal to one approved Action per row, retaining the full approved Signal and Action text, using regular-weight body copy, and no explanatory subtitle. Add the fixed label `Công nghệ đã kiểm chứng:` under each Action and leave its adjacent fill-in placeholder blank.
3. Findings: exactly three consecutive slides per Signal.
   - Page A: exact Signal statement; every related News title, required evidence-to-Signal explanation, and summary; source images placed only according to the Evidence-column rule; and every approved Opportunity/Threat record and priority. Do not display a `Liên hệ SIGNAL-…:` label.
   - Reference page: title it `SIGNAL-ID — GIẢI PHÁP ĐÃ TRIỂN KHAI THỰC TẾ, THAM CHIẾU CHO HÀNH ĐỘNG CỦA VSF`; create three blank reference cards plus one blank `Điểm chung:` band. Keep only the fixed labels and annotated empty regions; do not show a `Nguồn:` field or visible quote/backtick markers around placeholders. Do not copy or infer examples from any source.
   - Page B: complete Product Mapping, complete reviewed Product Gap, and complete approved Action. Retain every Markdown field and every missing-capability item. Put missing features in a two-column table; keep the left text exact and leave every right `THAM CHIẾU` cell blank and annotated for PowerPoint entry.
4. Approach: title it `Từ Điểm nhấn thị trường đến Đề xuất hành động`, with no explanatory subtitle and no separate `Từ Signal đến Action` heading above the flow. Retain the Signal to O/T to Product Mapping to Product Gap to Action sequence, plus PREPARE, VALIDATE, MONITOR, and ACT definitions.

Do not add agenda, provenance, Map-only, Gap-only, Action-only, continuation, or closing Summary slides. The reference page is presentation scaffolding, not a new WR3 pipeline stage or analysis artifact. The expected slide count is `3 + 3 * number_of_signals`.

## Preserve content and visual fidelity

- Preserve every approved substantive field; do not summarize, compress, rewrite, or omit source wording to make it fit.
- Parse each required Markdown `Liên hệ SIGNAL-…` sentence for lineage validation, then render only its explanation directly between the News title and summary. Do not display the `Liên hệ SIGNAL-…:` prefix. Use the normal body text color and regular weight. Reject a missing sentence, an empty explanation, a Signal ID different from the containing Finding, or an explanation longer than 180 characters.
- Preserve each citation link at the same computed font size as the approved fullscreen HTML. Do not add a converter-only font scaling override.
- Use the bundled local `assets/fonts/VSFPro.ttf` as `VSF Pro` for every display heading and `assets/fonts/Lexend-VariableFont_wght.ttf` as `Lexend` for all body copy. Embed both fonts in standalone HTML with `@font-face`; use the same family names in editable PowerPoint output.
- Use `assets/vsf-logo-transparent.png` as the default logo asset. Render it without a border, white tile, background fill, or shadow so the logo blends directly into the slide background while preserving clear space and aspect ratio.
- Use `assets/backgrounds1.png` as the full-bleed background image for slide 1 only. Keep it behind the fixed cover copy, with `object-fit: cover` and no separate floating image element.
- Apply user-approved Finding Board copy refinements at the presentation and News-editorial source layers; never rewrite the approved Markdown. Use `khách hàng` instead of standalone `khách` everywhere in the generated deck, including News cards, avoid the phrase `nhiều nhất`, remove unnecessary item counts from proposed work, and translate descriptive English terms into clear Vietnamese when a natural equivalent exists. Keep quantitative evidence unchanged, and preserve technical names, IDs, URLs, dates, lineage keys, and control enums such as AI, IoT, KPI, Smart City, VSF, SIGNAL, ACTION, PREPARE, and HIGH.
- Render `Capability còn thiếu` as `Tính năng còn thiếu`. Translate terms such as `service blueprint`, `go/no-go`, and `pilot` in narrative copy to Vietnamese equivalents such as `sơ đồ mô tả hành trình và cách thức phục vụ`, `đánh giá có nên triển khai`, and `thử nghiệm`.
- When a source deck is used, preserve only its validated News highlight boundaries exactly. Render highlights as red underlines with a light red marker band; never change the fixed cover copy.
- Preserve exact IDs, enums, source URLs, source order, and Vietnamese text from the Markdown.
- Preserve Map before Gap in reading order and validate the entire O/T to Map to Gap to Action lineage.
- Keep the same `SIGNAL-ID — title` on both Finding pages; use `NN · FINDING NN A/B` only as the eyebrow.
- Render the Signal as a full-width pale-blue statement bar on Page A.
- Use a two-column Page A: Evidence on the left; source image and O/T cards on the right.
- Use Page B for Market Fit and Gap above a full-width Action band. The two upper cards must always have exactly equal height, set by the taller card's content. Place the Action band immediately below their shared bottom edge instead of pinning it to the slide bottom. Include all Map fields, product evidence, capability status, every missing capability, gap level, proposed action, response, priority, next step, and expected outcome.
- Render missing features as table rows. Use `TÍNH NĂNG CÒN THIẾU` for the left header and `THAM CHIẾU` for the right header. Keep the complete approved wording on the left; leave the matching right cell blank with a unique `data-ppt-placeholder` name. Treat each cell as one editable text group, not separate objects for individual lines or inline fragments. Never derive the reference from News, TECH records, a source deck, or external research.
- Keep one compact footer row at the bottom of every News card: `NEWS-ID · source_name ↗` followed directly by `dd/mm/yyyy` (no `Xuất bản:` label); retrieve the date from the approved News bundle when no source-deck overlay is supplied, and retain the exact URL in the source link. Capitalize the first letter of every displayed bullet item.
- Keep all assets embedded as data URIs. Do not load network fonts, scripts, analytics, or remote assets.
- On the final Approach slide, reserve a dedicated logo column and constrain the title to the remaining header width; never allow the title to run underneath or behind the logo.
- Keep the Approach method labels compact: use a slightly smaller label size and enough label-column width for `OPPORTUNITY / THREAT` to wrap without touching its explanation.
- For every Finding Page A News card that contains an inline source image, let the image expand to fill the remaining card height. Use `object-fit: cover` for rectangular images and `object-fit: contain` for square or near-square images; never apply a one-News-ID-only sizing exception.
- On Finding Page B, keep the complete approved Product Gap feature table visible inside the fixed 16:9 card; use compact table typography and spacing when needed, never clip or hide the final row.

## Check the result

1. Confirm `gate_check: APPROVED`, `theme: finding-board`, `self_contained: true`, and `slides = 3 + 3 * number_of_signals`.
2. Confirm both bundled fonts are embedded, every embedded News image follows the Evidence-column rule, at least one related source image is available for every Signal, and no external asset dependency remains.
3. Open the HTML and test Arrow keys, Page Up/Down, Space, Home/End, fullscreen, scroll snap, and print preview. Confirm the logo has no visible frame or white box.
4. Inspect desktop and narrow widths for compact title-to-logo spacing, title wrapping, evidence density, image crop, logo clear space, O/T balance, all blank reference cards, blank Executive Summary technology fields, equal Page-B upper-card heights, complete feature/reference tables, Action-band overflow, and Vietnamese diacritics.
5. Inspect the printed PDF separately: a News card alone in its Evidence column must expand its image to consume the available space between summary and footer, while a four-News grid must use print-specific compact typography and metadata spacing so no citation or publication date crosses the card boundary.
6. Report the clickable absolute HTML path, slide count, source run ID, embedded News image IDs, and fill-in placeholder count. When PPTX is requested, also confirm the converter reports the same placeholder count and leaves every placeholder blank.
