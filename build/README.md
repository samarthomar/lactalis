# Model output (Phase 2)

Made by `scripts/train_forecast.py` from the synthetic data; charts by `scripts/report_phase2.py`.
The demo (Phase 4) reads `model_output.json`. All numbers come from synthetic data.

| Key | What it holds |
| --- | --- |
| `meta` | Dates, model type (LightGBM, Poisson), level (SKU x customer x day) |
| `accuracy` | Back-test Jan to 11 Oct 2026: today's method 25.8% error vs AI forecast 16.0% (38% less error) |
| `variants` | Error for every on/off mix of weather, holidays and promotions (all, iced coffee, hero series, hot days, holidays), for the demo toggles |
| `segments`, `by_sku` | Error by situation and by product |
| `backtest_series` | Last 10 weeks: actual vs today's method vs each model variant (hero series, iced coffee, all products) |
| `value` | Replay of Jan to Oct 2026 through the same stock rules: write-offs 1.63% to 1.04% (36% fewer), orders filled 98.7% to 99.8%. `ml_resized` (smaller buffers) is upside only, not a claim |
| `forecast` | 12 to 25 Oct 2026 per SKU x customer: forecast, 80% range, today's method, and a waterfall (normal day, holidays, promotion, weather) in cases |
| `whatif` | Wed 14 Oct: cases per SKU for 14 to 42°C x Ice Break 500mL promotion depth at Retailer A |
| `milk_check`, `milk_meta` | Raw milk needed vs expected and silo balance per day (silo start is an assumption) |
| `line_check` | Nambour line load vs capacity per day |
| `products`, `customers` | Reference lists |

Key demo facts produced here:
- Mon 12 Oct: today's method says 129 cases of Ice Break 500mL for Retailer A (it copies the King's Birthday holiday); the AI says 413.
- Wed 14 Oct: normal 321 + promotion 206 + heat 68 = 595 cases (today's method: 397).
- Breaka 750mL loses about 26 to 31 cases a day at Retailer A during the Ice Break promotion.
- Nambour line 3 runs at about 104% on Thu 15 and Fri 16 Oct; the silos run about 3,000 L short on Fri 16 Oct.

# Agent answer library (Phase 3)

Made by `scripts/build_agent_library.py` from `model_output.json` and `data/`. Review copy: `agent_library.md`.

| Key in `agent_library.json` | What it holds |
| --- | --- |
| `briefing` | Morning briefing: 3 items plus "also today", each linked to an alert |
| `alerts` | 6 agent alerts (demand, shelf-life, supply, order): what, why, confidence, impact, options, approve/reject outcome and audit text |
| `qa` | 20 prepared questions with keywords; `template` entries (temperature, promotion depth) fill numbers from `whatif_lookup` |
| `fallback` | Reply for unmatched questions plus the 3 closest questions; stopwords for the matcher |
| `whatif_lookup` | Wed 14 Oct cases by temperature x promotion depth (hero product all customers, hero at Retailer A, iced coffee total) |
| `matching` | Real record matching of 127 Fonterra vs 183 Lactalis customers, scored against the answer key; review queue and examples |
| `audit_seed` | First audit log rows shown at demo start |
| `routing_tests` | 25 typed questions and where the matcher sends them (the demo's JavaScript uses the same scoring) |

Matcher: a single word scores 1 if it appears as a whole word; a phrase or a keyword with symbols scores 2 (1 for symbols) if it appears in the text; plus 0.5 per word shared with the sample question. Best score of 1 or more answers; otherwise use the fallback.

# Demo file (Phase 4)

`scripts/build_demo.py` inlines `web/styles.css`, `web/charts.js`, `web/app.js`, the logo (`web/assets/techm_logo.png`) and the data into one offline file: `build/lactalis_demo.html` (about 550 KB, no internet needed). Re-run it after any change to data, model or answers:

    .venv\Scripts\python -X utf8 scripts\build_agent_library.py
    .venv\Scripts\python -X utf8 scripts\build_demo.py

Presenter keys: 1-6 or arrow keys change scene; Esc closes panels; Reset (top right) starts again.
Brand: Tech Mahindra Logo Usage Guidelines V.01 (Oct 2025): Mahindra Red #E31837, Steel Grey #4D4D4F, Clarity and Anchor greys, Impact Red, Blueprint Navy.

# Label check (Phase 5)

`web/labels.json` holds three cartons for a fictional brand (Sunvale Dairy Co.). Scene 6 runs a small rules engine (`checkLabel` in `web/app.js`) on them: allergens in bold and in the "Contains" statement, nutrition claims against Schedule 4 conditions, Health Star Rating graphic vs panel and recipe, per-serve arithmetic, origin wording, and "fresh" with reconstituted ingredients. Findings: Hazelnut Iced Coffee 5, Farm Fresh Lite Milk 3, Kids Strawberry Milk 2. A person sends each to the team that owns the fix (food safety, marketing, nutrition, legal, procurement) or marks it not an issue; both go to the audit log.

# Testing (Phase 6)

    .venv\Scripts\python -X utf8 scripts\check_numbers.py

`scripts/check_numbers.py` recomputes every alert number from the source tables (forecast, line load, silo balance, duplicates, price conflicts, matching counts, accuracy, value, label per-serve arithmetic) and fails if any shown figure disagrees. Last run: 0 failures.

Checked on 12 Oct 2026:
- Offline: no external links in the file; opened from disk in Chrome and Edge with the network blocked, renders fully.
- Screen sizes: 1024x768, 1280x720, 1366x768 and 1920x1080, all six scenes: nothing cut off, no "NaN"/"undefined" text.
- Full click-through: matching and steward queue, morning check, all six decisions (one rejected with a reason) with simulated SAP references, plant before/after, all three cartons reviewed, chat, Reset part-way through an animation.
- Chat: 27 answers, 47 routing tests pass in Python and in the browser.

Fixed during testing: scene tabs collapsed to zero height (now always shown); header and scene 1 squeezed below 1200 px; Reset during an animation let the old timer finish into the new run; two quick chat questions could drop an answer; legacy-codes chart now marks October as month to date (the alert's 6.9% is the last 4 weeks). Added answers: SAP connection, what we need from Lactalis, other regions and products, data security, pilot cost.

# Presenter script (Phase 7)

Claude Docs: https://claude.ai/code/artifact/77a38bb0-0f7c-4e0c-9bcb-1acdd74bc22e (run of show, talk track and clicks per scene, tough questions, recovery, rehearsal plan). Its click path was dry-run in the browser and every quoted number matched the screen.

Fixed during the dry run: the Retailer A what-if used the all-customer temperature effect (gave 326 cases at 28°C, negative at low temperatures); `train_forecast.py` now stores the model's prediction for the promoted customer (`whatif.hero_customer`) and `check_numbers.py` guards it. Sibling loss figures now round like the text (160, not 159). Chat: 28 answers, 52 routing tests.

## Demo admin login

The page opens on a sign-in screen (Tech Mahindra branding, "Prepared for Lactalis Australia"). It is a front door for the presentation only, not real security: everything runs in the browser.

- Demo username: `admin`. Demo password: `Lactalis@2026` (pre-filled, so the presenter only clicks **Sign in**). A wrong password shows an error.
- Role list: Administrator, Demand planner, Plant planner (label only; every role sees the same demo).
- Signing in adds an audit-log entry. The session stays signed in across a page refresh in the same tab; closing the tab signs out. **Reset** keeps you signed in; the red initial button in the header signs out.
- In a pilot this would be replaced by Lactalis single sign-on.
