import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import PptxGenJS from "pptxgenjs";
import { containBox, pxToInches, pxToPoints, WIDE, imageSizing } from "./geometry.js";
import { firstFontFamily, numberPx, parseCssColor, parseRotation, parseShadow } from "./style-parser.js";

export async function buildPptx(deck, outputPath, options = {}) {
  const pptx = new PptxGenJS();
  pptx.layout = "LAYOUT_WIDE";
  pptx.author = options.author || "HTML to Editable PowerPoint skill";
  pptx.subject = "Editable conversion from approved HTML";
  pptx.title = path.basename(outputPath);
  pptx.company = options.company || "";
  pptx.lang = options.lang || "vi-VN";
  pptx.theme = {
    headFontFace: "Arial",
    bodyFontFace: "Arial",
    lang: options.lang || "vi-VN",
  };

  const stats = { text: 0, placeholders: 0, shapes: 0, images: 0, svg: 0, rasters: 0, imageRasterFallbacks: 0, hyperlinks: 0, skipped: 0, fontEmbedding: "delegated_to_windows_wrapper", fontFamilies: [] };
  const fontFamilies = new Set();
  for (const sourceSlide of deck.slides) {
    const slide = pptx.addSlide();
    const background = parseCssColor(sourceSlide.backgroundColor, { color: "FFFFFF", transparency: 0 });
    slide.background = { color: background.color, transparency: background.transparency };
    const source = sourceSlide.bbox;
    const elements = [...sourceSlide.elements].sort((a, b) => (a.zIndex - b.zIndex) || (a.domIndex - b.domIndex));
    for (const item of elements) {
      const box = pxToInches(item.bbox, source, WIDE);
      if (box.w <= 0.001 && box.h <= 0.001) { stats.skipped++; continue; }
      if (item.kind === "raster" && item.rasterPath) {
        slide.addImage({ path: item.rasterPath, ...box, ...hyperlinkOptions(item) });
        stats.rasters++;
        if (item.hyperlink) stats.hyperlinks++;
        continue;
      }
      if (item.kind === "image" && item.src) {
        if (item.renderedImagePath) {
          slide.addImage({ path: item.renderedImagePath, ...box, ...hyperlinkOptions(item) });
          stats.images++;
          stats.imageRasterFallbacks++;
          if (item.hyperlink) stats.hyperlinks++;
          continue;
        }
        const sourceImage = toPptImage(item.src);
        if (item.style.objectFit === "contain" && item.naturalWidth && item.naturalHeight) {
          slide.addImage({ ...sourceImage, ...containBox(box, item.naturalWidth, item.naturalHeight), ...hyperlinkOptions(item) });
          stats.images++;
          if (item.hyperlink) stats.hyperlinks++;
          continue;
        }
        const sizing = imageSizing(item.style.objectFit, box);
        slide.addImage(sizing
          ? { ...sourceImage, x: box.x, y: box.y, sizing, ...hyperlinkOptions(item) }
          : { ...sourceImage, ...box, ...hyperlinkOptions(item) });
        stats.images++;
        if (item.hyperlink) stats.hyperlinks++;
        continue;
      }
      if (item.kind === "svg" && item.svg) {
        const border = strongestBorder(item.style);
        const fill = parseCssColor(item.style.backgroundColor);
        if (border.width > 0 || fill.transparency < 100) {
          addShape(pptx, slide, { ...item, kind: "rect" }, box, source);
          stats.shapes++;
        }
        slide.addImage({ data: `image/svg+xml;base64,${Buffer.from(item.svg).toString("base64")}`, ...box, ...hyperlinkOptions(item) });
        stats.svg++;
        if (item.hyperlink) stats.hyperlinks++;
        continue;
      }
      if (["rect", "roundRect", "ellipse", "line"].includes(item.kind)) {
        addShape(pptx, slide, item, box, source);
        stats.shapes++;
      }
      if (item.text) {
        addText(slide, item, box, source);
        stats.text++;
        if (item.hyperlink) stats.hyperlinks++;
        fontFamilies.add(powerpointFontFamily(item.style.fontFamily));
      } else if (item.placeholder) {
        addPlaceholderText(slide, item, box, source);
        fontFamilies.add(powerpointFontFamily(item.style.fontFamily));
        stats.placeholders++;
      }
    }
  }
  stats.fontFamilies = [...fontFamilies].filter(Boolean).sort();
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  await pptx.writeFile({ fileName: outputPath });
  return stats;
}

function addShape(pptx, slide, item, box, source) {
  const shapeType = item.kind === "roundRect" ? pptx.ShapeType.roundRect
    : item.kind === "ellipse" ? pptx.ShapeType.ellipse
      : item.kind === "line" ? pptx.ShapeType.line : pptx.ShapeType.rect;
  const isSvgPrimitive = ["rect", "circle", "ellipse", "line", "polygon"].includes(item.tag);
  const fill = parseCssColor(isSvgPrimitive ? item.style.fill : item.style.backgroundColor);
  const border = isSvgPrimitive ? {
    width: numberPx(item.style.strokeWidth, 0),
    color: parseCssColor(item.style.stroke),
    style: "solid",
  } : strongestBorder(item.style);
  const rotation = parseRotation(item.style.transform).rotation;
  const options = {
    ...box,
    fill: { color: fill.color, transparency: fill.transparency },
    line: {
      color: border.color.color,
      transparency: border.width > 0 ? border.color.transparency : 100,
      width: Math.max(0.1, pxToPoints(border.width, source.width)),
      dash: border.style === "dashed" ? "dash" : border.style === "dotted" ? "dash" : "solid",
    },
    rotate: rotation,
    ...hyperlinkOptions(item),
  };
  const shadow = parseShadow(item.style.boxShadow);
  if (shadow) options.shadow = shadow;
  slide.addShape(shapeType, options);
}

function addText(slide, item, box, source) {
  const color = parseCssColor(item.style.color, { color: "000000", transparency: 0 });
  const fontSize = pxToPoints(numberPx(item.style.fontSize, 16), source.width) * (item.fontScale || 1);
  const lineHeightPx = numberPx(item.style.lineHeight, 0);
  const lineSpacing = lineHeightPx > 0 ? pxToPoints(lineHeightPx, source.width) : undefined;
  const fontWeight = Number.parseInt(item.style.fontWeight, 10);
  const options = {
    ...box,
    margin: 0,
    fontFace: powerpointFontFamily(item.style.fontFamily),
    fontSize,
    bold: item.style.fontWeight === "bold" || (Number.isFinite(fontWeight) && fontWeight >= 600),
    italic: item.style.fontStyle === "italic" || item.style.fontStyle === "oblique",
    color: color.color,
    transparency: color.transparency,
    align: ["left", "center", "right", "justify"].includes(item.style.textAlign) ? item.style.textAlign : "left",
    valign: item.style.verticalAlign === "middle" ? "mid" : item.style.verticalAlign === "bottom" ? "bottom" : "top",
    breakLine: false,
    charSpacing: pxToPoints(numberPx(item.style.letterSpacing, 0), source.width),
    paraSpaceAfterPt: 0,
    isTextBox: true,
    ...hyperlinkOptions(item),
  };
  const keepSingleLine = Array.isArray(item.textLines)
    && item.textLines.length === 1
    && !["p", "div", "li", "td", "th"].includes(String(item.tag).toLowerCase());
  if (keepSingleLine) {
    options.wrap = false;
  }
  if (lineSpacing && Number.isFinite(lineSpacing)) options.lineSpacing = lineSpacing;
  slide.addText(item.text, options);
}

function addPlaceholderText(slide, item, box, source) {
  const color = parseCssColor(item.style.color, { color: "666666", transparency: 0 });
  const fontSize = pxToPoints(numberPx(item.style.fontSize, 14), source.width);
  const fontWeight = Number.parseInt(item.style.fontWeight, 10);
  slide.addText(" ", {
    ...box,
    margin: 0,
    fontFace: powerpointFontFamily(item.style.fontFamily),
    fontSize,
    bold: item.style.fontWeight === "bold" || (Number.isFinite(fontWeight) && fontWeight >= 600),
    italic: item.style.fontStyle === "italic" || item.style.fontStyle === "oblique",
    color: color.color,
    transparency: color.transparency,
    align: ["left", "center", "right", "justify"].includes(item.style.textAlign) ? item.style.textAlign : "left",
    valign: item.style.verticalAlign === "middle" ? "mid" : item.style.verticalAlign === "bottom" ? "bottom" : "top",
    isTextBox: true,
    objectName: `Placeholder: ${item.placeholder}`,
    altText: item.placeholderPrompt || `Fill-in placeholder ${item.placeholder}`,
  });
}

function powerpointFontFamily(value) {
  return firstFontFamily(value);
}

function hyperlinkOptions(item) {
  return item.hyperlink?.url ? { hyperlink: item.hyperlink } : {};
}

function strongestBorder(style) {
  const sides = ["Top", "Right", "Bottom", "Left"].map((side) => ({
    width: numberPx(style[`border${side}Width`], 0),
    color: parseCssColor(style[`border${side}Color`]),
    style: style[`border${side}Style`],
  }));
  return sides.sort((a, b) => b.width - a.width)[0];
}

function toPptImage(src) {
  if (src.startsWith("data:")) {
    if (/;base64,/i.test(src)) return { data: src.slice(5) };
    const comma = src.indexOf(",");
    const mime = src.slice(5, comma).split(";")[0] || "application/octet-stream";
    const decoded = decodeURIComponent(src.slice(comma + 1));
    return { data: `${mime};base64,${Buffer.from(decoded, "utf8").toString("base64")}` };
  }
  if (src.startsWith("file:")) return { path: fileURLToPath(src) };
  return { path: src };
}
