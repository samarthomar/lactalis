# Lactalis Australia - Demand Supply Control Tower demo

Working demo for the TechM pitch to Lactalis Australia. All data is synthetic.

## Layout
- `data/`   synthetic datasets generated in Phase 1
- `model/`  forecasting model training and back-test (Phase 2)
- `build/`  exported data file the demo reads (Phase 2-3)
- `web/`    the single offline HTML demo (Phase 4-5)

## Open the demo
Open `build/lactalis_demo.html` in Chrome or Edge. It runs offline; no install needed.

## Rebuild
Python 3.11. Python is used only at build time; the demo itself is one offline HTML file.

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python scripts/generate_data.py
.venv/Scripts/python scripts/train_forecast.py
.venv/Scripts/python scripts/build_agent_library.py
.venv/Scripts/python scripts/build_demo.py
.venv/Scripts/python scripts/check_numbers.py
```

## Source of requirements
BRD: Demand Supply Control Tower (Claude Docs; written under the earlier name Milk-to-Shelf Control Tower).

## Hosting on Vercel
`vercel.json` serves `public/index.html` as a static site (no install, no build). `middleware.js` asks for a password before the page loads:

1. Vercel project → Settings → Environment Variables → add `DEMO_PASSWORD` (any username is accepted).
2. Redeploy. Without `DEMO_PASSWORD` the site stays locked.

The demo's own admin sign-in screen is presentation only, not security.
