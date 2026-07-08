# ScreenEdge — Indian equities dashboard (static + AG Grid)

Migration of the Streamlit app to a **static frontend + one serverless function**.
Free, always-on hosting (Cloudflare Pages); the data is a daily batch artifact, so ~95%
of the app is pure static JSON and needs no running server.

## Architecture
```
stockradar-web/
├── scripts/build_data.py    # DAILY BUILD — reuses the real scoring.py/insights.py, emits public/data/*.json
├── public/                  # the static site Cloudflare Pages serves
│   ├── index.html           # 5-tab shell
│   ├── app.js               # Stocks tab (AG Grid) + stock card  ← Phase 1 done
│   ├── styles.css           # dark theme
│   └── data/                # stocks.json, indices.json, global.json  (generated — git-ignored or committed by CI)
├── functions/api/stock.js   # the ONLY backend: serverless proxy for live Yahoo/NSE (stock card, SIP, events)
└── dev-server.mjs           # local preview only
```

## Build the data (reuses your existing Python modules — single source of truth)
```bash
python scripts/build_data.py          # reads ../StockRadar-India repo's data/ + modules
# override repo location:  STOCKRADAR_REPO=/path/to/StockRadar-India python scripts/build_data.py
```
In production: add this as the last step of the existing daily GitHub Action (after `fetch_*.py`),
then commit `public/data/*.json`. Numbers are identical to Streamlit because it calls the same
`add_scores()` / `add_insights()`.

## Run locally
```bash
python scripts/build_data.py          # 1. build data
node dev-server.mjs                    # 2. serve → http://localhost:5056
```

## Deploy (free, always-on)
Push to a repo, connect Cloudflare Pages: build output dir = `public`, functions auto-detected from `functions/`.
No cold starts, no keep-alive hacks. (Vercel/Netlify equivalent.)

---

## Migration roadmap

- [x] **Phase 0 — Foundation**: Python build reusing real scoring/insights → `stocks/indices/global.json` (822×95, verified identical to Streamlit).
- [x] **Phase 1 — Shell + Stocks**: 5-tab nav, dark theme; Stocks/All-Stocks with 5 view tabs (Overview/Technicals/Returns/Risk/Fundamentals), global sort across tabs, filters, CSV export, slide-in stock card with lazy live-data hook.
- [x] **Phase 1b — Stocks rest**: Pre-built Screens (21, membership precomputed via real `run_screen`), Custom Screener (condition builder, ALL/ANY), advanced filters (market cap, RSI, regime/drawdown/index-membership).
- [x] **Phase 2 — Dashboard**: Spotlight, Market Overview (breadth tiles / regime dist / drawdown dist / regime-by-cap), Quick Picks (5 horizons, "view all" into grid), What Changed Today (day-over-day via real `compute_changes` on last 2 snapshots → `changes.json`), Sector Rotation (bar chart + click drill-down), Signals (bullish/bearish), Sector Top 5 (rank by any of 79 columns, both directions). Overview grid includes Industry; Quick Picks/Signals/Changes have "View all N → Stocks grid".
- [x] **Phase 3 — Index Dashboard**: Indian Indices (Category + Available ETF merged from `etf_mapping.csv`) + Global & Commodities grids; drill-down with A/D cards, gainers/losers (5/10/15 toggle), RS-vs-selected-index (1M/3M/6M) computed on the fly, across 5 view tabs. In `public/index-dash.js`.
- [x] **Phase 4a — Tools**: Stock Card (enhanced: reason line, description, analyst consensus, screen membership, peers), Compare (35+ metrics grouped, best-value highlight, Div Yield/Payout added, Universe Rank dropped), Watchlist (localStorage-savable, summary), Methodology (renders METHODOLOGY.md via marked). In `public/tools.js`.
- [x] **Phase 4b — Events + SIP (live)**: FII/DII cards, Corporate Actions (categorized + filters), Bulk/Block deals — via serverless NSE proxy (`functions/api/{fiidii,deals,corpactions}.js`, `_nse.js` cookie priming); SIP Calculator via `functions/api/history.js` (Yahoo monthly) + JS XIRR (bisection). Verified against live NSE + Yahoo through the local functions runtime (`dev-server.mjs` now executes `functions/`). In `public/events.js` + `public/tools.js`.
- [x] **Phase 5 — Polish + deploy prep**: mobile responsive (nav/substabs scroll, grids, panel full-width); deploy artifacts — `.gitignore`, `package.json`, `.github/workflows/build-and-deploy.yml.sample`, `DEPLOY.md`. Actual Cloudflare Pages connect is the owner's one-time step (see DEPLOY.md).

## Notes / decisions
- **AG Grid Community** (MIT, free) via CDN. Native sort/filter/virtualization handles 800+ rows.
- Green/red + insight/regime coloring via `cellClassRules` / cellRenderers (see `app.js` VIEWS).
- Backend Python modules (`scoring`, `insights`, `screens`, `history`, `config`) are **reused as build-time code** — never queried at request time.
- Live features (Yahoo/NSE) are the only runtime server need → one serverless function.
