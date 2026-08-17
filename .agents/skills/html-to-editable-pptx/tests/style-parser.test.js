import test from "node:test";
import assert from "node:assert/strict";
import { firstFontFamily, parseCssColor, parseRotation, parseShadow } from "../src/style-parser.js";

test("parses CSS colors and opacity", () => {
  assert.deepEqual(parseCssColor("#123456"), { color: "123456", transparency: 0 });
  assert.deepEqual(parseCssColor("rgba(255, 0, 128, 0.25)"), { color: "FF0080", transparency: 75 });
  assert.equal(parseCssColor("transparent").transparency, 100);
});

test("maps computed transform matrix rotation", () => {
  const value = parseRotation("matrix(0, 1, -1, 0, 0, 0)");
  assert.ok(Math.abs(value.rotation - 90) < 0.001);
  assert.equal(value.unsupported, false);
  assert.equal(parseRotation("matrix3d(1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1)").unsupported, true);
});

test("extracts declared font and simple shadow", () => {
  assert.equal(firstFontFamily("'Aptos Display', Arial, sans-serif"), "Aptos Display");
  const shadow = parseShadow("rgba(0, 0, 0, 0.25) 4px 6px 12px");
  assert.equal(shadow.type, "outer");
  assert.ok(shadow.distance > 0);
});
