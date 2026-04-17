"""
fetch_global.py
Fetches historical data for commodities, currencies and global indices
via Yahoo Finance, calculates technical indicators, saves to global_technicals.csv

Usage:
    python scripts/fetch_global.py
"""

from pathlib import Path
from datetime import datetime

import time
import yfinance as yf
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

from indicators import (
    ema, rsi, macd_signal_label, supertrend,
    roc, cagr, day_change_pct,
    trend_consistency, momentum_acceleration, momentum_quality,
    annualized_sd, max_drawdown, atr_pct,
    days_since_52w_high, drawdown_status, ema_cross,
    market_regime, vol_trend,
)

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_CSV = ROOT / "data" / "global_technicals.csv"

# ─────────────────────────────────────────────
# INSTRUMENTS
# ─────────────────────────────────────────────
INSTRUMENTS = {
    # Commodities
    "Gold":         {"ticker": "GC=F",     "category": "Commodity"},
    "Silver":       {"ticker": "SI=F",     "category": "Commodity"},
    "Crude Oil":    {"ticker": "CL=F",     "category": "Commodity"},
    "Natural Gas":  {"ticker": "NG=F",     "category": "Commodity"},
    # Currencies
    "USD/INR":      {"ticker": "INR=X",    "category": "Currency"},
    "EUR/INR":      {"ticker": "EURINR=X", "category": "Currency"},
    "GBP/INR":      {"ticker": "GBPINR=X", "category": "Currency"},
    # Global Indices
    "S&P 500":      {"ticker": "^GSPC",    "category": "Global Index"},
    "Nasdaq":       {"ticker": "^IXIC",    "category": "Global Index"},
    "Dow Jones":    {"ticker": "^DJI",     "category": "Global Index"},
    "Nikkei 225":   {"ticker": "^N225",    "category": "Global Index"},
    "Hang Seng":    {"ticker": "^HSI",     "category": "Global Index"},
    "FTSE 100":     {"ticker": "^FTSE",    "category": "Global Index"},
    "India VIX":    {"ticker": "^INDIAVIX", "category": "Global Index"},
    "US 10Y Yield": {"ticker": "^TNX",     "category": "Global Index"},
}

# ─────────────────────────────────────────────
# CALC ALL INDICATORS FOR ONE INSTRUMENT
# ─────────────────────────────────────────────

def calc_technicals(name, ticker, category, hist):
    c = hist["Close"]
    h = hist["High"]
    lo = hist["Low"]

    e50 = ema(c, 50)
    e200 = ema(c, 200)

    # 52W
    w52 = c.tail(252)
    high52 = w52.max()
    low52 = w52.min()
    pct_high = round((c.iloc[-1] - high52) / high52 * 100, 2)
    pct_low = round((c.iloc[-1] - low52) / low52 * 100, 2)

    ds_high = days_since_52w_high(c)
    dd_stat = drawdown_status(pct_high, ds_high)
    cross_label, cross_days = ema_cross(c)
    vol_r, vol_t = vol_trend(c)
    tc = trend_consistency(c)
    roc6 = roc(c, 126)

    row = {
        "Name": name,
        "Ticker": ticker,
        "Category": category,
        "Current Price": round(c.iloc[-1], 4),
        "Day Change %": day_change_pct(c),
        "EMA 50": round(e50.iloc[-1], 4),
        "EMA 200": round(e200.iloc[-1], 4),
        "EMA Cross": cross_label,
        "Days Since EMA Cross": cross_days,
        "RSI 14": round(rsi(c).iloc[-1], 2),
        "MACD Signal": macd_signal_label(c),
        "Supertrend": supertrend(h, lo, c) if len(hist) > 20 else np.nan,
        "ROC 1M %": roc(c, 21),
        "ROC 3M %": roc(c, 63),
        "ROC 6M %": roc6,
        "1Y CAGR %": cagr(c, 1),
        "3Y CAGR %": cagr(c, 3),
        "Trend Consistency (12M)": tc,
        "Momentum Acceleration": momentum_acceleration(c),
        "Momentum Quality": momentum_quality(c),
        "SD 1Y %": annualized_sd(c),
        "ATR % (14D)": atr_pct(h, lo, c) if len(hist) > 14 else np.nan,
        "Vol Ratio (20D/60D)": vol_r,
        "Vol Trend": vol_t,
        "52W High": round(high52, 4),
        "52W Low": round(low52, 4),
        "% from 52W High": pct_high,
        "% from 52W Low": pct_low,
        "1Y Max Drawdown %": max_drawdown(c),
        "Days Since 52W High": ds_high,
        "Drawdown Status": dd_stat,
        "Market Regime": market_regime(
            c.iloc[-1], e200.iloc[-1], pct_high, roc6, tc,
        ),
    }
    return row


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Global & Commodities Data Fetch")
    print("=" * 60)

    results = []
    failed = []

    for name, meta in INSTRUMENTS.items():
        ticker = meta["ticker"]
        category = meta["category"]
        print(f"  Fetching {name} ({ticker})...", end=" ", flush=True)

        # Try up to 3 times with 10s waits between attempts
        hist = None
        for attempt in range(3):
            try:
                hist_try = yf.Ticker(ticker).history(period="5y")
                if hist_try is not None and not hist_try.empty and len(hist_try) >= 30:
                    hist = hist_try
                    break
            except Exception:
                pass
            if attempt < 2:
                print(f"retry {attempt + 1}...", end=" ", flush=True)
                time.sleep(10)

        if hist is None:
            print(f"SKIP — all 3 attempts failed")
            failed.append(name)
            continue

        try:
            row = calc_technicals(name, ticker, category, hist)
            results.append(row)
            print(f"{len(hist)} rows → Regime: {row['Market Regime']} ✓")
        except Exception as e:
            print(f"ERROR — {e}")
            failed.append(name)

    if not results:
        print("No data fetched. Keeping previous file.")
        return

    out = pd.DataFrame(results)

    # Sort by category
    cat_order = {"Commodity": 0, "Currency": 1, "Global Index": 2}
    out["_sort"] = out["Category"].map(cat_order)
    out = out.sort_values(["_sort", "Name"]).drop(columns="_sort").reset_index(drop=True)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    # Merge with previous data — keep old rows for instruments that failed today
    if OUTPUT_CSV.exists():
        try:
            prev = pd.read_csv(OUTPUT_CSV)
            new_names = set(out['Name'].tolist())
            old_kept = prev[~prev['Name'].isin(new_names)]
            if not old_kept.empty:
                print(f"   Keeping {len(old_kept)} instruments from previous run (failed today)")
                out = pd.concat([out, old_kept], ignore_index=True)
        except Exception as e:
            print(f"   Merge warning: {e}")

    # Re-sort after merge
    out["_sort"] = out["Category"].map(cat_order)
    out = out.sort_values(["_sort", "Name"]).drop(columns="_sort").reset_index(drop=True)

    out.to_csv(OUTPUT_CSV, index=False)
    print(f"\n✅ Done — {len(out)} instruments saved to {OUTPUT_CSV}")
    if failed:
        print(f"⚠️  Failed ({len(failed)}): {', '.join(failed)}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
