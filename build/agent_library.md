# Agent answer library (Phase 3)

Made by `scripts/build_agent_library.py` from `build/model_output.json` and `data/`. Synthetic data.
**On-screen disclosure:** Agent answers are pre-configured from the model results for this demo. In production a live AI agent would generate them from your data.

## Morning briefing

> Good morning. Mon 12 Oct: 3 things need your attention today.

1. Heat plus the 40% off Ice Break Iced Coffee 500mL promotion: plan 595 cases for National Retailer A on Wed 14 Oct, not 397.
2. Nambour line 3 is over capacity on Thu 15 Oct and Fri 16 Oct. Make 562 cases earlier on spare time; no overtime needed.
3. Milk silos run about 3,143 L short on Fri 16 Oct. Moving one white-milk run to Sat 17 Oct fixes it at no extra cost.

Also today:
- Today's method under-calls Mon 12 Oct because it copies the King's Birthday holiday
- Cut Ice Break Iced Coffee 750mL, Oak Iced Coffee 600mL, Breaka Iced Coffee 750mL, Ice Break Iced Coffee Less Sugar 500mL at National Retailer A during the promotion
- Old Fonterra customer codes still on 7% of orders

_Every suggestion needs a person to approve it. Answers on this screen are pre-configured for the demo._

## Alerts

### A1 · Demand agent · high
**Ice Break Iced Coffee 500mL at National Retailer A: plan 595 cases for Wed 14 Oct, not 397**

Heat (Wed 14 Oct, Thu 15 Oct, Fri 16 Oct) arrives in the same week as the 40% off promotion (Wed 14 Oct to Tue 20 Oct). The AI forecast is 595 cases for Wed 14 Oct; today's method says 397.

Why:
- Normal Wednesday: 321 cases
- Promotion 40% off: +206 cases
- Heat 34°C (normal 26°C): +68 cases

Confidence: Medium (420 to 792 cases (80% range)). On promotion days the forecast error was 17% vs 28% for today's method.
Impact: Over the promotion week the AI expects 4,145 cases vs 2,386 from today's method: 1,759 cases (about A$26k of sales at list price) at risk of going short.
Suggestion: Raise the Ice Break Iced Coffee 500mL plan for National Retailer A to the AI forecast for Wed 14 Oct to Tue 20 Oct.
- Approve → Plan updated: 4,145 cases over the promotion week. Nambour line 3 load is checked next (see the supply alert).
- Reject → Plan stays at today's method (2,386 cases). Expected shortfall about 1,759 cases. The agent will flag this again if orders run ahead of plan.

### A2 · Demand agent · medium
**Today's method under-calls Mon 12 Oct because it copies the King's Birthday holiday**

Today's method copies last Mon 5 Oct (King's Birthday, a public holiday) and plans 129 cases of Ice Break Iced Coffee 500mL for National Retailer A. The AI knows it was a holiday and forecasts 413.

Why:
- Holidays were the weakest point of today's method in the back-test: 87% error vs 20% for the AI

Confidence: Medium (292 to 551 cases (80% range)). On public holidays and the day before the forecast error was 20% vs 87% for today's method.
Impact: 284 cases more for Mon 12 Oct on this one product and customer.
Suggestion: Use the AI forecast for the week after any public holiday.
- Approve → Rule saved: the week after a public holiday uses the AI forecast by default.
- Reject → No change. The planner adjusts post-holiday weeks by hand as today.

### A3 · Shelf-life agent · medium
**Cut Ice Break Iced Coffee 750mL, Oak Iced Coffee 600mL, Breaka Iced Coffee 750mL, Ice Break Iced Coffee Less Sugar 500mL at National Retailer A during the promotion**

Shoppers switch to the discounted Ice Break Iced Coffee 500mL. Its neighbours sell less: Breaka Iced Coffee 750mL loses about 24 to 31 cases a weekday. Today's method does not see this and would plan 258 cases too many.

Why:
- Ice Break Iced Coffee 750mL: 311 fewer cases over the week
- Oak Iced Coffee 600mL: 170 fewer cases over the week
- Breaka Iced Coffee 750mL: 160 fewer cases over the week
- Ice Break Iced Coffee Less Sugar 500mL: 120 fewer cases over the week
- Back-test error on products next to a promotion: 34% today vs 16% with the AI

Confidence: Medium (Based on past promotions in the same product family). Error on products next to a promotion: 16%.
Impact: About A$2,873 of stock (at cost) at risk of being written off. With 16 days of shelf life and customers needing 80% left, unsold stock has about 3 days to ship.
Suggestion: Lower the plan for these products at National Retailer A to the AI forecast for the promotion week.
- Approve → Plans lowered by 258 cases; frees Nambour line 3 capacity on the hot days.
- Reject → No change. Stock levels for these products will be watched daily for ageing.

### A4 · Supply agent · high
**Nambour line 3 is over capacity on Thu 15 Oct and Fri 16 Oct**

Line 3 (flavoured milk and iced coffee) needs 104% on Thu 15 Oct, 104% on Fri 16 Oct: 562 cases above its 7,200 cases a day.

Why:
- Promotion and heat both land on the iced coffee range
- Line 3 has 1,975 spare cases on Tue 13 Oct and Wed 14 Oct before the peak

Confidence: Medium (556 to 1,047 cases (80% range)). On hot days (over 32°C) the forecast error was 16% vs 23% for today's method.
Impact: Without action about 562 cases of iced coffee cannot be made in time for the hot days.
- Option (recommended): Make 562 cases earlier on Tue 13 Oct and Wed 14 Oct. Uses spare line 3 time; stock is made 1 to 3 days earlier and still has more than 80% of its 21-day shelf life when shipped. No overtime.
- Option: Book an extra shift on Thu 15 Oct. Adds up to 2,000 cases a day; overtime cost; keeps the plan as is.
Suggestion: Make 562 cases earlier on spare line 3 time; keep the extra shift as back-up.
- Approve → Production plan moved: line 3 back under 100% on Thu 15 Oct and Fri 16 Oct. Milk is used a day or two earlier; silos stay above zero on those days.
- Reject → Plan unchanged. The agent books a provisional extra shift request for the production manager.

### A5 · Supply agent · high
**Raw milk silos run about 3,143 L short on Fri 16 Oct**

Farm intake drops about 3% on hot days (Thu 15 Oct, Fri 16 Oct, Sat 17 Oct) while demand peaks. The silo balance goes below zero on Fri 16 Oct.

Why:
- Heat stress lowers cow yields
- Promotion and heat raise demand on Wed 14 Oct, Thu 15 Oct, Fri 16 Oct
- Assumption: silos start the week at 0.8 days of intake

Confidence: Medium (Silo starting level is an assumption). Intake is planned from the last 28 days of farm deliveries.
Impact: Shortfall of about 3,143 L on Fri 16 Oct.
- Option (recommended): Move 300 cases of Pauls Full Cream Milk 2L from Fri 16 Oct to Sat 17 Oct. Saves about 5,400 L on Fri 16 Oct; the silo ends the day at about 2,257 L. Line 1 on Sat 17 Oct goes to 67% and the silo still ends Sat 17 Oct at 24,274 L. Stock cover at the warehouse carries Fri 16 Oct orders. No extra cost; the Nambour scheduler confirms.
- Option: Buy spot milk. Order about 5,000 L from a third-party supplier for delivery on Thu 15 Oct. Extra cost.
Suggestion: Move the Pauls Full Cream Milk 2L run to Sat 17 Oct; keep a spot milk quote as back-up.
- Approve → Production plan updated: 300 cases of Pauls Full Cream Milk 2L moved to Sat 17 Oct. Silo on Fri 16 Oct now ends at about 2,257 L.
- Reject → No change. Risk stays open on the supply dashboard.

### A6 · Order agent · medium
**Old Fonterra customer codes still on 7% of orders**

Since 1 Apr 2026 some National Retailer B and Independent Grocers orders arrive under old Fonterra codes (FON-QLD-0412, FON-QLD-0877). The share fell from 17% in April to 7% in the last 4 weeks (858 order lines).

Why:
- 8 orders were keyed in twice (old and new code) and came back as 273 cases of returns
- 9 products have a different old Fonterra price for National Retailer B (-6% to +4%)

Confidence: High (Codes matched to customers in the record-matching step). Matching accuracy on auto-matches: 100.0%.
Impact: Duplicate returns cost about A$7,617 so far; legacy orders split one customer's demand across two codes, which hides it from planning.
Suggestion: Map the old codes to the Lactalis customers on intake, hold any order that repeats one under the other code, and use the Lactalis price list.
- Approve → Mapping rule active: old codes are translated on intake; possible duplicates are held for a check.
- Reject → No change. Customer service keeps checking old codes by hand.

## Questions and answers

| # | Question | Answer | Shows |
| --- | --- | --- | --- |
| Q1 | Why is the Ice Break Iced Coffee 500mL forecast so high on Wed 14 Oct? | Three things add up. A normal Wednesday at National Retailer A is 321 cases. The 40% off promotion adds 206. The 34°C heat (normal is 26°C) adds 68. Total 595 cases, likely range 420 to 792. Today's method says 397 because it only copies last week. | waterfall |
| Q2 | What if it is only 28°C on Wed 14 Oct? | At 28°C with the promotion, all customers together need about 3,910 cases of iced coffee on Wed 14 Oct, and 1,817 cases of Ice Break Iced Coffee 500mL. At the forecast 34°C it is 4,532 and 2,086. | whatif |
| Q3 | What if the promotion is 25% off instead of 40%? | At 25% off, National Retailer A needs about 563 cases of Ice Break Iced Coffee 500mL on Wed 14 Oct (595 at 40% off, 380 with no promotion). Iced coffee across all customers: 4,597 cases. The size of the lift is learned from 263 past promotions. | whatif |
| Q4 | How accurate is the forecast? | We replayed 2026-01-01 to 2026-10-11 day by day, forecasting 14 days ahead with forecast (not actual) weather. Today's method was 74.2% accurate; the AI was 84.0%. That is 38% less error. This is synthetic data: on real data we would aim for at least 20% less error in the pilot. | accuracy |
| Q5 | Where does the AI help most? | Biggest gains: public holidays and the day before 87% to 20% error; products next to a promotion 34% to 16% error; school holidays 31% to 15% error; all days 26% to 16% error. These are the days when copying last week goes wrong. | segments |
| Q6 | Why does today's method get Mon 12 Oct wrong? | It copies last Mon 5 Oct, which was the King's Birthday public holiday, so it plans only 129 cases of Ice Break Iced Coffee 500mL for National Retailer A. The AI knows it was a holiday and forecasts 413. In the back-test, holidays and the day before had 87% error with today's method and 20% with the AI. | monday |
| Q7 | Which products lose sales because of the promotion? | Shoppers switch to the discounted Ice Break Iced Coffee 500mL at National Retailer A. Over the promotion week: Ice Break Iced Coffee 750mL: 311 fewer cases over the week; Oak Iced Coffee 600mL: 170 fewer cases over the week; Breaka Iced Coffee 750mL: 160 fewer cases over the week; Ice Break Iced Coffee Less Sugar 500mL: 120 fewer cases over the week. Today's method would plan 258 cases too many, about A$2,873 at cost at risk of write-off. | siblings |
| Q8 | Can Nambour make enough this week? | Lines 1 and 2 are fine. Line 3 (flavoured milk and iced coffee) is over on Thu 15 Oct (104%) and Fri 16 Oct (104%), 562 cases in total. It has 1,975 spare cases before that, so making them earlier avoids overtime. An extra shift adds up to 2,000 cases a day if needed. | lines |
| Q9 | Do we have enough raw milk? | Not quite. Hot days cut farm intake by about 3%, and demand peaks at the same time. The silos end Fri 16 Oct about 3,143 L short. Moving 300 cases of Pauls Full Cream Milk 2L to Sat 17 Oct, when intake recovers and line 1 has room, leaves about 2,257 L. Buying about 5,000 L of spot milk is the back-up. Note: the silo starting level is an assumption. | milk |
| Q10 | How much could this save? | We replayed 2026-01-01 to 2026-10-11 (284 days) through the same stock rules, changing only the forecast. Write-offs fell from 1.63% to 1.04% of production (36% fewer) and orders filled rose from 98.73% to 99.84%. On this synthetic Queensland range that is about A$339k a year and 324,757 L of milk not wasted. Real gains will be smaller; the pilot target is at least 15% fewer write-offs. | value |
| Q11 | Which orders still use old Fonterra codes? | Since 1 Apr 2026 some National Retailer B and Independent Grocers orders arrive under old Fonterra codes (FON-QLD-0412, FON-QLD-0877). The share fell from 17% in April to 7% in the last 4 weeks (858 order lines). 8 orders were keyed in twice (old and new code) and came back as 273 cases of returns. | legacy |
| Q12 | How many Fonterra customers match our records? | We compared 127 Fonterra customer records with 183 Lactalis ones. 69 matched automatically (100.0% correct when checked against the answer key), 2 need a person to check, and 56 look like new customers. Overall 98.6% of the real pairs were found. | matching |
| Q13 | Are there price conflicts? | Yes. 9 products have an old Fonterra price for National Retailer B that differs from the Lactalis list by -6% to +4%. The largest gap is Breaka Iced Coffee 750mL. The agent flags these for the commercial team; it does not change prices. | prices |
| Q14 | What are we throwing away today? | In the last 12 months (synthetic): short-dated / expired in DC 89,394 cases; damaged in handling 1,999 cases; customer return: duplicate order under legacy Fonterra code 273 cases. Most short-dated stock is Pauls Full Cream Milk 2L, Pauls Reduced Fat Milk 2L, Pauls Full Cream Milk 3L. | writeoffs |
| Q15 | What data does the model use? | Order history by product, customer and day, plus three outside signals: the weather forecast, school and public holidays, and the promotion calendar (including promotions on neighbouring products). The model is LightGBM (Poisson), SKU x customer x day. Each signal was tested on and off: for iced coffee the error went from 26.0% with history only to 16.4% with all three. | signals |
| Q16 | Who decides? Does the AI change the plan by itself? | No. Agents suggest; a planner approves or rejects every change, and each decision is written to the audit log with the reason. Rules such as minimum shelf life, line capacity and price lists are never changed by an agent. | audit |
| Q17 | Is this real Lactalis data? | No. The data is synthetic, built to look like a Queensland fresh milk range after the Fonterra purchase and the South Brisbane closure. The forecast model is real and was trained on that data. Agent answers in this demo are pre-configured; in a pilot they would come from a live AI model reading your data. |  |
| Q18 | What would a pilot look like? | Start with one region and the fresh milk and iced coffee range. Connect order history, the promotion calendar, weather and plant data; run the forecast next to today's method; let planners approve agent suggestions. Pilot targets: at least 20% less forecast error and at least 15% fewer write-offs, measured on real data. |  |
| Q19 | Which days are hot this week? | Forecast maximums in Brisbane: Mon 12 Oct 28°C, Tue 13 Oct 30°C, Wed 14 Oct 34°C, Thu 15 Oct 35°C, Fri 16 Oct 33°C, Sat 17 Oct 29°C, Sun 18 Oct 27°C. Days over 32°C: Wed 14 Oct, Thu 15 Oct, Fri 16 Oct. On hot days the AI had 16% error vs 23% for today's method. | weather |
| Q20 | What is the total forecast for the promotion week? | For Ice Break Iced Coffee 500mL at National Retailer A, Wed 14 Oct to Tue 20 Oct: 4,145 cases (AI) vs 2,386 (today's method). Across all products and customers the AI forecasts 101,356 cases that week. | forecast |
| Q21 | What does the label check look for? | Allergens in bold and in the 'Contains' statement, nutrition claims against their conditions (for example 'good source of protein' needs 10 g per serve), the Health Star Rating graphic against the nutrition panel and the current recipe, per-serve arithmetic, origin wording, and 'fresh' wording on milk with reconstituted ingredients. The cartons here are a fictional brand. | label |
| Q22 | Does the label agent approve artwork by itself? | No. It finds and explains issues; the regulatory reviewer sends each one to the team that owns the fix (food safety, marketing, nutrition, legal, procurement) or marks it not an issue, and every decision is logged. It makes the check faster and more consistent; it does not replace sign-off. | label |
| Q23 | How does this connect to SAP? | In this demo the SAP step is simulated: each approval shows the change it would send. In a pilot the agents start read-only, using extracts of orders, the material and customer masters and the production plan. Writing approved changes back uses standard SAP interfaces agreed with your IT and security teams, and only after a person approves. | audit |
| Q24 | What would you need from Lactalis? | About two years of orders by product, customer and day; the promotion calendar; plant line capacities and the production plan; milk intake; write-offs; and both customer lists. Plus a few hours a week from a demand planner and a supply planner to review suggestions, and read-only data access agreed with IT. |  |
| Q25 | Can it cover other regions and products? | Yes. The same approach runs per region and per product range. The pilot starts with Queensland fresh milk and iced coffee because short shelf life makes errors costly. Other regions are added once accuracy is proven on real data; longer-life ranges such as cheese and yoghurt use the same models with their own shelf-life rules. |  |
| Q26 | Is our data safe? | In a pilot the data stays in an environment your IT security team approves, with role-based access and every action logged. Your data is not used to train public AI models. The exact set-up is agreed with your IT team before any data moves. |  |
| Q27 | What does the pilot cost? | The commercial proposal covers that separately. The pilot is fixed in scope and time, and its value is measured against today's method on your own data before any wider roll-out. |  |
| Q28 | Why this forecasting model? | LightGBM is proven for demand forecasting at this scale: it handles thousands of product, customer and day combinations, retrains daily in minutes and shows which signals drove each number. Language models are used to explain results in plain words, not to produce the numbers. | waterfall |

Unmatched question → "That question isn't in the demo set yet. In a live system the agent would answer it from your data. Closest questions I can answer:" plus the 3 closest questions.

## Record matching (scene 1), scored against the answer key

- fonterra_records: 127
- lactalis_records: 183
- true_pairs: 72
- auto_matched: 69
- auto_correct: 69
- review: 2
- review_correct_suggestion: 2
- new: 56
- new_correct: 55
- auto_precision_pct: 100.0
- pairs_found_pct: 98.6
- thresholds: {'auto': 0.9, 'review': 0.75}
- method: name similarity (after removing PTY LTD, CO, BAR and accents) 65%, postcode 25%, channel 10%

Review queue (person decides):

| Fonterra record | Suggested Lactalis record | Score | Why | Answer key |
| --- | --- | --- | --- | --- |
| LIGHTHOUSE ROASTING CO BRISBANE | Lighthouse Roasters Brisbane | 0.841 | names 91% alike, postcode differs (4603 vs 4602), same channel | same customer |
| SUMMIT ROASTING CO CALOUNDRA | Summit Roasters Caloundra | 0.834 | names 90% alike, postcode differs (4354 vs 4353), same channel | same customer |

True pairs the matcher missed (it called them new customers):
- INDEPENDENT GROCERS - QLD BUYING GROUP -> really Independent Grocers (best score 0.342)

Closest look-alikes correctly kept apart (new customers):
- BAY FOODSTORE CALOUNDRA vs Bean Foodstore Caloundra (0.709)
- RIVERSIDE CAFE BEAUDESERT vs Riverside Deli Toowoomba (0.695)
- COASTAL GROCER CABOOLTURE vs Market Eatery Caboolture (0.674)
- LIGHTHOUSE CAFE CLEVELAND vs Lighthouse Roasters Cleveland (0.664)
- MARKET ROASTERS MAROOCHYDORE vs Creek Roasters Maroochydore (0.664)

## Typed-question routing test

| Question | Expected | Got | OK |
| --- | --- | --- | --- |
| why so many cases of ice break on wednesday | Q1 | Q1 | yes |
| explain the 595 | Q1 | Q1 | yes |
| what if it's 26 degrees | Q2 | Q2 | yes |
| what happens at 40°C | Q2 | Q2 | yes |
| what if we only do 25% off | Q3 | Q3 | yes |
| how accurate is it | Q4 | Q4 | yes |
| can I trust the forecast | Q4 | Q4 | yes |
| where does it help the most | Q5 | Q5 | yes |
| why is monday wrong | Q6 | Q6 | yes |
| does breaka lose sales | Q7 | Q7 | yes |
| do we need overtime at nambour | Q8 | Q8 | yes |
| is there enough milk friday | Q9 | Q9 | yes |
| what's the ROI | Q10 | Q10 | yes |
| how much money will we save | Q10 | Q10 | yes |
| old fonterra codes | Q11 | Q11 | yes |
| how good is the customer matching | Q12 | Q12 | yes |
| any price conflicts | Q13 | Q13 | yes |
| how much do we waste | Q14 | Q14 | yes |
| what inputs does the model use | Q15 | Q15 | yes |
| does the AI decide on its own | Q16 | Q16 | yes |
| is this real data | Q17 | Q17 | yes |
| what would a pilot look like | Q18 | Q18 | yes |
| which days are hot | Q19 | Q19 | yes |
| total for the promotion week | Q20 | Q20 | yes |
| what does the label checker look for | Q21 | Q21 | yes |
| check the allergens on the carton | Q21 | Q21 | yes |
| who signs off the artwork | Q22 | Q22 | yes |
| how sure are you | Q4 | Q4 | yes |
| how confident is the forecast | Q4 | Q4 | yes |
| does it replace planners | Q16 | Q16 | yes |
| what about SAP | Q23 | Q23 | yes |
| how does it connect to our systems | Q23 | Q23 | yes |
| what do you need from us | Q24 | Q24 | yes |
| what's wrong with the label | Q21 | Q21 | yes |
| is the iced coffee carton compliant | Q21 | Q21 | yes |
| is the forecast any good | Q4 | Q4 | yes |
| what happens on public holidays | Q6 | Q6 | yes |
| why is monday so low | Q6 | Q6 | yes |
| what about the old fonterra prices | Q13 | Q13 | yes |
| can it handle other states | Q25 | Q25 | yes |
| what about cheese | Q25 | Q25 | yes |
| who is accountable if it's wrong | Q16 | Q16 | yes |
| is our data safe | Q26 | Q26 | yes |
| how much does this cost | Q27 | Q27 | yes |
| can I see the audit trail | Q16 | Q16 | yes |
| how does the AI know about the weather | Q15 | Q15 | yes |
| is this our data | Q17 | Q17 | yes |
| are the agent answers live AI | Q17 | Q17 | yes |
| what does it cost | Q27 | Q27 | yes |
| why should we believe 36% | Q10 | Q10 | yes |
| why LightGBM, not a newer AI model | Q28 | Q28 | yes |
| who won the footy | None | None | yes |