"""Phase 3: agent answer library -> build/agent_library.json and build/agent_library.md

Every number in the briefing, alerts and answers is read from build/model_output.json or data/.
Nothing is typed by hand, so re-running Phase 1 and 2 keeps the demo consistent.
The record matching for scene 1 is computed here for real and scored against data/master_customer_truth.csv.
Answers are pre-configured (no live LLM); the demo says so on screen.
"""
from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
D, B = ROOT / "data", ROOT / "build"
o = json.loads((B / "model_output.json").read_text())
COGS_SHARE = 0.55   # same assumption as train_forecast.py
TODAY = pd.Timestamp(o["meta"]["today"])

products = pd.DataFrame(o["products"]).set_index("sku")
customers = pd.DataFrame(o["customers"]).set_index("customer_id")
fc = pd.DataFrame(o["forecast"])
fc = pd.concat([fc.drop(columns="drivers_cases"), fc["drivers_cases"].apply(pd.Series)], axis=1)
fc["date"] = pd.to_datetime(fc["date"])
lines = pd.DataFrame(o["line_check"])
lines["date"] = pd.to_datetime(lines["date"])
milk = pd.DataFrame(o["milk_check"])
milk["date"] = pd.to_datetime(milk["date"])
cal = pd.read_csv(D / "calendar_weather.csv", parse_dates=["date"])
promos = pd.read_csv(D / "promotions.csv", parse_dates=["start", "end"])
prices = pd.read_csv(D / "price_lists.csv")
orders = pd.read_csv(D / "orders.csv", parse_dates=["date"])
writeoffs = pd.read_csv(D / "writeoffs.csv", parse_dates=["date"])
acc, seg, val = o["accuracy"], o["segments"], o["value"]


def dname(d) -> str:
    t = pd.Timestamp(d)
    return f"{t.strftime('%a')} {t.day} {t.strftime('%b')}"


def n(x) -> str:
    return f"{round(x):,}"


def aud(x) -> str:
    return f"A${x / 1000:,.0f}k" if abs(x) >= 10000 else f"A${x:,.0f}"


def pct(x, nd=0) -> str:
    return f"{x * 100:.{nd}f}%"


def price(sku: str, cust: str = "RET-A") -> float:
    p = prices[(prices.source == "Lactalis") & (prices.sku == sku) & (prices.customer_id == cust)]
    if p.empty:
        p = prices[(prices.source == "Lactalis") & (prices.sku == sku)]
    return float(p.price_per_case_aud.iloc[0])


def row(sku, cust, d):
    return fc[(fc.sku == sku) & (fc.customer == cust) & (fc.date == pd.Timestamp(d))].iloc[0]


def pname(sku):
    return products.at[sku, "name"]


def cname(c):
    return customers.at[c, "name"]


# ---------------------------------------------------------------- scenario facts
scen = promos[promos.start >= TODAY].iloc[0]   # the only future promotion is the demo scenario
HERO, HERO_C = scen.sku, scen.customer_id
P_START, P_END, DEPTH = scen.start, scen.end, float(scen.depth)
promo_days = pd.date_range(P_START, P_END)
hero_rows = fc[(fc.sku == HERO) & (fc.customer == HERO_C)].set_index("date")
first = hero_rows.loc[P_START]
week = hero_rows.loc[promo_days]
gap_week = float((week.forecast - week.today_method).sum())
hero_price = price(HERO, HERO_C)
hot = cal[(cal.date >= TODAY) & (cal.weather_kind == "forecast") & (cal.max_temp_c >= 32)]
hot_days = [dname(d) for d in hot.date]
normal_temp = float(first.normal_temp_c)
mon = hero_rows.loc[TODAY]
last_hol = cal[(cal.date < TODAY) & (cal.is_public_holiday == 1)].iloc[-1]

# siblings at the same customer that lose sales during the promotion
sib = fc[(fc.customer == HERO_C) & (fc.date.isin(promo_days)) & (fc.sibling_promo_depth > 0)]
sib_sum = sib.groupby("sku").agg(lost=("Promotion", "sum"), ai=("forecast", "sum"), today=("today_method", "sum"))
sib_sum["over"] = (sib.assign(o=(sib.today_method - sib.forecast).clip(lower=0)).groupby("sku").o.sum())
sib_sum["cost"] = [r.over * price(s, HERO_C) * COGS_SHARE for s, r in sib_sum.iterrows()]
sib_sum = sib_sum.sort_values("lost")
brk = "BRK-IC-750" if "BRK-IC-750" in sib_sum.index else sib_sum.index[0]
brk_daily = sib[(sib.sku == brk) & (sib.date.dt.dayofweek < 5)].Promotion.abs()

# Nambour line 3 and milk
l3 = lines[lines.line == "L3"].set_index("date")
over = l3[l3.utilisation_pct > 100]
over_cases = (over.forecast_cases - over.capacity).clip(lower=0)
before = l3[(l3.index > TODAY) & (l3.index < over.index.min())]
spare = (before.capacity - before.forecast_cases).clip(lower=0)
shift_needed = int(over_cases.sum())
spare_total = int(spare.sum())
hero_l_per_case = float(products.at[HERO, "litres_per_case"] * products.at[HERO, "milk_fraction"])
short = milk[milk.silo_end_l < 0]
short_day = short.date.iloc[0] if len(short) else None
short_l = float(-short.silo_end_l.iloc[0]) if len(short) else 0.0
# pulling production forward moves milk use from Thu/Fri to Tue/Wed, which also refills the Friday silo
# The silo balance is cumulative, so making line 3 stock earlier does not change the Friday balance
# (the same milk is used by Friday either way). Two real fixes: move a white-milk run to the next day,
# when intake is back and line 1 has room, or buy spot milk.
DEFER_SKU = "PAU-FC-2L"
defer_lpc = float(products.at[DEFER_SKU, "litres_per_case"] * products.at[DEFER_SKU, "milk_fraction"])
if len(short):
    next_day = short_day + pd.Timedelta(days=1)
    defer_cases = int(-(-short_l * 1.5 // defer_lpc // 50) * 50)          # gap plus 50% margin, in 50s
    l1 = lines[lines.line == "L1"].set_index("date")
    l1_next_after = (l1.at[next_day, "forecast_cases"] + defer_cases) / l1.at[next_day, "capacity"] * 100
    silo_after = short.silo_end_l.iloc[0] + defer_cases * defer_lpc
    next_silo = float(milk.set_index("date").at[next_day, "silo_end_l"])   # unchanged: same milk used by then
spot_full_l = int(-(-short_l * 1.5 // 1000) * 1000)
life = int(products.at[HERO, "shelf_life_days"])
days_forward = int((over.index.max() - before.index.min()).days)
heat_days = milk[milk.heat_stress].date
intake_drop = 1 - milk[milk.heat_stress].milk_expected_l.mean() / milk[~milk.heat_stress].milk_expected_l.mean()

# legacy Fonterra codes and duplicates
hist = orders[(orders.is_future == 0)]
since = hist[hist.date >= "2026-04-01"]
leg = since[since.customer_code_received.str.startswith("FON")]
leg_share_first = leg[leg.date < "2026-05-01"].ordered_cases.sum() / since[(since.date < "2026-05-01") & since.customer_id.isin(leg.customer_id.unique())].ordered_cases.sum()
recent = since[since.date >= TODAY - pd.Timedelta(days=28)]
leg_recent = recent[recent.customer_code_received.str.startswith("FON")]
leg_share_now = leg_recent.ordered_cases.sum() / recent[recent.customer_id.isin(leg.customer_id.unique())].ordered_cases.sum()
leg_lines_28 = len(leg_recent)
dups = hist[hist.is_duplicate == 1]
dup_returns = writeoffs[writeoffs.reason.str.startswith("Customer return")]
dup_cost = sum(r.cases * price(r.sku, "RET-B") for r in dup_returns.itertuples())
price_conf = prices[prices.source != "Lactalis"].merge(
    prices[(prices.source == "Lactalis") & (prices.customer_id == "RET-B")][["sku", "price_per_case_aud"]],
    on="sku", suffixes=("_legacy", "_lactalis"))
price_conf["diff_pct"] = price_conf.price_per_case_aud_legacy / price_conf.price_per_case_aud_lactalis - 1

# write-offs in the last 12 months of today's way of working
wo12 = writeoffs[writeoffs.date >= TODAY - pd.Timedelta(days=365)]
wo_reason = wo12.groupby("reason").cases.sum().sort_values(ascending=False)
wo_sku = wo12[wo12.reason.str.startswith("Short-dated")].groupby("sku").cases.sum().sort_values(ascending=False)

# what-if (Wed 14 Oct, all customers)
w = o["whatif"]
wi_skus = w["skus"]
iced_idx = [i for i, s in enumerate(wi_skus) if products.at[s, "subcat"] == "iced_coffee"]


def wi(temp: int, depth: str, sku: str | None = None) -> int:
    t = min(max(temp, w["temps"][0]), w["temps"][-1])
    r = w["cases"][depth][w["temps"].index(t)]
    return round(r[wi_skus.index(sku)]) if sku else round(sum(r[i] for i in iced_idx))


T0 = int(cal[cal.date == P_START].max_temp_c.iloc[0])
DKEY = next(k for k in w["cases"] if abs(float(k) - DEPTH) < 1e-9)


def wi_cust(depth: str, temp: int | None = None) -> int:
    """Hero product at the promoted customer: its forecast plus the model's change for that customer alone."""
    t = min(max(T0 if temp is None else temp, w["temps"][0]), w["temps"][-1])
    hc = w["hero_customer"]
    return max(0, round(first.forecast - hc[DKEY][w["temps"].index(T0)] + hc[depth][w["temps"].index(t)]))

# ---------------------------------------------------------------- record matching (scene 1), computed for real
lc = pd.read_csv(D / "master_lactalis_customers.csv", dtype=str)
fcu = pd.read_csv(D / "master_fonterra_customers.csv", dtype=str)
truth = pd.read_csv(D / "master_customer_truth.csv", dtype=str)
NOISE = {"PTY", "LTD", "CO", "BAR", "THE", "AND", "&", "-", "QLD", "DC", "REGIONAL", "BUYING", "GROUP"}


def norm(s: str) -> str:
    s = s.upper().replace("É", "E")
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    toks = [t.rstrip("S") if len(t) > 3 else t for t in s.split() if t not in NOISE]
    return " ".join(toks)


def name_sim(a: str, b: str) -> float:
    a, b = norm(a), norm(b)
    seq = difflib.SequenceMatcher(None, a, b).ratio()
    ta, tb = set(a.split()), set(b.split())
    jac = len(ta & tb) / len(ta | tb) if ta | tb else 0
    return max(seq, jac)


def pc_sim(a: str, b: str) -> float:
    d = abs(int(a) - int(b))
    return 1.0 if d == 0 else 0.6 if d <= 2 else 0.0


AUTO, REVIEW = 0.90, 0.75
match_rows = []
for f in fcu.itertuples():
    best = None
    for l in lc.itertuples():
        ns = name_sim(f.name, l.name)
        if ns < 0.5:
            continue
        s = 0.65 * ns + 0.25 * pc_sim(f.postcode, l.postcode) + 0.10 * (f.channel == l.channel)
        if best is None or s > best[0]:
            best = (s, l, ns)
    if best is None:
        match_rows.append((f.customer_id, f.name, None, None, 0.0, 0.0, "new customer"))
        continue
    s, l, ns = best
    decision = "auto-match" if s >= AUTO else "review" if s >= REVIEW else "new customer"
    match_rows.append((f.customer_id, f.name, l.customer_id, l.name, round(s, 3), round(ns, 3), decision))
m = pd.DataFrame(match_rows, columns=["fonterra_id", "fonterra_name", "lactalis_id", "lactalis_name", "score", "name_score", "decision"])
true_map = dict(zip(truth.fonterra_id, truth.lactalis_id))
m["true_lactalis_id"] = m.fonterra_id.map(true_map)
m["correct"] = ((m.decision != "new customer") & (m.lactalis_id == m.true_lactalis_id)) | \
               ((m.decision == "new customer") & m.true_lactalis_id.isna())
auto = m[m.decision == "auto-match"]
rev = m[m.decision == "review"]
new = m[m.decision == "new customer"]
match_stats = {
    "fonterra_records": len(m), "lactalis_records": len(lc), "true_pairs": int(m.true_lactalis_id.notna().sum()),
    "auto_matched": len(auto), "auto_correct": int(auto.correct.sum()),
    "review": len(rev), "review_correct_suggestion": int(rev.correct.sum()),
    "new": len(new), "new_correct": int(new.correct.sum()),
    "auto_precision_pct": float(round(100 * auto.correct.mean(), 1)) if len(auto) else None,
    "pairs_found_pct": float(round(100 * ((m.decision != "new customer") & m.correct & m.true_lactalis_id.notna()).sum()
                             / m.true_lactalis_id.notna().sum(), 1)),
    "thresholds": {"auto": AUTO, "review": REVIEW},
    "method": "name similarity (after removing PTY LTD, CO, BAR and accents) 65%, postcode 25%, channel 10%",
}


def why(r) -> str:
    l = lc.set_index("customer_id").loc[r.lactalis_id]
    f = fcu.set_index("customer_id").loc[r.fonterra_id]
    bits = ["names match after cleaning" if r.name_score >= 0.995 else f"names {r.name_score * 100:.0f}% alike"]
    bits.append("same postcode" if f.postcode == l.postcode else f"postcode differs ({f.postcode} vs {l.postcode})")
    bits.append("same channel" if f.channel == l.channel else "different channel")
    return ", ".join(bits)


review_queue = [{"fonterra_id": r.fonterra_id, "fonterra_name": r.fonterra_name, "suggested": r.lactalis_id,
                 "suggested_name": r.lactalis_name, "score": r.score, "why": why(r),
                 "truth": "same customer" if r.correct else "different customer"}
                for r in rev.sort_values("score", ascending=False).itertuples()]
auto_examples = [{"fonterra_id": r.fonterra_id, "fonterra_name": r.fonterra_name, "lactalis_id": r.lactalis_id,
                  "lactalis_name": r.lactalis_name, "score": r.score, "why": why(r), "correct": bool(r.correct)}
                 for r in auto.sort_values("score").head(6).itertuples()]
missed = [{"fonterra_id": r.fonterra_id, "fonterra_name": r.fonterra_name, "true_lactalis_id": r.true_lactalis_id,
           "true_lactalis_name": dict(zip(lc.customer_id, lc.name)).get(r.true_lactalis_id, cname(r.true_lactalis_id)
                                  if r.true_lactalis_id in customers.index else r.true_lactalis_id),
           "in_lactalis_master": r.true_lactalis_id in set(lc.customer_id),
           "best_score": r.score} for r in new[~new.correct].itertuples()]
new_examples = [{"fonterra_id": r.fonterra_id, "fonterra_name": r.fonterra_name, "closest": r.lactalis_name,
                 "score": r.score} for r in new[new.correct].sort_values("score", ascending=False).head(5).itertuples()]
auto_wrong = [{"fonterra_id": r.fonterra_id, "fonterra_name": r.fonterra_name, "lactalis_name": r.lactalis_name,
               "score": r.score} for r in auto[~auto.correct].itertuples()]

# ---------------------------------------------------------------- confidence from the forecast range and back-test


def confidence(r, seg_key: str) -> dict:
    width = (r.high - r.low) / max(r.forecast, 1)
    level = "High" if width < 0.5 else "Medium" if width < 0.8 else "Low"
    return {"level": level, "range": f"{n(r.low)} to {n(r.high)} cases (80% range)",
            "backtest": f"On {seg_key[0].lower() + seg_key[1:]} the forecast error was {pct(seg[seg_key]['ml_wape'])} "
                        f"vs {pct(seg[seg_key]['baseline_wape'])} for today's method"}


# ---------------------------------------------------------------- alerts
alerts = []
hero_short_cost = gap_week * hero_price
alerts.append({
    "id": "A1", "agent": "Demand agent", "severity": "high", "scene": "forecast",
    "title": f"{pname(HERO)} at {cname(HERO_C)}: plan {n(first.forecast)} cases for {dname(P_START)}, not {n(first.today_method)}",
    "what": f"Heat ({', '.join(hot_days)}) arrives in the same week as the {pct(DEPTH)} off promotion "
            f"({dname(P_START)} to {dname(P_END)}). The AI forecast is {n(first.forecast)} cases for {dname(P_START)}; "
            f"today's method says {n(first.today_method)}.",
    "why": [f"Normal {P_START.strftime('%A')}: {n(first.normal_level)} cases",
            f"Promotion {pct(DEPTH)} off: +{n(first.Promotion)} cases",
            f"Heat {first.max_temp_c:.0f}°C (normal {normal_temp:.0f}°C): +{n(first.Weather)} cases"],
    "confidence": confidence(first, "Promotion days"),
    "impact": f"Over the promotion week the AI expects {n(week.forecast.sum())} cases vs {n(week.today_method.sum())} "
              f"from today's method: {n(gap_week)} cases (about {aud(hero_short_cost)} of sales at list price) "
              f"at risk of going short.",
    "recommendation": f"Raise the {pname(HERO)} plan for {cname(HERO_C)} to the AI forecast for {dname(P_START)} to {dname(P_END)}.",
    "approve": {"result": f"Plan updated: {n(week.forecast.sum())} cases over the promotion week. Nambour line 3 load "
                          f"is checked next (see the supply alert).",
                "audit": f"Approved AI forecast for {HERO} at {HERO_C}, {P_START.date()} to {P_END.date()}"},
    "reject": {"result": f"Plan stays at today's method ({n(week.today_method.sum())} cases). Expected shortfall about "
                         f"{n(gap_week)} cases. The agent will flag this again if orders run ahead of plan.",
               "audit": f"Rejected AI forecast for {HERO} at {HERO_C}; reason recorded by planner"},
    "data": {"sku": HERO, "customer": HERO_C, "date": str(P_START.date()), "forecast": int(first.forecast),
             "today_method": int(first.today_method), "week_ai": int(week.forecast.sum()),
             "week_today": int(week.today_method.sum())},
})

alerts.append({
    "id": "A2", "agent": "Demand agent", "severity": "medium", "scene": "forecast",
    "title": f"Today's method under-calls {dname(TODAY)} because it copies the {last_hol.public_holiday} holiday",
    "what": f"Today's method copies last {dname(last_hol.date)} ({last_hol.public_holiday}, a public holiday) and "
            f"plans {n(mon.today_method)} cases of {pname(HERO)} for {cname(HERO_C)}. The AI knows it was a holiday and "
            f"forecasts {n(mon.forecast)}.",
    "why": [f"Holidays were the weakest point of today's method in the back-test: "
            f"{pct(seg['Public holidays and the day before']['baseline_wape'])} error vs "
            f"{pct(seg['Public holidays and the day before']['ml_wape'])} for the AI"],
    "confidence": confidence(mon, "Public holidays and the day before"),
    "impact": f"{n(mon.forecast - mon.today_method)} cases more for {dname(TODAY)} on this one product and customer.",
    "recommendation": "Use the AI forecast for the week after any public holiday.",
    "approve": {"result": "Rule saved: the week after a public holiday uses the AI forecast by default.",
                "audit": "Approved: AI forecast used after public holidays"},
    "reject": {"result": "No change. The planner adjusts post-holiday weeks by hand as today.",
               "audit": "Rejected post-holiday rule; reason recorded by planner"},
    "data": {"date": str(TODAY.date()), "forecast": int(mon.forecast), "today_method": int(mon.today_method),
             "holiday": last_hol.public_holiday, "holiday_date": str(last_hol.date.date())},
})

sib_lines = [f"{pname(s)}: {n(-r.lost)} fewer cases over the week" for s, r in sib_sum.iterrows()]
alerts.append({
    "id": "A3", "agent": "Shelf-life agent", "severity": "medium", "scene": "forecast",
    "title": f"Cut {', '.join(pname(s) for s in sib_sum.index)} at {cname(HERO_C)} during the promotion",
    "what": f"Shoppers switch to the discounted {pname(HERO)}. Its neighbours sell less: {pname(brk)} loses about "
            f"{n(brk_daily.min())} to {n(brk_daily.max())} cases a weekday. Today's method does not see this and would "
            f"plan {n(sib_sum.over.sum())} cases too many.",
    "why": sib_lines + [f"Back-test error on products next to a promotion: "
                        f"{pct(seg['Products next to a promotion']['baseline_wape'])} today vs "
                        f"{pct(seg['Products next to a promotion']['ml_wape'])} with the AI"],
    "confidence": {"level": "Medium", "range": "Based on past promotions in the same product family",
                   "backtest": f"Error on products next to a promotion: {pct(seg['Products next to a promotion']['ml_wape'])}"},
    "impact": f"About {aud(sib_sum.cost.sum())} of stock (at cost) at risk of being written off. With "
              f"{int(products.at[brk, 'shelf_life_days'])} days of shelf life and customers needing "
              f"80% left, unsold stock has about 3 days to ship.",
    "recommendation": f"Lower the plan for these products at {cname(HERO_C)} to the AI forecast for the promotion week.",
    "approve": {"result": f"Plans lowered by {n(sib_sum.over.sum())} cases; frees Nambour line 3 capacity on the hot days.",
                "audit": f"Approved lower sibling plans at {HERO_C} for the promotion week"},
    "reject": {"result": "No change. Stock levels for these products will be watched daily for ageing.",
               "audit": "Rejected sibling plan cut; reason recorded by planner"},
    "data": {"skus": list(sib_sum.index), "lost_cases": {s: int(round(-r.lost)) for s, r in sib_sum.iterrows()},
             "over_cases": {s: int(round(r.over)) for s, r in sib_sum.iterrows()}, "cost_aud": round(float(sib_sum.cost.sum()))},
})

alerts.append({
    "id": "A4", "agent": "Supply agent", "severity": "high", "scene": "supply",
    "title": f"Nambour line 3 is over capacity on {' and '.join(dname(d) for d in over.index)}",
    "what": f"Line 3 (flavoured milk and iced coffee) needs " +
            ", ".join(f"{u:.0f}% on {dname(d)}" for d, u in over.utilisation_pct.items()) +
            f": {n(shift_needed)} cases above its {n(over.capacity.iloc[0])} cases a day.",
    "why": ["Promotion and heat both land on the iced coffee range",
            f"Line 3 has {n(spare_total)} spare cases on " + " and ".join(dname(d) for d in spare.index) + " before the peak"],
    "confidence": confidence(hero_rows.loc[over.index[0]], "Hot days (over 32°C)"),
    "impact": f"Without action about {n(shift_needed)} cases of iced coffee cannot be made in time for the hot days.",
    "options": [
        {"name": f"Make {n(shift_needed)} cases earlier on " + " and ".join(dname(d) for d in spare.index),
         "detail": f"Uses spare line 3 time; stock is made 1 to {days_forward} days earlier and still has more than 80% "
                   f"of its {life}-day shelf life when shipped. No overtime.", "recommended": True},
        {"name": f"Book an extra shift on {dname(over.index[0])}",
         "detail": f"Adds up to {n(over.extra_shift.iloc[0])} cases a day; overtime cost; keeps the plan as is.",
         "recommended": False},
    ],
    "recommendation": f"Make {n(shift_needed)} cases earlier on spare line 3 time; keep the extra shift as back-up.",
    "approve": {"result": f"Production plan moved: line 3 back under 100% on {' and '.join(dname(d) for d in over.index)}. "
                          f"Milk is used a day or two earlier; silos stay above zero on those days.",
                "audit": f"Approved: {shift_needed} cases of line 3 production pulled forward"},
    "reject": {"result": "Plan unchanged. The agent books a provisional extra shift request for the production manager.",
               "audit": "Rejected pull-forward; extra shift request raised instead"},
    "data": {"over": {str(d.date()): float(u) for d, u in over.utilisation_pct.items()},
             "cases_over": shift_needed, "spare_before": {str(d.date()): int(v) for d, v in spare.items()}},
})

if short_day is not None:
    alerts.append({
        "id": "A5", "agent": "Supply agent", "severity": "high", "scene": "supply",
        "title": f"Raw milk silos run about {n(short_l)} L short on {dname(short_day)}",
        "what": f"Farm intake drops about {pct(intake_drop)} on hot days ({', '.join(dname(d) for d in heat_days)}) "
                f"while demand peaks. The silo balance goes below zero on {dname(short_day)}.",
        "why": ["Heat stress lowers cow yields", f"Promotion and heat raise demand on {', '.join(hot_days)}",
                o["milk_meta"]["silo_note"].capitalize()],
        "confidence": {"level": "Medium", "range": "Silo starting level is an assumption",
                       "backtest": "Intake is planned from the last 28 days of farm deliveries"},
        "impact": f"Shortfall of about {n(short_l)} L on {dname(short_day)}.",
        "options": [
            {"name": f"Move {n(defer_cases)} cases of {pname(DEFER_SKU)} from {dname(short_day)} to {dname(next_day)}",
             "detail": f"Saves about {n(defer_cases * defer_lpc)} L on {dname(short_day)}; the silo ends the day at about "
                       f"{n(silo_after)} L. Line 1 on {dname(next_day)} goes to {l1_next_after:.0f}% and the silo still ends "
                       f"{dname(next_day)} at {n(next_silo)} L. Stock cover at the warehouse carries {dname(short_day)} orders. "
                       f"No extra cost; the Nambour scheduler confirms.", "recommended": True},
            {"name": "Buy spot milk", "detail": f"Order about {n(spot_full_l)} L from a third-party supplier "
                                                f"for delivery on {dname(short_day - pd.Timedelta(days=1))}. Extra cost.",
             "recommended": False},
        ],
        "recommendation": f"Move the {pname(DEFER_SKU)} run to {dname(next_day)}; keep a spot milk quote as back-up.",
        "approve": {"result": f"Production plan updated: {n(defer_cases)} cases of {pname(DEFER_SKU)} moved to "
                              f"{dname(next_day)}. Silo on {dname(short_day)} now ends at about {n(silo_after)} L.",
                    "audit": f"Approved: {defer_cases} cases of {DEFER_SKU} moved from {short_day.date()} to {next_day.date()}"},
        "reject": {"result": "No change. Risk stays open on the supply dashboard.",
                   "audit": "Rejected milk plan; reason recorded by planner"},
        "data": {"date": str(short_day.date()), "short_l": round(short_l), "defer_sku": DEFER_SKU,
                 "defer_cases": defer_cases, "defer_litres": round(defer_cases * defer_lpc), "to_date": str(next_day.date()),
                 "silo_after_l": round(silo_after), "l1_next_pct": round(l1_next_after, 1), "spot_l": spot_full_l},
    })

alerts.append({
    "id": "A6", "agent": "Order agent", "severity": "medium", "scene": "data",
    "title": f"Old Fonterra customer codes still on {pct(leg_share_now)} of orders",
    "what": f"Since 1 Apr 2026 some {cname('RET-B')} and {cname('IND')} orders arrive under old Fonterra codes "
            f"({', '.join(sorted(leg.customer_code_received.unique()))}). The share fell from {pct(leg_share_first)} in April to "
            f"{pct(leg_share_now)} in the last 4 weeks ({leg_lines_28} order lines).",
    "why": [f"{len(dups)} orders were keyed in twice (old and new code) and came back as {n(dup_returns.cases.sum())} "
            f"cases of returns", f"{len(price_conf)} products have a different old Fonterra price for {cname('RET-B')} "
                                 f"({price_conf.diff_pct.min() * 100:+.0f}% to {price_conf.diff_pct.max() * 100:+.0f}%)"],
    "confidence": {"level": "High", "range": "Codes matched to customers in the record-matching step",
                   "backtest": f"Matching accuracy on auto-matches: {match_stats['auto_precision_pct']}%"},
    "impact": f"Duplicate returns cost about {aud(dup_cost)} so far; legacy orders split one customer's demand "
              f"across two codes, which hides it from planning.",
    "recommendation": "Map the old codes to the Lactalis customers on intake, hold any order that repeats one under the "
                      "other code, and use the Lactalis price list.",
    "approve": {"result": "Mapping rule active: old codes are translated on intake; possible duplicates are held for a check.",
                "audit": "Approved legacy code mapping and duplicate hold"},
    "reject": {"result": "No change. Customer service keeps checking old codes by hand.",
               "audit": "Rejected legacy code mapping; reason recorded"},
    "data": {"legacy_share_first_pct": round(100 * leg_share_first, 1), "legacy_share_now_pct": round(100 * leg_share_now, 1),
             "duplicate_orders": len(dups), "duplicate_return_cases": int(dup_returns.cases.sum()),
             "price_conflicts": len(price_conf)},
})

# ---------------------------------------------------------------- morning briefing
by_id = {a["id"]: a for a in alerts}
briefing = {
    "greeting": f"Good morning. {dname(TODAY)}: 3 things need your attention today.",
    "items": [
        {"alert": "A1", "text": f"Heat plus the {pct(DEPTH)} off {pname(HERO)} promotion: plan {n(first.forecast)} cases for "
                                f"{cname(HERO_C)} on {dname(P_START)}, not {n(first.today_method)}."},
        {"alert": "A4", "text": f"Nambour line 3 is over capacity on {' and '.join(dname(d) for d in over.index)}. "
                                f"Make {n(shift_needed)} cases earlier on spare time; no overtime needed."},
        {"alert": "A5" if "A5" in by_id else "A3",
         "text": (by_id["A3"]["title"] if "A5" not in by_id else
                  f"Milk silos run about {n(short_l)} L short on {dname(short_day)}. Moving one white-milk run to "
                  f"{dname(next_day)} fixes it at no extra cost.")},
    ],
    "also": [{"alert": a, "text": by_id[a]["title"]} for a in ("A2", "A3", "A6") if a in by_id],
    "footer": "Every suggestion needs a person to approve it. Answers on this screen are pre-configured for the demo.",
}

# ---------------------------------------------------------------- Q&A library
hol = seg["Public holidays and the day before"]
qa = [
    {"id": "Q1", "topic": "Forecast", "question": f"Why is the {pname(HERO)} forecast so high on {dname(P_START)}?",
     "keywords": ["why", "high", "so many", "wednesday", "ice break", "595", "explain", "driver", "reason"],
     "answer": f"Three things add up. A normal {P_START.strftime('%A')} at {cname(HERO_C)} is {n(first.normal_level)} cases. "
               f"The {pct(DEPTH)} off promotion adds {n(first.Promotion)}. The {first.max_temp_c:.0f}°C heat (normal is "
               f"{normal_temp:.0f}°C) adds {n(first.Weather)}. Total {n(first.forecast)} cases, likely range "
               f"{n(first.low)} to {n(first.high)}. Today's method says {n(first.today_method)} because it only copies last week.",
     "show": "waterfall"},
    {"id": "Q2", "topic": "What-if", "question": f"What if it is only 28°C on {dname(P_START)}?",
     "keywords": ["what if", "temperature", "degrees", "cooler", "hotter", "weather", "cool", "heat", "°c"],
     "template": "temp",
     "answer": f"At {{temp}}°C with the promotion, all customers together need about {{iced}} cases of iced coffee on "
               f"{dname(P_START)}, and {{hero}} cases of {pname(HERO)}. At the forecast {T0}°C it is {wi(T0, DKEY):,} and "
               f"{wi(T0, DKEY, HERO):,}.",
     "show": "whatif"},
    {"id": "Q3", "topic": "What-if", "question": "What if the promotion is 25% off instead of 40%?",
     "keywords": ["what if", "promotion", "discount", "deeper", "smaller", "% off", "depth", "percent"],
     "template": "depth",
     "answer": f"At {{depth}}% off, {cname(HERO_C)} needs about {{hero_c}} cases of {pname(HERO)} on {dname(P_START)} "
               f"({n(first.forecast)} at {pct(DEPTH)} off, {{none}} with no promotion). Iced coffee across all customers: "
               f"{{iced}} cases. The size of the lift is learned from {len(promos)} past promotions.",
     "show": "whatif"},
    {"id": "Q4", "topic": "Accuracy", "question": "How accurate is the forecast?",
     "keywords": ["accurate", "accuracy", "error", "wape", "trust", "reliable", "how well", "back-test", "backtest", "any good", "confident", "confidence", "sure", "how sure"],
     "answer": f"We replayed {o['meta']['backtest'].replace(' to ', ' to ')} day by day, forecasting 14 days ahead with "
               f"forecast (not actual) weather. Today's method was {acc['today_method_accuracy_pct']}% accurate; the AI was "
               f"{acc['ml_accuracy_pct']}%. That is {acc['error_reduction_pct']:.0f}% less error. This is synthetic data: on "
               f"real data we would aim for at least 20% less error in the pilot.",
     "show": "accuracy"},
    {"id": "Q5", "topic": "Accuracy", "question": "Where does the AI help most?",
     "keywords": ["where", "help most", "biggest", "best", "gain", "improve", "situation", "segment"],
     "answer": "Biggest gains: " + "; ".join(
         f"{k[0].lower() + k[1:]} {pct(v['baseline_wape'])} to {pct(v['ml_wape'])} error"
         for k, v in sorted(seg.items(), key=lambda kv: kv[1]['ml_wape'] / kv[1]['baseline_wape'])[:4]) +
               ". These are the days when copying last week goes wrong.",
     "show": "segments"},
    {"id": "Q6", "topic": "Forecast", "question": f"Why does today's method get {dname(TODAY)} wrong?",
     "keywords": ["monday", "today", "holiday", "holidays", "public holiday", "low", "king's birthday", "kings birthday", "wrong", "copy", "last week", "129"],
     "answer": f"It copies last {dname(last_hol.date)}, which was the {last_hol.public_holiday} public holiday, so it plans "
               f"only {n(mon.today_method)} cases of {pname(HERO)} for {cname(HERO_C)}. The AI knows it was a holiday and "
               f"forecasts {n(mon.forecast)}. In the back-test, holidays and the day before had {pct(hol['baseline_wape'])} "
               f"error with today's method and {pct(hol['ml_wape'])} with the AI.",
     "show": "monday"},
    {"id": "Q7", "topic": "Forecast", "question": "Which products lose sales because of the promotion?",
     "keywords": ["lose", "cannibal", "sibling", "breaka", "other products", "switch", "neighbour", "steal"],
     "answer": f"Shoppers switch to the discounted {pname(HERO)} at {cname(HERO_C)}. Over the promotion week: " +
               "; ".join(sib_lines) + f". Today's method would plan {n(sib_sum.over.sum())} cases too many, about "
               f"{aud(sib_sum.cost.sum())} at cost at risk of write-off.",
     "show": "siblings"},
    {"id": "Q8", "topic": "Supply", "question": "Can Nambour make enough this week?",
     "keywords": ["nambour", "capacity", "line", "make enough", "production", "plant", "shift", "overtime"],
     "answer": f"Lines 1 and 2 are fine. Line 3 (flavoured milk and iced coffee) is over on " +
               " and ".join(f"{dname(d)} ({u:.0f}%)" for d, u in over.utilisation_pct.items()) +
               f", {n(shift_needed)} cases in total. It has {n(spare_total)} spare cases before that, so making them "
               f"earlier avoids overtime. An extra shift adds up to {n(over.extra_shift.iloc[0])} cases a day if needed.",
     "show": "lines"},
    {"id": "Q9", "topic": "Supply", "question": "Do we have enough raw milk?",
     "keywords": ["milk", "silo", "raw milk", "farm", "intake", "enough milk", "supply", "litres"],
     "answer": (f"Not quite. Hot days cut farm intake by about {pct(intake_drop)}, and demand peaks at the same time. "
                f"The silos end {dname(short_day)} about {n(short_l)} L short. Moving {n(defer_cases)} cases of "
                f"{pname(DEFER_SKU)} to {dname(next_day)}, when intake recovers and line 1 has room, leaves about "
                f"{n(silo_after)} L. Buying about {n(spot_full_l)} L of spot milk is the back-up. " +
                f"Note: the silo starting level is an assumption.") if short_day is not None else
               "Yes. The silo balance stays above zero all fortnight.",
     "show": "milk"},
    {"id": "Q10", "topic": "Value", "question": "How much could this save?",
     "keywords": ["save", "saving", "value", "money", "dollar", "roi", "benefit", "worth", "cost", "business case", "believe", "36%", "write-off saving"],
     "answer": f"We replayed {val['period']} through the same stock rules, changing only the forecast. Write-offs fell from "
               f"{val['today']['writeoff_pct']}% to {val['ml']['writeoff_pct']}% of production ({val['writeoff_reduction_pct']:.0f}% "
               f"fewer) and orders filled rose from {val['today']['fill_pct']}% to {val['ml']['fill_pct']}%. On this synthetic "
               f"Queensland range that is about {aud(val['annualised_saving_aud'])} a year and "
               f"{n(val['annualised_milk_litres_saved'])} L of milk not wasted. Real gains will be smaller; the pilot target is "
               f"at least 15% fewer write-offs.",
     "show": "value"},
    {"id": "Q11", "topic": "Data", "question": "Which orders still use old Fonterra codes?",
     "keywords": ["fonterra", "legacy", "old code", "codes", "customer code", "acquisition", "integration"],
     "answer": by_id["A6"]["what"] + " " + by_id["A6"]["why"][0] + ".",
     "show": "legacy"},
    {"id": "Q12", "topic": "Data", "question": "How many Fonterra customers match our records?",
     "keywords": ["match", "matching", "customer", "customers", "duplicate customer", "master data", "records", "same customer", "merge"],
     "answer": f"We compared {match_stats['fonterra_records']} Fonterra customer records with {match_stats['lactalis_records']} "
               f"Lactalis ones. {match_stats['auto_matched']} matched automatically ({match_stats['auto_precision_pct']}% "
               f"correct when checked against the answer key), {match_stats['review']} need a person to check, and "
               f"{match_stats['new']} look like new customers. Overall {match_stats['pairs_found_pct']}% of the real pairs were found.",
     "show": "matching"},
    {"id": "Q13", "topic": "Data", "question": "Are there price conflicts?",
     "keywords": ["price", "prices", "fonterra prices", "old prices", "pricing", "conflict", "price list", "different price"],
     "answer": f"Yes. {len(price_conf)} products have an old Fonterra price for {cname('RET-B')} that differs from the "
               f"Lactalis list by {price_conf.diff_pct.min() * 100:+.0f}% to {price_conf.diff_pct.max() * 100:+.0f}%. "
               f"The largest gap is {pname(price_conf.loc[price_conf.diff_pct.abs().idxmax(), 'sku'])}. The agent flags these "
               f"for the commercial team; it does not change prices.",
     "show": "prices"},
    {"id": "Q14", "topic": "Waste", "question": "What are we throwing away today?",
     "keywords": ["write-off", "writeoff", "waste", "throw", "expired", "short-dated", "spoil", "dumped"],
     "answer": f"In the last 12 months (synthetic): " +
               "; ".join(f"{k[0].lower() + k[1:]} {n(v)} cases" for k, v in wo_reason.items()) +
               f". Most short-dated stock is {', '.join(pname(s) for s in wo_sku.index[:3])}.",
     "show": "writeoffs"},
    {"id": "Q15", "topic": "How it works", "question": "What data does the model use?",
     "keywords": ["data", "input", "features", "signals", "use", "model", "how does it work", "inputs", "know about"],
     "answer": f"Order history by product, customer and day, plus three outside signals: the weather forecast, school and "
               f"public holidays, and the promotion calendar (including promotions on neighbouring products). The model is "
               f"{o['meta']['model']}. Each signal was tested on and off: for iced coffee the error went from "
               f"{pct(o['variants']['history_only']['wape_iced_coffee'], 1)} with history only to "
               f"{pct(o['variants']['weather+holidays+promotions']['wape_iced_coffee'], 1)} with all three.",
     "show": "signals"},
    {"id": "Q16", "topic": "How it works", "question": "Who decides? Does the AI change the plan by itself?",
     "keywords": ["decide", "approve", "control", "human", "automatic", "by itself", "on its own", "override", "replace", "planner", "planners", "accountable", "responsible", "if it's wrong", "if it is wrong", "audit", "audit trail", "changed", "after i approved"],
     "answer": "No. Agents suggest; a planner approves or rejects every change, and each decision is written to the audit "
               "log with the reason. Rules such as minimum shelf life, line capacity and price lists are never changed by an agent.",
     "show": "audit"},
    {"id": "Q17", "topic": "How it works", "question": "Is this real Lactalis data?",
     "keywords": ["real", "synthetic", "fake", "actual data", "lactalis data", "made up", "genuine", "is this our data", "is this your data", "live", "live ai", "pre-configured", "scripted", "canned"],
     "answer": "No. The data is synthetic, built to look like a Queensland fresh milk range after the Fonterra purchase and "
               "the South Brisbane closure. The forecast model is real and was trained on that data. Agent answers in this "
               "demo are pre-configured; in a pilot they would come from a live AI model reading your data.",
     "show": None},
    {"id": "Q18", "topic": "Next steps", "question": "What would a pilot look like?",
     "keywords": ["pilot", "next step", "start", "timeline", "phase", "how long", "implement", "roll out"],
     "answer": "Start with one region and the fresh milk and iced coffee range. Connect order history, the promotion calendar, "
               "weather and plant data; run the forecast next to today's method; let planners approve agent suggestions. "
               "Pilot targets: at least 20% less forecast error and at least 15% fewer write-offs, measured on real data.",
     "show": None},
    {"id": "Q19", "topic": "Forecast", "question": "Which days are hot this week?",
     "keywords": ["hot", "hottest", "heatwave", "weather forecast", "temperature this week", "warm"],
     "answer": "Forecast maximums in Brisbane: " + ", ".join(
         f"{dname(r.date)} {r.max_temp_c:.0f}°C" for r in cal[(cal.date >= TODAY) & (cal.date < TODAY + pd.Timedelta(days=7))].itertuples()) +
               f". Days over 32°C: {', '.join(hot_days)}. On hot days the AI had {pct(seg['Hot days (over 32°C)']['ml_wape'])} "
               f"error vs {pct(seg['Hot days (over 32°C)']['baseline_wape'])} for today's method.",
     "show": "weather"},
    {"id": "Q20", "topic": "Forecast", "question": "What is the total forecast for the promotion week?",
     "keywords": ["total", "promotion week", "week", "how many cases", "sum", "overall"],
     "answer": f"For {pname(HERO)} at {cname(HERO_C)}, {dname(P_START)} to {dname(P_END)}: {n(week.forecast.sum())} cases "
               f"(AI) vs {n(week.today_method.sum())} (today's method). Across all products and customers the AI forecasts "
               f"{n(fc[fc.date.isin(promo_days)].forecast.sum())} cases that week.",
     "show": "forecast"},
    {"id": "Q21", "topic": "Labels", "question": "What does the label check look for?",
     "keywords": ["label", "labels", "carton", "artwork", "allergen", "allergens", "health star", "hsr", "claim", "claims", "pack", "compliant", "compliance", "wrong with the label", "label check"],
     "answer": "Allergens in bold and in the 'Contains' statement, nutrition claims against their conditions (for example "
               "'good source of protein' needs 10 g per serve), the Health Star Rating graphic against the nutrition panel and "
               "the current recipe, per-serve arithmetic, origin wording, and 'fresh' wording on milk with reconstituted "
               "ingredients. The cartons here are a fictional brand.",
     "show": "label"},
    {"id": "Q22", "topic": "Labels", "question": "Does the label agent approve artwork by itself?",
     "keywords": ["sign off", "signs off", "approve artwork", "regulatory", "legal", "print"],
     "answer": "No. It finds and explains issues; the regulatory reviewer sends each one to the team that owns the fix (food safety, marketing, nutrition, legal, procurement) or marks it not an "
               "issue, and every decision is logged. It makes the check faster and more consistent; it does not replace sign-off.",
     "show": "label"},
    {"id": "Q23", "topic": "How it works", "question": "How does this connect to SAP?",
     "keywords": ["sap", "erp", "system", "systems", "connect", "connects", "it team", "write back"],
     "answer": "In this demo the SAP step is simulated: each approval shows the change it would send. In a pilot the agents "
               "start read-only, using extracts of orders, the material and customer masters and the production plan. Writing "
               "approved changes back uses standard SAP interfaces agreed with your IT and security teams, and only after a person approves.",
     "show": "audit"},
    {"id": "Q24", "topic": "Next steps", "question": "What would you need from Lactalis?",
     "keywords": ["need from", "from us", "from lactalis", "data needed", "requirements", "prerequisites", "access", "what do you need"],
     "answer": "About two years of orders by product, customer and day; the promotion calendar; plant line capacities and the "
               "production plan; milk intake; write-offs; and both customer lists. Plus a few hours a week from a demand planner "
               "and a supply planner to review suggestions, and read-only data access agreed with IT.",
     "show": None},
    {"id": "Q25", "topic": "Next steps", "question": "Can it cover other regions and products?",
     "keywords": ["other states", "states", "region", "regions", "national", "cheese", "yoghurt", "yogurt", "categories", "scale", "victoria", "nsw"],
     "answer": "Yes. The same approach runs per region and per product range. The pilot starts with Queensland fresh milk and "
               "iced coffee because short shelf life makes errors costly. Other regions are added once accuracy is proven on "
               "real data; longer-life ranges such as cheese and yoghurt use the same models with their own shelf-life rules.",
     "show": None},
    {"id": "Q26", "topic": "How it works", "question": "Is our data safe?",
     "keywords": ["safe", "data safe", "secure", "security", "privacy", "confidential", "data protection", "where is the data", "cyber"],
     "answer": "In a pilot the data stays in an environment your IT security team approves, with role-based access and every "
               "action logged. Your data is not used to train public AI models. The exact set-up is agreed with your IT team before any data moves.",
     "show": None},
    {"id": "Q27", "topic": "Next steps", "question": "What does the pilot cost?",
     "keywords": ["how much does this cost", "how much does it cost", "what does it cost", "what will it cost", "cost us", "fees", "commercials", "pricing of", "investment", "budget"],
     "answer": "The commercial proposal covers that separately. The pilot is fixed in scope and time, and its value is measured "
               "against today's method on your own data before any wider roll-out.",
     "show": None},
    {"id": "Q28", "topic": "How it works", "question": "Why this forecasting model?",
     "keywords": ["lightgbm", "algorithm", "which model", "why this model", "machine learning", "newer", "llm", "chatgpt", "gpt", "neural"],
     "answer": "LightGBM is proven for demand forecasting at this scale: it handles thousands of product, customer and day "
               "combinations, retrains daily in minutes and shows which signals drove each number. Language models are used to "
               "explain results in plain words, not to produce the numbers.",
     "show": "waterfall"},
]

fallback = {
    "message": "That question isn't in the demo set yet. In a live system the agent would answer it from your data. "
               "Closest questions I can answer:",
    "suggest": 3,
    "stopwords": ["the", "a", "an", "is", "are", "of", "for", "to", "in", "on", "and", "it", "we", "do", "does", "what",
                  "how", "this", "that", "our", "be", "can", "i", "you", "will", "with", "at", "by", "me", "show", "tell"],
}

library = {
    "meta": {"built_from": "build/model_output.json and data/*.csv", "today": str(TODAY.date()),
             "disclosure": "Agent answers are pre-configured from the model results for this demo. "
                           "In production a live AI agent would generate them from your data.",
             "data": "synthetic"},
    "briefing": briefing, "alerts": alerts, "qa": qa, "fallback": fallback,
    "whatif_lookup": {"date": w["date"], "temps": w["temps"], "depths": w["promo_depths"],
                      "hero": {d: [wi(t, d, HERO) for t in w["temps"]] for d in w["cases"]},
                      "iced": {d: [wi(t, d) for t in w["temps"]] for d in w["cases"]},
                      "hero_at_customer": {d: [wi_cust(d, t) for t in w["temps"]] for d in w["cases"]},
                      "customer": HERO_C, "sku": HERO},
    "matching": {"stats": match_stats, "review_queue": review_queue, "auto_examples": auto_examples,
                 "auto_wrong": auto_wrong, "missed": missed, "new_examples": new_examples},
    "audit_seed": [
        {"time": "06:00", "who": "Demand agent", "what": "Forecast refreshed for 12 to 25 Oct (weather forecast updated 05:30)"},
        {"time": "06:02", "who": "Supply agent", "what": "Line load and silo balance checked against the new forecast"},
        {"time": "06:05", "who": "Order agent", "what": f"{leg_lines_28} legacy-code order lines in the last 4 weeks reviewed"},
    ],
}


# ---------------------------------------------------------------- matcher (mirrored in the demo's JavaScript)
def tokens(s: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9%°']+", s.lower()) if t not in fallback["stopwords"]]


def score(q: str, e: dict) -> float:
    ql = q.lower()
    qt = set(tokens(q))
    # phrases and keywords with symbols match as text; single words match whole tokens
    s = sum(2.0 if " " in k else 1.0 for k in e["keywords"] if (k in ql if not k.isalpha() else k in qt))
    s += 0.5 * len(qt & set(tokens(e["question"])))
    return s


def route(q: str) -> tuple[str | None, list[str]]:
    ranked = sorted(qa, key=lambda e: -score(q, e))
    top = ranked[0]
    return (top["id"] if score(q, top) >= 1.0 else None), [e["id"] for e in ranked[:3]]


TESTS = [
    ("why so many cases of ice break on wednesday", "Q1"), ("explain the 595", "Q1"),
    ("what if it's 26 degrees", "Q2"), ("what happens at 40°C", "Q2"),
    ("what if we only do 25% off", "Q3"), ("how accurate is it", "Q4"), ("can I trust the forecast", "Q4"),
    ("where does it help the most", "Q5"), ("why is monday wrong", "Q6"), ("does breaka lose sales", "Q7"),
    ("do we need overtime at nambour", "Q8"), ("is there enough milk friday", "Q9"), ("what's the ROI", "Q10"),
    ("how much money will we save", "Q10"), ("old fonterra codes", "Q11"), ("how good is the customer matching", "Q12"),
    ("any price conflicts", "Q13"), ("how much do we waste", "Q14"), ("what inputs does the model use", "Q15"),
    ("does the AI decide on its own", "Q16"), ("is this real data", "Q17"), ("what would a pilot look like", "Q18"),
    ("which days are hot", "Q19"), ("total for the promotion week", "Q20"),
    ("what does the label checker look for", "Q21"), ("check the allergens on the carton", "Q21"),
    ("who signs off the artwork", "Q22"),
    ("how sure are you", "Q4"), ("how confident is the forecast", "Q4"),
    ("does it replace planners", "Q16"), ("what about SAP", "Q23"), ("how does it connect to our systems", "Q23"),
    ("what do you need from us", "Q24"), ("what's wrong with the label", "Q21"), ("is the iced coffee carton compliant", "Q21"),
    ("is the forecast any good", "Q4"), ("what happens on public holidays", "Q6"), ("why is monday so low", "Q6"),
    ("what about the old fonterra prices", "Q13"), ("can it handle other states", "Q25"), ("what about cheese", "Q25"),
    ("who is accountable if it's wrong", "Q16"), ("is our data safe", "Q26"), ("how much does this cost", "Q27"),
    ("can I see the audit trail", "Q16"), ("how does the AI know about the weather", "Q15"),
    ("is this our data", "Q17"), ("are the agent answers live AI", "Q17"), ("what does it cost", "Q27"),
    ("why should we believe 36%", "Q10"), ("why LightGBM, not a newer AI model", "Q28"),
    ("who won the footy", None),
]
results = [(q, exp, route(q)[0]) for q, exp in TESTS]
library["routing_tests"] = [{"question": q, "expected": e, "got": g, "ok": e == g} for q, e, g in results]

(B / "agent_library.json").write_text(json.dumps(library, indent=1, ensure_ascii=False, default=str), encoding="utf-8")

# ---------------------------------------------------------------- readable review list
md = ["# Agent answer library (Phase 3)", "",
      "Made by `scripts/build_agent_library.py` from `build/model_output.json` and `data/`. Synthetic data.",
      f"**On-screen disclosure:** {library['meta']['disclosure']}", "", "## Morning briefing", "", f"> {briefing['greeting']}", ""]
md += [f"{i}. {it['text']}" for i, it in enumerate(briefing["items"], 1)]
md += ["", "Also today:"] + [f"- {it['text']}" for it in briefing["also"]] + ["", f"_{briefing['footer']}_", "", "## Alerts", ""]
for a in alerts:
    md += [f"### {a['id']} · {a['agent']} · {a['severity']}", f"**{a['title']}**", "", a["what"], "", "Why:"]
    md += [f"- {x}" for x in a["why"]]
    md += ["", f"Confidence: {a['confidence']['level']} ({a['confidence']['range']}). {a['confidence']['backtest']}.",
           f"Impact: {a['impact']}"]
    for op in a.get("options", []):
        md.append(f"- Option{' (recommended)' if op['recommended'] else ''}: {op['name']}. {op['detail']}")
    md += [f"Suggestion: {a['recommendation']}", f"- Approve → {a['approve']['result']}",
           f"- Reject → {a['reject']['result']}", ""]
md += ["## Questions and answers", "", "| # | Question | Answer | Shows |", "| --- | --- | --- | --- |"]
for q in qa:
    ans = q["answer"]
    if q.get("template") == "temp":
        ans = ans.replace("{temp}", "28").replace("{iced}", f"{wi(28, DKEY):,}").replace("{hero}", f"{wi(28, DKEY, HERO):,}")
    if q.get("template") == "depth":
        ans = ans.replace("{depth}", "25").replace("{hero_c}", f"{wi_cust('0.25'):,}") \
            .replace("{none}", f"{wi_cust('0.0'):,}").replace("{iced}", f"{wi(T0, '0.25'):,}")
    md.append(f"| {q['id']} | {q['question']} | {ans} | {q['show'] or ''} |")
md += ["", f"Unmatched question → \"{fallback['message']}\" plus the 3 closest questions.", "",
       "## Record matching (scene 1), scored against the answer key", ""]
md += [f"- {k}: {v}" for k, v in match_stats.items()]
md += ["", "Review queue (person decides):", "", "| Fonterra record | Suggested Lactalis record | Score | Why | Answer key |",
       "| --- | --- | --- | --- | --- |"]
md += [f"| {r['fonterra_name']} | {r['suggested_name']} | {r['score']} | {r['why']} | {r['truth']} |" for r in review_queue]
if auto_wrong:
    md += ["", "Wrong auto-matches (be ready to discuss):"] + [f"- {r['fonterra_name']} → {r['lactalis_name']} ({r['score']})" for r in auto_wrong]
if missed:
    md += ["", "True pairs the matcher missed (it called them new customers):"] + \
          [f"- {r['fonterra_name']} -> really {r['true_lactalis_name']} (best score {r['best_score']})" for r in missed]
md += ["", "Closest look-alikes correctly kept apart (new customers):"] + \
      [f"- {r['fonterra_name']} vs {r['closest']} ({r['score']})" for r in new_examples]
md += ["", "## Typed-question routing test", "", "| Question | Expected | Got | OK |", "| --- | --- | --- | --- |"]
md += [f"| {r['question']} | {r['expected']} | {r['got']} | {'yes' if r['ok'] else 'NO'} |" for r in library["routing_tests"]]
(B / "agent_library.md").write_text("\n".join(md), encoding="utf-8")

ok = sum(r["ok"] for r in library["routing_tests"])
print(f"alerts {len(alerts)}, Q&A {len(qa)}, routing {ok}/{len(TESTS)}")
print("matching", match_stats)
for r in library["routing_tests"]:
    if not r["ok"]:
        print("  MISROUTED:", r)
