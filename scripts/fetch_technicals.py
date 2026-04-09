"""
fetch_technicals.py
Fetches daily technical data for all Nifty 500+ stocks via Yahoo Finance.
Outputs technicals.csv for the Streamlit app.

Usage:
    python scripts/fetch_technicals.py
    python scripts/fetch_technicals.py --symbols path/to/symbols.csv
"""

import argparse
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import yfinance as yf
import pandas as pd
import numpy as np

from indicators import (
    ema, rsi, macd_signal_label, supertrend, atr, atr_pct,
    roc, cagr, day_change_pct, trend_consistency,
    momentum_acceleration, momentum_quality,
    annualized_sd, max_drawdown, vol_trend,
    days_since_52w_high, drawdown_status, ema_cross,
    market_regime, rs_vs_benchmark, capture_ratios, beta,
)

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────
NIFTY_TICKER = "^NSEI"
EMA_SHORT = 50
EMA_LONG = 200
RSI_PERIOD = 14
ST_ATR_PERIOD = 10
ST_MULTIPLIER = 3.0
ATR_PERIOD = 14
MAX_WORKERS = 5
SLEEP_BETWEEN = 1
SMALL_CAP = 5_000
MID_CAP = 20_000

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SYMBOLS = ROOT / "data" / "nifty500_symbols.csv"
OUTPUT_CSV = ROOT / "data" / "technicals.csv"
FAILED_CSV = ROOT / "data" / "failed_stocks.csv"


# ────────────────────────────────────────────────
# PER-STOCK FUNCTION
# ────────────────────────────────────────────────

def get_stock_data(ticker, nifty_close, nifty_daily_ret, nifty_monthly_ret):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="max")

        if hist.empty or len(hist) < 30:
            return None, ticker

        close = hist["Close"]
        high = hist["High"]
        low = hist["Low"]
        volume = hist["Volume"]
        current_price = close.iloc[-1]

        # Identity
        name = next(
            (info.get(k) for k in ("longName", "shortName") if info.get(k) and info.get(k) != "N/A"),
            ticker,
        )
        sector = info.get("sector", "N/A")
        industry = info.get("industry", "N/A")
        raw_mcap = info.get("marketCap")
        mcap_cr = raw_mcap / 1e7 if raw_mcap else np.nan
        cap_cat = (
            "Small" if not np.isnan(mcap_cr) and mcap_cr < SMALL_CAP else
            "Mid" if not np.isnan(mcap_cr) and mcap_cr < MID_CAP else
            "Large" if not np.isnan(mcap_cr) else "Unknown"
        )

        # EMAs
        ema50 = ema(close, EMA_SHORT).iloc[-1]
        ema200 = ema(close, EMA_LONG).iloc[-1]

        # Indicators
        rsi_val = rsi(close, RSI_PERIOD).iloc[-1]
        macd_flag = macd_signal_label(close)
        st_flag = supertrend(high, low, close, ST_ATR_PERIOD, ST_MULTIPLIER)

        # Returns
        roc_1m = roc(close, 21)
        roc_3m = roc(close, 63)
        roc_6m = roc(close, 126)
        roc_12m = roc(close, 252)
        day_chg = day_change_pct(close)

        # Volume
        vol_roc_1m = np.nan
        if len(volume) >= 42:
            recent_avg = volume.iloc[-21:].mean()
            prior_avg = volume.iloc[-42:-21].mean()
            vol_roc_1m = ((recent_avg - prior_avg) / prior_avg * 100) if prior_avg > 0 else np.nan

        # Beta
        stock_daily_ret = close.pct_change().dropna().tail(252)
        beta_1y = beta(stock_daily_ret, nifty_daily_ret)
        beta_5y = info.get("beta", np.nan)
        if pd.isna(beta_5y):
            stock_monthly_ret = close.resample("ME").last().pct_change().dropna().tail(60)
            beta_5y = beta(stock_monthly_ret, nifty_monthly_ret)

        # Risk
        sd_1y = annualized_sd(close, 252)
        atr_pct_val = atr_pct(high, low, close, ATR_PERIOD)

        # 52W
        high_52 = info.get("fiftyTwoWeekHigh", np.nan)
        low_52 = info.get("fiftyTwoWeekLow", np.nan)
        pct_from_high = ((current_price - high_52) / high_52 * 100) if not pd.isna(high_52) else np.nan
        pct_from_low = ((current_price - low_52) / low_52 * 100) if not pd.isna(low_52) else np.nan

        # Derived
        max_dd = max_drawdown(close, 252)
        cagr_1y = cagr(close, 1)
        cagr_3y = cagr(close, 3)
        tc = trend_consistency(close)
        mom_accel = momentum_acceleration(close)
        mom_qual = momentum_quality(close)
        vol_r, vol_t = vol_trend(close)
        ds_high = days_since_52w_high(close)
        dd_stat = drawdown_status(pct_from_high, ds_high)
        cross_label, cross_days = ema_cross(close)
        rs_1m = rs_vs_benchmark(close, nifty_close, 21)
        rs_3m = rs_vs_benchmark(close, nifty_close, 63)
        rs_6m = rs_vs_benchmark(close, nifty_close, 126)
        regime = market_regime(current_price, ema200, pct_from_high, roc_6m, tc)
        up_cap, down_cap, cap_ratio = capture_ratios(close, nifty_close)

        def r(v, d=2):
            return round(v, d) if not pd.isna(v) else np.nan

        return {
            "Symbol": ticker,
            "Name": name,
            "Sector": sector,
            "Industry": industry,
            "Market Cap (Cr)": r(mcap_cr),
            "Cap Category": cap_cat,
            "Current Price": r(current_price),
            "Day Change %": r(day_chg),
            f"EMA {EMA_SHORT}": r(ema50),
            f"EMA {EMA_LONG}": r(ema200),
            "RSI 14": r(rsi_val),
            "MACD Signal": macd_flag,
            "Supertrend": st_flag,
            "ROC 1M %": r(roc_1m),
            "ROC 3M %": r(roc_3m),
            "ROC 6M %": r(roc_6m),
            "ROC 12M %": r(roc_12m),
            "Vol ROC 1M %": r(vol_roc_1m),
            "Beta 1Y (Daily)": r(beta_1y, 4),
            "Beta 5Y (Monthly)": r(beta_5y, 4),
            "SD 1Y %": r(sd_1y),
            "ATR % (14D)": r(atr_pct_val),
            "52W High": r(high_52),
            "52W Low": r(low_52),
            "% from 52W High": r(pct_from_high),
            "% from 52W Low": r(pct_from_low),
            "1Y Max Drawdown %": r(max_dd),
            "1Y CAGR %": r(cagr_1y),
            "3Y CAGR %": r(cagr_3y),
            "Market Regime": regime,
            "Drawdown Status": dd_stat,
            "Days Since 52W High": ds_high,
            "Trend Consistency (12M)": tc,
            "Momentum Acceleration": mom_accel,
            "Momentum Quality": mom_qual,
            "Vol Ratio (20D/60D)": vol_r,
            "Vol Trend": vol_t,
            "EMA Cross": cross_label,
            "Days Since EMA Cross": cross_days,
            "RS vs Nifty 1M %": rs_1m,
            "RS vs Nifty 3M %": rs_3m,
            "RS vs Nifty 6M %": rs_6m,
            "Up Capture Ratio": up_cap,
            "Down Capture Ratio": down_cap,
            "Capture Ratio": cap_ratio,
        }, None

    except Exception as e:
        print(f"  ✗ {ticker}: {e}")
        return None, ticker


# ────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fetch Nifty 500 technicals")
    parser.add_argument("--symbols", type=str, default=str(DEFAULT_SYMBOLS),
                        help="Path to CSV with Symbol column")
    args = parser.parse_args()

    # Load symbols
    df_symbols = pd.read_csv(args.symbols)
    col = df_symbols.columns[0]
    tickers = df_symbols[col].dropna().astype(str).str.strip().tolist()
    print(f"Loaded {len(tickers)} symbols from {args.symbols}")

    # Load Nifty
    print("Fetching Nifty index history...")
    nifty_hist = yf.Ticker(NIFTY_TICKER).history(period="max")
    nifty_close = nifty_hist["Close"]
    nifty_daily_ret = nifty_close.pct_change().dropna()
    nifty_monthly_ret = nifty_close.resample("ME").last().pct_change().dropna()
    print(f"Nifty history: {len(nifty_hist)} rows\n")

    # Parallel fetch
    results = []
    failed = []

    print(f"Fetching {len(tickers)} stocks with {MAX_WORKERS} workers...\n")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_map = {
            executor.submit(get_stock_data, t, nifty_close, nifty_daily_ret, nifty_monthly_ret): t
            for t in tickers
        }
        for i, future in enumerate(as_completed(future_map), 1):
            ticker = future_map[future]
            try:
                data, fail = future.result()
                if data:
                    results.append(data)
                    print(f"  ✓ [{i:3d}/{len(tickers)}] {ticker}")
                else:
                    failed.append({"Ticker": fail or ticker, "Reason": "No data / insufficient history"})
                    print(f"  – [{i:3d}/{len(tickers)}] {ticker}  (skipped)")
            except Exception as e:
                failed.append({"Ticker": ticker, "Reason": str(e)})
                print(f"  ✗ [{i:3d}/{len(tickers)}] {ticker}  ERROR: {e}")

            time.sleep(SLEEP_BETWEEN / MAX_WORKERS)

    # Save
    if results:
        df = pd.DataFrame(results)
        df = df.sort_values("Market Cap (Cr)", ascending=False, na_position="last").reset_index(drop=True)
        OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(OUTPUT_CSV, index=False)
        print(f"\n✅ Saved {len(results)} stocks → {OUTPUT_CSV}")
    else:
        print("\n⚠️  No results to save.")

    if failed:
        pd.DataFrame(failed).to_csv(FAILED_CSV, index=False)
        print(f"⚠️  {len(failed)} failed → {FAILED_CSV}")

    print("\nDone.")


if __name__ == "__main__":
    main()
