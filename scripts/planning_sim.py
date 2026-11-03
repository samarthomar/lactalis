"""Shared DC planning simulation: same rules for today's method and the ML forecast.

Each day, production for day d is planned from a forecast of day d's orders:
    produce = forecast x K(sub-category) - usable stock,   capped by Nambour line capacity.
Stock ships oldest first; stock with less than MIN_LEFT of its shelf life left is written off.
Constants mirror scripts/generate_data.py.
"""
from __future__ import annotations

import math

import pandas as pd

MIN_LEFT = 0.80
COVER_K = {"white_take_home": 1.45, "white_single": 1.45, "barista": 1.45, "lactose_free": 2.2,
           "flavoured_milk": 2.1, "iced_coffee": 2.3}
SHORT_LIFE_ICED_K = 2.0
LINE_CAP = {"L1": 9000, "L2": 2500, "L3": 7200}
PRE_CLOSE_CAP = {"L1": 14000, "L2": 4000, "L3": 7200}
SOUTH_BRIS_CLOSE = pd.Timestamp("2026-07-10")
RAMP_END = pd.Timestamp("2026-08-09")


def cover_k(subcat: str, life: int) -> float:
    if subcat == "iced_coffee" and life < 21:
        return SHORT_LIFE_ICED_K
    return COVER_K[subcat]


def simulate(actual: pd.DataFrame, forecast: pd.DataFrame, products: pd.DataFrame, buffer_scale: float = 1.0) -> pd.DataFrame:
    """actual, forecast: index = dates, columns = SKUs (cases per day). Returns daily rows per SKU.
    buffer_scale shrinks or grows the safety part of the cover target (K - 1)."""
    info = products.set_index("sku")
    skus = list(actual.columns)
    batches = {s: [[1, actual[s].iloc[:7].mean() * 1.5]] for s in skus}
    rows = []
    for i, d in enumerate(actual.index):
        want = {}
        for s in skus:
            life = int(info.at[s, "shelf_life_days"])
            usable = sum(q for a, q in batches[s] if life - a >= math.ceil(MIN_LEFT * life))
            k = 1 + (cover_k(info.at[s, "subcat"], life) - 1) * buffer_scale
            want[s] = max(0.0, float(forecast.at[d, s]) * k - usable)
        cap = PRE_CLOSE_CAP if d < SOUTH_BRIS_CLOSE else LINE_CAP
        ramp = 0.85 if SOUTH_BRIS_CLOSE <= d <= RAMP_END else 1.0
        produced = {}
        for line in ("L1", "L2", "L3"):
            members = [s for s in skus if info.at[s, "line"] == line]
            need = sum(want[s] for s in members)
            scale = min(1.0, cap[line] * ramp / need) if need > 0 else 1.0
            for s in members:
                produced[s] = round(want[s] * scale)
        for s in skus:
            life = int(info.at[s, "shelf_life_days"])
            min_left = math.ceil(MIN_LEFT * life)
            b = batches[s]
            b.append([1, produced[s]])
            demand = float(actual.at[d, s])
            remaining = demand
            for batch in sorted(b, key=lambda x: -x[0]):
                if life - batch[0] < min_left or remaining <= 0:
                    continue
                take = min(batch[1], remaining)
                batch[1] -= take
                remaining -= take
            expired = sum(q for a, q in b if life - a < min_left and q > 0)
            b[:] = [[a + 1, q] for a, q in b if q > 0 and life - a >= min_left]
            rows.append((d, s, produced[s], demand, demand - remaining, remaining, expired, sum(q for _, q in b)))
    return pd.DataFrame(rows, columns=["date", "sku", "produced", "ordered", "shipped", "short", "written_off", "stock"])
