"""Phase 6: recompute the numbers the demo shows, from the source tables, and check they agree.

Run after build_demo.py. Prints PASS/FAIL per check and exits 1 on any failure.
"""
from __future__ import annotations

import json
import re
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
D, B, W = ROOT / "data", ROOT / "build", ROOT / "web"
M = json.loads((B / "model_output.json").read_text(encoding="utf-8"))
L = json.loads((B / "agent_library.json").read_text(encoding="utf-8"))
LB = json.loads((W / "labels.json").read_text(encoding="utf-8"))
html = (B / "lactalis_demo.html").read_text(encoding="utf-8")
fc = pd.DataFrame(M["forecast"])
lines = pd.DataFrame(M["line_check"])
milk = pd.DataFrame(M["milk_check"]).set_index("date")
orders = pd.read_csv(D / "orders.csv")
products = pd.read_csv(D / "products.csv").set_index("sku")
A = {a["id"]: a["data"] for a in L["alerts"]}
fails = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))
    if not ok:
        fails.append(name)


def rnd(x, dp):
    """Round half up, as on a nutrition panel (Python round() gives 8.25 -> 8.2)."""
    return float(Decimal(str(x)).quantize(Decimal(1).scaleb(-dp), rounding=ROUND_HALF_UP))


def near(a, b, tol=1):
    return abs(a - b) <= tol


# ---- A1 promotion forecast
a = A["A1"]
row = fc[(fc.sku == a["sku"]) & (fc.customer == a["customer"]) & (fc.date == a["date"])].iloc[0]
check("A1 day forecast / today method", row.forecast == a["forecast"] and row.today_method == a["today_method"],
      f"{row.forecast} vs {a['forecast']}, {row.today_method} vs {a['today_method']}")
promos = pd.read_csv(D / "promotions.csv")
p = promos[(promos.sku == a["sku"]) & (promos.customer_id == a["customer"]) & (promos.start <= a["date"]) & (promos.end >= a["date"])].iloc[0]
wk = fc[(fc.sku == a["sku"]) & (fc.customer == a["customer"]) & (fc.date >= p.start) & (fc.date <= p.end)]
check("A1 promotion week totals", wk.forecast.sum() == a["week_ai"] and wk.today_method.sum() == a["week_today"],
      f"{wk.forecast.sum()}/{wk.today_method.sum()} vs {a['week_ai']}/{a['week_today']}")

# ---- A3 neighbouring products
check("A3 surplus total 258", sum(A["A3"]["over_cases"].values()) == 258)

# ---- A4 line 3
a = A["A4"]
l3 = lines[lines.line == "L3"].set_index("date")
over = sum(l3.at[d, "forecast_cases"] - l3.at[d, "capacity"] for d in a["over"])
check("A4 cases over capacity", over == a["cases_over"], f"{over} vs {a['cases_over']}")
check("A4 utilisation %", all(near(l3.at[d, "utilisation_pct"], v, 0.05) for d, v in a["over"].items()))
spare = {d: int(l3.at[d, "capacity"] - l3.at[d, "forecast_cases"]) for d in a["spare_before"]}
check("A4 spare before", spare == a["spare_before"], f"{spare}")
check("A4 spare covers move", sum(spare.values()) >= a["cases_over"], f"{sum(spare.values())} >= {a['cases_over']}")

# ---- A5 milk
a = A["A5"]
check("A5 silo short", milk.at[a["date"], "silo_end_l"] == -a["short_l"], f"{milk.at[a['date'], 'silo_end_l']}")
litres = a["defer_cases"] * products.at[a["defer_sku"], "litres_per_case"] * products.at[a["defer_sku"], "milk_fraction"]
check("A5 litres moved", near(litres, a["defer_litres"]), f"{litres}")
check("A5 silo after", a["defer_litres"] - a["short_l"] == a["silo_after_l"])
l1 = lines[(lines.line == "L1") & (lines.date == a["to_date"])].iloc[0]
pct = (l1.forecast_cases + a["defer_cases"]) / l1.capacity * 100
check("A5 line 1 next day %", near(pct, a["l1_next_pct"], 0.1), f"{pct:.1f}")

# ---- A6 legacy codes
dups = orders[orders.is_duplicate == 1]
check("A6 duplicate orders", len(dups) == A["A6"]["duplicate_orders"] and dups.ordered_cases.sum() == A["A6"]["duplicate_return_cases"],
      f"{len(dups)} / {dups.ordered_cases.sum()}")
blob = json.loads(re.search(r"window\.DEMO = (\{.*?\});</script>", html, re.S).group(1).replace("<\\/", "</"))
if blob:
    ex = blob["extra"]
    check("A6 price conflicts", len(ex["price_conflicts"]) == A["A6"]["price_conflicts"])
    lm = ex["legacy_monthly"]
    # alert "now" = last 28 days; the chart's last bar is October to date, so only April must agree exactly
    check("A6 legacy April %", near(lm[0]["share"] * 100, A["A6"]["legacy_share_first_pct"], 0.05), f"{lm[0]['share']}")
    check("A6 'now' sits between Sep and Oct-to-date", lm[-1]["share"] * 100 - 0.05 <= A["A6"]["legacy_share_now_pct"] <= lm[-2]["share"] * 100 + 0.05,
          f"{lm[-2]['share']}, {A['A6']['legacy_share_now_pct']}, {lm[-1]['share']}")

# ---- what-if at the promoted customer: never negative, at plan matches A1, rises with discount
wl = L["whatif_lookup"]
hc = wl["hero_at_customer"]
t0 = wl["temps"].index(34)
check("what-if at plan = A1 forecast", hc["0.4"][t0] == A["A1"]["forecast"], f"{hc['0.4'][t0]}")
check("what-if never negative", min(min(v) for v in hc.values()) >= 0)
deps = sorted(hc, key=float)
check("what-if rises with discount", all(hc[a][i] <= hc[b][i] for a, b in zip(deps, deps[1:]) for i in range(len(wl["temps"]))))
check("what-if: hotter day never far below a cooler one", all(v[i + 1] >= v[i] - 5 for v in hc.values() for i in range(len(v) - 1)))

# ---- matching
s = L["matching"]["stats"]
check("matching counts add up", s["auto_matched"] + s["review"] + s["new"] == s["fonterra_records"])
check("matching precision", near(s["auto_correct"] / s["auto_matched"] * 100, s["auto_precision_pct"], 0.05))

# ---- accuracy and value
ac = M["accuracy"]
check("accuracy = 1 - WAPE", near(100 - ac["today_method_wape"] * 100, ac["today_method_accuracy_pct"], 0.06)
      and near(100 - ac["ml_wape"] * 100, ac["ml_accuracy_pct"], 0.06))
check("error reduction", near((1 - ac["ml_wape"] / ac["today_method_wape"]) * 100, ac["error_reduction_pct"], 0.1))
v = M["value"]
red = (1 - v["ml_resized"]["writeoff_pct"] / v["today"]["writeoff_pct"]) * 100
red2 = (1 - v["ml"]["writeoff_pct"] / v["today"]["writeoff_pct"]) * 100
check("write-off reduction %", near(red, v["writeoff_reduction_pct"], 0.6) or near(red2, v["writeoff_reduction_pct"], 0.6),
      f"resized {red:.1f}, same buffers {red2:.1f}, shown {v['writeoff_reduction_pct']}")
days = 284
for key in ("ml", "ml_resized"):
    sav = (v["today"]["writeoff_cost_aud"] - v[key]["writeoff_cost_aud"]) * 365 / days
    print(f"      annualised saving using {key}: A${sav:,.0f}")
check("annualised saving matches a method", any(near((v["today"]["writeoff_cost_aud"] - v[k]["writeoff_cost_aud"]) * 365 / days,
                                                      v["annualised_saving_aud"], 500) for k in ("ml", "ml_resized")))

# ---- labels: per-serve arithmetic
for c in LB["cartons"]:
    k = c["serve_ml"] / 100
    bad = []
    for name, (per100, serve) in c["nip"].items():
        exp = rnd(Decimal(str(per100)) * Decimal(str(k)), 0 if ("kJ" in name or "mg" in name) else 1)
        if not near(serve, exp, 0.01):
            bad.append(f"{name}: {serve} vs {exp}")
    print(f"      {c['id']} per-serve mismatches: {bad or 'none'}")
check("labels: only C1 sodium is a per-serve error",
      [c["id"] for c in LB["cartons"] for n, (a1, b1) in c["nip"].items()
       if not near(b1, rnd(Decimal(str(a1)) * c["serve_ml"] / 100, 0 if ("kJ" in n or "mg" in n) else 1), 0.01)] == ["C1"])

# ---- the briefing quotes the alert numbers
text = json.dumps(L, ensure_ascii=False)
for n in ["595", "397", "4,145", "2,386", "3,143", "2,257", "562", "258", "273"]:
    check(f"number {n} appears in the agent text", n in text)

print(f"\n{len(fails)} failure(s)" + (": " + ", ".join(fails) if fails else ""))
sys.exit(1 if fails else 0)
