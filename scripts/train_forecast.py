"""Phase 2: forecasting engine.

1. Build a daily panel: SKU x customer x day (legacy Fonterra codes merged into the master customer).
2. Back-test on 1 Jan - 11 Oct 2026: today's method vs LightGBM, and every on/off combination of
   the weather, holiday and promotion signals (for the demo's "switch a source off" toggles).
3. Re-train on all history and forecast 12-25 Oct 2026 with driver breakdowns and ranges.
4. What-if grid for Wed 14 Oct (temperature x Ice Break promotion depth).
5. Milk and Nambour line checks for the forecast fortnight.
6. Value: replay Jan-Oct 2026 through the same planning rules with each forecast.
Writes build/model_output.json and build/phase2_report.png.

Run:  .venv/Scripts/python scripts/train_forecast.py
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from planning_sim import LINE_CAP, simulate  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
D, B = ROOT / "data", ROOT / "build"
B.mkdir(exist_ok=True)

HIST_START = pd.Timestamp("2024-07-01")
TODAY = pd.Timestamp("2026-10-12")
HIST_END = TODAY - pd.Timedelta(days=1)
HORIZON = pd.date_range(TODAY, TODAY + pd.Timedelta(days=13))
TEST_START = pd.Timestamp("2026-01-01")
SCENARIO_DAY = pd.Timestamp("2026-10-14")
HERO = ("ICB-IC-500", "RET-A")
COGS_SHARE = 0.55   # assumption: cost of goods as a share of list price per case

products = pd.read_csv(D / "products.csv")
customers = pd.read_csv(D / "customers.csv")
cal = pd.read_csv(D / "calendar_weather.csv", parse_dates=["date"])
promos = pd.read_csv(D / "promotions.csv", parse_dates=["start", "end"])
orders = pd.read_csv(D / "orders.csv", parse_dates=["date"])
milk = pd.read_csv(D / "milk_intake.csv", parse_dates=["date"])
lines = pd.read_csv(D / "plant_lines.csv")
prices = pd.read_csv(D / "price_lists.csv")

# ---------------------------------------------------------------- panel
hist = orders[(orders.is_future == 0) & (orders.is_duplicate == 0)]
y = hist.groupby(["sku", "customer_id", "date"]).ordered_cases.sum()
combos = orders[["sku", "customer_id"]].drop_duplicates()
dates = pd.date_range(HIST_START, HORIZON[-1])
panel = combos.merge(pd.DataFrame({"date": dates}), how="cross")
panel = panel.merge(y.rename("y").reset_index(), on=["sku", "customer_id", "date"], how="left")
panel.loc[panel.date <= HIST_END, "y"] = panel.loc[panel.date <= HIST_END, "y"].fillna(0)
panel = panel.merge(cal, on="date").merge(products[["sku", "subcat", "line", "litres_per_case", "milk_fraction"]], on="sku")
panel = panel.sort_values(["sku", "customer_id", "date"]).reset_index(drop=True)

# own promotion depth per row
panel["promo_depth"] = 0.0
key = panel.sku + "|" + panel.customer_id
pos = {k: np.where(key.to_numpy() == k)[0] for k in key.unique()}
didx = {d: i for i, d in enumerate(dates)}
for p in promos.itertuples():
    r = pos.get(f"{p.sku}|{p.customer_id}")
    if r is not None:
        panel.loc[r[didx[p.start]:didx[p.end] + 1], "promo_depth"] = p.depth


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    g = df.groupby(["sku", "customer_id"], sort=False)
    # sibling promotion: deepest promotion on another product of the same family at the same customer
    grp = df.groupby(["date", "customer_id", "subcat"])["promo_depth"]
    top = grp.transform("max")
    n_top = df.assign(is_top=df.promo_depth.eq(top) & (top > 0)).groupby(["date", "customer_id", "subcat"])["is_top"].transform("sum")
    second = grp.transform(lambda s: s.nlargest(2).iloc[-1] if len(s) > 1 else 0.0)
    df["promo_sibling_depth"] = np.where((df.promo_depth == top) & (n_top <= 1), second, top)
    df.loc[df.promo_sibling_depth < 0, "promo_sibling_depth"] = 0
    df["promo_tomorrow_depth"] = np.where(df.promo_depth == 0, g["promo_depth"].shift(-1).fillna(0), 0)
    prev = g["promo_depth"].shift(1).fillna(0)
    ended = (prev > 0) & (df.promo_depth == 0)
    df["post_promo"] = 0
    for k in (0, 1, 2):
        df["post_promo"] = df["post_promo"] | ended.groupby([df.sku, df.customer_id]).shift(k).fillna(False).astype(int)
    df["day_after_holiday"] = g["is_public_holiday"].shift(1).fillna(0)
    doy = df.date.dt.dayofyear
    df["doy_sin"], df["doy_cos"] = np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25)
    df["trend_days"] = (df.date - HIST_START).dt.days
    xmas = pd.to_datetime(df.date.dt.year.astype(str) + "-12-25")
    to_x = (xmas - df.date).dt.days
    df["xmas_window"] = np.where(to_x.between(-7, 14), to_x, 15)
    for L in (14, 21, 28, 35):
        df[f"lag{L}"] = g["y"].shift(L)
    df["same_dow_mean"] = df[["lag14", "lag21", "lag28", "lag35"]].mean(axis=1)
    df["roll28_lag14"] = g["y"].transform(lambda s: s.shift(14).rolling(28, min_periods=7).mean())
    df["sku_code"] = df.sku.astype("category").cat.codes
    df["cust_code"] = df.customer_id.astype("category").cat.codes
    df["subcat_code"] = df.subcat.astype("category").cat.codes
    return df


panel = add_features(panel)

BASE = ["sku_code", "cust_code", "subcat_code", "dow", "doy_sin", "doy_cos", "trend_days",
        "lag14", "lag21", "lag28", "lag35", "same_dow_mean", "roll28_lag14"]
GROUPS = {
    "weather": ["max_temp_c", "rain_mm"],
    "holidays": ["school_holiday", "is_public_holiday", "day_before_holiday", "day_after_holiday", "xmas_window"],
    "promotions": ["promo_depth", "promo_sibling_depth", "promo_tomorrow_depth", "post_promo"],
}
PARAMS = dict(objective="poisson", n_estimators=700, learning_rate=0.04, num_leaves=63, min_child_samples=30,
              subsample=0.8, subsample_freq=1, colsample_bytree=0.8, verbose=-1, random_state=7)


def features_for(on: tuple[str, ...]) -> list[str]:
    return BASE + [f for g in on for f in GROUPS[g]]


def fit(df: pd.DataFrame, feats: list[str]) -> lgb.LGBMRegressor:
    tr = df.dropna(subset=["lag35", "y"])
    return lgb.LGBMRegressor(**PARAMS).fit(tr[feats], tr["y"], categorical_feature=["sku_code", "cust_code", "subcat_code"])


def wape(a, f) -> float:
    a, f = np.asarray(a, float), np.asarray(f, float)
    return float(np.abs(a - f).sum() / a.sum())


# ---------------------------------------------------------------- back-test
train = panel[(panel.date < TEST_START)]
test = panel[(panel.date >= TEST_START) & (panel.date <= HIST_END)].copy()
lag7 = panel.groupby(["sku", "customer_id"])["y"].shift(7)
test["baseline"] = lag7.loc[test.index] * (1 + 0.6 * test.promo_depth)   # today's method (see generate_data.py)

# in real use the model only has the weather forecast, not the observed temperature: add forecast-like error
wx_rng = np.random.default_rng(11)
temp_err = pd.Series(wx_rng.normal(0, 1.8, test.date.nunique()), index=sorted(test.date.unique()))
test_x = test.copy()
test_x["max_temp_c"] = test_x.max_temp_c + test_x.date.map(temp_err)

combos_on = [c for r in range(4) for c in itertools.combinations(GROUPS, r)]
variants = {}
for on in combos_on:
    name = "+".join(on) if on else "history_only"
    m = fit(train, features_for(on))
    test[f"pred_{name}"] = m.predict(test_x[features_for(on)])
    pc = f"pred_{name}"
    ic = test.subcat == "iced_coffee"
    hero = (test.sku == HERO[0]) & (test.customer_id == HERO[1])
    variants[name] = {"signals": list(on), "wape": round(wape(test.y, test[pc]), 4),
                      "wape_iced_coffee": round(wape(test.y[ic], test[pc][ic]), 4),
                      "wape_hero": round(wape(test.y[hero], test[pc][hero]), 4),
                      "wape_hot_days": round(wape(test.y[test.max_temp_c > 32], test[pc][test.max_temp_c > 32]), 4),
                      "wape_holidays": round(wape(test.y[test.is_public_holiday + test.day_before_holiday > 0],
                                                  test[pc][test.is_public_holiday + test.day_before_holiday > 0]), 4)}
    print(f"{name:32s} WAPE {variants[name]['wape']:.3f}")
FULL = "weather+holidays+promotions"
test["ml"] = test[f"pred_{FULL}"]
base_wape = wape(test.y, test.baseline)
ml_wape = wape(test.y, test.ml)
print(f"today's method WAPE {base_wape:.3f}  |  ML WAPE {ml_wape:.3f}")


def seg(mask) -> dict:
    t = test[mask]
    return {"days": int(t.date.nunique()), "baseline_wape": round(wape(t.y, t.baseline), 4), "ml_wape": round(wape(t.y, t.ml), 4)}


segments = {
    "All days": seg(test.y.notna()),
    "Hot days (over 32°C)": seg(test.max_temp_c > 32),
    "Promotion days": seg(test.promo_depth > 0),
    "Products next to a promotion": seg(test.promo_sibling_depth > 0),
    "Public holidays and the day before": seg((test.is_public_holiday == 1) | (test.day_before_holiday == 1)),
    "School holidays": seg(test.school_holiday == 1),
    "After South Brisbane closed (from 10 Jul)": seg(test.date >= "2026-07-10"),
}
by_sku = {s: {"baseline_wape": round(wape(g.y, g.baseline), 4), "ml_wape": round(wape(g.y, g.ml), 4)}
          for s, g in test.groupby("sku")}

# residual ranges (ratio of actual to forecast) by sub-category for the 80% band
test["ratio"] = (test.y + 1) / (test.ml + 1)
bands = test.groupby("subcat").ratio.quantile([0.1, 0.9]).unstack()

# back-test series for the demo chart (last 10 weeks): hero series and total iced coffee
tail = test[test.date >= HIST_END - pd.Timedelta(days=69)]
pred_cols = ["y", "baseline"] + [f"pred_{('+'.join(o) if o else 'history_only')}" for o in combos_on]


def series(frame: pd.DataFrame) -> dict:
    s = frame.groupby("date")[pred_cols].sum()
    return {"dates": [d.strftime("%Y-%m-%d") for d in s.index],
            **{c.replace("pred_", ""): [round(v) for v in s[c]] for c in pred_cols}}


backtest_series = {
    "hero": series(tail[(tail.sku == HERO[0]) & (tail.customer_id == HERO[1])]),
    "iced_coffee_total": series(tail[tail.subcat == "iced_coffee"]),
    "all_products": series(tail),
}

# ---------------------------------------------------------------- value: replay Jan-Oct 2026 through the same planning rules
act = test.pivot_table(index="date", columns="sku", values="y", aggfunc="sum")
fc_base = test.pivot_table(index="date", columns="sku", values="baseline", aggfunc="sum").reindex(act.index)
fc_ml = test.pivot_table(index="date", columns="sku", values="ml", aggfunc="sum").reindex(act.index)
sim_base = simulate(act, fc_base, products).assign(method="today")
sim_ml = simulate(act, fc_ml, products).assign(method="ml")
price = prices[prices.source == "Lactalis"].groupby("sku").price_per_case_aud.mean()
lit = products.set_index("sku")


def summarise(sim: pd.DataFrame) -> dict:
    t = sim.sum(numeric_only=True)
    cost = (sim.written_off * sim.sku.map(price) * COGS_SHARE).sum()
    litres = (sim.written_off * sim.sku.map(lit.litres_per_case) * sim.sku.map(lit.milk_fraction)).sum()
    return {"writeoff_pct": round(t.written_off / t.produced * 100, 2), "fill_pct": round(t.shipped / t.ordered * 100, 2),
            "written_off_cases": int(t.written_off), "short_cases": int(t.short), "produced_cases": int(t.produced),
            "writeoff_cost_aud": int(cost), "milk_litres_wasted": int(litres)}


# a more reliable forecast needs less safety stock: shrink the buffer in line with the error reduction
buffer_scale = ml_wape / base_wape
sim_ml_rs = simulate(act, fc_ml, products, buffer_scale=buffer_scale).assign(method="ml_resized")
val_base, val_ml, val_rs = summarise(sim_base), summarise(sim_ml), summarise(sim_ml_rs)
days_in_test = act.shape[0]


def gains(v: dict) -> dict:
    return {"writeoff_reduction_pct": round((1 - v["written_off_cases"] / val_base["written_off_cases"]) * 100, 1),
            "annualised_saving_aud": int((val_base["writeoff_cost_aud"] - v["writeoff_cost_aud"]) * 365 / days_in_test),
            "annualised_milk_litres_saved": int((val_base["milk_litres_wasted"] - v["milk_litres_wasted"]) * 365 / days_in_test)}


value = {
    "period": f"{TEST_START.date()} to {HIST_END.date()} ({days_in_test} days)",
    "today": val_base, "ml": val_ml, "ml_resized": val_rs, "buffer_scale": round(buffer_scale, 3),
    **gains(val_ml), "resized": gains(val_rs),
    "assumption": f"Write-off cost = {int(COGS_SHARE*100)}% of synthetic list price per case. 'ml' keeps today's stock "
                  f"buffers; 'ml_resized' shrinks the safety part of the buffer to {buffer_scale:.0%} in line with the lower error.",
}
print("resized buffers:", gains(val_rs), "fill", val_rs["fill_pct"])
monthly = pd.concat([sim_base, sim_ml, sim_ml_rs]).assign(month=lambda x: x.date.dt.strftime("%Y-%m")) \
    .groupby(["method", "month"])[["produced", "ordered", "shipped", "written_off"]].sum()
value["monthly"] = [{"month": m, "method": meth, "writeoff_pct": round(r.written_off / r.produced * 100, 2),
                     "fill_pct": round(r.shipped / r.ordered * 100, 2)} for (meth, m), r in monthly.iterrows()]
print("value:", value["writeoff_reduction_pct"], "% fewer write-offs; fill", val_base["fill_pct"], "->", val_ml["fill_pct"])

# ---------------------------------------------------------------- final model on all history, forecast the fortnight
feats = features_for(tuple(GROUPS))
final = fit(panel[panel.date <= HIST_END], feats)
fut = panel[panel.date.isin(HORIZON)].copy()
fut["forecast"] = final.predict(fut[feats])
lo = fut.subcat.map(bands[0.1]); hi = fut.subcat.map(bands[0.9])
fut["low"] = ((fut.forecast + 1) * lo - 1).clip(lower=0)
fut["high"] = (fut.forecast + 1) * hi - 1
# driver breakdown as a waterfall in cases: a normal day for this weekday and season, then add holidays,
# then promotions, then the weather forecast; the steps add up exactly to the forecast
month_temp = panel[panel.date <= HIST_END].groupby(panel.date.dt.month).max_temp_c.mean()
NEUTRAL = {"holidays": {"school_holiday": 0, "is_public_holiday": 0, "day_before_holiday": 0, "day_after_holiday": 0, "xmas_window": 15},
           "promotions": {"promo_depth": 0.0, "promo_sibling_depth": 0.0, "promo_tomorrow_depth": 0, "post_promo": 0}}
step = fut.copy()
step["max_temp_c"] = step.date.dt.month.map(month_temp)
step["rain_mm"] = 0.0
for g in NEUTRAL.values():
    for c, v in g.items():
        step[c] = v
levels = [final.predict(step[feats])]
for g in ("holidays", "promotions"):
    for c in NEUTRAL[g]:
        step[c] = fut[c]
    levels.append(final.predict(step[feats]))
levels.append(fut["forecast"].to_numpy())
fut["normal_level"] = levels[0]
fut["drv_Holidays"], fut["drv_Promotion"], fut["drv_Weather"] = levels[1] - levels[0], levels[2] - levels[1], levels[3] - levels[2]
fut["normal_temp"] = step.max_temp_c.to_numpy()
DRIVER_GROUPS = ["Holidays", "Promotion", "Weather"]

# what today's method would say for the same fortnight (same weekday last week, promotion-adjusted);
# for days 8-14 it only has two-week-old data
last = panel[panel.date.between(HORIZON[0] - pd.Timedelta(days=7), HIST_END)][["sku", "customer_id", "date", "y"]]
last = last.assign(date=last.date + pd.Timedelta(days=7)).rename(columns={"y": "last_week"})
fut = fut.merge(last, on=["sku", "customer_id", "date"], how="left")
fut["today_method"] = fut.last_week.fillna(fut.lag14) * (1 + 0.6 * fut.promo_depth)

forecast_rows = [{
    "date": r.date.strftime("%Y-%m-%d"), "sku": r.sku, "customer": r.customer_id,
    "forecast": round(r.forecast), "low": round(r.low), "high": round(r.high),
    "today_method": round(r.today_method), "normal_level": round(r.normal_level),
    "drivers_cases": {n: round(float(r[f"drv_{n}"]), 1) for n in DRIVER_GROUPS},
    "max_temp_c": float(r.max_temp_c), "normal_temp_c": round(float(r.normal_temp), 1), "promo_depth": float(r.promo_depth),
    "sibling_promo_depth": float(r.promo_sibling_depth),
} for _, r in fut.iterrows()]

# ---------------------------------------------------------------- what-if grid for Wed 14 Oct
day = panel[panel.date == SCENARIO_DAY].copy()
temps, depths = list(range(14, 43)), [0.0, 0.25, 0.33, 0.40, 0.50]
whatif = {"date": SCENARIO_DAY.strftime("%Y-%m-%d"), "temps": temps, "promo_depths": depths,
          "promo_target": {"sku": HERO[0], "customer": HERO[1]}, "skus": sorted(day.sku.unique()), "cases": {},
          "hero_customer": {}}    # the promoted product at the promoted customer only, [temp index]
hero_mask = (day.sku == HERO[0]) & (day.customer_id == HERO[1])
for dep in depths:
    base_rows = day.copy()
    base_rows.loc[hero_mask, "promo_depth"] = dep
    # recompute sibling promotion for this customer and family
    fam = base_rows.subcat == "iced_coffee"
    cust = base_rows.customer_id == HERO[1]
    base_rows.loc[fam & cust & ~hero_mask, "promo_sibling_depth"] = dep
    base_rows.loc[hero_mask, "promo_sibling_depth"] = 0.0
    grid, hero_c = [], []
    for t in temps:
        rows = base_rows.assign(max_temp_c=float(t))
        p = final.predict(rows[feats])
        hero_c.append(round(float(p[hero_mask.values].sum()), 1))
        grid.append(pd.Series(p, index=rows.sku.values).groupby(level=0).sum().reindex(whatif["skus"]).round().astype(int).tolist())
    whatif["cases"][str(dep)] = grid    # [temp index][sku index]
    whatif["hero_customer"][str(dep)] = hero_c

# ---------------------------------------------------------------- milk and Nambour line checks for the fortnight
daily = fut.groupby(["date", "sku"]).forecast.sum().reset_index().merge(products, on="sku")
daily["milk_l"] = daily.forecast * daily.litres_per_case * daily.milk_fraction * 1.02
intake_hist = milk.groupby("date").litres.sum()
base_intake = intake_hist[-28:].mean()
heat = cal.set_index("date").max_temp_c
SILO_START_L = int(base_intake * 0.8)   # assumption: raw milk in Nambour silos on Monday morning
silo = SILO_START_L
milk_check, line_check = [], []
for d in HORIZON:
    hot_before = (heat.get(d - pd.Timedelta(days=1), 0) > 33) or (heat.get(d - pd.Timedelta(days=2), 0) > 33)
    intake = base_intake * (1 - 0.035 * hot_before)
    need = daily.loc[daily.date == d, "milk_l"].sum()
    silo = silo + intake - need
    milk_check.append({"date": d.strftime("%Y-%m-%d"), "milk_needed_l": int(need), "milk_expected_l": int(intake),
                       "silo_end_l": int(silo), "heat_stress": bool(hot_before)})
    silo = min(max(silo, 0), SILO_START_L * 2.5)   # shortfall is bought in; silos hold about 2.5 days
    for ln in lines.itertuples():
        cases = daily.loc[(daily.date == d) & (daily.line == ln.line), "forecast"].sum()
        line_check.append({"date": d.strftime("%Y-%m-%d"), "line": ln.line, "description": ln.description,
                           "forecast_cases": int(cases), "capacity": int(ln.cases_per_day),
                           "extra_shift": int(ln.extra_shift_cases), "utilisation_pct": round(cases / ln.cases_per_day * 100, 1)})

# ---------------------------------------------------------------- export
imp = pd.Series(final.booster_.feature_importance("gain"), index=feats)
imp_groups = {"Recent history": imp[[c for c in BASE if c.startswith(("lag", "same", "roll"))]].sum(),
              "Product and customer": imp[["sku_code", "cust_code", "subcat_code"]].sum(),
              "Weekday and season": imp[["dow", "doy_sin", "doy_cos", "trend_days"]].sum(),
              **{k.capitalize(): imp[v].sum() for k, v in GROUPS.items()}}
tot = sum(imp_groups.values())
out = {
    "meta": {"today": TODAY.strftime("%Y-%m-%d"), "history": f"{HIST_START.date()} to {HIST_END.date()}",
             "backtest": f"{TEST_START.date()} to {HIST_END.date()}", "model": "LightGBM (Poisson), SKU x customer x day",
             "data": "synthetic", "level": "SKU x customer x day; accuracy = 1 - WAPE"},
    "accuracy": {"today_method_wape": round(base_wape, 4), "ml_wape": round(ml_wape, 4),
                 "today_method_accuracy_pct": round((1 - base_wape) * 100, 1), "ml_accuracy_pct": round((1 - ml_wape) * 100, 1),
                 "error_reduction_pct": round((1 - ml_wape / base_wape) * 100, 1)},
    "variants": variants, "segments": segments, "by_sku": by_sku,
    "feature_importance": {k: round(v / tot, 3) for k, v in imp_groups.items()},
    "backtest_series": backtest_series, "value": value,
    "forecast": forecast_rows, "whatif": whatif, "milk_check": milk_check, "line_check": line_check,
    "milk_meta": {"silo_start_l": SILO_START_L, "silo_note": "assumption: silos start the week at 0.8 days of intake"},
    "products": products[["sku", "name", "brand", "subcat", "litres_per_case", "milk_fraction", "shelf_life_days", "line"]].to_dict("records"),
    "customers": customers[["customer_id", "name", "channel"]].to_dict("records"),
}
(B / "model_output.json").write_text(json.dumps(out, indent=1))
final.booster_.save_model(str(B / "model_full.txt"))
print("wrote", B / "model_output.json", f"({(B / 'model_output.json').stat().st_size / 1024:.0f} KB)")
