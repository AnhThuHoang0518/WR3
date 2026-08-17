const NAMED = { transparent: "00000000", black: "000000FF", white: "FFFFFFFF" };

export function parseCssColor(input, fallback = { color: "000000", transparency: 100 }) {
  if (!input) return fallback;
  const value = input.trim().toLowerCase();
  if (value in NAMED) return fromHex8(NAMED[value]);
  if (/^#[0-9a-f]{3,8}$/i.test(value)) {
    let hex = value.slice(1);
    if (hex.length === 3 || hex.length === 4) hex = [...hex].map((c) => c + c).join("");
    if (hex.length === 6) hex += "ff";
    return fromHex8(hex);
  }
  const match = value.match(/^rgba?\(([^)]+)\)$/);
  if (!match) return fallback;
  const parts = match[1].replaceAll(",", " ").replace("/", " ").split(/\s+/).filter(Boolean);
  const channel = (v) => v.endsWith("%") ? Math.round(parseFloat(v) * 2.55) : Math.round(parseFloat(v));
  const alpha = parts[3] == null ? 1 : parts[3].endsWith("%") ? parseFloat(parts[3]) / 100 : parseFloat(parts[3]);
  return {
    color: [channel(parts[0]), channel(parts[1]), channel(parts[2])].map((n) => n.toString(16).padStart(2, "0")).join("").toUpperCase(),
    transparency: Math.round((1 - Math.max(0, Math.min(1, alpha))) * 100),
  };
}

function fromHex8(hex) {
  return {
    color: hex.slice(0, 6).toUpperCase(),
    transparency: Math.round((1 - parseInt(hex.slice(6, 8), 16) / 255) * 100),
  };
}

export function numberPx(value, fallback = 0) {
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export function parseRotation(transform) {
  if (!transform || transform === "none") return { rotation: 0, unsupported: false };
  const matrix = transform.match(/^matrix\(([^)]+)\)$/);
  if (matrix) {
    const [a, b, c, d] = matrix[1].split(",").map(Number);
    return { rotation: Math.atan2(b, a) * 180 / Math.PI, unsupported: Math.abs(a * c + b * d) > 0.001 };
  }
  const matrix3d = transform.match(/^matrix3d\(/);
  return { rotation: 0, unsupported: Boolean(matrix3d) };
}

export function parseShadow(value) {
  if (!value || value === "none" || hasTopLevelComma(value)) return null;
  const colorToken = value.match(/rgba?\([^)]+\)|#[0-9a-f]{3,8}/i)?.[0];
  const numbers = value.match(/-?\d*\.?\d+px/g)?.map(numberPx) ?? [];
  if (numbers.length < 2) return null;
  const [x, y, blur = 0] = numbers;
  const color = parseCssColor(colorToken ?? "rgba(0,0,0,0.25)");
  return {
    type: "outer",
    color: color.color,
    opacity: (100 - color.transparency) / 100,
    blur: Math.max(0, blur * 0.75),
    angle: (Math.atan2(y, x) * 180 / Math.PI + 360) % 360,
    distance: Math.sqrt(x * x + y * y) * 0.75,
  };
}

function hasTopLevelComma(value) {
  let depth = 0;
  for (const character of value) {
    if (character === "(") depth++;
    else if (character === ")") depth--;
    else if (character === "," && depth === 0) return true;
  }
  return false;
}

export function firstFontFamily(value) {
  return (value || "Arial").split(",")[0].trim().replace(/^['"]|['"]$/g, "");
}
