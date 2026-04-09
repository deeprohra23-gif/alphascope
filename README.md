# StockRadar India

Technical + Fundamental screener for 880+ Indian stocks across 50 indices, built with Streamlit.

---

## Repo Structure

```
├── app.py                      ← Streamlit entry point
├── config.py                   ← Column definitions, screen rules, color maps
├── scoring.py                  ← Composite scoring (Technical / Momentum / Fundamental)
├── styling.py                  ← Unified DataFrame styling
├── screens.py                  ← Pre-built screen filter logic
├── requirements.txt            ← App dependencies
├── requirements-scripts.txt    ← Data script dependencies
│
├── data/
│   ├── technicals.csv          ← Daily: stock technicals (auto-updated)
│   ├── indices_technicals.csv  ← Daily: index technicals (auto-updated)
│   ├── global_technicals.csv   ← Daily: global/commodities (auto-updated)
│   ├── fundamentals.csv        ← Monthly: scraped from screener.in (manual)
│   ├── index_constituents.csv  ← Quarterly: index membership (manual)
│   └── nifty500_symbols.csv    ← Symbol list for fetch_technicals.py
│
├── scripts/
│   ├── indicators.py           ← Shared indicator library (used by all 3 fetchers)
│   ├── fetch_technicals.py     ← Daily: fetches stock data via yfinance
│   ├── fetch_indices.py        ← Daily: fetches index data from NSE archives
│   ├── fetch_global.py         ← Daily: fetches global/commodity data via yfinance
│   └── run_daily.py            ← Orchestrator: runs all 3 + optional git push
│
└── .github/workflows/
    └── daily_update.yml        ← GitHub Actions: auto-runs Mon-Fri at 5:30 PM IST
```

---

## Local Setup

```bash
# App only
pip install -r requirements.txt
streamlit run app.py

# Data scripts (for generating/refreshing data)
pip install -r requirements-scripts.txt
```

---

## Data Pipeline

### Daily (automated via GitHub Actions)

The three daily scripts fetch fresh technical data:

```bash
# Run all three
cd scripts
python run_daily.py

# Or individually
python fetch_technicals.py      # ~30-45 min (880+ stocks via yfinance)
python fetch_indices.py         # ~15-20 min (downloads 5 years of NSE CSVs)
python fetch_global.py          # ~1 min (13 instruments via yfinance)

# Run all + auto-push to GitHub
python run_daily.py --push
```

### Monthly (manual)

- **fundamentals.csv** — Export from screener.in Nifty 500 watchlist, ensure `Symbol` is the first column
- **index_constituents.csv** — Update index membership mapping

---

## GitHub Actions Automation

The workflow in `.github/workflows/daily_update.yml` runs Mon-Fri at 5:30 PM IST (after market close):

1. Checks out the repo
2. Installs `requirements-scripts.txt`
3. Runs `scripts/run_daily.py`
4. Commits and pushes updated CSVs

Streamlit Cloud auto-deploys on push, so the live app refreshes automatically.

To enable: just push this repo to GitHub and ensure Actions are enabled.
You can also trigger manually from the Actions tab → "Run workflow".

---

## Deploying to Streamlit Cloud

1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. New app → connect your repo → set main file as `app.py`
4. Deploy

---

## Screens

22 pre-built screens across 5 categories:

| Category | Screens |
|---|---|
| Momentum | Momentum Leaders, Breakout Candidates, Reversal Watch, Volume Surge |
| Quality | Quality Compounders, Hidden Gems, Consistent Growers, Debt Free |
| Value | Value Picks, Fallen Angels, Low PEG, Undervalued Small Caps |
| Income | Dividend Aristocrats, High FCF Yield, Consistent Dividend Growers |
| Combined | SIP Worthy, All Rounder, Operator Favorites, Turnaround, Strong Bull, Defensive Quality |

Plus a custom screen builder with up to 8 user-defined conditions.
