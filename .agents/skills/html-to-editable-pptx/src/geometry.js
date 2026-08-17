export const WIDE = Object.freeze({ width: 13.333333, height: 7.5 });

export function pxToInches(bbox, source, target = WIDE) {
  const sx = target.width / source.width;
  const sy = target.height / source.height;
  return {
    x: bbox.x * sx,
    y: bbox.y * sy,
    w: bbox.width * sx,
    h: bbox.height * sy,
  };
}

export function pxToPoints(value, sourceWidth, targetWidth = WIDE.width) {
  return value * targetWidth / sourceWidth * 72;
}

export function clampBox(box, slide = WIDE) {
  const x = Math.max(0, box.x);
  const y = Math.max(0, box.y);
  return {
    x,
    y,
    w: Math.max(0.001, Math.min(box.w - (x - box.x), slide.width - x)),
    h: Math.max(0.001, Math.min(box.h - (y - box.y), slide.height - y)),
  };
}

export function isOutside(bbox, source) {
  return bbox.x < 0 || bbox.y < 0 || bbox.x + bbox.width > source.width || bbox.y + bbox.height > source.height;
}

export function imageSizing(objectFit, box) {
  const type = objectFit === "contain" ? "contain" : objectFit === "cover" ? "cover" : null;
  return type ? { type, w: box.w, h: box.h } : null;
}

export function containBox(box, naturalWidth, naturalHeight) {
  if (!(naturalWidth > 0) || !(naturalHeight > 0)) return box;
  const scale = Math.min(box.w / naturalWidth, box.h / naturalHeight);
  const w = naturalWidth * scale;
  const h = naturalHeight * scale;
  return { x: box.x + (box.w - w) / 2, y: box.y + (box.h - h) / 2, w, h };
}
