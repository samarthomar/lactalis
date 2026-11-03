/* Demand Supply Control Tower: demo app. Data comes from window.DEMO (built by scripts/build_demo.py). */
(() => {
  const { model: M, lib: L, extra: X } = window.DEMO;
  const C = Charts.C;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const fmt = n => Math.round(n).toLocaleString("en-AU");
  const pct = (x, d = 0) => (x * 100).toFixed(d) + "%";
  const WD = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"], MO = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const D = iso => new Date(iso + "T00:00:00");
  const dname = iso => { const d = D(iso); return `${WD[d.getDay()]} ${d.getDate()} ${MO[d.getMonth()]}`; };
  const dshort = iso => { const d = D(iso); return `${WD[d.getDay()]} ${d.getDate()}`; };
  const d2 = iso => { const d = D(iso); return `${WD[d.getDay()]}\n${d.getDate()}`; };
  const dmon = iso => { const d = D(iso); return `${d.getDate()} ${MO[d.getMonth()]}`; };
  const PROD = Object.fromEntries(M.products.map(p => [p.sku, p]));
  const CUST = Object.fromEntries(M.customers.map(c => [c.customer_id, c]));
  const SC = X.scenario;
  const ALERT = Object.fromEntries(L.alerts.map(a => [a.id, a]));
  const QA = Object.fromEntries(L.qa.map(q => [q.id, q]));
  const DATES = [...new Set(M.forecast.map(r => r.date))].sort();
  const WX = Object.fromEntries(X.weather.map(w => [w.date, w]));
  const WI = L.whatif_lookup;
  const DKEY = Object.keys(WI.hero).find(k => Math.abs(+k - SC.depth) < 1e-9);
  const T0 = Math.round(WX[SC.start].max_temp_c);
  const STATS = L.matching.stats;
  const QUEUE = X.review;
  const NEW_SHOWN = STATS.new - QUEUE.filter(q => q.kind === "rule").length;

  /* ------------------------------------------------------------------ state */
  const initial = () => ({
    scene: 1, clock: 7 * 60 + 30, audit: L.audit_seed.map(a => ({ ...a })), newAudit: 0,
    match: "idle", steward: {},
    sku: SC.sku, cust: SC.customer, day: SC.start,
    bt: "hero", sig: { weather: true, holidays: true, promotions: true },
    wiTemp: T0, wiDepth: DKEY,
    planView: "before",
    morning: "idle", sel: null, decisions: {}, options: {}, rejecting: null, sapSeq: 41,
    chat: [],
    lbSel: "C1", lbState: {}, lbReview: {},
  });
  let S = initial();

  const clockStr = () => `${String(Math.floor(S.clock / 60)).padStart(2, "0")}:${String(S.clock % 60).padStart(2, "0")}`;
  function tick(min = 2) { S.clock += min; $("#clock").textContent = `Mon 12 Oct 2026 · ${clockStr()}`; }
  function audit(who, what) {
    S.audit.push({ time: clockStr(), who, what, fresh: true });
    S.newAudit++;
    renderAudit();
  }
  function toast(msg) {
    const t = $("#toast"); t.textContent = msg; t.classList.add("show");
    clearTimeout(toast.t); toast.t = setTimeout(() => t.classList.remove("show"), 2600);
  }

  /* ------------------------------------------------------------------ scenes */
  const SCENES = [
    { n: 1, name: "Data View", render: scene1, chips: ["Q12", "Q11", "Q13"] },
    { n: 2, name: "Demand Forecast", render: scene2, chips: ["Q1", "Q2", "Q3", "Q6", "Q4"] },
    { n: 3, name: "Plant & Milk Check", render: scene3, chips: ["Q8", "Q9", "Q19"] },
    { n: 4, name: "Agent View", render: scene4, chips: ["Q16", "Q1", "Q7"] },
    { n: 5, name: "Business Value", render: scene5, chips: ["Q10", "Q5", "Q18", "Q17"] },
    { n: 6, name: "Label Agent", render: scene6, chips: ["Q21", "Q22", "Q17"] },
  ];
  function nav() {
    $("#scenes").innerHTML = SCENES.map(s => `<button data-go="${s.n}" class="${s.n === S.scene ? "on" : ""}"><span class="n">${s.n}</span>${esc(s.name)}</button>`).join("");
  }
  function go(n) { S.scene = Math.max(1, Math.min(SCENES.length, n)); render(); window.scrollTo({ top: 0 }); }
  function render() {
    nav();
    const main = $("#main");
    main.innerHTML = "";
    SCENES[S.scene - 1].render(main);
    chips();
  }
  const head = (kicker, title, lede, right = "") =>
    `<div class="scene-head"><div><div class="kicker">${kicker}</div><h1>${title}</h1><div class="lede">${lede}</div></div>${right}</div>`;

  /* ================================================================== scene 1: records */
  function resolved() {
    if (S.match !== "done") return 0;
    return STATS.auto_matched + NEW_SHOWN + Object.keys(S.steward).length;
  }
  function scene1(main) {
    const total = STATS.fonterra_records, res = resolved();
    const sampleRow = r => `<tr><td class="mono">${esc(r.id)}</td><td>${esc(r.name)}</td><td class="num">${esc(r.postcode)}</td><td>${esc(r.channel)}</td><td><span class="mono">${esc(r.product_code)}</span><div class="small muted">${esc(r.product_name)}</div></td></tr>`;
    main.innerHTML = head("Data foundation", "Data View",
      `Since 1 April 2026 Lactalis also runs the former Fonterra consumer business. Its customers sit in a separate list, with different codes and spellings. Before a forecast can be trusted, the records have to agree.`) + `
    <div class="grid g-main">
      <div class="card" data-show="matching">
        <div class="row between"><div><h3>Two customer lists</h3><div class="sub">${fmt(STATS.lactalis_records)} Lactalis records · ${fmt(total)} former Fonterra records · sample shown</div></div>
          <button class="btn primary" id="runMatch" ${S.match !== "idle" ? "disabled" : ""}>${S.match === "done" ? "Matched" : S.match === "running" ? "Matching…" : "Match records with AI"}</button></div>
        <div class="progress mt8"><i id="matchBar" style="width:${S.match === "done" ? 100 : 0}%"></i></div>
        <div class="src stack mt12">
          <div><div class="tag navy">Lactalis</div><table class="t mt8"><tr><th>Code</th><th>Name</th><th>Postcode</th><th>Channel</th><th>Main product</th></tr>${X.samples_lactalis.slice(0, 7).map(sampleRow).join("")}</table></div>
          <div class="mid muted" style="font-size:22px">⇅</div>
          <div><div class="tag red">Former Fonterra</div><table class="t mt8"><tr><th>Code</th><th>Name</th><th>Postcode</th><th>Channel</th><th>Main product</th></tr>${X.samples_fonterra.slice(0, 7).map(sampleRow).join("")}</table></div>
        </div>
        <div class="note mt8">Same customers, written differently: capitals, "PTY LTD", "ESPRESSO BAR", "CAFÉ", a postcode one digit out. Lactalis sells them milk; the former Fonterra side sells them cheese and butter.</div>
      </div>
      <div class="card">
        <h3>Record quality</h3><div class="sub">Former Fonterra customers linked to a Lactalis record or confirmed as new</div>
        <div class="gauge"><div class="big num" id="qScore">${pct(res / total, 1)}</div><div class="muted small">${fmt(res)} of ${fmt(total)} records</div></div>
        <div class="meter mt8"><i style="width:${res / total * 100}%"></i></div>
        <div class="note mt8">Pilot target: at least 95% of records matched within scope.</div>
        <div id="matchSummary" class="mt16"></div>
      </div>
    </div>
    <div id="matchResults"></div>
    <div class="grid g3 mt16">
      <div class="card" data-show="legacy"><h3>Orders still under old Fonterra codes</h3><div class="sub">${esc(CUST["RET-B"].name)} and ${esc(CUST.IND.name)}, share of cases</div><div class="chart" id="cLegacy"></div><div class="note">* Oct = 1 to ${+M.meta.today.slice(8) - 1} Oct so far</div></div>
      <div class="card"><h3>Duplicate orders</h3><div class="sub">Same order keyed in under the old and new code</div>
        <div class="kpi"><div class="value num">${X.duplicates.orders} <small>orders</small></div><div class="delta muted">${fmt(X.duplicates.cases)} cases sent and returned. Linked records let the order agent hold a repeat before it ships.</div></div></div>
      <div class="card" data-show="prices"><h3>Price list conflicts</h3><div class="sub">${esc(CUST["RET-B"].name)}: old Fonterra price vs Lactalis list</div>
        <table class="t">${X.price_conflicts.slice().sort((a, b) => Math.abs(b.diff) - Math.abs(a.diff)).slice(0, 4).map(p => `<tr><td>${esc(p.name)}</td><td class="num">$${p.legacy.toFixed(2)}</td><td class="num">$${p.lactalis.toFixed(2)}</td><td class="num ${Math.abs(p.diff) > .03 ? "red strong" : ""}">${p.diff > 0 ? "+" : ""}${(p.diff * 100).toFixed(1)}%</td></tr>`).join("")}</table>
        <div class="note mt8">${X.price_conflicts.length} conflicts flagged for the commercial team. Agents never change prices.</div></div>
    </div>`;
    Charts.bars($("#cLegacy"), {
      labels: X.legacy_monthly.map((m, i) => MO[+m.month.slice(5) - 1] + (i === X.legacy_monthly.length - 1 ? "*" : "")), series: [{ values: X.legacy_monthly.map(m => m.share * 100), color: C.red }],
      height: 170, yFmt: v => v + "%", valueLabels: v => v.toFixed(0) + "%", colorFn: (v, i) => i === X.legacy_monthly.length - 1 ? C.red : C.soft, maxBar: 30,
    });
    $("#runMatch").onclick = runMatch;
    if (S.match === "done") matchResults();
  }
  let EPOCH = 0;
  const later = (fn, ms) => { const ep = EPOCH; setTimeout(() => { if (ep === EPOCH) fn(); }, ms); };
  function runMatch() {
    S.match = "running"; render();
    requestAnimationFrame(() => { const b = $("#matchBar"); if (b) b.style.width = "100%"; });
    later(() => {
      S.match = "done"; tick(1);
      audit("Data agent", `Matched ${STATS.fonterra_records} former Fonterra customer records: ${STATS.auto_matched} automatic, ${QUEUE.length} to a steward, ${NEW_SHOWN} new customers`);
      render();
    }, 1500);
  }
  function matchResults() {
    $("#matchSummary").innerHTML = `
      <table class="t"><tr><td>Matched automatically</td><td class="num strong">${STATS.auto_matched}</td></tr>
      <tr><td>Sent to a data steward</td><td class="num strong">${QUEUE.length}</td></tr>
      <tr><td>New customers (no match)</td><td class="num strong">${NEW_SHOWN}</td></tr></table>
      <div class="note mt8">Checked against the answer key: ${STATS.auto_correct} of ${STATS.auto_matched} automatic matches are right.</div>`;
    const ex = L.matching.auto_examples.slice(0, 5);
    const box = $("#matchResults");
    box.innerHTML = `<div class="grid g2 mt16">
      <div class="card"><h3>Matched automatically</h3><div class="sub">The hardest automatic matches, with the reasons</div>
        <table class="t"><tr><th>Former Fonterra</th><th>Lactalis</th><th>Score</th><th>Why</th></tr>
        ${ex.map(r => `<tr><td>${esc(r.fonterra_name)}</td><td>${esc(r.lactalis_name)}</td><td class="num">${Math.round(r.score * 100)}%</td><td class="small muted">${esc(r.why)}</td></tr>`).join("")}</table>
        <div class="note mt8">Method: name similarity after removing "PTY LTD", "CO", "BAR" and accents (65%), postcode (25%), channel (10%). Above 90%: automatic. 75 to 90%: a person checks.</div></div>
      <div class="card" data-show="steward"><h3>Data steward review</h3><div class="sub">The agent asks a person when it is not sure</div>
        ${QUEUE.map((q, i) => queueItem(q, i)).join("")}</div></div>`;
    $$("[data-steward]", box).forEach(b => b.onclick = () => steward(+b.dataset.i, b.dataset.steward));
  }
  function queueItem(q, i) {
    const f = q.fonterra, l = q.lactalis, d = S.steward[i];
    const mark = (a, b) => a === b ? esc(a) : `<span class="diff">${esc(a)}</span>`;
    const yes = q.kind === "rule" ? "Link as buying group" : "Same customer", no = q.kind === "rule" ? "Keep separate" : "Different customer";
    return `<div class="queue-item ${d ? "done" : ""}">
      <div class="row between"><span class="tag ${q.kind === "rule" ? "navy" : "red"}">${q.kind === "rule" ? "Rule: always ask" : `Score ${Math.round(q.score * 100)}%`}</span><span class="tiny muted">${esc(q.why)}</span></div>
      <div class="pair mt8"><div><div class="h">Former Fonterra · ${esc(f.id)}</div><div class="strong">${esc(f.name)}</div><div>${mark(f.postcode, l.postcode)} · ${mark(f.channel, l.channel)}</div></div>
        <div><div class="h">Lactalis · ${esc(l.id)}</div><div class="strong">${esc(l.name)}</div><div>${esc(l.postcode)} · ${esc(l.channel)}</div></div></div>
      ${d ? `<div class="mt8 small"><span class="status approved">${d === "same" ? yes : no}</span> · answer key: ${esc(q.truth)} ${(d === "same") === q.truth.startsWith("same") ? "✓" : "✗"}</div>`
          : `<div class="row mt8"><button class="btn small dark" data-steward="same" data-i="${i}">${yes}</button><button class="btn small" data-steward="diff" data-i="${i}">${no}</button></div>`}
    </div>`;
  }
  function steward(i, choice) {
    S.steward[i] = choice; tick(1);
    const q = QUEUE[i];
    audit("Data steward", choice === "same" ? `Linked ${q.fonterra.id} to ${q.lactalis.id} (${q.kind === "rule" ? "buying group" : "same customer"})` : `Kept ${q.fonterra.id} separate from ${q.lactalis.id}`);
    render();
    if (Object.keys(S.steward).length === QUEUE.length) toast(`Record quality now ${pct(resolved() / STATS.fonterra_records, 1)}`);
  }

  /* ================================================================== scene 2: forecast */
  function rowsFor(sku, cust) {
    const rs = M.forecast.filter(r => r.sku === sku && (cust === "ALL" || r.customer === cust));
    if (cust !== "ALL") return DATES.map(d => rs.find(r => r.date === d));
    return DATES.map(d => {
      const g = rs.filter(r => r.date === d);
      const sum = k => g.reduce((a, r) => a + r[k], 0);
      return { date: d, sku, customer: "ALL", forecast: sum("forecast"), low: null, high: null, today_method: sum("today_method"),
        normal_level: sum("normal_level"), drivers_cases: ["Holidays", "Promotion", "Weather"].reduce((o, k) => (o[k] = g.reduce((a, r) => a + r.drivers_cases[k], 0), o), {}),
        max_temp_c: g[0].max_temp_c, normal_temp_c: g[0].normal_temp_c, promo_depth: Math.max(...g.map(r => r.promo_depth)), sibling_promo_depth: Math.max(...g.map(r => r.sibling_promo_depth)) };
    });
  }
  function driverWords(r) {
    const out = [], dc = r.drivers_cases, p = PROD[SC.sku].name;
    const sign = v => (v >= 0 ? "+" : "−") + fmt(Math.abs(v));
    out.push([`Normal ${WD[D(r.date).getDay()] === "Sat" || WD[D(r.date).getDay()] === "Sun" ? "weekend day" : "day"} for this product and customer`, fmt(r.normal_level)]);
    if (Math.abs(dc.Holidays) >= 1) out.push([dc.Holidays > 0 ? "School or public holiday lifts demand" : "School or public holiday lowers demand", sign(dc.Holidays)]);
    if (Math.abs(dc.Promotion) >= 1) {
      let w;
      if (r.promo_depth > 0) w = `${Math.round(r.promo_depth * 100)}% off promotion`;
      else if (r.sibling_promo_depth > 0 && dc.Promotion < 0) w = `Shoppers switch to the promoted ${p}`;
      else if (dc.Promotion > 0) w = "Retailer stocks up the day before the promotion";
      else w = "Dip after a promotion";
      out.push([w, sign(dc.Promotion)]);
    }
    if (Math.abs(dc.Weather) >= 1) out.push([`${Math.round(r.max_temp_c)}°C forecast (normal for October ${Math.round(r.normal_temp_c)}°C)`, sign(dc.Weather)]);
    const resid = r.forecast - r.normal_level - dc.Holidays - dc.Promotion - dc.Weather;
    if (Math.abs(resid) >= 1) out.push(["Rounding and other effects", sign(resid)]);
    return out;
  }
  function scene2(main) {
    const rows = rowsFor(S.sku, S.cust);
    const di = Math.max(0, DATES.indexOf(S.day)), r = rows[di];
    const custName = S.cust === "ALL" ? "all retailers" : CUST[S.cust].name;
    const mon = M.forecast.find(x => x.sku === SC.sku && x.customer === SC.customer && x.date === DATES[0]);
    main.innerHTML = head("Live model output", "Demand Forecast",
      `Forecast across different products and retailers for the next 14 days. The model uses internal factors (past orders, promotions) and external factors (weather, school and public holidays) that influence the forecast values.`) + `
    <div class="filters"><label>Product<select id="selSku" aria-label="Product">${M.products.map(p => `<option value="${p.sku}" ${p.sku === S.sku ? "selected" : ""}>${esc(p.name)}</option>`).join("")}</select></label>
       <label>Retailer<select id="selCust" aria-label="Retailer">${M.customers.map(c => `<option value="${c.customer_id}" ${c.customer_id === S.cust ? "selected" : ""}>${esc(c.name)}</option>`).join("")}<option value="ALL" ${S.cust === "ALL" ? "selected" : ""}>All retailers</option></select></label></div>
    <div class="grid g-main">
      <div class="card" data-show="forecast">
        <div class="row between"><div><h3>Next 14 days: ${esc(PROD[S.sku].name)}, ${esc(custName)}</h3><div class="sub">Cases per day. Click a day to see why.</div></div>
          ${S.sku === SC.sku && S.cust === SC.customer ? `<span class="tag red">${esc(SC.mechanic)} promotion ${dmon(SC.start)} to ${dmon(SC.end)}</span>` : ""}</div>
        <div class="chart" id="cFc"></div>
        <div class="legend"><span><i style="background:${C.red}"></i>AI forecast</span>${S.cust !== "ALL" ? `<span><i class="box" style="background:${C.soft};opacity:.6"></i>Likely range (80%)</span>` : ""}<span><i class="dash"></i>Today's method (same day last week, adjusted for promotions)</span></div>
        <div class="row mt8" id="wxStrip" style="gap:4px"></div>
      </div>
      <div class="card" data-show="waterfall">
        <h3>Why ${fmt(r.forecast)} cases on ${dname(r.date)}?</h3>
        <div class="sub">${esc(PROD[S.sku].name)}, ${esc(custName)}${r.low != null ? ` · likely ${fmt(r.low)} to ${fmt(r.high)}` : ""}</div>
        <div class="chart" id="cWf"></div>
        <ul class="drivers">${driverWords(r).map(([w, v]) => `<li><span>${esc(w)}</span><span class="v">${v}</span></li>`).join("")}<li><span>AI forecast</span><span class="v">${fmt(r.forecast)}</span></li></ul>
        <div class="callout mt12 small">Today's method says <b>${fmt(r.today_method)}</b>${Math.abs(r.forecast - r.today_method) >= 1 ? `, ${fmt(Math.abs(r.forecast - r.today_method))} cases ${r.forecast > r.today_method ? "short" : "too many"}` : ""}.</div>
      </div>
    </div>
    <div class="callout mt16" data-show="monday"><b>${dname(DATES[0])}:</b> today's method plans ${fmt(mon.today_method)} cases of ${esc(PROD[SC.sku].name)} for ${esc(CUST[SC.customer].name)}, because last Monday was the ${esc(ALERT.A2 ? ALERT.A2.data.holiday : "public")} holiday. The AI knows that and forecasts <b>${fmt(mon.forecast)}</b>.</div>
    <div class="grid g2 mt16">
      <div class="card" data-show="accuracy">
        <div class="row between"><div><h3>Does each signal help?</h3><div class="sub">Back-test: the last 10 weeks, forecast 14 days ahead with forecast (not actual) weather</div></div></div>
        <div class="row"><div class="seg" id="btSeg">${[["hero", "Ice Break 500mL, Retailer A"], ["iced_coffee_total", "All iced coffee"], ["all_products", "All products"]].map(([k, t]) => `<button data-bt="${k}" class="${S.bt === k ? "on" : ""}">${t}</button>`).join("")}</div></div>
        <div class="row mt8" id="sigs">${["weather", "holidays", "promotions"].map(k => `<label class="switch"><input type="checkbox" data-sig="${k}" ${S.sig[k] ? "checked" : ""}><span class="sw"></span>${k[0].toUpperCase() + k.slice(1)}</label>`).join("")}</div>
        <div class="chart mt8" id="cBt"></div>
        <div class="legend"><span><i style="background:${C.ink}"></i>Actual orders</span><span><i class="dash"></i>Today's method</span><span><i style="background:${C.red}"></i>AI forecast</span></div>
        <div class="grid g3 mt12 kpi-row" id="btErr"></div>
      </div>
      <div class="card" data-show="whatif">
        <h3>What if? ${dname(SC.start)}</h3><div class="sub">Move the temperature and the discount; the model answers instantly</div>
        <div class="row between"><span class="small">Max temperature</span><span class="strong num" id="wiT">${S.wiTemp}°C</span></div>
        <input type="range" id="wiTemp" min="${WI.temps[0]}" max="${WI.temps[WI.temps.length - 1]}" value="${S.wiTemp}" aria-label="Temperature">
        <div class="row between mt8"><span class="small">${esc(PROD[SC.sku].name)} promotion at ${esc(CUST[SC.customer].name)}</span>
          <div class="seg" id="wiDep">${WI.depths.map((d, i) => { const k = Object.keys(WI.hero)[i]; return `<button data-dep="${k}" class="${k === S.wiDepth ? "on" : ""}">${d ? Math.round(d * 100) + "% off" : "None"}</button>`; }).join("")}</div></div>
        <div class="grid g3 mt12" id="wiOut"></div>
        <div class="chart mt8" id="cWi"></div>
      </div>
    </div>`;

    // forecast chart
    const promoIdx = rows.map((x, i) => x.promo_depth > 0 ? i : -1).filter(i => i >= 0);
    const shade = [];
    if (promoIdx.length) shade.push({ from: promoIdx[0], to: promoIdx[promoIdx.length - 1], color: C.cream, opacity: 1, label: `Promotion at ${CUST[SC.customer].name}`, textColor: C.red });
    Charts.line($("#cFc"), {
      labels: DATES.map(d2), height: 270, highlight: di, shade,
      band: rows[0].low != null ? { low: rows.map(x => x.low), high: rows.map(x => x.high), color: C.soft, opacity: .35 } : null,
      series: [{ values: rows.map(x => x.today_method), color: C.steel, dash: "5 4", width: 1.6 }, { values: rows.map(x => x.forecast), color: C.red, width: 2.6, dots: true }],
      tip: i => `${dname(DATES[i])}: AI ${fmt(rows[i].forecast)}, today's method ${fmt(rows[i].today_method)}, ${rows[i].max_temp_c}°C`,
      onPick: i => { S.day = DATES[i]; render(); }, xEvery: 1,
    });
    $("#wxStrip").innerHTML = X.weather.map(w => `<div title="${dname(w.date)}: ${w.max_temp_c}°C, ${w.rain_mm} mm rain" style="flex:1;text-align:center;font-size:11px;padding:3px 0;border-radius:4px;${w.max_temp_c >= 32 ? `background:${C.red};color:#fff;font-weight:700` : `background:${C.cream};color:${C.muted}`}">${Math.round(w.max_temp_c)}°</div>`).join("");
    $("#wxStrip").insertAdjacentHTML("afterbegin", `<span class="tiny muted" style="width:44px">Max °C</span>`);
    // waterfall
    const dc = r.drivers_cases, steps = [{ label: "Normal\nday", value: r.normal_level }];
    if (Math.abs(dc.Holidays) >= 1) steps.push({ label: "Holidays", value: dc.Holidays });
    if (Math.abs(dc.Promotion) >= 1) steps.push({ label: "Promotion", value: dc.Promotion });
    if (Math.abs(dc.Weather) >= 1) steps.push({ label: `Weather\n${Math.round(r.max_temp_c)}°C`, value: dc.Weather });
    Charts.waterfall($("#cWf"), { steps, total: r.forecast, totalLabel: "AI\nforecast", height: 230, ref: { value: r.today_method, label: `today's method ${fmt(r.today_method)}` } });
    $("#selSku").onchange = e => { S.sku = e.target.value; render(); };
    $("#selCust").onchange = e => { S.cust = e.target.value; render(); };
    // back-test
    $$("[data-bt]").forEach(b => b.onclick = () => { S.bt = b.dataset.bt; drawBt(); $$("[data-bt]").forEach(x => x.classList.toggle("on", x === b)); });
    $$("[data-sig]").forEach(c => c.onchange = () => { S.sig[c.dataset.sig] = c.checked; drawBt(); });
    drawBt();
    // what-if
    $("#wiTemp").oninput = e => { S.wiTemp = +e.target.value; $("#wiT").textContent = S.wiTemp + "°C"; drawWi(); };
    $$("[data-dep]").forEach(b => b.onclick = () => { S.wiDepth = b.dataset.dep; $$("[data-dep]").forEach(x => x.classList.toggle("on", x === b)); drawWi(); });
    drawWi();
  }
  const variantKey = () => ["weather", "holidays", "promotions"].filter(k => S.sig[k]).join("+") || "history_only";
  const wape = (y, f) => y.reduce((a, v, i) => a + Math.abs(v - f[i]), 0) / y.reduce((a, v) => a + v, 0);
  function drawBt() {
    const s = M.backtest_series[S.bt], vk = variantKey();
    Charts.line($("#cBt"), {
      labels: s.dates.map(dmon), height: 220,
      series: [{ values: s.y, color: C.ink, width: 1.6 }, { values: s.baseline, color: C.steel, dash: "5 4", width: 1.3 }, { values: s[vk], color: C.red, width: 2.2 }],
      tip: i => `${dname(s.dates[i])}: actual ${fmt(s.y[i])}, today's method ${fmt(s.baseline[i])}, AI ${fmt(s[vk][i])}`,
    });
    const eB = wape(s.y, s.baseline), eA = wape(s.y, s[vk]);
    const full = M.variants[vk][{ hero: "wape_hero", iced_coffee_total: "wape_iced_coffee", all_products: "wape" }[S.bt]];
    const on = ["weather", "holidays", "promotions"].filter(k => S.sig[k]);
    $("#btErr").innerHTML = `
      <div class="kpi"><div class="label">Today's method, these 10 weeks</div><div class="value num" style="color:${C.steel}">~${pct(eB, 1)}</div><div class="delta muted">error</div></div>
      <div class="kpi"><div class="label">AI${on.length ? " with " + on.join(", ") : ", history only"}</div><div class="value num red">~${pct(eA, 1)}</div><div class="delta muted">error</div></div>
      <div class="kpi"><div class="label">AI, full back-test Jan to Oct</div><div class="value num">~${pct(full, 1)}</div><div class="delta muted">error, same signals</div></div>`;
  }
  function drawWi() {
    const ti = WI.temps.indexOf(S.wiTemp), t0 = WI.temps.indexOf(T0);
    const heroC = WI.hero_at_customer[S.wiDepth][ti], hero = WI.hero[S.wiDepth][ti], iced = WI.iced[S.wiDepth][ti];
    const b = { heroC: WI.hero_at_customer[DKEY][t0], hero: WI.hero[DKEY][t0], iced: WI.iced[DKEY][t0] };
    const d = (v, base) => { const x = v - base; return Math.abs(x) < 1 ? `<span class="muted">as planned</span>` : `<span class="${x > 0 ? "red" : ""}">${x > 0 ? "+" : "−"}${fmt(Math.abs(x))} vs plan</span>`; };
    $("#wiOut").innerHTML = `
      <div class="kpi"><div class="label">${esc(PROD[SC.sku].name.replace("Iced Coffee ", ""))}, ${esc(CUST[SC.customer].name)}</div><div class="value num">${fmt(heroC)}</div><div class="delta">${d(heroC, b.heroC)}</div></div>
      <div class="kpi"><div class="label">Same product, all customers</div><div class="value num">${fmt(hero)}</div><div class="delta">${d(hero, b.hero)}</div></div>
      <div class="kpi"><div class="label">All iced coffee, all customers</div><div class="value num">${fmt(iced)}</div><div class="delta">${d(iced, b.iced)}</div></div>`;
    Charts.line($("#cWi"), {
      labels: WI.temps.map(t => t + "°"), height: 170, xEvery: 4, yLabel: "",
      yMin: Math.floor(Math.min(...WI.iced["0.0"]) * .85 / 500) * 500,
      series: [{ values: WI.iced["0.0"], color: C.cream2, width: 2 }, { values: WI.iced[S.wiDepth], color: C.red, width: 2.4 }],
      points: [{ i: ti, v: iced, label: fmt(iced) }],
      tip: i => `${WI.temps[i]}°C: ${fmt(WI.iced[S.wiDepth][i])} cases of iced coffee`,
    });
  }

  /* ================================================================== scene 3: plant and milk */
  function plan() {
    const lines = M.line_check.map(r => ({ ...r })), milk = M.milk_check.map(r => ({ ...r }));
    const changes = [];
    const lpc = s => PROD[s].litres_per_case * PROD[s].milk_fraction;
    const shiftSilo = (date, litres) => { const i = milk.findIndex(m => m.date === date); for (let k = i; k < milk.length; k++) milk[k].silo_end_l += litres; };
    if (S.planView === "after" && S.decisions.A4 === "approved") {
      const d = ALERT.A4.data, L3 = lines.filter(r => r.line === "L3");
      const overDays = L3.filter(r => d.over[r.date] != null), spare = d.spare_before, spareTot = Object.values(spare).reduce((a, b) => a + b, 0);
      let moved = 0;
      overDays.forEach(r => { const x = r.forecast_cases - r.capacity; r.forecast_cases -= x; moved += x; shiftSilo(r.date, x * lpc(SC.sku)); });
      Object.entries(spare).forEach(([dt, sp]) => { const r = L3.find(x => x.date === dt), add = Math.round(moved * sp / spareTot); r.forecast_cases += add; shiftSilo(dt, -add * lpc(SC.sku)); });
      changes.push("A4");
    }
    if (S.planView === "after" && S.decisions.A5 === "approved") {
      const d = ALERT.A5.data;
      const a = lines.find(r => r.line === "L1" && r.date === d.date), b = lines.find(r => r.line === "L1" && r.date === d.to_date);
      a.forecast_cases -= d.defer_cases; b.forecast_cases += d.defer_cases;
      shiftSilo(d.date, d.defer_litres); shiftSilo(d.to_date, -d.defer_litres);
      changes.push("A5");
    }
    lines.forEach(r => r.utilisation_pct = r.forecast_cases / r.capacity * 100);
    return { lines, milk, changes };
  }
  function scene3(main) {
    const approvedPlant = ["A4", "A5"].filter(k => S.decisions[k] === "approved");
    if (!approvedPlant.length) S.planView = "before";
    const P = plan();
    const totFc = M.forecast.reduce((a, r) => a + r.forecast, 0);
    const need = P.milk.reduce((a, r) => a + r.milk_needed_l, 0), exp = P.milk.reduce((a, r) => a + r.milk_expected_l, 0);
    const overDays = P.lines.filter(r => r.utilisation_pct > 100.05);
    const shortDays = P.milk.filter(r => r.silo_end_l < 0);
    main.innerHTML = head("From forecast to plant", "Plant &amp; Milk Check",
      `Every morning the forecast is turned into litres of raw milk and line time at Nambour, for the next 14 days.`,
      `<div class="seg" id="planSeg"><button data-pv="before" class="${S.planView === "before" ? "on" : ""}">Today's plan</button><button data-pv="after" class="${S.planView === "after" ? "on" : ""}" ${approvedPlant.length ? "" : "disabled title='Approve plant changes in scene 4 first'"}>After approved changes${approvedPlant.length ? ` (${approvedPlant.length})` : ""}</button></div>`) + `
    <div class="card"><div class="chain">
      <div><div class="small muted">Cases forecast, 14 days</div><div class="v num">${fmt(totFc)}</div><div class="tiny muted">16 products, 6 customers</div></div>
      <div><div class="small muted">Raw milk needed</div><div class="v num">${(need / 1e6).toFixed(1)}M L</div><div class="tiny muted">litres per case × milk share of each product</div></div>
      <div><div class="small muted">Milk expected from farms</div><div class="v num">${(exp / 1e6).toFixed(1)}M L</div><div class="tiny muted">${M.milk_meta ? "last 28 days of deliveries; less on hot days" : ""}</div></div>
      <div><div class="small muted">Problems found</div><div class="v num ${overDays.length + shortDays.length ? "red" : ""}">${overDays.length + shortDays.length}</div><div class="tiny muted">${overDays.length} line-days over capacity · ${shortDays.length} day${shortDays.length === 1 ? "" : "s"} short of milk</div></div>
    </div></div>
    <div class="grid g2 mt16">
      <div class="card" data-show="lines"><h3>Nambour line load</h3><div class="sub">Share of standard daily capacity. Red: over 100%.</div><div id="heat"></div>
        <div class="note mt8">Line 1: large-format white (2L, 3L). Line 2: 1L white and lactose free. Line 3: flavoured milk and iced coffee.</div></div>
      <div class="card" data-show="milk"><h3>Raw milk left in the silos at day end</h3><div class="sub">Thousand litres. Below zero: not enough milk for the plan.</div><div class="chart" id="cSilo"></div>
        <div class="note">${esc((M.milk_meta.silo_note || "").replace(/^assumption/i, "Assumption"))}. Farm intake falls on hot days (heat stress).</div></div>
    </div>
    <div class="callout mt16" id="gapBox"></div>`;
    // heatmap
    const lineIds = ["L1", "L2", "L3"];
    const cls = u => u > 100.05 ? "h4" : u >= 95 ? "h3" : u >= 80 ? "h2" : u >= 50 ? "h1" : "h0";
    $("#heat").innerHTML = `<table class="heat"><tr><th></th>${DATES.map(d => `<th>${WD[D(d).getDay()]}<br>${D(d).getDate()}</th>`).join("")}</tr>
      ${lineIds.map(l => `<tr><th class="rowh">Line ${l.slice(1)}</th>${DATES.map(d => { const r = P.lines.find(x => x.line === l && x.date === d); return `<td class="${cls(r.utilisation_pct)}" title="${esc(r.description)}: ${fmt(r.forecast_cases)} of ${fmt(r.capacity)} cases">${Math.round(r.utilisation_pct)}</td>`; }).join("")}</tr>`).join("")}</table>`;
    Charts.bars($("#cSilo"), {
      labels: P.milk.map(m => d2(m.date)), series: [{ values: P.milk.map(m => m.silo_end_l / 1000) }], height: 230, yFmt: v => fmt(v),
      colorFn: v => v < 0 ? C.red : C.cream2, tip: i => `${dname(P.milk[i].date)}: ${fmt(P.milk[i].silo_end_l)} L left; needed ${fmt(P.milk[i].milk_needed_l)} L, expected ${fmt(P.milk[i].milk_expected_l)} L`,
      valueLabels: (v, i) => v < 0 ? fmt(P.milk[i].silo_end_l) + " L" : "", maxBar: 26, dataMin: -30, negShade: true,
    });
    const g = $("#gapBox");
    if (overDays.length || shortDays.length) {
      const parts = [];
      if (overDays.length) parts.push(`line 3 is over capacity on ${[...new Set(overDays.map(r => dname(r.date)))].join(" and ")} (${fmt(overDays.reduce((a, r) => a + r.forecast_cases - r.capacity, 0))} cases)`);
      if (shortDays.length) parts.push(`the silos run ${fmt(-shortDays[0].silo_end_l)} L short on ${dname(shortDays[0].date)}`);
      g.innerHTML = `<div class="row between"><div><b>${parts.length} gap${parts.length > 1 ? "s" : ""} found:</b> ${parts.join("; ")}.</div><button class="btn primary" data-go="4">Hand to the agents →</button></div>`;
    } else {
      g.innerHTML = `<b>No gaps left.</b> The approved changes fit the plant and the milk available. <span class="muted">Silo low point: ${fmt(Math.min(...P.milk.map(m => m.silo_end_l)))} L.</span>`;
    }
    $$("[data-pv]").forEach(b => b.onclick = () => { if (b.disabled) return; S.planView = b.dataset.pv; render(); });
  }

  /* ================================================================== scene 4: agents */
  const ORDER = ["A1", "A4", "A5", "A3", "A2", "A6"].filter(k => ALERT[k]);
  const ASK = { A1: "Q1", A2: "Q6", A3: "Q7", A4: "Q8", A5: "Q9", A6: "Q11" };
  const SEEN = { forecast: 2, supply: 3, data: 1 };
  const AGENTS = [
    { name: "Demand agent", steps: ["Reading the weather forecast", "Checking the promotion calendar", "Comparing with today's plan"] },
    { name: "Supply agent", steps: ["Turning cases into litres", "Checking Nambour line load", "Checking silo balance"] },
    { name: "Shelf-life agent", steps: ["Checking stock age", "Looking for products losing sales"] },
    { name: "Order agent", steps: ["Scanning incoming orders", "Checking old Fonterra codes"] },
  ];
  function scene4(main) {
    main.innerHTML = head("Agents, with a person in control", "Agent View",
      `Four agents watch demand, supply, shelf life and orders. Each suggestion comes with its reasons. A planner approves or rejects it; approved changes go to SAP (simulated here) and every step is logged.`) + `
    <div class="card"><div class="row between"><div><h3>Morning check, ${dname(DATES[0])}</h3><div class="sub">The agents run at 06:00 each day; press to replay this morning's run</div></div>
      <button class="btn primary" id="runMorning" ${S.morning !== "idle" ? "disabled" : ""}>${S.morning === "done" ? "Check complete" : S.morning === "running" ? "Running…" : "Run the morning check"}</button></div>
      <div class="agents mt8">${AGENTS.map((a, i) => `<div class="agent"><div class="nm"><span class="dot ${S.morning === "done" ? "done" : ""}" id="dot${i}"></span>${a.name}</div><div class="st" id="st${i}">${S.morning === "done" ? findingsFor(a.name) : "Waiting"}</div></div>`).join("")}</div></div>
    <div class="grid g-3col mt16" id="agentGrid"></div>`;
    $("#runMorning").onclick = runMorning;
    if (S.morning === "done") agentGrid();
  }
  const findingsFor = name => { const n = ORDER.filter(k => ALERT[k].agent === name).length; return n ? `${n} finding${n > 1 ? "s" : ""}` : "Nothing to report"; };
  function runMorning() {
    S.morning = "running";
    $("#runMorning").disabled = true; $("#runMorning").textContent = "Running…";
    let t = 0;
    AGENTS.forEach((a, i) => {
      later(() => { const d = $("#dot" + i); if (d) d.className = "dot busy"; }, t + i * 120);
      a.steps.forEach((s, k) => later(() => { const e = $("#st" + i); if (e) e.textContent = s + "…"; }, t + i * 120 + k * 650));
      later(() => { const d = $("#dot" + i), e = $("#st" + i); if (d) d.className = "dot done"; if (e) e.textContent = findingsFor(a.name); }, t + i * 120 + a.steps.length * 650);
    });
    later(() => {
      S.morning = "done"; S.sel = ORDER[0];
      audit("Agents", `Morning check: ${ORDER.length} findings (${ORDER.filter(k => ALERT[k].severity === "high").length} high)`);
      render();
    }, 120 * 3 + 3 * 650 + 400);
  }
  function agentGrid() {
    const a = ALERT[S.sel] || ALERT[ORDER[0]];
    const b = L.briefing;
    $("#agentGrid").innerHTML = `
      <div>
        <div class="card"><div class="kicker">Morning briefing</div><h3>${esc(b.greeting)}</h3>
          <ol style="padding-left:18px;margin:8px 0 0">${b.items.map(it => `<li class="small" style="margin-bottom:6px"><a href="#" data-sel="${it.alert}" style="color:inherit">${esc(it.text)}</a></li>`).join("")}</ol>
          <div class="note">${esc(b.footer)}</div></div>
        <div class="alert-list mt12">${ORDER.map((k, i) => { const x = ALERT[k], d = S.decisions[k]; return `<button class="alert-row ${x.severity} ${k === a.id ? "sel" : ""} fade-in" style="animation-delay:${i * 80}ms" data-sel="${k}"><span class="bar"></span><span><span class="who">${esc(x.agent)} · ${x.severity}${d ? ` · <span class="status ${d}">${d}</span>` : ""}</span><br><span class="tt">${esc(x.title)}</span></span></button>`; }).join("")}</div>
      </div>
      <div class="card" id="alertDetail">${alertDetail(a)}</div>
      <div class="card"><div class="row between"><h3>Audit log</h3><button class="btn small" id="openAudit">Open full log</button></div>
        <div class="sub">Latest first</div>${S.audit.slice().reverse().slice(0, 9).map(auditRow).join("")}</div>`;
    $$("[data-sel]", $("#agentGrid")).forEach(e => e.onclick = ev => { ev.preventDefault(); S.sel = e.dataset.sel; S.rejecting = null; agentGrid(); });
    $("#openAudit").onclick = () => openDrawer("audit");
    bindDetail(a);
  }
  function alertDetail(a) {
    const d = S.decisions[a.id];
    const optSel = S.options[a.id] != null ? S.options[a.id] : Math.max(0, (a.options || []).findIndex(o => o.recommended));
    return `<div class="row between"><span class="tag ${a.severity === "high" ? "solid" : "red"}">${esc(a.agent)} · ${a.severity}</span>
        <span class="row"><button class="btn small" data-ask="${ASK[a.id] || ""}">Ask why</button><button class="btn small ghost" data-go="${SEEN[a.scene] || 2}">See in scene ${SEEN[a.scene] || 2} →</button></span></div>
      <h2 style="font-size:20px;margin-top:10px">${esc(a.title)}</h2>
      <p class="small" style="margin:8px 0">${esc(a.what)}</p>
      <div class="strong small">Why</div>
      <ul class="small" style="margin:4px 0 8px;padding-left:18px">${a.why.map(w => `<li>${esc(w)}</li>`).join("")}</ul>
      <div class="grid g2 small"><div><span class="muted">Confidence</span><br><b>${esc(a.confidence.level)}</b> · ${esc(a.confidence.range)}<br><span class="muted tiny">${esc(a.confidence.backtest)}</span></div>
        <div><span class="muted">Impact</span><br>${esc(a.impact)}</div></div>
      ${(a.options || []).length ? `<div class="strong small mt12">Options</div>${a.options.map((o, i) => `<label class="opt ${i === optSel ? "on" : ""}"><input type="radio" name="opt" data-opt="${i}" ${i === optSel ? "checked" : ""} ${d ? "disabled" : ""}><span><b>${esc(o.name)}</b>${o.recommended ? ' <span class="tag red">suggested</span>' : ""}<br><span class="small muted">${esc(o.detail)}</span></span></label>`).join("")}` : ""}
      <div class="callout mt12 small"><b>Suggestion:</b> ${esc(a.recommendation)}</div>
      <div id="decision" class="mt12">${decisionBlock(a)}</div>`;
  }
  function decisionBlock(a) {
    const d = S.decisions[a.id];
    if (d === "approved") return `<div class="status approved">✓ Approved by planner at ${esc(S.decisionTime[a.id])}</div><p class="small">${esc(a.approve.result)}</p>${sapCard(a.id)}`;
    if (d === "rejected") return `<div class="status rejected">✗ Rejected by planner at ${esc(S.decisionTime[a.id])}: ${esc(S.rejectReason[a.id])}</div><p class="small">${esc(a.reject.result)}</p>`;
    if (S.rejecting === a.id) return `<div class="row"><select id="rejReason">${["Customer confirmed a lower order", "Plant or labour constraint", "Already handled by phone", "I disagree with the forecast", "Other"].map(r => `<option>${r}</option>`).join("")}</select>
      <button class="btn dark" id="rejConfirm">Confirm reject</button><button class="btn ghost" id="rejCancel">Cancel</button></div><div class="note mt8">The reason goes to the audit log and helps the agents learn.</div>`;
    return `<div class="row"><button class="btn primary" id="approve">Approve</button><button class="btn" id="reject">Reject</button><span class="note">Nothing changes until a person decides.</span></div>`;
  }
  function sapCard(id) {
    const rows = X.sap[id] || [];
    return `<div class="sap"><div class="row between"><span class="hd">Sent to SAP · simulated</span><span class="mono">${esc(S.sapRef[id])}</span></div>
      <table class="t mt8">${rows.map(([k, v]) => `<tr><td class="muted" style="width:110px">${esc(k)}</td><td>${esc(v)}</td></tr>`).join("")}
      <tr><td class="muted">Status</td><td><b>Posted to test system (simulated)</b></td></tr></table></div>`;
  }
  function bindDetail(a) {
    const box = $("#alertDetail");
    $$("[data-opt]", box).forEach(r => r.onchange = () => { S.options[a.id] = +r.dataset.opt; box.innerHTML = alertDetail(a); bindDetail(a); });
    const ap = $("#approve", box), rj = $("#reject", box);
    if (ap) ap.onclick = () => decide(a, "approved");
    if (rj) rj.onclick = () => { S.rejecting = a.id; box.innerHTML = alertDetail(a); bindDetail(a); };
    const rc = $("#rejConfirm", box);
    if (rc) rc.onclick = () => { S.rejectReason[a.id] = $("#rejReason").value; decide(a, "rejected"); };
    const cc = $("#rejCancel", box);
    if (cc) cc.onclick = () => { S.rejecting = null; box.innerHTML = alertDetail(a); bindDetail(a); };
    $$("[data-ask]", box).forEach(b => b.onclick = () => { openDrawer("chat"); if (b.dataset.ask) ask(QA[b.dataset.ask].question); });
  }
  function decide(a, how) {
    tick(2);
    S.decisions[a.id] = how; S.rejecting = null;
    S.decisionTime[a.id] = clockStr();
    if (how === "approved") {
      S.sapRef[a.id] = `SIM-4500${String(++S.sapSeq).padStart(4, "0")}`;
      const opt = (a.options || [])[S.options[a.id] != null ? S.options[a.id] : Math.max(0, (a.options || []).findIndex(o => o.recommended))];
      audit("Planner", `${a.approve.audit}${opt && !opt.recommended ? ` (chose: ${opt.name})` : ""}`);
      audit("SAP (simulated)", `${S.sapRef[a.id]} posted: ${(X.sap[a.id] || [["", "change"]])[0][1]}`);
      toast(`Approved · sent to SAP (simulated) as ${S.sapRef[a.id]}`);
      if (a.id === "A4" || a.id === "A5") S.planView = "after";
    } else {
      audit("Planner", `Rejected ${a.id}: ${S.rejectReason[a.id]}`);
      toast("Rejected · reason logged");
    }
    const next = ORDER.find(k => !S.decisions[k]);
    agentGrid();
    if (next && next !== a.id) setTimeout(() => { const e = $(`.alert-row[data-sel="${next}"]`); if (e) e.classList.add("flash"); }, 200);
  }

  /* ================================================================== scene 5: value */
  function scene5(main) {
    const v = M.value, acc = M.accuracy;
    main.innerHTML = head("Replay of January to October", "Business Value",
      `We replayed ${(([a, b]) => `${dmon(a)} to ${dmon(b)} ${b.slice(0, 4)}`)(M.meta.backtest.split(" to "))} day by day through the same stock rules, changing only the forecast. Synthetic Queensland range; real gains will be smaller.`) + `
    <div class="grid g5" data-show="value">
      ${kpiFT("Forecast accuracy", acc.today_method_accuracy_pct + "%", acc.ml_accuracy_pct + "%", `${Math.round(acc.error_reduction_pct)}% less error`)}
      ${kpiFT("Write-offs, share of production", v.today.writeoff_pct + "%", v.ml.writeoff_pct + "%", `${Math.round(v.writeoff_reduction_pct)}% fewer cases thrown away`)}
      ${kpiFT("Orders delivered in full", v.today.fill_pct + "%", v.ml.fill_pct + "%", `${fmt(v.today.short_cases - v.ml.short_cases)} fewer cases short`)}
      <div class="card kpi"><div class="label">Raw milk not wasted</div><div class="value num">${fmt(v.annualised_milk_litres_saved / 1000)}k <small>L a year</small></div><div class="delta muted">same farms, less milk poured away</div></div>
      <div class="card kpi"><div class="label">Lower write-off cost</div><div class="value num">A$${fmt(v.annualised_saving_aud / 1000)}k <small>a year</small></div><div class="delta muted">at 55% of list price; Queensland range only</div></div>
    </div>
    <div class="grid g2 mt16">
      <div class="card"><h3>Write-offs by month</h3><div class="sub">Share of production, same stock rules</div><div class="chart" id="cWo"></div>
        <div class="note">April: the Easter long weekend and Anzac Day. Stock made as if for normal days is not ordered over the holidays and goes out of date; the model expects the drop.</div>
        <div class="legend"><span><i class="box" style="background:${C.cream2}"></i>Today's method</span><span><i class="box" style="background:${C.red}"></i>AI forecast</span></div></div>
      <div class="card" data-show="segments"><h3>Where the error falls</h3><div class="sub">Forecast error by situation (lower is better)</div><div class="chart" id="cSeg"></div>
        <div class="legend"><span><i class="box" style="background:${C.cream2}"></i>Today's method</span><span><i class="box" style="background:${C.red}"></i>AI forecast</span></div></div>
    </div>
    <div class="grid g2 mt16">
      <div class="card tint"><h3>Pilot measures</h3><div class="sub">Targets to confirm once a real baseline is measured</div>
        <table class="t"><tr><th>Measure</th><th>Target</th></tr>
        ${[["Forecast error by product, customer, warehouse and day", "At least 20% lower than today"], ["Fresh write-offs", "At least 15% lower"], ["On-time, in-full delivery to retailers", "No worse than today"],
           ["Gap between raw milk planned and needed", "Smaller than baseline"], ["Lactalis and Fonterra records matched", "At least 95% in scope"], ["Agent suggestions planners accept", "At least 70%; alert within 1 hour"]]
          .map(([a, b]) => `<tr><td>${a}</td><td class="strong">${b}</td></tr>`).join("")}</table></div>
      <div class="card"><h3>Roadmap</h3><div class="sub">Start small, prove it on real data, then widen</div>
        <div class="road">
          <div class="now"><h4>Now</h4><ul><li>This demo</li><li>Synthetic data, real model</li></ul></div>
          <div><h4>Discovery</h4><ul><li>Today's error and write-off rates</li><li>Data access for one region</li><li>Name a sponsor</li></ul></div>
          <div><h4>Pilot: Queensland</h4><ul><li>Nambour, fresh and flavoured milk</li><li>SAP history, promotions, milk intake, weather</li><li>AI beside today's method</li><li>Planner-approved write-back to SAP</li></ul></div>
          <div><h4>Later</h4><ul><li>All states and plants</li><li>Yoghurt, desserts, cheese, butter</li><li>Retailer scan data</li></ul></div>
        </div></div>
    </div>`;
    const mt = v.monthly.filter(r => r.method === "today"), ml = v.monthly.filter(r => r.method === "ml");
    Charts.bars($("#cWo"), { labels: mt.map(r => MO[+r.month.slice(5) - 1]), series: [{ values: mt.map(r => r.writeoff_pct), color: C.cream2 }, { values: ml.map(r => r.writeoff_pct), color: C.red }], height: 230, yFmt: v => v.toFixed(1) + "%", maxBar: 18 });
    const seg = Object.entries(M.segments);
    Charts.hpair($("#cSeg"), { rows: seg.map(([k, s]) => ({ label: k.replace(" (from 10 Jul)", ""), a: s.baseline_wape * 100, b: s.ml_wape * 100 })), aName: "Today's method", bName: "AI forecast", fmt: x => x.toFixed(0) + "%", padL: 230 });
  }
  const kpiFT = (label, a, b, note) => `<div class="card kpi"><div class="label">${label}</div><div class="fromto"><span class="from num">${a}</span><span class="arrow">→</span><span class="to num">${b}</span></div><div class="delta red">${note}</div></div>`;

  /* ================================================================== scene 6: label check */
  const LB = X.labels;
  const REF_MILK_FAT = 3.4;   // regular full cream milk, g/100 mL: reference food for "reduced fat"
  const decs = k => /\(g\)/.test(k) ? 1 : 0;              // grams to 0.1; kJ and mg to whole numbers
  const unitStep = k => Math.pow(10, -decs(k));
  const nfmt = (k, v) => v.toFixed(decs(k));
  const cap = s => s[0].toUpperCase() + s.slice(1);
  function checkLabel(c) {
    const out = [];
    const nip = c.nip, per = k => nip[k][0], serve = k => nip[k][1];
    const allergens = [...new Set(c.ingredients.filter(i => i.allergen).map(i => i.allergen))];
    // 1 allergens named in bold in the ingredient list
    const notBold = c.ingredients.filter(i => i.allergen && !i.bold);
    out.push(notBold.length ? { sev: "Must fix", ref: "ing", title: `${cap(notBold[0].allergen)} not declared in bold`,
      evidence: `"${notBold.map(i => i.text).join('", "')}" contains ${notBold.map(i => i.allergen).join(", ")} but is not shown in bold.`,
      rule: "Plain English Allergen Labelling (Standard 1.2.3): allergens appear in bold, using the required name, in the ingredient list.",
      fix: `Show "${notBold[0].allergen}" in bold in "${notBold[0].text}", as for the other allergens.` }
      : { pass: "Allergens shown in bold in the ingredient list" });
    // 2 summary statement lists every allergen
    const missing = allergens.filter(a => !c.contains.includes(a));
    out.push(missing.length ? { sev: "Must fix", ref: "contains", title: `Allergen summary is missing ${missing.join(", ")}`,
      evidence: `Ingredients contain ${allergens.join(" and ")}; the summary says "Contains: ${c.contains.map(cap).join(", ")}."`,
      rule: "Standard 1.2.3: a separate summary statement starting \"Contains\" lists every allergen in the food.",
      fix: `Change to "Contains: ${allergens.map(cap).join(", ")}."` }
      : { pass: "Allergen summary statement complete" });
    // 3 nutrition content claims
    for (const cl of c.claims) {
      const l = cl.toLowerCase();
      if (/good source of protein|high protein/.test(l)) {
        const p = serve("Protein (g)");
        out.push(p >= 10 ? { pass: `"${cl}" claim supported (${p} g protein per serve)` } : { sev: "Must fix", ref: "claim", title: `"${cl}" claim not supported`,
          evidence: `${p} g protein per ${c.serve_ml} mL serve.`, rule: "Schedule 4 conditions: \"good source\" of protein needs at least 10 g per serve; \"source of protein\" needs at least 5 g.",
          fix: p >= 5 ? `Change to "Source of protein", or increase protein to 10 g per serve.` : "Remove the claim." });
      } else if (/low fat/.test(l)) {
        const f = per("Fat, total (g)");
        out.push(f <= 1.5 ? { pass: `"${cl}" claim supported` } : { sev: "Must fix", ref: "claim", title: `"${cl}" claim not supported`,
          evidence: `${f} g fat per 100 mL.`, rule: "Schedule 4 conditions: \"low fat\" means no more than 1.5 g fat per 100 mL for a liquid.",
          fix: f <= REF_MILK_FAT * .75 ? `Use "Reduced fat" (${Math.round((1 - f / REF_MILK_FAT) * 100)}% less than regular milk at ${REF_MILK_FAT} g), or bring fat to 1.5 g.` : "Bring fat to 1.5 g per 100 mL or remove the claim." });
      } else if (/no added sugar/.test(l)) {
        const hits = c.ingredients.filter(i => LB.added_sugar_terms.some(t => i.text.toLowerCase().includes(t)));
        out.push(!hits.length ? { pass: `"${cl}" claim supported` } : { sev: "Must fix", ref: "claim", title: `"${cl}" claim not allowed with these ingredients`,
          evidence: `Ingredients include ${hits.map(h => `"${h.text}"`).join(", ")}.`, rule: "Standard 1.2.7: for a \"no added sugar\" claim, concentrated fruit juice counts as added sugar (except in some juice and water-based drinks, not dairy drinks).",
          fix: "Remove the claim, or replace the apple juice concentrate." });
      }
    }
    // 4 Health Star Rating graphic matches the panel and the current recipe
    const e100 = per("Energy (kJ)"), sug = per("- sugars (g)");
    out.push(c.hsr.energy_kj_per_100ml !== e100 ? { sev: "Must fix", ref: "hsr", title: "Health Star Rating energy icon does not match the nutrition panel",
      evidence: `Icon says ${c.hsr.energy_kj_per_100ml} kJ per 100 mL; the panel says ${e100} kJ.`, rule: "Health Star Rating style guide: values in the graphic match the nutrition information panel.", fix: `Change the icon to ${e100} kJ.` }
      : { pass: "Health Star Rating energy icon matches the panel" });
    out.push(c.hsr.spec_sugars_g !== sug ? { sev: "Must fix", ref: "hsr", title: "Health Star Rating needs recalculating",
      evidence: `${c.hsr.stars} stars were calculated on recipe ${c.hsr.spec_version} (${c.hsr.spec_sugars_g} g sugars per 100 mL); this artwork shows ${sug} g.`,
      rule: "The rating is calculated from the food as sold; a recipe change means a new calculation. Health Star Rating is moving towards being mandatory.", fix: "Recalculate the stars with the new recipe before print." }
      : { pass: "Health Star Rating based on the current recipe" });
    // 5 nutrition panel arithmetic (per serve = per 100 mL x serve size)
    const bad = Object.entries(nip).filter(([k, [a, b]]) => Math.abs(Math.round(a * c.serve_ml / 100 / unitStep(k) + 1e-9) * unitStep(k) - b) > 1e-9);
    out.push(bad.length ? { sev: "Must fix", ref: "nip", rows: bad.map(([k]) => k), title: `Nutrition panel per-serve value wrong: ${bad.map(([k]) => k.replace(/ \(.*\)/, "").replace("- ", "")).join(", ")}`,
      evidence: bad.map(([k, [a, b]]) => `${k}: ${a} per 100 mL × ${c.serve_ml / 100} = ${+(a * c.serve_ml / 100).toFixed(2)}, but the panel says ${b}`).join("; ") + ".",
      rule: "Standard 1.2.8: per-serve and per-100 mL values must agree.", fix: bad.map(([k, [a]]) => `${k} per serve: ${nfmt(k, a * c.serve_ml / 100)}`).join("; ") }
      : { pass: "Nutrition panel per-serve values add up" });
    // 6 origin claim vs Country of Origin label
    out.push(c.origin_claim && /100%/.test(c.origin_claim) && c.cool.aus_pct < 100 ? { sev: "Check", ref: "origin", title: "Origin wording does not match the origin label",
      evidence: `Front says "${c.origin_claim}"; the origin label says "at least ${c.cool.aus_pct}% Australian ingredients".`,
      rule: "Country of Origin Food Labelling: claims elsewhere on the pack must not contradict the standard mark.", fix: "Confirm the milk source and align the two statements." }
      : { pass: "Origin label consistent with other claims" });
    // 7 "fresh" wording with reconstituted ingredients
    const recon = c.ingredients.filter(i => /reconstituted/i.test(i.text));
    out.push(/fresh/i.test(c.front_text) && recon.length ? { sev: "Check", ref: "name", title: "\"Fresh\" used on milk with reconstituted ingredients",
      evidence: `Name says "${c.front_text}"; ingredients include "${recon[0].text}".`,
      rule: "Australian Consumer Law s29: no misleading representations. In 2026 the ACCC acted on milk labelled fresh that contained reconstituted ingredients.",
      fix: "Legal review: drop \"Fresh\" or remove the reconstituted ingredient." }
      : { pass: "No freshness wording issues" });
    // 8 storage and date
    out.push(c.storage && c.date_mark ? { pass: "Storage instruction and date mark present" } : { sev: "Must fix", ref: "back", title: "Storage instruction or date mark missing", evidence: "", rule: "Standard 1.2.6 and 1.2.5.", fix: "Add them." });
    return out;
  }
  const LABEL_RESULTS = Object.fromEntries(LB.cartons.map(c => [c.id, checkLabel(c)]));

  const TEAM = { contains: "food safety team", ing: "food safety team", claim: "marketing team", hsr: "nutrition team", nip: "nutrition team",
                 origin: "procurement team", name: "legal team", back: "artwork team" };
  const team = f => TEAM[f.ref] || "regulatory team";
  function carton(c, findings, scanned) {
    const nums = {};
    findings.filter(f => !f.pass).forEach((f, i) => { (nums[f.ref] = nums[f.ref] || []).push(i + 1); });
    const flag = ref => scanned && nums[ref] ? ` flagged" data-n="${nums[ref].join(",")}` : "";
    const badRows = new Set(scanned ? findings.filter(f => f.rows).flatMap(f => f.rows) : []);
    const ing = c.ingredients.map(i => i.bold ? `<b>${esc(i.text)}</b>` : esc(i.text)).join(", ");
    return `<div class="carton-wrap" id="cartonWrap">
      <div class="panel front" style="--pc:${c.colour};--pa:${c.accent}">
        <div class="brand">${esc(LB.brand)}</div>
        <div class="pname mark${flag("name")}">${esc(c.front_text)}</div>
        <div class="psize">${esc(c.size)}</div>
        <div class="claims mark${flag("claim")}">${c.claims.map(x => `<span>${esc(x)}</span>`).join("")}</div>
        ${c.origin_claim ? `<div class="ribbon mark${flag("origin")}">${esc(c.origin_claim)}</div>` : ""}
        <div class="hsr mark${flag("hsr")}"><div class="stars"><b>${c.hsr.stars.toFixed(1)}</b><span>${"★".repeat(Math.floor(c.hsr.stars))}${c.hsr.stars % 1 ? "½" : ""}</span><small>HEALTH STAR RATING</small></div>
          <div class="icon"><b>${c.hsr.energy_kj_per_100ml}kJ</b><small>ENERGY<br>PER 100mL</small></div></div>
      </div>
      <div class="panel back mark${flag("back")}">
        <div class="h">Ingredients</div>
        <p class="mark${flag("ing")}">${ing}.</p>
        <p class="mark${flag("contains")}"><b>Contains: ${c.contains.map(cap).join(", ")}.</b></p>
        <div class="h">Nutrition information</div>
        <div class="tiny">Servings per package: ${c.size === "2 L" ? 8 : 1} · Serving size: ${c.serve_ml} mL</div>
        <table class="nip mark${flag("nip")}"><tr><th></th><th>Per serve</th><th>Per 100 mL</th></tr>
          ${Object.entries(c.nip).map(([k, [a, b]]) => `<tr class="${badRows.has(k) ? "bad" : ""}"><td>${esc(k)}</td><td>${nfmt(k, b)}</td><td>${nfmt(k, a)}</td></tr>`).join("")}</table>
        <div class="cool mark${flag("origin")}"><div class="kang">▲</div><div><b>Made in ${esc(c.cool.made_in)}</b> from at least ${c.cool.aus_pct}% Australian ingredients<div class="bar"><i style="width:${c.cool.aus_pct}%"></i></div></div></div>
        <div class="tiny mt8">${esc(c.storage)}. ${esc(c.date_mark)}: see top of pack.</div>
      </div>
      ${scanned === "scanning" ? '<div class="scanline"></div>' : ""}
    </div>`;
  }

  function scene6(main) {
    const c = LB.cartons.find(x => x.id === S.lbSel) || LB.cartons[0];
    const st = S.lbState[c.id] || "idle";
    const findings = LABEL_RESULTS[c.id], issues = findings.filter(f => !f.pass), passes = findings.filter(f => f.pass);
    const rv = S.lbReview[c.id] || {};
    main.innerHTML = head("Same agents, another job", "Label Agent",
      `Before artwork goes to print, the label agent checks it against allergen, nutrition claim, Health Star Rating and origin rules. A person reviews every finding.`,
      `<span class="tag">${esc(LB.brand)} is a fictional brand</span>`) + `
    <div class="row" style="gap:8px">${LB.cartons.map(x => { const s = S.lbState[x.id], n = LABEL_RESULTS[x.id].filter(f => !f.pass).length, done = Object.keys(S.lbReview[x.id] || {}).length;
      return `<button class="ctab ${x.id === c.id ? "on" : ""}" data-carton="${x.id}"><i style="background:${x.colour}"></i><span><b>${esc(x.name)}</b> ${esc(x.size)}<br><span class="tiny muted">${s === "done" ? (done === n ? "All findings reviewed" : `${n} finding${n === 1 ? "" : "s"} · ${done} reviewed`) : "Not checked"}</span></span></button>`; }).join("")}</div>
    <div class="grid g-main mt16">
      <div class="card"><div class="row between"><div><h3>${esc(c.name)} ${esc(c.size)}: artwork for approval</h3><div class="sub">Front and back panels as sent by the design agency</div></div>
        <button class="btn primary" id="runLabel" ${st !== "idle" ? "disabled" : ""}>${st === "done" ? "Checked" : st === "scanning" ? "Checking…" : "Check this label"}</button></div>
        ${carton(c, findings, st === "idle" ? false : st)}</div>
      <div class="card" data-show="label"><h3>Findings</h3><div class="sub">${st === "done" ? `${issues.length} to review · ${passes.length} checks passed` : "Run the check to see findings"}</div>
        <div id="lbFindings">${st === "done" ? issues.map((f, i) => finding(c, f, i, rv[i])).join("") +
          `<details class="mt12"><summary class="small strong">${passes.length} checks passed</summary><ul class="small" style="padding-left:18px;margin:6px 0">${passes.map(p => `<li>${esc(p.pass)}</li>`).join("")}</ul></details>
           <div class="note mt12">${esc(LB.rules_note)}</div>` : ""}</div></div>
    </div>`;
    $$("[data-carton]").forEach(b => b.onclick = () => { S.lbSel = b.dataset.carton; render(); });
    $("#runLabel").onclick = () => {
      S.lbState[c.id] = "scanning"; render();
      later(() => {
        S.lbState[c.id] = "done"; tick(1);
        audit("Label agent", `Checked ${c.name} ${c.size} artwork: ${issues.length} findings (${issues.filter(f => f.sev === "Must fix").length} must fix), ${passes.length} checks passed`);
        render();
      }, 1600);
    };
    $$("[data-lb]").forEach(b => b.onclick = () => {
      const i = +b.dataset.i, f = issues[i];
      (S.lbReview[c.id] = S.lbReview[c.id] || {})[i] = b.dataset.lb;
      tick(1);
      audit("Regulatory reviewer", b.dataset.lb === "send" ? `${c.name}: sent to ${team(f)}: ${f.title}` : `${c.name}: marked not an issue: ${f.title}`);
      render();
    });
  }
  function finding(c, f, i, r) {
    return `<div class="queue-item ${r ? "done" : ""}"><div class="row between"><span class="row" style="gap:6px"><span class="numb">${i + 1}</span><span class="tag ${f.sev === "Must fix" ? "solid" : "red"}">${f.sev}</span></span>${r ? `<span class="small status ${r === "send" ? "approved" : "rejected"}">${r === "send" ? "Sent to " + team(f) : "Not an issue"}</span>` : ""}</div>
      <div class="strong mt8">${esc(f.title)}</div>
      <div class="small mt8">${esc(f.evidence)}</div>
      <div class="tiny muted mt8">${esc(f.rule)}</div>
      <div class="small mt8"><b>Suggested fix:</b> ${esc(f.fix)}</div>
      ${r ? "" : `<div class="row mt8"><button class="btn small dark" data-lb="send" data-i="${i}">Send to ${team(f)}</button><button class="btn small" data-lb="dismiss" data-i="${i}">Not an issue</button></div>`}</div>`;
  }

  /* ------------------------------------------------------------------ audit drawer */
  const auditRow = a => `<div class="audit-row ${a.fresh ? "new" : ""}"><span class="tm">${esc(a.time)}</span><span><span class="wh">${esc(a.who)}</span> · ${esc(a.what)}</span></div>`;
  function renderAudit() {
    $("#auditCount").textContent = S.audit.length;
    $("#auditLog").innerHTML = S.audit.slice().reverse().map(auditRow).join("");
    setTimeout(() => S.audit.forEach(a => a.fresh = false), 1500);
  }

  /* ------------------------------------------------------------------ chat */
  const STOP = new Set(L.fallback.stopwords);
  const tokens = s => (s.toLowerCase().match(/[a-z0-9%°']+/g) || []).filter(t => !STOP.has(t));
  function score(q, e) {
    const ql = q.toLowerCase(), qt = new Set(tokens(q));
    let s = 0;
    for (const k of e.keywords) {
      const plain = /^[a-z]+$/.test(k);
      if (plain ? qt.has(k) : ql.includes(k)) s += k.includes(" ") ? 2 : 1;
    }
    const et = new Set(tokens(e.question));
    for (const t of qt) if (et.has(t)) s += .5;
    return s;
  }
  function route(q) {
    const ranked = L.qa.map(e => [score(q, e), e]).sort((a, b) => b[0] - a[0]);
    const top = ranked[0][0] > 0 ? ranked.slice(0, L.fallback.suggest).map(x => x[1])
      : SCENES[S.scene - 1].chips.slice(0, L.fallback.suggest).map(id => QA[id]);   // nothing related: offer this scene's questions
    return { best: ranked[0][0] >= 1 ? ranked[0][1] : null, top };
  }
  const AGENT_OF = { Forecast: "Demand agent", "What-if": "Demand agent", Accuracy: "Demand agent", Supply: "Supply agent", Data: "Data agent", Waste: "Shelf-life agent", Labels: "Label agent", Value: "Control tower", "How it works": "Control tower", "Next steps": "Control tower" };
  const SHOW_SCENE = { waterfall: 2, whatif: 2, monday: 2, siblings: 4, accuracy: 2, segments: 5, signals: 2, weather: 2, forecast: 2, lines: 3, milk: 3, matching: 1, legacy: 1, prices: 1, value: 5, writeoffs: 5, audit: 4, label: 6 };
  function fill(e, q) {
    let a = e.answer;
    if (e.template === "temp") {
      const m = q.match(/(\d{1,2})\s*(°|degrees|deg\b|c\b)/i) || q.match(/\b(\d{2})\b/);
      let t = m ? +m[1] : 28; t = Math.max(WI.temps[0], Math.min(WI.temps[WI.temps.length - 1], t));
      const i = WI.temps.indexOf(t);
      a = a.replace("{temp}", t).replace("{iced}", fmt(WI.iced[DKEY][i])).replace("{hero}", fmt(WI.hero[DKEY][i]));
      S.wiTemp = t; S.wiDepth = DKEY;
    }
    if (e.template === "depth") {
      const m = q.match(/(\d{1,2})\s*%/);
      const want = m ? +m[1] / 100 : .25;
      const k = Object.keys(WI.hero).reduce((b, x) => Math.abs(+x - want) < Math.abs(+b - want) ? x : b);
      const i = WI.temps.indexOf(T0);
      a = a.replace("{depth}", Math.round(+k * 100)).replace("{hero_c}", fmt(WI.hero_at_customer[k][i])).replace("{none}", fmt(WI.hero_at_customer["0.0"][i])).replace("{iced}", fmt(WI.iced[k][i]));
      if (+k === 0) a = a.replace(/^At 0% off/, "With no promotion");
      S.wiTemp = T0; S.wiDepth = k;
    }
    return a;
  }
  function ask(q) {
    q = q.trim(); if (!q) return;
    S.chat.push({ me: true, text: q });
    const typing = { typing: true };
    S.chat.push(typing);
    drawChat();
    later(() => {
      const r = route(q), at = S.chat.indexOf(typing);
      const msg = r.best ? { who: AGENT_OF[r.best.topic] || "Control tower", text: fill(r.best, q), show: r.best.show }
        : { who: "Control tower", text: L.fallback.message, suggest: r.top.map(e => e.question) };
      S.chat.splice(at < 0 ? S.chat.length : at, at < 0 ? 0 : 1, msg);
      drawChat();
    }, 650 + Math.random() * 350);
  }
  function drawChat() {
    const log = $("#chatLog");
    if (!S.chat.length) S.chat.push({ who: "Control tower", text: `Good morning. Ask me about the forecast, the plant, the milk or the customer records. ${L.meta.disclosure}` });
    log.innerHTML = S.chat.map(m => m.typing ? `<div class="msg bot typing"><span></span><span></span><span></span></div>`
      : m.me ? `<div class="msg me">${esc(m.text)}</div>`
      : `<div class="msg bot"><div class="who">${esc(m.who)}</div>${esc(m.text)}${m.show && SHOW_SCENE[m.show] ? `<div class="mt8"><button class="btn small" data-show-go="${m.show}">Show me</button></div>` : ""}${m.suggest ? `<div class="chips mt8">${m.suggest.map(s => `<button class="chip" data-q="${esc(s)}">${esc(s)}</button>`).join("")}</div>` : ""}</div>`).join("");
    log.scrollTop = log.scrollHeight;
    $$("[data-q]", log).forEach(b => b.onclick = () => ask(b.dataset.q));
    $$("[data-show-go]", log).forEach(b => b.onclick = () => showMe(b.dataset.showGo));
  }
  function showMe(key) {
    closeDrawers();
    const n = SHOW_SCENE[key];
    if (key === "siblings") { if (S.morning === "done") S.sel = "A3"; }
    if (n !== S.scene) go(n); else render();
    setTimeout(() => { const e = $(`[data-show="${key}"]`) || $(`[data-show="forecast"]`); if (e && S.scene === n) { e.scrollIntoView({ behavior: "smooth", block: "center" }); e.classList.add("flash"); } }, 60);
  }
  function chips() {
    const ids = SCENES[S.scene - 1].chips;
    $("#chatChips").innerHTML = ids.filter(id => QA[id]).slice(0, 3).map(id => `<button class="chip" data-q="${esc(QA[id].question)}">${esc(QA[id].question)}</button>`).join("");
    $$("#chatChips [data-q]").forEach(b => b.onclick = () => ask(b.dataset.q));
  }

  /* ------------------------------------------------------------------ drawers, keys, boot */
  function openDrawer(id) {
    closeDrawers();
    $("#" + id).classList.add("open"); $("#scrim").classList.add("show");
    if (id === "chat") { drawChat(); setTimeout(() => $("#chatInput").focus(), 200); }
    if (id === "audit") renderAudit();
  }
  function closeDrawers() { $$(".drawer").forEach(d => d.classList.remove("open")); $("#scrim").classList.remove("show"); }

  document.addEventListener("click", e => {
    const g = e.target.closest("[data-go]");
    if (g && !g.disabled) { go(+g.dataset.go); }
    if (e.target.closest("[data-close]") || e.target.id === "scrim") closeDrawers();
  });
  $("#btnChat").onclick = () => openDrawer("chat");
  $("#btnAudit").onclick = () => openDrawer("audit");
  $("#btnReset").onclick = () => { if (confirm("Reset the demo to the start?")) { EPOCH++; S = initial(); fresh(); closeDrawers(); tick(0); renderAudit(); render(); } };
  $("#chatForm").onsubmit = e => { e.preventDefault(); const i = $("#chatInput"); ask(i.value); i.value = ""; };
  document.addEventListener("keydown", e => {
    if (!document.body.classList.contains("signed-in")) return;
    if (e.target.closest && e.target.closest("input, select, textarea")) return;
    if (e.key === "ArrowRight") go(S.scene + 1);
    if (e.key === "ArrowLeft") go(S.scene - 1);
    if (e.key === "Escape") closeDrawers();
    if (/^[1-6]$/.test(e.key)) go(+e.key);
  });
  let rz;
  window.addEventListener("resize", () => { clearTimeout(rz); rz = setTimeout(render, 150); });
  /* demo admin login: a front door for the presentation, not real security */
  const DEMO_USER = "admin", DEMO_PASS = "Lactalis@2026";
  const signedIn = () => { try { return sessionStorage.getItem("ctUser"); } catch (e) { return null; } };
  function enter(role) {
    document.body.classList.add("signed-in");
    $("#userName").textContent = role === "Administrator" ? "Admin" : role;
    $("#userAv").textContent = role[0];
    $("#btnUser").title = `Signed in as ${role} · sign out`;
  }
  $("#loginPass").value = DEMO_PASS;
  $("#loginForm").onsubmit = e => {
    e.preventDefault();
    const u = $("#loginUser").value.trim().toLowerCase(), p = $("#loginPass").value, role = $("#loginRole").value;
    if (!u || !p) { $("#loginErr").textContent = "Enter a username and password."; return; }
    if (u !== DEMO_USER || p !== DEMO_PASS) { $("#loginErr").textContent = "Username or password is not correct."; $("#loginPass").select(); return; }
    $("#loginErr").textContent = "";
    try { sessionStorage.setItem("ctUser", role); } catch (err) { /* private window: stay signed in for this page only */ }
    enter(role); audit(role, "Signed in to the control tower"); render();
  };
  $("#btnUser").onclick = () => {
    if (!confirm("Sign out?")) return;
    try { sessionStorage.removeItem("ctUser"); } catch (e) { /* ignore */ }
    closeDrawers(); document.body.classList.remove("signed-in");
    $("#loginPass").value = DEMO_PASS; $("#loginErr").textContent = "";
    setTimeout(() => $("#loginPass").focus(), 50);
  };
  if (signedIn()) enter(signedIn()); else setTimeout(() => $(".login-btn").focus(), 50);
  function fresh() { S.decisionTime = {}; S.rejectReason = {}; S.sapRef = {}; }
  fresh();
  renderAudit();
  render();
  window.__route = q => (route(q).best || {}).id || null;
})();
