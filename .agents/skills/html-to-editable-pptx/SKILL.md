---
name: html-to-editable-pptx
description: Convert a visually approved HTML/CSS slide deck into a high-fidelity editable PowerPoint (.pptx), including named blank fill-in placeholders and clickable links, with automatic Windows font registration/embedding and a hard visual quality gate. Use when the user has finished HTML slides and asks to export, convert, or recreate them in editable PowerPoint without redesigning, reflowing, rewriting, auto-filling placeholders, or rasterizing the whole slide.
---

# HTML to Editable PowerPoint

Treat the rendered HTML as the single source of truth. Do not redesign, rebalance, reflow, rewrite, or infer a replacement layout. Let Chromium resolve Grid, Flexbox, CSS variables, media queries, and calculated values; use the resulting DOM geometry directly.

## Required workflow

1. Inspect the input HTML and identify the slide selector. Prefer `[data-ppt-slide]`, then `.slide`; otherwise pass `--slide-selector` explicitly.
2. Verify local fonts and linked assets are accessible. Do not silently substitute a font or missing image. On Windows, always use the wrapper: it extracts local/embedded TTF or OTF fonts, registers them for the conversion session, and asks PowerPoint to embed them in a passing deck.
3. Install dependencies once in this skill directory with `npm install` when `node_modules` is absent.
4. Run the converter. On this WR3 Windows host, prefer the wrapper because it can use the Node runtime bundled with VS Code:

   ```powershell
   powershell -File .\scripts\html2ppt.ps1 input.html --output output\deck.pptx --debug
   ```

   On a standard Node.js 20+ host, `node ./bin/html2ppt.js ...` or the installed `html2ppt` binary is equivalent.

5. Inspect `conversion-report.json`, including `qualityGate`, `placeholderValidation`, `fontAutomation`, `preview.layoutInspection`, HTML/PPT previews, and visual diffs. Treat `MAJOR_MISMATCH`, `FAIL`, `BLOCKED`, PowerPoint text overflow/overlap, missing/renamed placeholders, missing PPT rendering, or failed font embedding as a failed conversion.
6. Only hand off the path in `conversion-report.json.output` when `qualityGate.status = "PASS"`. On failure, the converter keeps `candidate.pptx` inside the validation directory for diagnosis and does not promote it to the requested deliverable path.
7. Open the passing PPTX and spot-check editability, clickable links, text wrapping, image crop, stacking, and any reported fallback.
8. Iterate only on conversion rules or explicit HTML annotations. Never "fix" fidelity by changing the approved layout unless the user requests an HTML change.

## Inputs and options

- Required: one local HTML file or URL.
- `--output <file>`: requested PPTX deliverable path; populated only after the hard quality gate passes.
- `--slide-selector <css>`: selector for one HTML element per slide.
- `--viewport <width>x<height>`: Chromium viewport in CSS pixels; default `1920x1080`. Match the approved browser state, including browser zoom/display scaling. For a 1920×1080 display at 125% scaling, the effective fullscreen CSS viewport is typically near `1536x864`.
- `--media <screen|print>`: CSS media type used before navigation and DOM measurement; default `screen`. Use `print` only when the approved reference is the HTML print layout.
- `--browser <path>`: Chromium/Chrome/Edge executable; otherwise auto-detect.
- `--debug`: retain DOM snapshot, element rasters, previews, and diffs.
- `--strict`: additionally fail on warnings. Visual `PASS`, successful placeholder validation, and complete PPT rendering are mandatory even without this flag.

## HTML authoring contract

Annotations are optional, but honor them when present:

- `data-ppt-slide`: mark a slide.
- `data-ppt-ignore="true"`: omit a web-only control or helper.
- `data-ppt-type="text|rect|roundRect|ellipse|line|image|svg"`: override mapping.
- `data-ppt-font-scale="<number>"`: apply a deliberate, explicitly authored font-size scale to one exported text group when the approved HTML uses an exceptionally tight label. Never add this annotation automatically to links or metadata.
- `data-ppt-group`: preserve a logical group name in diagnostics.
- `data-ppt-no-raster`: prohibit element-level raster fallback.
- `data-ppt-placeholder="<stable-name>"`: preserve an empty HTML region as a named, blank, editable PowerPoint text box. Keep the element visually empty; never inject prompt or source content.
- `data-ppt-placeholder-prompt="<description>"`: add an accessibility/diagnostic description without displaying it on the slide.

Give every placeholder a unique stable name within its slide and a non-zero rendered width and height. A placeholder is a fill-in text box for the recipient, not permission to infer or copy content into it.

Do not require every element to be annotated. Ignore hidden elements, scripts, styles, navigation controls, and accessibility-only helpers.

## Conversion rules

- Measure every exported object with `getBoundingClientRect()` relative to its rendered slide.
- Read final values with `getComputedStyle()`; do not parse Grid/Flex to calculate coordinates.
- Use one px-to-inch transformation per slide.
- Map each semantic text cluster to one editable text box. A heading, paragraph, list item, button, link, table cell, or explicit `data-ppt-text-group` is one cluster; retain its line breaks inside that one box. Do not split a cluster into per-line or inline-fragment text boxes. Carry Chromium's measured line height into the PowerPoint box as exact point spacing so the group stays within its measured bounds.
- Export every `data-ppt-placeholder` element even when it has no text, and create a blank editable text box at its exact rendered bounds. Preserve its stable name in the PowerPoint Selection Pane and its optional prompt as metadata. Do not display default instructions, quote marks, backticks, or other visible sentinel characters around a placeholder; do not populate it from neighboring content.
- Treat every `td` or `th` as one semantic group. In a `TÍNH NĂNG CÒN THIẾU` / `THAM CHIẾU` table, export one editable text box for the missing-feature cell and one for its matching reference cell; retain an empty reference as its named blank placeholder.
- Preserve supported `http:`, `https:`, and `mailto:` anchors as clickable PowerPoint hyperlinks on the corresponding editable object, using the anchor's computed HTML font size unless the approved HTML itself explicitly supplies `data-ppt-font-scale`.
- Map panels, cards, badges, circles, rules, and supported SVG primitives to editable native shapes.
- Add images as image objects and use PowerPoint `contain`/`cover` sizing without stretching.
- Keep complex SVG as SVG images. Rasterize only small, decorative unsupported elements; never rasterize the whole slide or a text-bearing container.
- Preserve DOM/z-index stacking order. Add an element's background shape before its text.
- Report unsupported CSS, font fallback, text overflow, failed assets, off-slide objects, SVG fallback, and validation gaps.

## Validation gates

The conversion is complete only when:

- a `.pptx` exists and can be opened;
- slide count matches;
- primary text and shapes remain editable;
- images are not stretched;
- all fallbacks are recorded;
- every annotated placeholder exists as a blank editable text box, and placeholder count and names match the HTML;
- links required by the HTML remain clickable in PowerPoint;
- custom TTF/OTF fonts used by the HTML are available while PowerPoint renders and are embedded in the final PPTX when the Windows wrapper reports them;
- HTML slides and PPT slides were rendered at the same target size;
- no slide has `MAJOR_MISMATCH`, and PowerPoint's rendered-text inspection reports no overflow or substantially overlapping editable text boxes. A pixel-only `REVIEW` may pass because font antialiasing and image resampling differ between Chromium and PowerPoint;
- `qualityGate.status` is `PASS` and `conversion-report.json.output` is non-null.

If PowerPoint or LibreOffice is unavailable, keep the deck as a validation candidate with `visualValidation.status = "BLOCKED"`; do not present it as the final deliverable.

## Fidelity priority

Prioritize, in order: geometry, text editability, typography, fill/border/color, image crop, layer order, effects, decorative details. Never sacrifice whole-slide editability for a minor CSS effect.

## Supporting resources

- Read [references/support-matrix.md](references/support-matrix.md) when a deck uses SVG, gradients, filters, masks, unusual typography, transforms, or image positioning.
- Run [scripts/render-ppt.ps1](scripts/render-ppt.ps1) only through the CLI unless diagnosing PowerPoint preview export.
- Use files in `examples/` for regression checks; expected behavior is listed in [examples/expected.json](examples/expected.json). Run `examples/09-placeholders.html` whenever placeholder behavior changes.

## Non-goals

Do not create slide design, improve hierarchy, rewrite content, change spacing, split or merge slides, or reproduce the deck as full-slide screenshots.
