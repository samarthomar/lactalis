/* Small SVG chart helpers: no libraries, so the demo runs offline. */
const Charts = (() => {
  const NS = "http://www.w3.org/2000/svg";
  const C = { red: "#E31837", deep: "#5F0229", soft: "#F8B4A3", steel: "#4D4D4F", ink: "#29251D", cream: "#F6F2EA",
              cream2: "#E5DFD3", navy: "#0A0838", muted: "#7A746A", line: "#E9E4DA" };

  function el(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs || {}) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function text(parent, x, y, s, attrs) { const t = el("text", Object.assign({ x, y }, attrs || {}), parent); t.textContent = s; return t; }
  function xlabel(f, x, lb) {
    const parts = String(lb).split("\n");
    const t = text(f.svg, x, f.H - 10 - (parts.length - 1) * 13, "", { "text-anchor": "middle" });
    parts.forEach((s, k) => { const sp = el("tspan", { x, dy: k ? 13 : 0 }, t); sp.textContent = s; });
    return t;
  }
  function title(node, s) { el("title", {}, node).textContent = s; }
  const fmt = v => Math.round(v).toLocaleString("en-AU");

  function niceMax(v) {
    if (v <= 0) return 1;
    const p = Math.pow(10, Math.floor(Math.log10(v)));
    const m = v / p;
    for (const k of [1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]) if (m <= k + 1e-9) return k * p;
    return 10 * p;
  }
  function ticks(min, max, n) {
    const raw = (max - min) / n, p = Math.pow(10, Math.floor(Math.log10(raw))), m = raw / p;
    const step = (m <= 1 ? 1 : m <= 2 ? 2 : m <= 2.5 ? 2.5 : m <= 5 ? 5 : 10) * p;
    const out = [];
    for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) out.push(+v.toFixed(6));
    return out;
  }

  function frame(host, o) {
    host.innerHTML = "";
    const W = Math.max(280, host.clientWidth || 600), H = o.height || 260;
    const pad = Object.assign({ l: 52, r: 14, t: 12, b: (o.labels || []).some(l => String(l).includes("\n")) ? 44 : 30 }, o.pad || {});
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, height: H, role: "img" }, host);
    if (o.label) svg.setAttribute("aria-label", o.label);
    const iw = W - pad.l - pad.r, ih = H - pad.t - pad.b;
    let lo = o.yMin != null ? o.yMin : 0, hi = o.yMax;
    if (hi == null) hi = niceMax(o.dataMax * 1.08);
    if (o.dataMin != null && o.dataMin < lo) lo = -niceMax(-o.dataMin * 1.15);
    const y = v => pad.t + ih - (v - lo) / (hi - lo) * ih;
    const g = el("g", { class: "grid" }, svg);
    for (const t of ticks(lo, hi, o.yTicks || 4)) {
      el("line", { x1: pad.l, x2: W - pad.r, y1: y(t), y2: y(t) }, g);
      text(svg, pad.l - 8, y(t) + 4, o.yFmt ? o.yFmt(t) : fmt(t), { "text-anchor": "end" });
    }
    if (o.yLabel) text(svg, 12, pad.t + ih / 2, o.yLabel, { transform: `rotate(-90 12 ${pad.t + ih / 2})`, "text-anchor": "middle" });
    return { svg, W, H, pad, iw, ih, y, lo, hi };
  }

  /* line chart over categorical x (dates) */
  function line(host, o) {
    const n = o.labels.length;
    const all = o.series.flatMap(s => s.values).concat(o.band ? o.band.high : []).filter(v => v != null);
    const f = frame(host, Object.assign({ dataMax: Math.max(...all) }, o));
    const x = i => f.pad.l + (n === 1 ? f.iw / 2 : i / (n - 1) * f.iw);
    const step = n > 1 ? f.iw / (n - 1) : f.iw;
    for (const sh of o.shade || []) {
      const x0 = x(sh.from) - step / 2, x1 = x(sh.to) + step / 2;
      const r = el("rect", { x: Math.max(f.pad.l, x0), y: f.pad.t, width: Math.min(f.W - f.pad.r, x1) - Math.max(f.pad.l, x0), height: f.ih, fill: sh.color, opacity: sh.opacity || 1 }, f.svg);
      if (sh.label) text(f.svg, (Math.max(f.pad.l, x0) + Math.min(f.W - f.pad.r, x1)) / 2, f.pad.t + 12, sh.label, { "text-anchor": "middle", style: `fill:${sh.textColor || C.muted};font-weight:600` });
      if (sh.title) title(r, sh.title);
    }
    if (o.band) {
      const pts = o.band.high.map((v, i) => `${x(i)},${f.y(v)}`).concat(o.band.low.map((v, i) => `${x(i)},${f.y(v)}`).reverse());
      el("polygon", { points: pts.join(" "), fill: o.band.color || C.soft, opacity: o.band.opacity || .35 }, f.svg);
    }
    if (o.highlight != null) el("line", { x1: x(o.highlight), x2: x(o.highlight), y1: f.pad.t, y2: f.pad.t + f.ih, stroke: C.ink, "stroke-width": 1, "stroke-dasharray": "2 3" }, f.svg);
    for (const s of o.series) {
      let d = "";
      s.values.forEach((v, i) => { if (v == null) return; d += (d ? "L" : "M") + x(i) + "," + f.y(v); });
      const p = el("path", { d, fill: "none", stroke: s.color, "stroke-width": s.width || 2, "stroke-linejoin": "round", "stroke-linecap": "round" }, f.svg);
      if (s.dash) p.setAttribute("stroke-dasharray", s.dash);
      if (s.animate) {
        const L = p.getTotalLength ? p.getTotalLength() : 0;
        if (L) { p.style.strokeDasharray = L; p.style.strokeDashoffset = L; p.getBoundingClientRect(); p.style.transition = "stroke-dashoffset 1s ease"; p.style.strokeDashoffset = 0; }
      }
      if (s.dots) s.values.forEach((v, i) => v != null && el("circle", { cx: x(i), cy: f.y(v), r: 3, fill: s.color }, f.svg));
    }
    const every = o.xEvery || Math.ceil(n / Math.max(2, Math.floor(f.iw / 70)));
    o.labels.forEach((lb, i) => { if (i % every === 0 || i === n - 1 && o.xLast) xlabel(f, x(i), lb); });
    if (o.onPick || o.tip) {
      o.labels.forEach((lb, i) => {
        const r = el("rect", { class: "hit", x: x(i) - step / 2, y: f.pad.t, width: step, height: f.ih }, f.svg);
        if (o.tip) title(r, o.tip(i));
        if (o.onPick) r.addEventListener("click", () => o.onPick(i));
      });
    }
    if (o.points) for (const pt of o.points) {
      el("circle", { cx: x(pt.i), cy: f.y(pt.v), r: 5, fill: pt.color || C.red, stroke: "#fff", "stroke-width": 2 }, f.svg);
      if (pt.label) text(f.svg, x(pt.i) + (pt.dx || 0), f.y(pt.v) - 10, pt.label, { "text-anchor": pt.anchor || "middle", style: `fill:${pt.color || C.red};font-weight:700;font-size:12px` });
    }
    return f;
  }

  /* grouped or single bars; colorFn(v, i, seriesIndex) */
  function bars(host, o) {
    const n = o.labels.length, m = o.series.length;
    const vals = o.series.flatMap(s => s.values);
    const f = frame(host, Object.assign({ dataMax: Math.max(...vals, o.ref ? o.ref.value : 0) }, o, { dataMin: Math.min(0, o.dataMin || 0, ...vals) }));
    const slot = f.iw / n, bw = Math.min(o.maxBar || 46, slot * .72 / m);
    const zero = f.y(0);
    if (o.negShade && f.lo < 0) {
      el("rect", { x: f.pad.l, y: zero, width: f.iw, height: f.pad.t + f.ih - zero, fill: C.red, opacity: .07 }, f.svg);
      text(f.svg, f.pad.l + 6, f.pad.t + f.ih - 6, "short of milk", { style: `fill:${C.red};font-weight:600` });
    }
    if (f.lo < 0) el("line", { x1: f.pad.l, x2: f.W - f.pad.r, y1: zero, y2: zero, stroke: C.ink, "stroke-width": 1 }, f.svg);
    o.series.forEach((s, j) => s.values.forEach((v, i) => {
      const cx = f.pad.l + slot * i + slot / 2 - (m * bw) / 2 + j * bw;
      const top = f.y(Math.max(0, v)), h = Math.abs(f.y(v) - zero);
      const r = el("rect", { x: cx + 1, y: top, width: Math.max(1, bw - 2), height: Math.max(.5, h), rx: 2,
        fill: o.colorFn ? o.colorFn(v, i, j) : s.color }, f.svg);
      if (o.tip) title(r, o.tip(i, j));
      if (o.valueLabels) text(f.svg, cx + bw / 2, v >= 0 ? top - 5 : top + h + 13, o.valueLabels(v, i, j), { "text-anchor": "middle", style: `fill:${C.ink};font-weight:600` });
      if (o.onPick) { r.style.cursor = "pointer"; r.addEventListener("click", () => o.onPick(i)); }
    }));
    if (o.ref) {
      el("line", { x1: f.pad.l, x2: f.W - f.pad.r, y1: f.y(o.ref.value), y2: f.y(o.ref.value), stroke: o.ref.color || C.ink, "stroke-width": 1.2, "stroke-dasharray": o.ref.dash || "" }, f.svg);
      if (o.ref.label) text(f.svg, f.W - f.pad.r, f.y(o.ref.value) - 5, o.ref.label, { "text-anchor": "end", style: `fill:${o.ref.color || C.ink};font-weight:600` });
    }
    const every = o.xEvery || 1;
    o.labels.forEach((lb, i) => { if (i % every === 0) xlabel(f, f.pad.l + slot * i + slot / 2, lb); });
    return f;
  }

  /* waterfall: start bar, steps (+/-), total bar, optional reference line */
  function waterfall(host, o) {
    const steps = o.steps;
    let run = 0, maxv = 0, minv = 0;
    const segs = steps.map((s, i) => {
      const from = i === 0 ? 0 : run, to = i === 0 ? s.value : run + s.value;
      run = to; maxv = Math.max(maxv, from, to); minv = Math.min(minv, from, to);
      return { ...s, from, to };
    });
    segs.push({ label: o.totalLabel, from: 0, to: o.total, total: true });
    maxv = Math.max(maxv, o.total, o.ref ? o.ref.value : 0);
    const f = frame(host, Object.assign({ dataMax: maxv, dataMin: minv, pad: { l: 44, r: 12, t: 22, b: 36 } }, o));
    const n = segs.length, slot = f.iw / n, bw = Math.min(70, slot * .62);
    segs.forEach((s, i) => {
      const cx = f.pad.l + slot * i + slot / 2;
      const y0 = f.y(Math.max(s.from, s.to)), h = Math.max(1, Math.abs(f.y(s.from) - f.y(s.to)));
      const col = s.total ? C.red : i === 0 ? C.steel : s.to >= s.from ? C.soft : C.cream2;
      const r = el("rect", { x: cx - bw / 2, y: y0, width: bw, height: h, rx: 3, fill: col }, f.svg);
      r.style.transformOrigin = `${cx}px ${f.y(s.from)}px`;
      r.style.animation = `wf .5s ${i * .15}s ease both`;
      const lbl = s.total || i === 0 ? fmt(s.to) : (s.to >= s.from ? "+" : "−") + fmt(Math.abs(s.to - s.from));
      text(f.svg, cx, y0 - 6, lbl, { "text-anchor": "middle", style: `fill:${C.ink};font-weight:700;font-size:13px` });
      const words = String(s.label).split("\n");
      words.forEach((w, k) => text(f.svg, cx, f.H - 22 + k * 12, w, { "text-anchor": "middle" }));
      if (i < n - 1 && !segs[i + 1].total) el("line", { x1: cx + bw / 2, x2: cx + slot - bw / 2, y1: f.y(s.to), y2: f.y(s.to), stroke: C.muted, "stroke-dasharray": "2 2" }, f.svg);
    });
    if (o.ref) {
      el("line", { x1: f.pad.l, x2: f.W - f.pad.r, y1: f.y(o.ref.value), y2: f.y(o.ref.value), stroke: C.steel, "stroke-width": 1.4, "stroke-dasharray": "5 4" }, f.svg);
      text(f.svg, f.W - f.pad.r, f.y(o.ref.value) - 5, o.ref.label, { "text-anchor": "end", style: `fill:${C.steel};font-weight:600` });
    }
    return f;
  }

  /* horizontal paired bars: rows [{label, a, b}] */
  function hpair(host, o) {
    host.innerHTML = "";
    const W = Math.max(300, host.clientWidth || 500), rowH = o.rowH || 38, padL = o.padL || 210, padR = 56;
    const H = o.rows.length * rowH + 8;
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, height: H }, host);
    const max = o.max || niceMax(Math.max(...o.rows.flatMap(r => [r.a, r.b])));
    const x = v => padL + v / max * (W - padL - padR);
    o.rows.forEach((r, i) => {
      const y0 = 4 + i * rowH;
      text(svg, padL - 10, y0 + rowH / 2 + 2, r.label, { "text-anchor": "end", style: `fill:${C.ink};font-size:12px` });
      const ra = el("rect", { x: padL, y: y0 + 5, height: 11, width: Math.max(1, x(r.a) - padL), rx: 2, fill: o.aColor || C.cream2 }, svg);
      const rb = el("rect", { x: padL, y: y0 + 18, height: 11, width: Math.max(1, x(r.b) - padL), rx: 2, fill: o.bColor || C.red }, svg);
      title(ra, `${o.aName}: ${o.fmt(r.a)}`); title(rb, `${o.bName}: ${o.fmt(r.b)}`);
      text(svg, x(r.a) + 6, y0 + 15, o.fmt(r.a), { style: `fill:${C.muted};font-size:11px` });
      text(svg, x(r.b) + 6, y0 + 28, o.fmt(r.b), { style: `fill:${C.ink};font-size:11px;font-weight:700` });
    });
  }

  const style = document.createElement("style");
  style.textContent = "@keyframes wf{from{transform:scaleY(0)}to{transform:scaleY(1)}}";
  document.head.appendChild(style);
  return { line, bars, waterfall, hpair, C, fmt };
})();
