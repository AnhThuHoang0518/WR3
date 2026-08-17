# HTML to Editable PowerPoint

This skill converts finished HTML slides into editable `.pptx` files. Chromium supplies final geometry; PptxGenJS serializes native text, named blank fill-in text boxes, shapes, images, and supported SVG content. The converter does not redesign the source HTML and never uses a full-slide screenshot as the PowerPoint slide.

```powershell
npm install
powershell -File .\scripts\html2ppt.ps1 C:\path\deck.html --output C:\path\deck.pptx --debug
```

Use `--slide-selector ".mi-slide"` for custom markup and `--viewport 1920x1080` to override the fixed render size. The output validation directory contains HTML previews, PowerPoint previews, DOM geometry, conversion diagnostics, and visual diffs.

Mark a blank fill-in region with `data-ppt-placeholder="stable-name"`; keep the element empty and give it non-zero rendered dimensions. The converter preserves it as a named blank text box instead of omitting it.
