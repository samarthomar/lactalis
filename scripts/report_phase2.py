"""Phase 2 report: charts from build/model_output.json -> build/phase2_report.png"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

B = Path(__file__).resolve().parents[1] / "build"
o = json.loads((B / "model_output.json").read_text())
INK, MUTED, TODAY_C, AI_C, ACT_C, WARN = "#1f2933", "#9aa5b1", "#d97706", "#2563a6", "#1f2933", "#c2410c"
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlelocation": "left"})
fig, ax = plt.subplots(4, 2, figsize=(13, 15))
acc = o["accuracy"]
fig.suptitle(f"Forecast model cuts error from {acc['today_method_wape']*100:.1f}% to {acc['ml_wape']*100:.1f}% "
             f"and write-offs by {o['value']['writeoff_reduction_pct']:.0f}% (synthetic data, back-test Jan-Oct 2026)",
             x=0.02, ha="left", fontsize=12, fontweight="bold", color=INK)

# 1 error by situation
seg = o["segments"]
names = list(seg)[::-1]
y = np.arange(len(names))
ax[0, 0].barh(y + 0.2, [seg[n]["baseline_wape"] * 100 for n in names], 0.4, color=TODAY_C, label="Today's method")
ax[0, 0].barh(y - 0.2, [seg[n]["ml_wape"] * 100 for n in names], 0.4, color=AI_C, label="AI forecast")
ax[0, 0].set_yticks(y, names)
ax[0, 0].set_xlabel("Forecast error, % (lower is better)")
ax[0, 0].set_title("Biggest gains on holidays and promotions")
ax[0, 0].legend(frameon=False, loc="lower right")

# 2 back-test, all products last 10 weeks
s = o["backtest_series"]["all_products"]
d = pd.to_datetime(s["dates"])
ax[0, 1].plot(d, s["y"], color=ACT_C, lw=1.6, label="Actual orders")
ax[0, 1].plot(d, s["baseline"], color=TODAY_C, lw=1, ls="--", label="Today's method")
ax[0, 1].plot(d, s["weather+holidays+promotions"], color=AI_C, lw=1.2, label="AI forecast")
ax[0, 1].set_title("Back-test, all products, last 10 weeks")
ax[0, 1].set_ylabel("Cases per day")
ax[0, 1].legend(frameon=False, ncol=3, loc="upper left")
ax[0, 1].tick_params(axis="x", rotation=30)

# 3 signals path, iced coffee
v = o["variants"]
path = [("History only", "history_only"), ("+ holidays", "holidays"), ("+ promotions", "holidays+promotions"),
        ("+ weather", "weather+holidays+promotions")]
vals = [v[k]["wape_iced_coffee"] * 100 for _, k in path]
ax[1, 0].bar(range(4), vals, color=[MUTED, AI_C, AI_C, AI_C])
for i, val in enumerate(vals):
    ax[1, 0].text(i, val + 0.3, f"{val:.1f}%", ha="center", color=INK)
ax[1, 0].axhline(seg["All days"]["baseline_wape"] * 100, color=TODAY_C, ls="--", lw=1)
ax[1, 0].text(3.4, seg["All days"]["baseline_wape"] * 100 + 0.3, "today's method (all products)", ha="right", color=TODAY_C, fontsize=8)
ax[1, 0].set_xticks(range(4), [p for p, _ in path])
ax[1, 0].set_ylabel("Forecast error, iced coffee, %")
ax[1, 0].set_title("Each outside signal removes more error (iced coffee)")

# 4 waterfall for the scenario
f = [r for r in o["forecast"] if r["sku"] == "ICB-IC-500" and r["customer"] == "RET-A" and r["date"] == "2026-10-14"][0]
steps = [("Normal\nWednesday", f["normal_level"]), ("Promotion\n40% off", f["drivers_cases"]["Promotion"]),
         ("Heat\n34°C", f["drivers_cases"]["Weather"])]
base = 0
for i, (n, val) in enumerate(steps):
    ax[1, 1].bar(i, val, bottom=base if i else 0, color=MUTED if i == 0 else AI_C)
    ax[1, 1].text(i, (base if i else 0) + val + 8, f"{'+' if i else ''}{val:.0f}", ha="center", color=INK)
    base = base + val if i else val
ax[1, 1].bar(3, f["forecast"], color=AI_C)
ax[1, 1].text(3, f["forecast"] + 8, f"{f['forecast']}", ha="center", fontweight="bold", color=INK)
ax[1, 1].axhline(f["today_method"], color=TODAY_C, ls="--", lw=1)
ax[1, 1].text(-0.4, f["today_method"] + 8, f"today's method: {f['today_method']}", color=TODAY_C, fontsize=8)
ax[1, 1].set_xticks(range(4), [s[0] for s in steps] + ["AI\nforecast"])
ax[1, 1].set_ylabel("Cases")
ax[1, 1].set_title(f"Ice Break 500mL, Retailer A, Wed 14 Oct: {f['forecast']} cases")

# 5 what-if
w = o["whatif"]
skus = w["skus"]
iced = [i for i, s in enumerate(skus) if s.startswith(("ICB", "BRK-IC", "OAK-IC"))]
for dep, col, lab in (("0.0", MUTED, "No promotion"), ("0.4", AI_C, "Ice Break 500mL 40% off at Retailer A")):
    tot = [sum(row[i] for i in iced) for row in w["cases"][dep]]
    ax[2, 0].plot(w["temps"], tot, color=col, lw=2, label=lab)
ax[2, 0].set_xlabel("Max temperature on Wed 14 Oct (°C)")
ax[2, 0].set_ylabel("Iced coffee cases, all customers")
ax[2, 0].set_title("What-if: heat lifts iced coffee sharply above 25°C")
ax[2, 0].legend(frameon=False)

# 6 line 3 utilisation
lc = pd.DataFrame(o["line_check"])
l3 = lc[lc.line == "L3"]
dd = pd.to_datetime(l3.date)
cols = [WARN if u > 100 else AI_C for u in l3.utilisation_pct]
ax[2, 1].bar(dd, l3.utilisation_pct, color=cols)
ax[2, 1].axhline(100, color=INK, lw=1)
ax[2, 1].text(dd.iloc[-1], 101.5, "standard capacity", ha="right", fontsize=8)
ax[2, 1].set_ylabel("Nambour line 3 load, % of capacity")
ax[2, 1].set_title("Nambour line 3 over capacity Thu-Fri")
ax[2, 1].tick_params(axis="x", rotation=30)

# 7 milk silo balance
mc = pd.DataFrame(o["milk_check"])
md = pd.to_datetime(mc.date)
ax[3, 0].bar(md, mc.silo_end_l / 1000, color=[WARN if v < 0 else AI_C for v in mc.silo_end_l])
ax[3, 0].axhline(0, color=INK, lw=1)
ax[3, 0].set_ylabel("Raw milk left in silos at day end, thousand L")
ax[3, 0].set_title("Milk silos run short on Fri 16 Oct (heat stress + promotion)")
ax[3, 0].tick_params(axis="x", rotation=30)

# 8 value
mv = pd.DataFrame(o["value"]["monthly"])
for meth, col, lab, off in (("today", TODAY_C, "Today's method", -5), ("ml", AI_C, "AI forecast (same stock rules)", 5)):
    m = mv[mv.method == meth]
    ax[3, 1].bar(pd.to_datetime(m.month) + pd.Timedelta(days=off), m.writeoff_pct, width=10, color=col, label=lab)
vb, vr = o["value"]["today"], o["value"]["ml"]
ax[3, 1].xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b"))
ax[3, 1].set_ylabel("Write-offs, % of production")
ax[3, 1].set_title(f"Write-offs {vb['writeoff_pct']}% to {vr['writeoff_pct']}%; orders filled {vb['fill_pct']}% to {vr['fill_pct']}%")
ax[3, 1].legend(frameon=False)

fig.tight_layout(rect=(0, 0, 1, 0.97))
fig.savefig(B / "phase2_report.png", dpi=120)
print("saved", B / "phase2_report.png")
