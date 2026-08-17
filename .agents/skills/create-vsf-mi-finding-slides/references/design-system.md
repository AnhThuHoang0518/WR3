# VSF Finding-board design system

Use `../assets/finding-layout-reference.png` as the visual source of truth.

## Brand and canvas

- Heading font: `../assets/fonts/VSFPro.ttf` (family name `VSF Pro`).
- Body font: `../assets/fonts/Lexend-VariableFont_wght.ttf` (family name `Lexend`).
- Logo: `../assets/vsf-logo-transparent.png` (transparent PNG; do not place inside a framed tile).
- Cover background: `../assets/backgrounds1.png`, applied only to slide 1 as a full-bleed image with `object-fit: cover`.
- Format: 16:9, white canvas, thin neutral outer border.
- Main text: `#202124`; secondary text: `#666666`; border: `#DDDCD8`.
- VSF accent: `#E5002B`; deep red: `#8F151A`.
- Signal surface: `#EAF3FF` with `#BED5EF` border and dark blue copy.
- Opportunity surface: `#DDF5EE` with `#91D9C3` border.
- Threat surface: `#FDE8E8` with `#F4B4B4` border.
- Neutral cards: white or `#F8F8F7`, 8px radius, 1px border, no decorative shadows.
- Show the transparent VSF logo directly on the slide background at the upper-right on every slide, including the cover. Do not add a border, white rounded tile, background fill, or shadow. Keep the title-to-logo gap compact and preserve the logo's aspect ratio and clear space.
- In print, preserve the fixed cover composition and its logo position; responsive rules must not introduce a stage panel or run metadata.
- Always use the approved fixed cover composition: thin red top rule and double red left rule, logo at upper-right, and report copy centered vertically in the left field. Use fixed copy `VSF MARKET INTELLIGENCE`, `Market Intelligence Report`, and a two-line unit label with `• Khối Smart City` on line two; show only the computed `Tuần N - Tháng M (dd/mm/yyyy – dd/mm/yyyy)` label as dynamic cover text. Do not show run metadata, report time, stage cards, or a red side panel.
- Keep the supplied background behind all cover elements; do not add a second floating cover artwork layer.

## Typography

- Use bundled `VSF Pro` for titles and labels; use bundled variable `Lexend` for body text. Embed both local TTF assets in standalone HTML and use the same family names in editable PowerPoint output; never load remote fonts.
- Finding title: 29–38 px, bold, compact line height.
- Eyebrow and section labels: 11–13 px, uppercase, spaced, red or gray.
- Body: 12–16 px with at least 1.3 line height. For dense Evidence cards, summary copy may reduce slightly to 11.2–13 px and Signal-connection metadata to 10–11 px; preserve separate grid rows for title, connection, summary, and footer so text never overlaps. Capitalize every displayed bullet item's first letter. Evidence citations may use 9–11 px.
- Preserve Vietnamese diacritics. Do not uppercase long Vietnamese sentences.

## Finding Page A: evidence and O/T

1. Header: eyebrow, exact Signal ID/title, and logo tile.
2. Signal bar: full width, approved Signal statement without shortening.
3. Main body: two columns at roughly 58% / 42%.
   - Left: Evidence label and every News card with complete title, evidence-to-Signal explanation, summary, and compact clickable citation. Place the explanation directly between the title and summary in the normal body color and regular weight; do not display a `Liên hệ SIGNAL-…:` label.
   - Right upper: exactly one dominant related source image in a neutral media frame when an unused related source image is available.
   - Text always appears before imagery. Center a source image in the available space after the summary and before the source/date footer only when that News card is alone in its Evidence column. If two News cards share a column, neither card receives an image.
   - Right lower: every Opportunity and Threat record in stacked green/red cards with ID, type, priority, and complete wording. When this stack leaves a large empty lower area and no unused image remains, reuse one source image from the same Signal beneath the O/T cards.

## Finding Page B: market fit, gap, and action

1. Repeat header title and logo for pair continuity.
2. Main upper area: Product Mapping on the left and Product Gap on the right.
   - Mapping: PM ID/title, O/T lineage, complete market problem, mandatory capabilities if supplied, and complete target customer.
   - Gap: GAP ID, Product Mapping lineage, complete VSF product evidence, capability status, and gap level. Render every missing feature as one row in a two-column table: `TÍNH NĂNG CÒN THIẾU` on the left and one blank `THAM CHIẾU` fill-in cell on the right. Each cell is one semantic, editable text group; never divide one cell into separate line-level text objects.
   - The Mapping and Gap cards must share the exact same top and bottom edges. Stretch the shorter card to the taller card's content height on every desktop and printed Page B.
3. Immediately after the upper cards: full-width Action band with Action ID, response, priority, Product Gap lineage, proposed action, next step, and expected outcome. Do not force the band to the bottom when the upper content is short.

Use empty space deliberately, but never drop content or replace it with ellipses. Fit the approved text using the three fixed Finding pages, balanced internal scrolling only on narrow interactive screens, and print-safe clipping checks.

## Real-world reference placeholder page

Insert one page between Finding Page A and Page B for every Signal. Title it `SIGNAL-ID — GIẢI PHÁP ĐÃ TRIỂN KHAI THỰC TẾ, THAM CHIẾU CHO HÀNH ĐỘNG CỦA VSF`.

- Show three equal reference cards and one full-width `Điểm chung:` band.
- Keep only fixed guidance labels: `Số liệu — quy mô triển khai:` and `Điểm chung:`. Do not show `Liên hệ SIGNAL-ID:` or a `Nguồn:` field on this fill-in template.
- Leave the solution title, combined solution description/Signal relevance, deployment scale, and common point empty. Mark each blank region with a unique `data-ppt-placeholder` name and optional non-visible prompt metadata. Do not use backticks, quotation marks, or other visible sentinel characters around a placeholder.
- Do not populate the slide from News, Signal, Product Mapping, Product Gap, Action, TECH records, the source-deck overlay, external research, or the reference PDF. The recipient fills it manually in the editable PPTX.
- Use subtle dashed borders or blank cells so the editable regions remain visible without showing instructional prompt text.

In the Executive Summary, keep the fixed label `Công nghệ đã kiểm chứng:` under every Action and leave the adjacent annotated placeholder blank.

## Imagery and citations

- Use source images without crowding Evidence text. Put images of stacked News cards in the right-side media gallery; a News card alone in an Evidence column may show only its own image centered after the summary and before the source/date footer. If all related images are already used and O/T leaves a large empty lower area, reuse one same-Signal source image below O/T. Rectangular images use `object-fit: cover`; square or near-square images use `object-fit: contain` on a neutral background.
- Keep News metadata in one compact footer row: a clickable `NEWS-ID · source_name ↗` followed by `Xuất bản: dd/mm/yyyy`. Preserve the citation's computed fullscreen-HTML font size in PowerPoint; do not shrink it only for export.
- Use the Signal connection from the approved Markdown. When a source deck supplies presentation metadata, validate that its visible connection is identical, then use only its visible article title, `Xuất bản: dd/mm/yyyy` date, and exact highlights.
- Do not show raw remote URLs, generic placeholders, or decorative stock photography.

## Interaction and export

- Support Arrow keys, Page Up/Down, Space, Home/End, scroll snap, Previous/Next controls, fullscreen, and progress.
- Hide controls in print.
- Use `@page { size: 13.333in 7.5in; margin: 0; }` and one slide per printed page.
- In print, let an inline image in a singleton Evidence-column News card flex vertically to fill the available space between summary and footer; do not leave a large unused image region.
- In print, compact four-News grids with smaller type, tighter padding, and a fixed two-column metadata row so citations and publication dates remain inside every card.
- Keep the full Product Gap feature/reference table inside its Page B card; compact table typography and spacing before allowing any approved row to be clipped.
- Every inline-image News card must flex its image to consume available space between summary and footer, including all image IDs and both singleton and two-card News grids. Rectangular images use `cover`; square/near-square images use `contain`.
- Stack cards below 900 px while keeping the desktop board unchanged.
- On the Approach slide, reserve at least 170px for the logo in the header and wrap or scale the title within the remaining column so it cannot overlap the logo.
- In the method flow, reserve about 170px for stage labels and use a 13px label size so `OPPORTUNITY / THREAT` never overlaps the explanatory text.
