# Synthetic data: Queensland fresh-milk pilot

All data here is **synthetic**, made by `scripts/generate_data.py` (fixed seed, so it rebuilds identically).
No Lactalis data is used. Demo "today" is **Monday 12 October 2026**; history runs 1 Jul 2024 to 11 Oct 2026,
and the next 14 days hold only the calendar, the weather forecast and the scenario promotion.

## Files

| File | Rows | What it holds |
| --- | --- | --- |
| `orders.csv` | ~86k | Daily orders by customer, SKU and requested delivery date; shipped cases; promotion; source plant; legacy Fonterra codes and duplicates |
| `dc_inventory_baseline.csv` | ~13k | Richlands DC per SKU per day under today's planning: produced, ordered, shipped, short, written off, closing stock, days of cover |
| `writeoffs.csv` | ~8k | Write-offs by date, SKU and reason |
| `calendar_weather.csv` | 847 | Dates, school and public holidays, max temperature, rain; future 14 days are a "forecast" |
| `promotions.csv` | ~260 | Retailer promotions (Wed to Tue weeks), depth and mechanic, including the demo scenario |
| `products.csv` | 16 | SKUs with brand, sub-category, pack, case size, shelf life, milk content, trend, weather sensitivity, line |
| `customers.csv` | 6 | Customer groups (retailers anonymised as A, B, C) |
| `milk_intake.csv` / `farms.csv` | ~43k / 52 | Daily raw milk collected per synthetic farm, Nambour catchment |
| `plant_lines.csv` | 3 | Nambour lines, capacity, extra-shift capacity, changeover time |
| `master_*.csv`, `price_lists.csv` | | Lactalis and Fonterra-legacy customer and product records, the true matches, and conflicting price lists, for the record-matching scene |
| `validation.png` | | Six charts checking the data behaves like fresh-dairy demand |

## Patterns built in

- Weekday pattern by channel (Friday peak, low Sunday).
- Hot days lift iced coffee (about +40% at 34°C) and flavoured milk; cold or wet days reduce them.
- School holidays: singles down about 10%, take-home 2L and 3L up about 5%, food service down.
- Public holidays: deliveries about 70% lower on the day and 25% higher the day before; Christmas build-up.
- Trends: lactose free +9% a year, barista +5%, full cream -2%.
- Promotions at retailers A, B and C: one per product family at a time; lift by depth; build-up the day before; dip for 3 days after; sibling products lose sales.
- From 1 Apr 2026, some Retailer B and independent orders arrive under old Fonterra customer codes (18% falling to 6%), plus occasional duplicate orders that come back as returns.
- South Brisbane closes 10 Jul 2026: white milk moves to Nambour; four-week ramp-up at 85% capacity.
- Milk intake: spring peak, summer dip, heat-stress dips after hot days, about -2% a year.

## Today's planning (the baseline the model must beat)

Planners copy the same weekday last week, adjust for known promotions, and top stock up to a buffer. They do not use weather.
Result: about **1.5% of production written off** and about **99% of orders filled**, with write-off spikes after Easter and Christmas.

## Assumptions to validate with a dairy expert

| Item | Value used |
| --- | --- |
| Shelf life | White 14 days; Zymil 21; Oak and Breaka 16; Ice Break 21 |
| Customer acceptance | At least 80% of shelf life must remain at delivery |
| Volumes | About 13,700 cases a day across 16 SKUs (Queensland pilot) |
| Nambour capacity after the move | Line 1: 9,000; Line 2: 2,500; Line 3: 7,200 cases a day |
| Holiday and school dates | Approximate Queensland dates; check against official calendars |
| Product names | Real Lactalis brands with illustrative pack names; retailer names anonymised |
