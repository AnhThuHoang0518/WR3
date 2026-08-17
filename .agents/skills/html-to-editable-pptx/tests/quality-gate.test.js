import test from "node:test";
import assert from "node:assert/strict";
import { determineQualityGate, parseArgs } from "../src/cli.js";

const passing = {
  warnings: [],
  pageErrors: [],
  preview: { status: "COMPLETE", layoutInspection: { status: "PASS" } },
  visualValidation: { status: "PASS" },
  placeholderValidation: { status: "PASS" },
};

test("quality gate passes a fully validated deck", () => {
  assert.equal(determineQualityGate(passing).status, "PASS");
});

test("quality gate accepts pixel review when PowerPoint layout inspection passes", () => {
  const result = determineQualityGate({ ...passing, visualValidation: { status: "REVIEW" } });
  assert.equal(result.status, "PASS");
  assert.deepEqual(result.reasons, []);
});

test("quality gate rejects overlapping or overflowing PowerPoint text", () => {
  const result = determineQualityGate({ ...passing, preview: { status: "COMPLETE", layoutInspection: { status: "FAIL" } } });
  assert.equal(result.status, "FAIL");
  assert.deepEqual(result.reasons, ["PPT_LAYOUT_FAIL"]);
});

test("quality gate rejects missing placeholders", () => {
  const result = determineQualityGate({ ...passing, placeholderValidation: { status: "FAIL" } });
  assert.equal(result.status, "FAIL");
  assert.deepEqual(result.reasons, ["PLACEHOLDER_FAIL"]);
});

test("strict mode also rejects warnings", () => {
  const result = determineQualityGate({ ...passing, strict: true, warnings: [{ code: "TEXT_OVERFLOW" }] });
  assert.equal(result.status, "FAIL");
  assert.deepEqual(result.reasons, ["WARNINGS:1"]);
});

test("CLI defaults to screen media", () => {
  assert.equal(parseArgs(["deck.html"]).media, "screen");
});

test("CLI accepts explicit print media", () => {
  assert.equal(parseArgs(["deck.html", "--media", "print"]).media, "print");
});

test("CLI rejects unsupported media", () => {
  assert.throws(() => parseArgs(["deck.html", "--media", "speech"]), /Use screen or print/);
});
