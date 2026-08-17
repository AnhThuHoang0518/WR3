import fs from "node:fs/promises";
import path from "node:path";
import { renderHtml } from "./render-html.js";
import { buildPptx } from "./ppt-builder.js";
import { renderPptPreview } from "./render-ppt.js";
import { comparePreviews, inspectDeck, inspectPptxPlaceholders } from "./validate.js";

export async function main(argv = process.argv.slice(2)) {
  const args = parseArgs(argv);
  if (args.help || !args.input) { printHelp(); return args.help ? 0 : 1; }
  const input = /^https?:\/\//i.test(args.input) ? args.input : path.resolve(args.input);
  if (!/^https?:\/\//i.test(input)) await fs.access(input);
  const output = path.resolve(args.output || defaultOutput(input));
  const artifactRoot = path.resolve(args.artifacts || `${output}.validation`);
  const dirs = {
    htmlRenderDir: path.join(artifactRoot, "html-render"),
    pptRenderDir: path.join(artifactRoot, "ppt-render"),
    elementRasterDir: path.join(artifactRoot, "element-raster"),
    imageRenderDir: path.join(artifactRoot, "image-render"),
    diffDir: path.join(artifactRoot, "visual-diff"),
  };
  await fs.mkdir(artifactRoot, { recursive: true });
  const candidateOutput = path.join(artifactRoot, "candidate.pptx");
  const startedAt = new Date().toISOString();
  const rendered = await renderHtml(input, { ...args, ...dirs });
  await fs.writeFile(path.join(artifactRoot, "dom-snapshot.json"), JSON.stringify(rendered.slides, null, 2));
  const warnings = inspectDeck(rendered);
  const nativeObjects = await buildPptx(rendered, candidateOutput, args);
  const placeholderValidation = await inspectPptxPlaceholders(candidateOutput, rendered);
  if (placeholderValidation.status === "FAIL") warnings.push({ code: "PLACEHOLDER_VALIDATION_FAILED", ...placeholderValidation });
  const previewViewport = rendered.slides[0]
    ? { width: rendered.slides[0].bbox.width, height: rendered.slides[0].bbox.height }
    : args.viewport;
  const preview = await renderPptPreview(candidateOutput, dirs.pptRenderDir, previewViewport);
  const visualValidation = preview.status === "COMPLETE"
    ? await comparePreviews(dirs.htmlRenderDir, dirs.pptRenderDir, dirs.diffDir, rendered.slides.length)
    : { status: "BLOCKED", reason: preview.reason };
  const qualityGate = determineQualityGate({ warnings, pageErrors: rendered.pageErrors, preview, visualValidation, placeholderValidation, strict: args.strict });
  if (qualityGate.status === "PASS") {
    await fs.mkdir(path.dirname(output), { recursive: true });
    await fs.copyFile(candidateOutput, output);
  }
  const report = {
    schemaVersion: 1,
    input,
    requestedOutput: output,
    output: qualityGate.status === "PASS" ? output : null,
    candidateOutput,
    startedAt,
    completedAt: new Date().toISOString(),
    viewport: args.viewport,
    renderedViewport: previewViewport,
    media: rendered.media,
    slideSelector: rendered.selector,
    slideCount: rendered.slides.length,
    browser: rendered.browserPath,
    nativeObjects,
    placeholderValidation,
    warnings,
    pageErrors: rendered.pageErrors,
    preview,
    visualValidation,
    qualityGate,
    editable: { text: true, fillInPlaceholders: placeholderValidation.status !== "FAIL", basicShapes: true, images: true, complexSvg: false, elementRasterFallback: false },
  };
  await fs.writeFile(path.join(artifactRoot, "conversion-report.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ requestedOutput: output, deliveryOutput: report.output, candidateOutput, artifactRoot, slides: rendered.slides.length, nativeObjects, placeholderValidation: placeholderValidation.status, warnings: warnings.length, visualValidation: visualValidation.status, qualityGate: qualityGate.status }, null, 2));
  return qualityGate.status === "PASS" ? 0 : 2;
}

export function determineQualityGate({ warnings = [], pageErrors = [], preview, visualValidation, placeholderValidation, strict = false }) {
  const reasons = [];
  if (pageErrors?.length) reasons.push(`PAGE_ERRORS:${pageErrors.length}`);
  if (preview?.status !== "COMPLETE") reasons.push(`PPT_PREVIEW_${preview?.status || "MISSING"}`);
  if (!preview?.layoutInspection || preview.layoutInspection.status !== "PASS") reasons.push(`PPT_LAYOUT_${preview?.layoutInspection?.status || "MISSING"}`);
  if (!visualValidation || !["PASS", "REVIEW"].includes(visualValidation.status)) reasons.push(`VISUAL_${visualValidation?.status || "MISSING"}`);
  if (placeholderValidation?.status === "FAIL") reasons.push("PLACEHOLDER_FAIL");
  if (strict && warnings.length) reasons.push(`WARNINGS:${warnings.length}`);
  return {
    status: reasons.length ? "FAIL" : "PASS",
    reasons,
    deliveryPolicy: "Only qualityGate=PASS may be copied to the requested output path or handed off as a deliverable.",
  };
}

export function parseArgs(argv) {
  const options = { viewport: { width: 1920, height: 1080 }, media: "screen", debug: false, strict: false };
  const positional = [];
  for (let index = 0; index < argv.length; index++) {
    const value = argv[index];
    if (!value.startsWith("--")) { positional.push(value); continue; }
    if (value === "--debug") options.debug = true;
    else if (value === "--strict") options.strict = true;
    else if (value === "--help") options.help = true;
    else {
      const next = argv[++index];
      if (!next) throw new Error(`Missing value for ${value}`);
      if (value === "--output") options.output = next;
      else if (value === "--artifacts") options.artifacts = next;
      else if (value === "--slide-selector") options.slideSelector = next;
      else if (value === "--browser") options.browser = next;
      else if (value === "--viewport") options.viewport = parseViewport(next);
      else if (value === "--media") options.media = parseMedia(next);
      else throw new Error(`Unknown option: ${value}`);
    }
  }
  options.input = positional[0];
  if (positional.length > 1) throw new Error(`Unexpected argument: ${positional[1]}`);
  return options;
}

function parseMedia(value) {
  const media = value.toLowerCase();
  if (!['screen', 'print'].includes(media)) throw new Error(`Invalid media '${value}'. Use screen or print.`);
  return media;
}

function parseViewport(value) {
  const match = value.match(/^(\d+)x(\d+)$/i);
  if (!match) throw new Error(`Invalid viewport '${value}'. Use WIDTHxHEIGHT.`);
  const width = Number(match[1]), height = Number(match[2]);
  if (width < 320 || height < 180) throw new Error("Viewport is too small.");
  return { width, height };
}

function defaultOutput(input) {
  if (/^https?:\/\//i.test(input)) return path.resolve("deck.pptx");
  const parsed = path.parse(input);
  return path.join(parsed.dir, `${parsed.name}.pptx`);
}

function printHelp() {
  console.log(`html2ppt <input.html> [options]\n\nOptions:\n  --output <file>          Requested deliverable path; populated only after quality PASS\n  --slide-selector <css>  Slide selector\n  --viewport <WxH>        CSS-pixel viewport (default 1920x1080)\n  --media <screen|print>  CSS media type (default screen)\n  --browser <path>        Chromium/Chrome/Edge executable\n  --artifacts <dir>       Validation artifact directory\n  --debug                 Retain detailed artifacts\n  --strict                Also fail on warnings\n  --help                  Show this help\n\nThe visual gate always requires PASS. REVIEW, FAIL, or BLOCKED stays as candidate.pptx inside the validation directory and must not be delivered.`);
}
