"""Phase 1: generate synthetic Lactalis-style data for the Queensland fresh-milk pilot.

Everything here is synthetic. Patterns are shaped by public facts (Queensland seasons,
school and public holidays, the South Brisbane -> Nambour move in July 2026, the Fonterra
deal completing 31 March 2026) and by stated assumptions listed in data/README.md.

Run:  .venv/Scripts/python scripts/generate_data.py
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20261012
rng = np.random.default_rng(SEED)
OUT = Path(__file__).resolve().parents[1] / "data"
OUT.mkdir(exist_ok=True)

HIST_START = pd.Timestamp("2024-07-01")
TODAY = pd.Timestamp("2026-10-12")          # demo "today": Monday
HIST_END = TODAY - pd.Timedelta(days=1)     # history runs to Sunday 11 Oct 2026
HORIZON_END = TODAY + pd.Timedelta(days=13)
FONTERRA_DAY = pd.Timestamp("2026-04-01")   # first day after completion (31 Mar 2026)
SOUTH_BRIS_CLOSE = pd.Timestamp("2026-07-10")
RAMP_END = pd.Timestamp("2026-08-09")

# ---------------------------------------------------------------- products
# sku, name, brand, subcat, size_l, units_per_case, base_cases_per_day, shelf_life_days,
# milk_fraction, annual_trend, temp_beta, line
SKUS = [
    ("PAU-FC-2L",   "Pauls Full Cream Milk 2L",            "Pauls",     "white_take_home", 2.0,  9, 3200, 14, 1.00, -0.02, 0.004, "L1"),
    ("PAU-FC-3L",   "Pauls Full Cream Milk 3L",            "Pauls",     "white_take_home", 3.0,  6, 1500, 14, 1.00, -0.02, 0.004, "L1"),
    ("PAU-RF-2L",   "Pauls Reduced Fat Milk 2L",           "Pauls",     "white_take_home", 2.0,  9, 1800, 14, 1.00, -0.01, 0.004, "L1"),
    ("PAU-BAR-2L",  "Pauls Barista Milk 2L",               "Pauls",     "barista",         2.0,  9,  700, 14, 1.00,  0.05, 0.002, "L1"),
    ("PAU-FC-1L",   "Pauls Full Cream Milk 1L",            "Pauls",     "white_single",    1.0, 12,  600, 14, 1.00, -0.02, 0.006, "L2"),
    ("PAU-RF-1L",   "Pauls Reduced Fat Milk 1L",           "Pauls",     "white_single",    1.0, 12,  500, 14, 1.00, -0.01, 0.006, "L2"),
    ("ZYM-LF-1L",   "Zymil Lactose Free Milk 1L",          "Zymil",     "lactose_free",    1.0, 12,  450, 21, 1.00,  0.09, 0.003, "L2"),
    ("ZYM-LF-2L",   "Zymil Lactose Free Milk 2L",          "Zymil",     "lactose_free",    2.0,  9,  350, 21, 1.00,  0.09, 0.003, "L1"),
    ("OAK-CHOC-600","Oak Chocolate Milk 600mL",            "Oak",       "flavoured_milk",  0.6, 12,  900, 16, 0.88,  0.00, 0.025, "L3"),
    ("OAK-STR-600", "Oak Strawberry Milk 600mL",           "Oak",       "flavoured_milk",  0.6, 12,  450, 16, 0.88,  0.00, 0.025, "L3"),
    ("OAK-IC-600",  "Oak Iced Coffee 600mL",               "Oak",       "iced_coffee",     0.6, 12,  500, 16, 0.82,  0.02, 0.035, "L3"),
    ("ICB-IC-500",  "Ice Break Iced Coffee 500mL",         "Ice Break", "iced_coffee",     0.5, 12, 1400, 21, 0.80,  0.04, 0.035, "L3"),
    ("ICB-IC-750",  "Ice Break Iced Coffee 750mL",         "Ice Break", "iced_coffee",     0.75,12,  700, 21, 0.80,  0.04, 0.035, "L3"),
    ("ICB-LS-500",  "Ice Break Iced Coffee Less Sugar 500mL","Ice Break","iced_coffee",    0.5, 12,  300, 21, 0.82,  0.08, 0.035, "L3"),
    ("BRK-IC-750",  "Breaka Iced Coffee 750mL",            "Breaka",    "iced_coffee",     0.75,12,  450, 16, 0.82,  0.00, 0.035, "L3"),
    ("BRK-CHOC-750","Breaka Chocolate Milk 750mL",         "Breaka",    "flavoured_milk",  0.75,12,  250, 16, 0.88,  0.00, 0.025, "L3"),
]
sku_df = pd.DataFrame(SKUS, columns=["sku", "name", "brand", "subcat", "size_l", "units_per_case",
                                     "base_cases_per_day", "shelf_life_days", "milk_fraction",
                                     "annual_trend", "temp_beta", "line"])
sku_df["litres_per_case"] = sku_df["size_l"] * sku_df["units_per_case"]
SINGLES = {"flavoured_milk", "iced_coffee"}

# ---------------------------------------------------------------- customers
CUSTOMERS = [
    ("RET-A", "National Retailer A",  "Major retail", "Retailer A DC, SE QLD", "major"),
    ("RET-B", "National Retailer B",  "Major retail", "Retailer B DC, SE QLD", "major"),
    ("RET-C", "Discount Retailer",    "Discount retail", "Retailer C DC, SE QLD", "major"),
    ("IND",   "Independent Grocers",  "Independent", "Richlands DC (direct to store)", "other"),
    ("FS",    "Food Service",         "Food service", "Richlands DC (route)", "other"),
    ("CNV",   "Convenience & Fuel",   "Convenience", "Richlands DC (route)", "other"),
]
cust_df = pd.DataFrame(CUSTOMERS, columns=["customer_id", "name", "channel", "ship_to", "tier"])

SHARES = {  # customer share of each SKU group's volume
    "white_take_home": {"RET-A": .34, "RET-B": .34, "RET-C": .12, "IND": .12, "FS": .04, "CNV": .04},
    "lactose_free":    {"RET-A": .36, "RET-B": .36, "RET-C": .08, "IND": .14, "FS": .03, "CNV": .03},
    "white_single":    {"RET-A": .20, "RET-B": .20, "RET-C": .08, "IND": .17, "FS": .15, "CNV": .20},
    "barista":         {"RET-A": .05, "RET-B": .05, "IND": .10, "FS": .80},
    "flavoured_milk":  {"RET-A": .22, "RET-B": .22, "RET-C": .06, "IND": .15, "FS": .05, "CNV": .30},
    "iced_coffee":     {"RET-A": .22, "RET-B": .22, "RET-C": .06, "IND": .15, "FS": .05, "CNV": .30},
}
DOW = {  # Mon..Sun order-delivery pattern
    "major": [1.15, 1.00, 0.95, 1.10, 1.20, 0.75, 0.35],
    "IND":   [1.20, 1.00, 1.00, 1.10, 1.20, 0.80, 0.20],
    "FS":    [1.10, 1.05, 1.00, 1.10, 1.20, 0.90, 0.30],
    "CNV":   [1.00, 0.95, 0.95, 1.00, 1.15, 1.10, 0.85],
}

# ---------------------------------------------------------------- calendar (approximate; verify against official QLD calendars)
SCHOOL_HOLIDAYS = [
    ("2024-06-22", "2024-07-07"), ("2024-09-14", "2024-09-29"), ("2024-12-14", "2025-01-27"),
    ("2025-04-05", "2025-04-21"), ("2025-06-28", "2025-07-13"), ("2025-09-20", "2025-10-05"),
    ("2025-12-13", "2026-01-26"), ("2026-04-03", "2026-04-19"), ("2026-06-27", "2026-07-12"),
    ("2026-09-19", "2026-10-05"), ("2026-12-12", "2027-01-26"),
]
PUBLIC_HOLIDAYS = {
    "2024-08-14": "Royal Queensland Show (Brisbane)", "2024-10-07": "King's Birthday",
    "2024-12-25": "Christmas Day", "2024-12-26": "Boxing Day", "2025-01-01": "New Year's Day",
    "2025-01-27": "Australia Day", "2025-04-18": "Good Friday", "2025-04-19": "Easter Saturday",
    "2025-04-21": "Easter Monday", "2025-04-25": "Anzac Day", "2025-05-05": "Labour Day",
    "2025-08-13": "Royal Queensland Show (Brisbane)", "2025-10-06": "King's Birthday",
    "2025-12-25": "Christmas Day", "2025-12-26": "Boxing Day", "2026-01-01": "New Year's Day",
    "2026-01-26": "Australia Day", "2026-04-03": "Good Friday", "2026-04-04": "Easter Saturday",
    "2026-04-06": "Easter Monday", "2026-04-25": "Anzac Day", "2026-05-04": "Labour Day",
    "2026-08-12": "Royal Queensland Show (Brisbane)", "2026-10-05": "King's Birthday",
    "2026-12-25": "Christmas Day", "2026-12-26": "Boxing Day",
}

days = pd.date_range(HIST_START, HORIZON_END, freq="D")
cal = pd.DataFrame({"date": days})
cal["dow"] = cal["date"].dt.dayofweek
cal["school_holiday"] = 0
for a, b in SCHOOL_HOLIDAYS:
    cal.loc[cal["date"].between(a, b), "school_holiday"] = 1
cal["public_holiday"] = cal["date"].dt.strftime("%Y-%m-%d").map(PUBLIC_HOLIDAYS).fillna("")
cal["is_public_holiday"] = (cal["public_holiday"] != "").astype(int)
cal["day_before_holiday"] = cal["is_public_holiday"].shift(-1, fill_value=0)

# ---------------------------------------------------------------- weather (synthetic, Brisbane-like)
doy = cal["date"].dt.dayofyear.to_numpy()
seasonal = 25.5 + 4.6 * np.cos(2 * np.pi * (doy - 20) / 365.25)
anom = np.zeros(len(cal))
for i in range(1, len(cal)):
    anom[i] = 0.7 * anom[i - 1] + rng.normal(0, 2.0)
# summer heatwaves
for _ in range(9):
    i = rng.integers(0, len(cal) - 5)
    if cal["date"].iloc[i].month in (11, 12, 1, 2, 3):
        anom[i:i + rng.integers(3, 6)] += rng.uniform(3.5, 6.0)
tmax = seasonal + anom
rain_p = np.clip(0.18 + 0.22 * np.cos(2 * np.pi * (doy - 40) / 365.25) + rng.normal(0, 0.12, len(cal)), 0, 1)
rain_mm = np.where(rng.random(len(cal)) < rain_p, rng.gamma(1.2, 8, len(cal)), 0.0)
cal["max_temp_c"] = tmax.round(1)
cal["rain_mm"] = rain_mm.round(1)

# Demo week: hot spell Wed 14 - Fri 16 Oct 2026 (the "BOM forecast" the agents react to)
DEMO_FORECAST = {
    "2026-10-12": (28, 0.05), "2026-10-13": (30, 0.05), "2026-10-14": (34, 0.0), "2026-10-15": (35, 0.10),
    "2026-10-16": (33, 0.40), "2026-10-17": (29, 0.60), "2026-10-18": (27, 0.20), "2026-10-19": (28, 0.10),
    "2026-10-20": (29, 0.10), "2026-10-21": (30, 0.15), "2026-10-22": (29, 0.30), "2026-10-23": (28, 0.30),
    "2026-10-24": (27, 0.20), "2026-10-25": (28, 0.10),
}
for d, (t, p) in DEMO_FORECAST.items():
    m = cal["date"] == pd.Timestamp(d)
    cal.loc[m, "max_temp_c"] = t
    cal.loc[m, "rain_mm"] = round(p * 12, 1)
# Recent history (1-11 Oct 2026) kept mild so the coming heat stands out
recent = cal["date"].between("2026-10-01", "2026-10-11")
cal.loc[recent, "max_temp_c"] = np.round(rng.uniform(25, 29.5, recent.sum()), 1)

# ---------------------------------------------------------------- promotions
promo_rows = []
PROMO_SKUS = {s: (0.16 if sc in SINGLES else 0.06) for s, sc in zip(sku_df.sku, sku_df.subcat) if sc != "barista"}
subcat_of_sku = dict(zip(sku_df.sku, sku_df.subcat))
LONG_AGO = HIST_START - pd.Timedelta(days=60)
weds = pd.date_range(HIST_START, HORIZON_END, freq="W-WED")   # retail promo weeks run Wednesday to Tuesday
for cust in ["RET-A", "RET-B", "RET-C"]:
    sku_last = {k: LONG_AGO for k in PROMO_SKUS}
    fam_last = {}                                              # one promotion per product family at a time
    for wed in weds:
        for sku in rng.permutation(list(PROMO_SKUS)):
            fam = subcat_of_sku[sku]
            if (wed - sku_last[sku]).days < 35 or (wed - fam_last.get(fam, LONG_AGO)).days < 15:
                continue
            if rng.random() > PROMO_SKUS[sku]:
                continue
            depth = float(rng.choice([0.25, 0.33, 0.40, 0.50], p=[.3, .3, .25, .15]))
            promo_rows.append((cust, sku, wed, wed + pd.Timedelta(days=6), depth,
                               "Half price" if depth == 0.5 else f"{int(depth*100)}% off"))
            sku_last[sku] = fam_last[fam] = wed + pd.Timedelta(days=6)
promos = pd.DataFrame(promo_rows, columns=["customer_id", "sku", "start", "end", "depth", "mechanic"])
# Clean slate around the demo scenario, then add the scenario promo (Ice Break 500mL, Retailer A, from Wed 14 Oct)
clash = (promos["start"] >= "2026-09-20") & (promos["customer_id"] == "RET-A") & \
        promos["sku"].isin(sku_df.loc[sku_df.subcat == "iced_coffee", "sku"])
promos = promos[~clash]
promos = promos[promos["start"] <= HIST_END]               # future promotions: only the demo scenario
promos = pd.concat([promos, pd.DataFrame([("RET-A", "ICB-IC-500", pd.Timestamp("2026-10-14"),
                                           pd.Timestamp("2026-10-20"), 0.40, "40% off")],
                                         columns=promos.columns)], ignore_index=True)
promos = promos.sort_values(["start", "customer_id", "sku"]).reset_index(drop=True)
promos.insert(0, "promo_id", [f"PR{i:04d}" for i in range(1, len(promos) + 1)])

# ---------------------------------------------------------------- demand
grid = []
for s in sku_df.itertuples():
    for c, share in SHARES[s.subcat].items():
        grid.append((s.sku, c, s.base_cases_per_day * share))
grid = pd.DataFrame(grid, columns=["sku", "customer_id", "base"])
dem = grid.merge(cal, how="cross").merge(sku_df[["sku", "subcat", "annual_trend", "temp_beta"]], on="sku") \
          .merge(cust_df[["customer_id", "tier"]], on="customer_id")
dem = dem.sort_values(["sku", "customer_id", "date"]).reset_index(drop=True)

years = (dem["date"] - HIST_START).dt.days / 365.25
mult = np.power(1 + dem["annual_trend"], years)
pattern_key = np.where(dem["tier"] == "major", "major", dem["customer_id"])
dow_mult = np.array([DOW[k][d] for k, d in zip(pattern_key, dem["dow"])])
mult *= dow_mult
t = dem["max_temp_c"]
mult *= np.exp(dem["temp_beta"] * np.clip(t - 24, 0, None))
is_single = dem["subcat"].isin(SINGLES)
mult *= np.where(is_single & (t < 20), 1 - 0.015 * (20 - t), 1.0)
mult *= np.where(is_single & (dem["rain_mm"] > 10), 0.95, 1.0)
# school holidays: singles and food service down, take-home up
sh = dem["school_holiday"] == 1
mult *= np.where(sh & is_single, 0.90, 1.0)
mult *= np.where(sh & (dem["subcat"] == "white_take_home"), 1.05, 1.0)
mult *= np.where(sh & (dem["customer_id"] == "FS"), 0.95, 1.0)
# public holidays and Christmas
mult *= np.where(dem["is_public_holiday"] == 1, 0.30, 1.0)
mult *= np.where(dem["day_before_holiday"] == 1, 1.25, 1.0)
md = dem["date"].dt.strftime("%m-%d")
xmas_build = md.between("12-18", "12-23") & dem["subcat"].isin(["white_take_home", "lactose_free"])
mult *= np.where(xmas_build, 1.25, 1.0)
mult *= np.where(md == "12-24", 1.10, 1.0)
mult *= np.where(md.between("12-27", "12-31"), 0.90, 1.0)

# promotions: lift, build-up day before, post-promo dip, cannibalisation within sub-category
dem["promo_id"] = ""
dem["promo_depth"] = 0.0
promo_mult = np.ones(len(dem))
key = dem["sku"] + "|" + dem["customer_id"]
idx_by_key = {k: np.where(key.to_numpy() == k)[0] for k in key.unique()}
date_index = {d: i for i, d in enumerate(days)}
subcat_of = dict(zip(sku_df.sku, sku_df.subcat))
for p in promos.itertuples():
    rows = idx_by_key.get(f"{p.sku}|{p.customer_id}")
    if rows is None:
        continue
    elastic = 2.2 if subcat_of[p.sku] in SINGLES else 1.0
    lift = 1 + elastic * p.depth
    s0, s1 = date_index[p.start], date_index[p.end]
    promo_mult[rows[s0:s1 + 1]] *= lift
    dem.loc[rows[s0:s1 + 1], "promo_id"] = p.promo_id
    dem.loc[rows[s0:s1 + 1], "promo_depth"] = p.depth
    if s0 - 1 >= 0:
        promo_mult[rows[s0 - 1]] *= 1 + 0.35 * (lift - 1)
    promo_mult[rows[s1 + 1:s1 + 4]] *= 0.88
    for other in sku_df.loc[(sku_df.subcat == subcat_of[p.sku]) & (sku_df.sku != p.sku), "sku"]:
        orows = idx_by_key.get(f"{other}|{p.customer_id}")
        if orows is not None:
            promo_mult[orows[s0:s1 + 1]] *= 1 - 0.55 * p.depth
mult *= promo_mult

# unpredictable shocks that no forecast can see (real demand has these too)
shock = np.ones(len(dem))
n_days = len(days)
for k, rows in idx_by_key.items():                       # retailer stock adjustments on one product: 2-5 days
    for _ in range(rng.poisson(n_days / 45)):
        s0 = rng.integers(0, n_days - 5)
        shock[rows[s0:s0 + rng.integers(2, 6)]] *= np.clip(rng.normal(1, 0.22), 0.55, 1.5)
cust_rows = {c: np.where(dem["customer_id"].to_numpy() == c)[0] for c in cust_df.customer_id}
day_pos = dem["date"].map(date_index).to_numpy()
for c, rows in cust_rows.items():                        # customer-wide events (DC stocktake, systems issue): 1-3 days
    for _ in range(rng.poisson(n_days / 60)):
        s0 = rng.integers(0, n_days - 3)
        hit = rows[(day_pos[rows] >= s0) & (day_pos[rows] < s0 + rng.integers(1, 4))]
        shock[hit] *= rng.uniform(0.7, 1.3)
for c in ["RET-A", "RET-B", "RET-C"]:                    # competitor promotions in a family: a week at about -15%
    for fam in SINGLES | {"white_take_home"}:
        rows = np.where((dem["customer_id"] == c).to_numpy() & (dem["subcat"] == fam).to_numpy())[0]
        for _ in range(rng.poisson(n_days / 70)):
            s0 = rng.integers(0, n_days - 7)
            hit = rows[(day_pos[rows] >= s0) & (day_pos[rows] < s0 + 7)]
            shock[hit] *= rng.uniform(0.78, 0.92)
mult *= shock

expected = dem["base"] * mult
sigma = 0.08 + 0.6 / np.sqrt(dem["base"].clip(lower=1))
noise = np.exp(rng.normal(-sigma ** 2 / 2, sigma))
dem["expected_cases"] = expected.round(2)
dem["ordered_cases"] = rng.poisson(np.clip(expected * noise, 0, None)).astype(int)
dem["is_future"] = (dem["date"] > HIST_END).astype(int)
dem.loc[dem["is_future"] == 1, "ordered_cases"] = -1   # unknown future

# ---------------------------------------------------------------- Fonterra legacy codes and duplicates (from 1 Apr 2026)
LEGACY = {"RET-B": "FON-QLD-0412", "IND": "FON-QLD-0877"}
dem["customer_code_received"] = dem["customer_id"]
dem["is_duplicate"] = 0
hist = dem["is_future"] == 0
post = hist & (dem["date"] >= FONTERRA_DAY) & dem["customer_id"].isin(LEGACY)
frac = np.interp((dem.loc[post, "date"] - FONTERRA_DAY).dt.days, [0, 193], [0.18, 0.06])
legacy_part = rng.binomial(dem.loc[post, "ordered_cases"], frac)
legacy_rows = dem.loc[post].copy()
legacy_rows["ordered_cases"] = legacy_part
legacy_rows["customer_code_received"] = legacy_rows["customer_id"].map(LEGACY)
dem.loc[post, "ordered_cases"] -= legacy_part
legacy_rows = legacy_rows[legacy_rows["ordered_cases"] > 0]
# duplicates: same order keyed in under both codes (about 1 day in 40)
dup_cand = dem.loc[post & (dem["customer_id"] == "RET-B") & dem["sku"].isin(["PAU-FC-2L", "PAU-FC-3L"])]
dup_days = rng.choice(dup_cand["date"].unique(), size=max(1, len(dup_cand["date"].unique()) // 40), replace=False)
dups = dup_cand[dup_cand["date"].isin(dup_days)].copy()
dups["ordered_cases"] = (dups["ordered_cases"] * rng.uniform(0.06, 0.12, len(dups))).round().astype(int)
dups["customer_code_received"] = dups["customer_id"].map(LEGACY)
dups["is_duplicate"] = 1
orders = pd.concat([dem, legacy_rows, dups], ignore_index=True)

# ---------------------------------------------------------------- baseline planning + DC inventory simulation (today's way of working)
LINE_CAP = {"L1": 9000, "L2": 2500, "L3": 7200}           # Nambour cases/day after the upgrade (assumption)
PRE_CLOSE_CAP = {"L1": 14000, "L2": 4000, "L3": 7200}      # Nambour + South Brisbane before 10 Jul 2026
MIN_LEFT = 0.80          # share of shelf life that must remain for a customer to accept stock (assumption)
COVER_K = {"white_take_home": 1.45, "white_single": 1.45, "barista": 1.45, "lactose_free": 2.2,
           "flavoured_milk": 2.1, "iced_coffee": 2.3}   # production target = forecast x K - usable stock
SHORT_LIFE_ICED_K = 2.0  # iced coffee lines with 21-day life hold less cover
line_of = dict(zip(sku_df.sku, sku_df.line))
life_of = dict(zip(sku_df.sku, sku_df.shelf_life_days))

hist_days = pd.date_range(HIST_START, HIST_END)
real_demand = orders[(orders.is_future == 0) & (orders.is_duplicate == 0)] \
    .groupby(["date", "sku"])["ordered_cases"].sum().unstack().reindex(hist_days).fillna(0)
dup_demand = orders[(orders.is_future == 0) & (orders.is_duplicate == 1)] \
    .groupby(["date", "sku"])["ordered_cases"].sum().unstack().reindex(hist_days).fillna(0) \
    .reindex(columns=real_demand.columns, fill_value=0)
promo_known = dem[dem.is_future == 0].assign(lift=lambda x: np.where(x.promo_depth > 0, 1 + 0.6 * x.promo_depth, 1.0)) \
    .groupby(["date", "sku"]).apply(lambda g: np.average(g["lift"], weights=g["base"]), include_groups=False) \
    .unstack().reindex(hist_days)

skus = list(real_demand.columns)
batches = {s: [[1, real_demand[s].iloc[:7].mean() * 1.5]] for s in skus}   # [age_days, cases]
inv_rows, wo_rows = [], []
for i, d in enumerate(hist_days):
    # plan production for day d (made the day before): naive same-weekday-last-week, promo-adjusted, order-up-to
    want = {}
    for s in skus:
        ref = real_demand[s].iloc[i - 7] if i >= 7 else real_demand[s].iloc[:7].mean()
        fc = ref * (promo_known[s].iloc[i] if not math.isnan(promo_known[s].iloc[i]) else 1.0)
        usable = sum(q for a, q in batches[s] if life_of[s] - a >= math.ceil(MIN_LEFT * life_of[s]))
        k = SHORT_LIFE_ICED_K if (subcat_of[s] == "iced_coffee" and life_of[s] < 21) else COVER_K[subcat_of[s]]
        want[s] = max(0.0, fc * k - usable)
    cap = PRE_CLOSE_CAP if d < SOUTH_BRIS_CLOSE else LINE_CAP
    ramp = 0.85 if SOUTH_BRIS_CLOSE <= d <= RAMP_END else 1.0
    produced = {}
    for line in ("L1", "L2", "L3"):
        members = [s for s in skus if line_of[s] == line]
        need = sum(want[s] for s in members)
        scale = min(1.0, cap[line] * ramp / need) if need > 0 else 1.0
        for s in members:
            produced[s] = round(want[s] * scale)
    for s in skus:
        b = batches[s]
        b.append([1, produced[s]])
        demand = real_demand[s].iloc[i] + dup_demand[s].iloc[i]
        min_left = math.ceil(MIN_LEFT * life_of[s])
        remaining = demand
        for batch in sorted(b, key=lambda x: -x[0]):                     # FIFO: oldest first
            if life_of[s] - batch[0] < min_left or remaining <= 0:
                continue
            take = min(batch[1], remaining)
            batch[1] -= take
            remaining -= take
        shipped = demand - remaining
        expired = sum(q for a, q in b if life_of[s] - a < min_left and q > 0)
        b[:] = [[a + 1, q] for a, q in b if q > 0 and life_of[s] - a >= min_left]
        dup_ret = dup_demand[s].iloc[i]
        damaged = rng.binomial(int(shipped), 0.0004) if shipped > 0 else 0
        stock = sum(q for _, q in b)
        avg_dem = real_demand[s].iloc[max(0, i - 7):i + 1].mean()
        inv_rows.append((d, s, produced[s], int(demand), int(shipped), int(remaining), int(expired),
                         int(stock), round(stock / avg_dem, 2) if avg_dem else 0.0,
                         "South Brisbane" if (d < SOUTH_BRIS_CLOSE and line_of[s] in ("L1", "L2")) else "Nambour"))
        if expired:
            wo_rows.append((d, s, int(expired), "Short-dated / expired in DC", "Richlands DC"))
        if dup_ret:
            wo_rows.append((d + pd.Timedelta(days=2), s, int(dup_ret), "Customer return: duplicate order under legacy Fonterra code", "Richlands DC"))
        if damaged:
            wo_rows.append((d, s, int(damaged), "Damaged in handling", "Richlands DC"))

inventory = pd.DataFrame(inv_rows, columns=["date", "sku", "produced_cases", "ordered_cases", "shipped_cases",
                                            "short_cases", "written_off_cases", "closing_stock_cases",
                                            "days_of_cover", "source_plant"])
writeoffs = pd.DataFrame(wo_rows, columns=["date", "sku", "cases", "reason", "location"])
writeoffs = writeoffs[writeoffs["date"] <= HIST_END]

# allocate shipments to customer orders by the SKU-day fill rate
fill = inventory.set_index(["date", "sku"]).eval("shipped_cases / ordered_cases").replace([np.inf], 1).fillna(1).clip(0, 1)
orders = orders.merge(fill.rename("fill").reset_index(), on=["date", "sku"], how="left")
orders["shipped_cases"] = np.where(orders.is_future == 1, -1,
                                   np.floor(orders["ordered_cases"] * orders["fill"].fillna(1))).astype(int)
orders["source_plant"] = np.where((orders["date"] < SOUTH_BRIS_CLOSE) & orders["sku"].map(line_of).isin(["L1", "L2"]),
                                  "South Brisbane", "Nambour")
orders["dc"] = "Richlands DC"
orders_out = orders[["date", "customer_id", "customer_code_received", "sku", "ordered_cases", "shipped_cases",
                     "promo_id", "promo_depth", "source_plant", "dc", "is_duplicate", "is_future"]] \
    .sort_values(["date", "customer_id", "sku", "customer_code_received"])

# ---------------------------------------------------------------- raw milk intake (synthetic farms, Nambour catchment)
REGIONS = ["Sunshine Coast Hinterland", "Gympie and Wide Bay", "Scenic Rim", "Darling Downs"]
farms = pd.DataFrame({
    "farm_id": [f"F{n:03d}" for n in range(1, 53)],
    "region": rng.choice(REGIONS, 52, p=[.35, .25, .15, .25]),
    "base_litres": rng.gamma(9, 450, 52).round(-1),
})
need_l = (inventory.merge(sku_df[["sku", "litres_per_case", "milk_fraction"]], on="sku")
          .assign(l=lambda x: x.produced_cases * x.litres_per_case * x.milk_fraction * 1.02)
          .groupby("date")["l"].sum())
scale = need_l.mean() * 1.04 / farms["base_litres"].sum()
farms["base_litres"] = (farms["base_litres"] * scale).round(-1)
mdays = pd.date_range(HIST_START, HIST_END)
m_doy = mdays.dayofyear.to_numpy()
m_season = 1 + 0.06 * np.cos(2 * np.pi * (m_doy - 290) / 365.25) - 0.05 * np.clip(np.cos(2 * np.pi * (m_doy - 20) / 365.25), 0, None)
m_trend = np.power(0.98, (mdays - HIST_START).days / 365.25)
hot = cal.set_index("date").reindex(mdays)["max_temp_c"].to_numpy()
heat = 1 - 0.035 * (pd.Series(hot > 33).rolling(2, min_periods=1).max().shift(1, fill_value=0).to_numpy())
milk_rows = []
for f in farms.itertuples():
    farm_noise = np.exp(rng.normal(0, 0.05, len(mdays)))
    litres = f.base_litres * m_season * m_trend * heat * farm_noise
    fat = np.round(rng.normal(4.05, 0.12, len(mdays)) - 0.1 * (heat < 1), 2)
    prot = np.round(rng.normal(3.35, 0.08, len(mdays)), 2)
    for d, l, fa, pr in zip(mdays, litres, fat, prot):
        milk_rows.append((d, f.farm_id, f.region, int(l), fa, pr, "Nambour"))
milk = pd.DataFrame(milk_rows, columns=["date", "farm_id", "region", "litres", "fat_pct", "protein_pct", "plant"])

# ---------------------------------------------------------------- plant lines
lines = pd.DataFrame([
    ("Nambour", "L1", "Large-format white (2L, 3L)", 9000, 3000, 25, "2 shifts; third shift adds 3,000 cases"),
    ("Nambour", "L2", "1L white and lactose free", 2500, 800, 30, "2 shifts"),
    ("Nambour", "L3", "Flavoured milk and iced coffee singles", 7200, 2000, 40, "2 shifts; extra night shift adds 2,000 cases"),
], columns=["plant", "line", "description", "cases_per_day", "extra_shift_cases", "changeover_minutes", "notes"])

# ---------------------------------------------------------------- master data (Lactalis vs Fonterra legacy) for the matching scene
first = ["Bean", "Grind", "Harbour", "Hinterland", "Coastal", "Sunny", "Ridge", "Valley", "Main St", "Riverside",
         "Corner", "Village", "Bay", "Summit", "Palm", "Creek", "Station", "Market", "Garden", "Lighthouse"]
kind = ["Cafe", "Espresso", "Kitchen", "Deli", "Grocer", "Foodstore", "Roasters", "Eatery"]
towns = ["Nambour", "Maroochydore", "Caloundra", "Noosa", "Gympie", "Ipswich", "Toowoomba", "Brisbane", "Redcliffe",
         "Beaudesert", "Caboolture", "Buderim", "Cleveland", "Springfield"]
l_cust, f_cust, truth = [], [], []
for i in range(1, 181):
    nm = f"{rng.choice(first)} {rng.choice(kind)} {rng.choice(towns)}"
    ch = rng.choice(["Food service", "Independent", "Convenience"], p=[.5, .35, .15])
    l_cust.append((f"L{100000 + i}", nm, ch, "QLD", f"{rng.integers(4000, 4620)}"))
lactalis_customers = pd.DataFrame(l_cust, columns=["customer_id", "name", "channel", "state", "postcode"])
lactalis_customers = pd.concat([pd.DataFrame([
    ("RET-A", "National Retailer A - QLD Regional DC", "Major retail", "QLD", "4110"),
    ("RET-B", "National Retailer B - QLD Regional DC", "Major retail", "QLD", "4073"),
    ("RET-C", "Discount Retailer - QLD DC", "Discount retail", "QLD", "4300"),
], columns=lactalis_customers.columns), lactalis_customers], ignore_index=True)


def variant(name: str) -> str:
    out = name.upper()
    for a, b in [(" CAFE", " CAFÉ"), (" ESPRESSO", " ESPRESSO BAR"), (" KITCHEN", " KITCHEN PTY LTD"),
                 (" GROCER", " GROCERS"), (" FOODSTORE", " FOOD STORE"), (" ROASTERS", " ROASTING CO")]:
        out = out.replace(a, b)
    if rng.random() < 0.3:
        out = out.replace(" ", "  ", 1)
    return out


fi = 1
for r in lactalis_customers.sample(70, random_state=SEED).itertuples():
    fid = f"FON-QLD-{fi:04d}"
    f_cust.append((fid, variant(r.name), r.channel, r.state, r.postcode if rng.random() > 0.15 else str(int(r.postcode) + 1)))
    truth.append((r.customer_id, fid, "same customer"))
    fi += 1
for _ in range(55):
    nm = f"{rng.choice(first)} {rng.choice(kind)} {rng.choice(towns)}".upper()
    f_cust.append((f"FON-QLD-{fi:04d}", nm, rng.choice(["Food service", "Independent"]), "QLD", f"{rng.integers(4000, 4620)}"))
    fi += 1
f_cust += [("FON-QLD-0412", "NATIONAL RETAILER B QLD", "Major retail", "QLD", "4073"),
           ("FON-QLD-0877", "INDEPENDENT GROCERS - QLD BUYING GROUP", "Independent", "QLD", "4000")]
truth += [("RET-B", "FON-QLD-0412", "same customer"), ("IND", "FON-QLD-0877", "same customer (buying group)")]
fonterra_customers = pd.DataFrame(f_cust, columns=["customer_id", "name", "channel", "state", "postcode"]) \
    .drop_duplicates("customer_id", keep="last")
customer_truth = pd.DataFrame(truth, columns=["lactalis_id", "fonterra_id", "relationship"])

lactalis_products = sku_df[["sku", "name", "brand", "subcat", "size_l", "units_per_case"]].copy()
fon_items = [
    ("FP1001", "Mainland Tasty Cheese Block 500g", "Mainland", "cheese"),
    ("FP1002", "Mainland Tasty Cheese Block 1kg", "Mainland", "cheese"),
    ("FP1003", "Mainland Colby Cheese Slices 500g", "Mainland", "cheese"),
    ("FP1004", "Mainland Vintage Cheese 250g", "Mainland", "cheese"),
    ("FP1101", "Perfect Italiano Mozzarella Grated 500g", "Perfect Italiano", "cheese"),
    ("FP1102", "Perfect Italiano Parmesan Grated 250g", "Perfect Italiano", "cheese"),
    ("FP1103", "Perfect Italiano Pizza Plus Grated 750g", "Perfect Italiano", "cheese"),
    ("FP1201", "Western Star Original Butter 500g", "Western Star", "butter"),
    ("FP1202", "Western Star Spreadable 375g", "Western Star", "butter"),
    ("FP1203", "Western Star Unsalted Butter 250g", "Western Star", "butter"),
]
fonterra_products = pd.DataFrame(fon_items, columns=["product_id", "name", "brand", "category"])

price_rows = []
for c in ["RET-A", "RET-B", "RET-C"]:
    for s in sku_df.itertuples():
        list_price = round(s.size_l * 1.55 * s.units_per_case * (1.6 if s.subcat in SINGLES else 1.0), 2)
        price_rows.append(("Lactalis", c, s.sku, list_price, "2026-07-01"))
for c, fid in [("RET-B", "FON-QLD-0412")]:
    for s in sku_df.sample(9, random_state=1).itertuples():
        lp = round(s.size_l * 1.55 * s.units_per_case * (1.6 if s.subcat in SINGLES else 1.0) * rng.uniform(0.93, 1.04), 2)
        price_rows.append(("Fonterra legacy", fid, s.sku, lp, "2026-04-01"))
price_lists = pd.DataFrame(price_rows, columns=["source", "customer_id", "sku", "price_per_case_aud", "effective_from"])

# ---------------------------------------------------------------- write files
cal_out = cal.rename(columns={"max_temp_c": "max_temp_c", "rain_mm": "rain_mm"})
cal_out["weather_kind"] = np.where(cal_out["date"] >= TODAY, "forecast", "observed")
files = {
    "calendar_weather.csv": cal_out,
    "products.csv": sku_df,
    "customers.csv": cust_df,
    "promotions.csv": promos,
    "orders.csv": orders_out,
    "dc_inventory_baseline.csv": inventory,
    "writeoffs.csv": writeoffs,
    "milk_intake.csv": milk,
    "farms.csv": farms,
    "plant_lines.csv": lines,
    "master_lactalis_customers.csv": lactalis_customers,
    "master_fonterra_customers.csv": fonterra_customers,
    "master_customer_truth.csv": customer_truth,
    "master_lactalis_products.csv": lactalis_products,
    "master_fonterra_products.csv": fonterra_products,
    "price_lists.csv": price_lists,
}
for name, df in files.items():
    df.to_csv(OUT / name, index=False, date_format="%Y-%m-%d")
    print(f"{name:34s} {len(df):>8,d} rows")
