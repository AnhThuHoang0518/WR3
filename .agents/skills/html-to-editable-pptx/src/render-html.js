import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { chromium } from "playwright-core";
import { extractDeck } from "./extract-dom.js";

const WINDOWS_BROWSERS = [
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
];

export async function findBrowser(explicit) {
  if (explicit) { await fs.access(explicit); return explicit; }
  for (const candidate of WINDOWS_BROWSERS) {
    try { await fs.access(candidate); return candidate; } catch {}
  }
  try { return chromium.executablePath(); } catch {}
  throw new Error("No Chromium, Chrome, or Microsoft Edge executable found. Pass --browser <path>.");
}

export async function renderHtml(input, options) {
  const browserPath = await findBrowser(options.browser);
  const browser = await chromium.launch({ headless: true, executablePath: browserPath });
  const context = await browser.newContext({ viewport: options.viewport, deviceScaleFactor: 1 });
  const page = await context.newPage();
  const media = options.media || "screen";
  await page.emulateMedia({ media });
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("console", (message) => { if (message.type() === "error") pageErrors.push(message.text()); });
  try {
    const url = /^https?:\/\//i.test(input) ? input : pathToFileURL(path.resolve(input)).href;
    await page.goto(url, { waitUntil: "networkidle" });
    await page.addStyleTag({ content: "*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}" });
    await page.evaluate(async () => {
      await document.fonts.ready;
      const images = [...document.images];
      await Promise.all(images.map((image) => image.complete ? Promise.resolve() : new Promise((resolve) => {
        image.addEventListener("load", resolve, { once: true });
        image.addEventListener("error", resolve, { once: true });
      })));
      await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    });
    const selector = options.slideSelector || await detectSlideSelector(page);
    const slides = await extractDeck(page, selector);
    await fs.mkdir(options.htmlRenderDir, { recursive: true });
    await fs.mkdir(options.elementRasterDir, { recursive: true });
    await fs.mkdir(options.imageRenderDir, { recursive: true });
    for (const slide of slides) {
      const locator = page.locator(selector).nth(slide.index - 1);
      await locator.screenshot({ path: path.join(options.htmlRenderDir, `slide-${String(slide.index).padStart(3, "0")}.png`) });
      for (const item of slide.elements.filter((entry) => entry.rasterEligible)) {
        try {
          const rasterPath = path.join(options.elementRasterDir, `${item.id}.png`);
          await page.locator(`[data-ppt-export-id="${item.id}"]`).screenshot({ path: rasterPath, omitBackground: true });
          item.rasterPath = rasterPath;
          item.kind = "raster";
        } catch (error) {
          item.rasterError = error.message;
        }
      }
      for (const item of slide.elements.filter((entry) => entry.kind === "image" && entry.style.objectFit === "cover" && /^data:image\/svg\+xml/i.test(entry.src || ""))) {
        try {
          const imagePath = path.join(options.imageRenderDir, `${item.id}.png`);
          await page.locator(`[data-ppt-export-id="${item.id}"]`).screenshot({ path: imagePath, omitBackground: true });
          item.renderedImagePath = imagePath;
          item.imageFallback = "SVG_IMG_COVER_RENDERED_PNG";
        } catch (error) {
          item.imageFallbackError = error.message;
        }
      }
    }
    return { slides, selector, browserPath, pageErrors, media };
  } finally {
    await browser.close();
  }
}

async function detectSlideSelector(page) {
  for (const selector of ["[data-ppt-slide]", "section.slide", ".slide"]) {
    if (await page.locator(selector).count()) return selector;
  }
  throw new Error("Cannot detect slides. Add data-ppt-slide/class=slide or pass --slide-selector.");
}
