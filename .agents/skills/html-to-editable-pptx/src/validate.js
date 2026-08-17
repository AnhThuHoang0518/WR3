import fs from "node:fs/promises";
import path from "node:path";
import JSZip from "jszip";
import pixelmatch from "pixelmatch";
import { PNG } from "pngjs";
import { isOutside } from "./geometry.js";
import { parseRotation } from "./style-parser.js";

export function inspectDeck(deck) {
  const warnings = [];
  for (const slide of deck.slides) {
    const placeholderNames = new Set();
    for (const item of slide.elements) {
      const at = { slide: slide.index, id: item.id, tag: item.tag };
      if (item.placeholder) {
        if (placeholderNames.has(item.placeholder)) warnings.push({ code: "DUPLICATE_PLACEHOLDER_NAME", name: item.placeholder, ...at });
        placeholderNames.add(item.placeholder);
        if (item.bbox.width <= 0 || item.bbox.height <= 0) warnings.push({ code: "EMPTY_PLACEHOLDER_BOUNDS", name: item.placeholder, ...at });
      }
      if (item.text && item.textOverflow) warnings.push({ code: "TEXT_OVERFLOW", ...at });
      if (item.text && item.fontAvailable === false) warnings.push({ code: "FONT_UNAVAILABLE", font: item.style.fontFamily, ...at });
      if (isOutside(item.bbox, slide.bbox)) warnings.push({ code: "OFF_SLIDE", bbox: item.bbox, ...at });
      if (item.unsupported?.length) warnings.push({ code: item.kind === "raster" ? "ELEMENT_RASTER_FALLBACK" : "UNSUPPORTED_CSS", features: item.unsupported, ...at });
      if (item.rasterError) warnings.push({ code: "ELEMENT_RASTER_FAILED", error: item.rasterError, ...at });
      const transform = parseRotation(item.style.transform);
      if (transform.unsupported) warnings.push({ code: "UNSUPPORTED_TRANSFORM", transform: item.style.transform, ...at });
      if (item.kind === "image" && item.style.objectPosition && item.style.objectPosition !== "50% 50%" && item.style.objectPosition !== "center center") {
        warnings.push({ code: "OBJECT_POSITION_APPROXIMATED", value: item.style.objectPosition, ...at });
      }
      if (item.kind === "image" && (!item.naturalWidth || !item.naturalHeight)) warnings.push({ code: "IMAGE_FAILED_TO_LOAD", src: item.src, ...at });
      if (item.imageFallback) warnings.push({ code: "IMAGE_ELEMENT_RASTER_FALLBACK", reason: item.imageFallback, ...at });
      if (item.imageFallbackError) warnings.push({ code: "IMAGE_ELEMENT_RASTER_FAILED", error: item.imageFallbackError, ...at });
      if (item.kind === "svg") warnings.push({ code: "COMPLEX_SVG_FALLBACK", ...at });
    }
  }
  return warnings;
}

export async function inspectPptxPlaceholders(pptxPath, deck) {
  const expected = deck.slides.flatMap((slide) => slide.elements
    .filter((item) => item.placeholder)
    .map((item) => `${slide.index}:${item.placeholder}`));
  if (!expected.length) return { status: "NOT_APPLICABLE", expected: 0, found: 0, missing: [], unexpected: [] };

  const zip = await JSZip.loadAsync(await fs.readFile(pptxPath));
  const found = [];
  for (const slide of deck.slides) {
    const file = zip.file(`ppt/slides/slide${slide.index}.xml`);
    if (!file) continue;
    const xml = await file.async("string");
    for (const match of xml.matchAll(/name="Placeholder: ([^"]+)"/g)) found.push(`${slide.index}:${match[1]}`);
  }
  const expectedSet = new Set(expected);
  const foundSet = new Set(found);
  const missing = expected.filter((name) => !foundSet.has(name));
  const unexpected = found.filter((name) => !expectedSet.has(name));
  const status = !missing.length && !unexpected.length && expected.length === found.length ? "PASS" : "FAIL";
  return { status, expected: expected.length, found: found.length, missing, unexpected };
}

export async function comparePreviews(htmlDir, pptDir, diffDir, slideCount) {
  await fs.mkdir(diffDir, { recursive: true });
  const slides = [];
  for (let index = 1; index <= slideCount; index++) {
    const file = `slide-${String(index).padStart(3, "0")}.png`;
    try {
      const html = PNG.sync.read(await fs.readFile(path.join(htmlDir, file)));
      const ppt = PNG.sync.read(await fs.readFile(path.join(pptDir, file)));
      if (html.width !== ppt.width || html.height !== ppt.height) {
        slides.push({ index, status: "DIMENSION_MISMATCH", html: [html.width, html.height], ppt: [ppt.width, ppt.height] });
        continue;
      }
      const diff = new PNG({ width: html.width, height: html.height });
      const pixels = pixelmatch(html.data, ppt.data, diff.data, html.width, html.height, { threshold: 0.12, includeAA: false });
      const ratio = pixels / (html.width * html.height);
      await fs.writeFile(path.join(diffDir, file), PNG.sync.write(diff));
      slides.push({ index, status: ratio > 0.25 ? "MAJOR_MISMATCH" : ratio > 0.12 ? "REVIEW" : "PASS", mismatchedPixels: pixels, ratio });
    } catch (error) {
      slides.push({ index, status: "MISSING_PREVIEW", reason: error.message });
    }
  }
  const status = slides.every((slide) => slide.status === "PASS") ? "PASS"
    : slides.some((slide) => ["MAJOR_MISMATCH", "DIMENSION_MISMATCH", "MISSING_PREVIEW"].includes(slide.status)) ? "FAIL" : "REVIEW";
  return { status, slides };
}
