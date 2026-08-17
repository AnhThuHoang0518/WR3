# Conversion support matrix

## Native editable

| HTML/CSS | PowerPoint output | Notes |
|---|---|---|
| Direct text in headings, paragraphs, labels, badges | Text box | Keeps explicit/rendered line breaks, font, size, weight, style, alignment, color, opacity, and letter spacing approximation. |
| Empty element with `data-ppt-placeholder` | Named blank text box | Keeps exact rendered bounds, remains empty and editable, and appears as `Placeholder: <stable-name>` in the Selection Pane. Optional prompt is metadata only. |
| Solid background, border, radius | Rectangle or rounded rectangle | Radius is approximated to PowerPoint's available rounded rectangle. |
| Circular element | Ellipse | Selected from geometry/radius or `data-ppt-type`. |
| `hr`, CSS divider, SVG line | Line | Border dash patterns are approximated. |
| Simple SVG `rect`, `circle`, `ellipse`, `line`, `polygon` | Native shape | Geometry comes from rendered SVG child bounds. |
| Normal image | Image | `contain` uses intrinsic dimensions; raster `cover` maps to PowerPoint crop. SVG-in-`img` cover uses a rendered element PNG because PptxGenJS does not reliably preserve that intrinsic ratio. |

## Fidelity-preserving non-editable elements

| Feature | Fallback |
|---|---|
| Complex SVG with paths, defs, masks, or filters | SVG image retained as SVG, not PNG. |
| Small decorative element using gradients, filters, masks, clip paths, or blend modes | Element PNG only when it has no text, is under 15% of slide area, and lacks `data-ppt-no-raster`. |

## Approximated and reported

- CSS `box-shadow` maps to the closest outer PowerPoint shadow.
- Non-uniform border radii map to a standard rounded rectangle.
- `object-position` other than center is reported; `cover` remains center-cropped.
- CSS rotation is mapped; scale is already reflected in the rendered bounding box. Skew and 3D transforms are reported.
- Complex font fallback chains are reduced to the first declared family that Chromium reports as available.
- Pseudo-elements use their final computed size and offsets because browsers do not expose `getBoundingClientRect()` directly for pseudo-elements.

## Unsupported without element fallback

- Editable CSS gradients, filters, backdrop filters, masks, blend modes, and complex clip paths.
- Per-side borders with different styles/colors in one native shape.
- Perfect browser-to-PowerPoint text metrics, variable-font axes, OpenType feature settings, and arbitrary writing modes.
- Editable complex SVG paths, charts rendered to canvas, video, WebGL, iframes, animations, transitions, and interactive states.
- Exact CSS perspective or 3D transforms.

The report must list every unsupported or approximated feature. A visual diff is evidence of similarity, not proof of semantic editability.

Blank fill-in placeholders are editable text boxes rather than theme-layout placeholders. Do not claim that they inherit a PowerPoint master layout, and do not convert them to visible instructional text.
