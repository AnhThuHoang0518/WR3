import test from "node:test";
import assert from "node:assert/strict";
import { containBox, imageSizing, isOutside, pxToInches, pxToPoints, WIDE } from "../src/geometry.js";

test("maps 1920x1080 geometry consistently to wide PowerPoint", () => {
  const box = pxToInches({ x: 192, y: 108, width: 960, height: 540 }, { width: 1920, height: 1080 });
  assert.equal(box.x, WIDE.width * 0.1);
  assert.equal(box.y, 0.75);
  assert.equal(box.w, WIDE.width * 0.5);
  assert.equal(box.h, 3.75);
});

test("maps CSS font pixels through the same slide scale", () => {
  assert.ok(Math.abs(pxToPoints(40, 1920) - 20) < 0.0001);
  assert.ok(Math.abs(pxToPoints(40, 1280) - 30) < 0.0001);
});

test("fits a contained image by intrinsic aspect ratio", () => {
  assert.deepEqual(containBox({ x: 1, y: 1, w: 4, h: 4 }, 600, 300), { x: 1, y: 2, w: 4, h: 2 });
});

test("detects objects outside slide", () => {
  const slide = { width: 1920, height: 1080 };
  assert.equal(isOutside({ x: 0, y: 0, width: 100, height: 100 }, slide), false);
  assert.equal(isOutside({ x: -1, y: 0, width: 100, height: 100 }, slide), true);
  assert.equal(isOutside({ x: 1900, y: 0, width: 30, height: 100 }, slide), true);
});

test("maps image contain and cover without stretching", () => {
  const box = { x: 1, y: 1, w: 4, h: 2 };
  assert.deepEqual(imageSizing("contain", box), { type: "contain", w: 4, h: 2 });
  assert.deepEqual(imageSizing("cover", box), { type: "cover", w: 4, h: 2 });
  assert.equal(imageSizing("fill", box), null);
});
