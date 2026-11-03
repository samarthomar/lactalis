"""Phase 4: assemble the single offline demo file -> build/lactalis_demo.html

Inlines web/styles.css, web/charts.js, web/app.js, the TechM logo and the data
(build/model_output.json, build/agent_library.json and a few extra tables made here).
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
D, B, W = ROOT / "data", ROOT / "build", ROOT / "web"
model = json.loads((B / "model_output.json").read_text(encoding="utf-8"))
lib = json.loads((B / "agent_library.json").read_text(encoding="utf-8"))
products = pd.DataFrame(model["products"]).set_index("sku")
customers = pd.DataFrame(model["customers"]).set_index("customer_id")
lc = pd.read_csv(D / "master_lactalis_customers.csv", dtype=str).set_index("customer_id")
fcu = pd.read_csv(D / "master_fonterra_customers.csv", dtype=str).set_index("customer_id")
orders = pd.read_csv(D / "orders.csv", parse_dates=["date"])
prices = pd.read_csv(D / "price_lists.csv")
cal = pd.read_csv(D / "calendar_weather.csv", parse_dates=["date"])
promos = pd.read_csv(D / "promotions.csv", parse_dates=["start", "end"])
TODAY = pd.Timestamp(model["meta"]["today"])


def rec(df, i, cid=None):
    r = df.loc[i]
    return {"id": cid or i, "name": r["name"], "postcode": r["postcode"], "channel": r["channel"]}


extra: dict = {}

# scene 1: legacy Fonterra codes by month (Retailer B and Independent Grocers)
hist = orders[(orders.is_future == 0) & (orders.date >= "2026-04-01") & orders.customer_id.isin(["RET-B", "IND"])]
hist = hist.assign(month=hist.date.dt.strftime("%Y-%m"), legacy=hist.customer_code_received.str.startswith("FON"))
mon = hist.groupby("month").apply(lambda g: g.loc[g.legacy, "ordered_cases"].sum() / g.ordered_cases.sum(), include_groups=False)
extra["legacy_monthly"] = [{"month": m, "share": round(float(v), 4)} for m, v in mon.items()]
dups = orders[orders.is_duplicate == 1]
extra["duplicates"] = {"orders": int(len(dups)), "cases": int(dups.ordered_cases.sum())}
pc = prices[prices.source != "Lactalis"].merge(
    prices[(prices.source == "Lactalis") & (prices.customer_id == "RET-B")][["sku", "price_per_case_aud"]], on="sku",
    suffixes=("_legacy", "_lactalis"))
extra["price_conflicts"] = [{"sku": r.sku, "name": products.at[r.sku, "name"], "legacy": r.price_per_case_aud_legacy,
                             "lactalis": r.price_per_case_aud_lactalis,
                             "diff": round(r.price_per_case_aud_legacy / r.price_per_case_aud_lactalis - 1, 4)}
                            for r in pc.itertuples()]

# scene 1: steward queue (matcher's review items + records a rule sends to a person)
m = lib["matching"]
extra["review"] = [{"fonterra": rec(fcu, r["fonterra_id"]), "lactalis": rec(lc, r["suggested"]), "score": r["score"],
                    "why": r["why"], "truth": r["truth"], "kind": "review"} for r in m["review_queue"]]
for r in m["missed"]:
    tgt = r["true_lactalis_id"]
    target = rec(lc, tgt) if tgt in lc.index else {"id": tgt, "name": customers.at[tgt, "name"], "postcode": "various",
                                                    "channel": customers.at[tgt, "channel"]}
    extra["review"].append({"fonterra": rec(fcu, r["fonterra_id"]), "lactalis": target, "score": r["best_score"],
                            "why": "Buying groups and head offices always go to a person: one record covers many stores",
                            "truth": "same customer (buying group)", "kind": "rule"})
ids = [r["fonterra_id"] for r in m["auto_examples"][:5]] + [r["fonterra"]["id"] for r in extra["review"]] + \
      [r["fonterra_id"] for r in m["new_examples"][:2]]
# the product each sample customer buys most: milk on the Lactalis side, cheese and butter on the former Fonterra side
MAIN_L = {"Food service": ["PAU-BAR-2L", "PAU-FC-2L"], "Convenience": ["OAK-IC-600", "ICB-IC-500", "OAK-CHOC-600"],
          "Independent": ["PAU-FC-2L", "ZYM-LF-2L", "PAU-RF-2L"], "Major retail": ["PAU-FC-3L"], "Discount retail": ["PAU-FC-2L"]}
MAIN_F = {"Food service": ["FP1101", "FP1201", "FP1102"], "Convenience": ["FP1004", "FP1202"],
          "Independent": ["FP1001", "FP1201", "FP1003"], "Major retail": ["FP1002"], "Discount retail": ["FP1001"]}
lprod = pd.read_csv(D / "master_lactalis_products.csv").set_index("sku")["name"]
fprod = pd.read_csv(D / "master_fonterra_products.csv").set_index("product_id")["name"]


def with_product(r, table, names):
    opts = table.get(r["channel"], next(iter(table.values())))
    code = opts[sum(map(ord, r["id"])) % len(opts)]
    return {**r, "product_code": code, "product_name": names[code]}


extra["samples_fonterra"] = [with_product(rec(fcu, i), MAIN_F, fprod) for i in ids]
lids = [r["lactalis_id"] for r in m["auto_examples"][:5]] + [r["lactalis"]["id"] for r in extra["review"] if r["lactalis"]["id"] in lc.index]
lids += [i for i in lc.index if i.startswith("L1")][:3]
extra["samples_lactalis"] = [with_product(rec(lc, i), MAIN_L, lprod) for i in dict.fromkeys(lids)]

# scene 2: weather and promotion for the 14 days
fut = cal[cal.date >= TODAY]
extra["weather"] = [{"date": str(r.date.date()), "max_temp_c": float(r.max_temp_c), "rain_mm": float(r.rain_mm)} for r in fut.itertuples()]
sc = promos[promos.start >= TODAY].iloc[0]
extra["scenario"] = {"sku": sc.sku, "customer": sc.customer_id, "start": str(sc.start.date()), "end": str(sc.end.date()),
                     "depth": float(sc.depth), "mechanic": sc.mechanic}

# scene 4: what each approval sends to SAP (simulated)
A = {a["id"]: a for a in lib["alerts"]}
P = lambda s: products.at[s, "name"]
CN = lambda c: customers.at[c, "name"]
sap = {}
if "A1" in A:
    d = A["A1"]["data"]
    sap["A1"] = [["Object", "Demand plan"], ["Material", f"{d['sku']} · {P(d['sku'])}"], ["Customer", CN(d["customer"])],
                 ["Period", f"{sc.start:%d %b} to {sc.end:%d %b %Y}"], ["Change", f"{d['week_today']:,} → {d['week_ai']:,} cases"]]
if "A2" in A:
    sap["A2"] = [["Object", "Planning rule"], ["Rule", "Week after a public holiday uses the AI forecast"], ["Scope", "All products, Queensland"]]
if "A3" in A:
    d = A["A3"]["data"]
    sap["A3"] = [["Object", "Demand plan"], ["Materials", ", ".join(d["skus"])], ["Customer", CN(sc.customer_id)],
                 ["Change", f"−{sum(d['over_cases'].values()):,} cases over the promotion week"]]
if "A4" in A:
    d = A["A4"]["data"]
    sap["A4"] = [["Object", "Production plan"], ["Plant / line", "Nambour · line 3"],
                 ["Change", f"{d['cases_over']:,} cases moved to " + " and ".join(pd.Timestamp(k).strftime("%a %d %b") for k in d["spare_before"])]]
if "A5" in A:
    d = A["A5"]["data"]
    sap["A5"] = [["Object", "Production plan"], ["Plant / line", "Nambour · line 1"], ["Material", f"{d['defer_sku']} · {P(d['defer_sku'])}"],
                 ["Change", f"{d['defer_cases']:,} cases from {pd.Timestamp(d['date']):%a %d %b} to {pd.Timestamp(d['to_date']):%a %d %b}"]]
if "A6" in A:
    sap["A6"] = [["Object", "Order intake mapping"], ["Rule", "FON-QLD-0412 → RET-B; FON-QLD-0877 → IND"],
                 ["Also", "Hold an order that repeats one under the other code"]]
extra["sap"] = sap

extra["labels"] = json.loads((W / "labels.json").read_text(encoding="utf-8"))
data = {"model": model, "lib": lib, "extra": extra}
blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str).replace("</", "<\\/")
logo = "data:image/png;base64," + base64.b64encode((W / "assets" / "techm_logo.png").read_bytes()).decode()
html = (W / "index.html").read_text(encoding="utf-8")
html = html.replace("/*__CSS__*/", (W / "styles.css").read_text(encoding="utf-8"))
html = html.replace("__LACTALIS_LOGO__", "data:image/png;base64," + base64.b64encode((W / "assets" / "lactalis_logo.png").read_bytes()).decode())
html = html.replace("__LOGO__", logo)
html = html.replace("/*__DATA__*/", blob)
html = html.replace("/*__JS__*/", (W / "charts.js").read_text(encoding="utf-8") + "\n" + (W / "app.js").read_text(encoding="utf-8"))
out = B / "lactalis_demo.html"
out.write_text(html, encoding="utf-8")
print(f"saved {out} ({out.stat().st_size / 1024:,.0f} KB)")
# copy for static hosting (Vercel serves public/index.html)
(ROOT / "public").mkdir(exist_ok=True)
(ROOT / "public" / "index.html").write_text(html, encoding="utf-8")
