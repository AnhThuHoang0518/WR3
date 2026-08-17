export async function extractDeck(page, selector) {
  return page.evaluate(({ selector }) => {
    const slides = [...document.querySelectorAll(selector)];
    if (!slides.length) throw new Error(`No slides match selector: ${selector}`);

    const px = (value) => Number.parseFloat(value) || 0;
    const colorVisible = (value) => value && value !== "transparent" && !value.endsWith(", 0)") && value !== "rgba(0, 0, 0, 0)";
    const ignored = (el) => el.closest('[data-ppt-ignore="true"], [data-ppt-ignore]:not([data-ppt-ignore="false"])') || ["SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE"].includes(el.tagName);
    const visible = (el, style, rect) => style.display !== "none" && style.visibility !== "hidden" && Number(style.opacity) > 0 && rect.width >= 0 && rect.height >= 0;
    const textRootSelector = 'h1,h2,h3,h4,h5,h6,p,li,td,th,button,a,[data-ppt-text-group]';
    const hasDirectText = (el) => [...el.childNodes].some((child) => child.nodeType === Node.TEXT_NODE && Boolean(child.textContent.trim()));
    const isTextRoot = (el) => {
      if (!(el.innerText || "").trim()) return false;
      if (el.matches(textRootSelector) || el.dataset.pptType === "text") return true;
      if (el.matches("span,strong,b,em,i,small,label") && !el.parentElement?.closest(textRootSelector)) return true;
      return ["DIV", "SECTION"].includes(el.tagName)
        && hasDirectText(el)
        && !el.parentElement?.closest(textRootSelector)
        && !el.querySelector(textRootSelector);
    };
    const hyperlink = (el) => {
      const anchor = el.closest("a[href]");
      if (!anchor) return null;
      try {
        const url = new URL(anchor.getAttribute("href"), document.baseURI);
        if (!["http:", "https:", "mailto:"].includes(url.protocol)) return null;
        return { url: url.href, tooltip: (anchor.getAttribute("title") || url.href).trim().slice(0, 255) };
      } catch {
        return null;
      }
    };
    const renderedTextLines = (el, slideRect, includeDescendants = false) => {
      const lines = [];
      let current = null;
      const beginLine = (rect) => {
        current = { raw: "", left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom };
        lines.push(current);
      };
      const tokens = [];
      const collect = (parent) => {
        for (const child of parent.childNodes) {
          if (child.nodeType === Node.ELEMENT_NODE && child.tagName === "BR") { tokens.push(null); continue; }
          if (child.nodeType === Node.TEXT_NODE) { tokens.push(child); continue; }
          if (includeDescendants && child.nodeType === Node.ELEMENT_NODE) collect(child);
        }
      };
      collect(el);
      for (const child of tokens) {
        if (!child) { current = null; continue; }
        const raw = child.textContent || "";
        for (let index = 0; index < raw.length; index++) {
          const range = document.createRange();
          try { range.setStart(child, index); range.setEnd(child, index + 1); } catch { continue; }
          const rect = range.getBoundingClientRect();
          const character = /\s/.test(raw[index]) ? " " : raw[index];
          if (!rect.height || (!rect.width && character === " ")) continue;
          if (!current || Math.abs(rect.top - current.top) > Math.max(1, rect.height * 0.4)) beginLine(rect);
          current.raw += character;
          current.left = Math.min(current.left, rect.left);
          current.top = Math.min(current.top, rect.top);
          current.right = Math.max(current.right, rect.right);
          current.bottom = Math.max(current.bottom, rect.bottom);
        }
      }
      return lines.map((line) => ({
        text: line.raw.replace(/\s+/g, " ").trim(),
        bbox: { x: line.left - slideRect.left, y: line.top - slideRect.top, width: line.right - line.left, height: line.bottom - line.top },
      })).filter((line) => line.text);
    };
    const complexSvg = (svg) => Boolean(svg.querySelector("path,defs,mask,filter,pattern,image,text,use,foreignObject"));
    const styleObject = (style) => ({
      fontFamily: style.fontFamily, fontSize: style.fontSize, fontWeight: style.fontWeight,
      fontStyle: style.fontStyle, lineHeight: style.lineHeight, letterSpacing: style.letterSpacing,
      color: style.color, backgroundColor: style.backgroundColor, backgroundImage: style.backgroundImage,
      borderTopColor: style.borderTopColor, borderTopWidth: style.borderTopWidth, borderTopStyle: style.borderTopStyle,
      borderRightColor: style.borderRightColor, borderRightWidth: style.borderRightWidth, borderRightStyle: style.borderRightStyle,
      borderBottomColor: style.borderBottomColor, borderBottomWidth: style.borderBottomWidth, borderBottomStyle: style.borderBottomStyle,
      borderLeftColor: style.borderLeftColor, borderLeftWidth: style.borderLeftWidth, borderLeftStyle: style.borderLeftStyle,
      borderRadius: style.borderRadius, textAlign: style.textAlign, verticalAlign: style.verticalAlign,
      opacity: style.opacity, boxShadow: style.boxShadow, transform: style.transform,
      fill: style.fill, fillOpacity: style.fillOpacity, stroke: style.stroke,
      strokeOpacity: style.strokeOpacity, strokeWidth: style.strokeWidth,
      objectFit: style.objectFit, objectPosition: style.objectPosition, overflow: style.overflow,
      filter: style.filter, backdropFilter: style.backdropFilter, clipPath: style.clipPath,
      maskImage: style.maskImage, mixBlendMode: style.mixBlendMode,
    });
    const classify = (el, style, rect) => {
      const forced = el.dataset.pptType;
      if (forced) return forced;
      const tag = el.tagName.toLowerCase();
      if (tag === "img") return "image";
      if (tag === "hr" || tag === "line") return "line";
      if (tag === "circle" || tag === "ellipse") return "ellipse";
      if (tag === "rect") return px(el.getAttribute("rx")) > 0 || px(el.getAttribute("ry")) > 0 ? "roundRect" : "rect";
      if (tag === "polygon") return "rect";
      if (tag === "svg" && complexSvg(el)) return "svg";
      const hasBox = colorVisible(style.backgroundColor) || px(style.borderTopWidth) > 0 || px(style.borderRightWidth) > 0 || px(style.borderBottomWidth) > 0 || px(style.borderLeftWidth) > 0;
      if (!hasBox) return "container";
      const radius = px(style.borderRadius);
      if (radius >= Math.min(rect.width, rect.height) * 0.45 && Math.abs(rect.width - rect.height) < 3) return "ellipse";
      return radius / Math.max(1, Math.min(rect.width, rect.height)) >= 0.15 ? "roundRect" : "rect";
    };
    const pseudoItem = (el, pseudo, slideRect, domIndex) => {
      const style = getComputedStyle(el, pseudo);
      const content = style.content;
      if (!content || content === "none" || content === "normal" || style.display === "none") return null;
      const parent = el.getBoundingClientRect();
      const width = px(style.width), height = px(style.height);
      if (!width && !height) return null;
      return {
        id: `${el.dataset.pptExportId}-${pseudo.slice(2)}`, tag: pseudo, classes: [], group: el.dataset.pptGroup || null,
        domIndex: domIndex - (pseudo === "::before" ? 0.1 : -0.1), zIndex: Number.parseInt(style.zIndex, 10) || 0,
        kind: px(style.borderRadius) >= Math.min(width, height) * 0.45 ? "ellipse" : "rect", text: "",
        bbox: { x: parent.left - slideRect.left + px(style.left), y: parent.top - slideRect.top + px(style.top), width, height },
        style: styleObject(style), pseudo: true,
      };
    };

    return slides.map((slide, slideIndex) => {
      const slideRect = slide.getBoundingClientRect();
      const slideStyle = getComputedStyle(slide);
      const elements = [];
      let domIndex = 0;
      for (const el of [slide, ...slide.querySelectorAll("*")]) {
        if (el === slide || ignored(el)) continue;
        if (el.parentElement?.closest("h1,h2,h3,h4,h5,h6")) continue;
        if (el.parentElement?.closest("p")?.querySelector("strong.mi-exec-emphasis")) continue;
        const svg = el.closest("svg");
        if (svg && svg !== el && complexSvg(svg)) continue;
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        if (!visible(el, style, rect)) continue;
        const id = `ppt-${slideIndex + 1}-${++domIndex}`;
        el.dataset.pptExportId = id;
        const textLines = isTextRoot(el) ? renderedTextLines(el, slideRect, true) : [];
        const text = textLines.map((line) => line.text).join("\n");
        const hasNestedText = [...el.children].some((child) => Boolean((child.textContent || "").trim()));
        const kind = classify(el, style, rect);
        const unsupported = [];
        if (style.backgroundImage !== "none") unsupported.push("background-image/gradient");
        if (style.filter !== "none") unsupported.push("filter");
        if (style.backdropFilter && style.backdropFilter !== "none") unsupported.push("backdrop-filter");
        if (style.clipPath !== "none") unsupported.push("clip-path");
        if (style.maskImage && style.maskImage !== "none") unsupported.push("mask");
        if (style.mixBlendMode !== "normal") unsupported.push("mix-blend-mode");
        if (style.transform.startsWith("matrix3d")) unsupported.push("3d-transform");
        const areaRatio = (rect.width * rect.height) / Math.max(1, slideRect.width * slideRect.height);
        const nestedText = (el.innerText || "").trim();
        const rasterEligible = unsupported.length > 0 && !nestedText && areaRatio <= 0.15 && !el.hasAttribute("data-ppt-no-raster");
        const item = {
          id, tag: el.tagName.toLowerCase(), classes: [...el.classList], group: el.dataset.pptGroup || null,
          domIndex, zIndex: Number.parseInt(style.zIndex, 10) || 0, kind, text, textLines,
          placeholder: el.dataset.pptPlaceholder || null,
          placeholderPrompt: el.dataset.pptPlaceholderPrompt || el.getAttribute("aria-label") || null,
          fontScale: Number.parseFloat(el.dataset.pptFontScale) || 1,
          hasNestedText,
          bbox: { x: rect.left - slideRect.left, y: rect.top - slideRect.top, width: rect.width, height: rect.height },
          style: styleObject(style), unsupported, rasterEligible,
          hyperlink: hyperlink(el),
          textOverflow: el.clientHeight > 0 && (el.scrollHeight > el.clientHeight + Math.max(2, px(style.fontSize) * 0.2) || el.scrollWidth > el.clientWidth + Math.max(2, px(style.fontSize) * 0.2)),
          fontAvailable: text ? document.fonts.check(`${style.fontSize} ${style.fontFamily}`) : true,
          src: el.tagName === "IMG" ? el.currentSrc || el.src : null,
          naturalWidth: el.tagName === "IMG" ? el.naturalWidth : null,
          naturalHeight: el.tagName === "IMG" ? el.naturalHeight : null,
          svg: kind === "svg" ? el.outerHTML : null,
        };
        if (kind !== "container" || text || rasterEligible || item.placeholder) elements.push(item);
        for (const pseudo of ["::before", "::after"]) {
          const synthetic = pseudoItem(el, pseudo, slideRect, domIndex);
          if (synthetic) elements.push(synthetic);
        }
      }
      return {
        index: slideIndex + 1,
        selector,
        bbox: { width: slideRect.width, height: slideRect.height },
        backgroundColor: slideStyle.backgroundColor,
        elements,
      };
    });
  }, { selector });
}
