"""Phase 1 check: charts showing the synthetic data behaves like fresh-dairy demand.

Run:  .venv/Scripts/python scripts/validate_data.py   -> data/validation.png
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

D = Path(__file__).resolve().parents[1] / "data"
orders = pd.read_csv(D / "orders.csv", parse_dates=["date"])
cal = pd.read_csv(D / "calendar_weather.csv", parse_dates=["date"])
inv = pd.read_csv(D / "dc_inventory_baseline.csv", parse_dates=["date"])
milk = pd.read_csv(D / "milk_intake.csv", parse_dates=["date"])
sku = pd.read_csv(D / "products.csv")

hist = orders[(orders.is_future == 0) & (orders.is_duplicate == 0)].merge(sku[["sku", "subcat", "litres_per_case"]])
INK, MUTED, A, B, C = "#1f2933", "#7b8794", "#2563a6", "#d97706", "#0f8a6c"
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlelocation": "left"})
fig, ax = plt.subplots(3, 2, figsize=(13, 11))
fig.suptitle("Synthetic Queensland fresh-milk data behaves like real dairy demand (synthetic data, Jul 2024 to Oct 2026)",
             x=0.02, ha="left", fontsize=12, fontweight="bold", color=INK)

# 1 total demand, 28-day average, white vs singles
g = hist.assign(group=np.where(hist.subcat.isin(["iced_coffee", "flavoured_milk"]), "Flavoured and iced coffee", "White and lactose free")) \
    .groupby(["date", "group"]).ordered_cases.sum().unstack().rolling(28).mean()
ax[0, 0].plot(g.index, g["White and lactose free"], color=A, label="White and lactose free")
ax[0, 0].plot(g.index, g["Flavoured and iced coffee"], color=B, label="Flavoured and iced coffee")
ax[0, 0].axvline(pd.Timestamp("2026-07-10"), color=MUTED, ls="--", lw=1)
ax[0, 0].text(pd.Timestamp("2026-07-14"), ax[0, 0].get_ylim()[1] * 0.97, "South Brisbane\ncloses", fontsize=8, color=MUTED, va="top")
ax[0, 0].set_title("Flavoured and iced coffee peak each summer; white milk is steady")
ax[0, 0].set_ylabel("Cases per day (28-day average)")
ax[0, 0].legend(frameon=False)

# 2 iced coffee vs temperature
ic = hist[hist.subcat == "iced_coffee"].groupby("date").ordered_cases.sum().to_frame().join(cal.set_index("date")["max_temp_c"])
ic = ic[ic.index.dayofweek < 5]
ax[0, 1].scatter(ic.max_temp_c, ic.ordered_cases, s=7, alpha=0.45, color=B)
ax[0, 1].set_title("Hot days lift iced coffee orders (weekdays)")
ax[0, 1].set_xlabel("Max temperature (°C)")
ax[0, 1].set_ylabel("Iced coffee cases per day")

# 3 promotion event study: average across every Ice Break 500mL promotion at Retailer A
promos = pd.read_csv(D / "promotions.csv", parse_dates=["start", "end"])
pa = hist[(hist.customer_code_received == hist.customer_id)]
piv = pa[pa.sku.isin(["ICB-IC-500", "ICB-IC-750"])].pivot_table(index="date", columns=["sku", "customer_id"],
                                                                 values="ordered_cases", aggfunc="sum")
rel = {k: [] for k in ("ICB-IC-500", "ICB-IC-750")}
for r in promos[(promos.customer_id == "RET-A") & (promos.sku == "ICB-IC-500") & (promos.start <= "2026-10-01")].itertuples():
    w = pd.date_range(r.start - pd.Timedelta(days=7), r.start + pd.Timedelta(days=13))
    for k in rel:   # Retailer A relative to Retailer B removes weather and season
        ratio = piv[(k, "RET-A")].reindex(w) / piv[(k, "RET-B")].reindex(w)
        rel[k].append((ratio / ratio.iloc[:7].mean()).to_numpy())
xs = np.arange(-7, 14)
ax[1, 0].plot(xs, np.nanmean(rel["ICB-IC-500"], axis=0) * 100, color=B, marker="o", ms=3, label="Ice Break 500mL (on promotion)")
ax[1, 0].plot(xs, np.nanmean(rel["ICB-IC-750"], axis=0) * 100, color=A, marker="o", ms=3, label="Ice Break 750mL (sibling)")
ax[1, 0].axvspan(0, 6, color=B, alpha=0.08)
ax[1, 0].axhline(100, color=MUTED, lw=0.8)
ax[1, 0].set_title("A promotion lifts one product and takes sales from its sibling")
ax[1, 0].set_xlabel("Days from promotion start (average of all Retailer A promotions)")
ax[1, 0].set_ylabel("Orders vs week before (=100), Retailer A vs B")
ax[1, 0].legend(frameon=False)

# 4 school holidays and weekday pattern
h = hist.merge(cal[["date", "school_holiday"]])
singles = h[h.subcat.isin(["iced_coffee", "flavoured_milk"])].groupby(["date", "school_holiday"]).ordered_cases.sum().reset_index()
singles["dow"] = singles.date.dt.dayofweek
pv = singles.groupby(["dow", "school_holiday"]).ordered_cases.mean().unstack()
x = np.arange(7)
ax[1, 1].bar(x - 0.2, pv[0], 0.4, color=B, label="School term")
ax[1, 1].bar(x + 0.2, pv[1], 0.4, color=MUTED, label="School holidays")
ax[1, 1].set_xticks(x, ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
ax[1, 1].set_title("Singles drop in school holidays; Friday is the busiest order day")
ax[1, 1].set_ylabel("Flavoured and iced coffee cases per day")
ax[1, 1].legend(frameon=False)

# 5 baseline write-offs and fill rate by month
m = inv.assign(month=inv.date.dt.to_period("M")).groupby("month")[["ordered_cases", "shipped_cases", "written_off_cases", "produced_cases"]].sum()
idx = m.index.to_timestamp()
ax[2, 0].bar(idx, m.written_off_cases / m.produced_cases * 100, width=20, color=A, label="Write-offs, % of production")
ax2 = ax[2, 0].twinx()
ax2.plot(idx, m.shipped_cases / m.ordered_cases * 100, color=C, marker="o", ms=3, label="Orders filled, %")
ax2.set_ylim(95, 100.5)
ax2.spines["top"].set_visible(False)
ax[2, 0].set_title("Today's planning: about 1.5% written off, about 99% of orders filled")
ax[2, 0].set_ylabel("Write-offs, % of production")
ax2.set_ylabel("Orders filled, %")
h1, l1 = ax[2, 0].get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax[2, 0].set_ylim(0, 9)
ax[2, 0].legend(h1 + h2, l1 + l2, frameon=False, loc="upper left", ncol=2)

# 6 milk intake vs milk needed
need = inv.merge(sku[["sku", "litres_per_case", "milk_fraction"]]).assign(
    l=lambda x: x.produced_cases * x.litres_per_case * x.milk_fraction * 1.02).groupby("date").l.sum().rolling(28).mean()
intake = milk.groupby("date").litres.sum().rolling(28).mean()
ax[2, 1].plot(intake.index, intake / 1000, color=C, label="Raw milk collected")
ax[2, 1].plot(need.index, need / 1000, color=A, label="Raw milk needed for production")
ax[2, 1].set_title("Milk supply drifts down about 2% a year and dips in summer")
ax[2, 1].set_ylabel("Thousand litres per day (28-day average)")
ax[2, 1].legend(frameon=False)

for a in ax.flat:
    a.tick_params(colors=INK)
fig.tight_layout(rect=(0, 0, 1, 0.96))
fig.savefig(D / "validation.png", dpi=130)
print("saved", D / "validation.png")
