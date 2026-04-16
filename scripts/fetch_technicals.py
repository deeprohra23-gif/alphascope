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
MAX_WORKERS = 10
SLEEP_BETWEEN = 0.3
SMALL_CAP = 5_000
MID_CAP = 20_000

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SYMBOLS = ROOT / "data" / "nifty500_symbols.csv"
OUTPUT_CSV = ROOT / "data" / "technicals.csv"
FAILED_CSV = ROOT / "data" / "failed_stocks.csv"
HISTORY_DIR = ROOT / "data" / "history"
HISTORY_RETENTION_DAYS = 365  # keep 1 year of snapshots


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

    # Batched parallel fetch — avoids rate limiting
    results = []
    failed = []
    failed_tickers = set()
    BATCH_SIZE = 200
    BATCH_COOLDOWN = 120  # seconds between batches

    total_batches = (len(tickers) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"Fetching {len(tickers)} stocks in {total_batches} batches of {BATCH_SIZE} ({MAX_WORKERS} workers)...\n")

    for batch_num in range(total_batches):
        batch_start = batch_num * BATCH_SIZE
        batch_end = min(batch_start + BATCH_SIZE, len(tickers))
        batch = tickers[batch_start:batch_end]

        print(f"── Batch {batch_num + 1}/{total_batches} ({len(batch)} stocks) ──")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_map = {
                executor.submit(get_stock_data, t, nifty_close, nifty_daily_ret, nifty_monthly_ret): t
                for t in batch
            }
            for i, future in enumerate(as_completed(future_map), 1):
                ticker = future_map[future]
                global_idx = batch_start + i
                try:
                    data, fail = future.result()
                    if data:
                        results.append(data)
                        print(f"  ✓ [{global_idx:3d}/{len(tickers)}] {ticker}")
                    else:
                        failed_tickers.add(ticker)
                        failed.append({"Ticker": fail or ticker, "Reason": "No data / insufficient history"})
                        print(f"  – [{global_idx:3d}/{len(tickers)}] {ticker}  (skipped)")
                except Exception as e:
                    failed_tickers.add(ticker)
                    failed.append({"Ticker": ticker, "Reason": str(e)})
                    print(f"  ✗ [{global_idx:3d}/{len(tickers)}] {ticker}  ERROR: {e}")

                time.sleep(SLEEP_BETWEEN / MAX_WORKERS)

        # Cooldown between batches (skip after last batch)
        if batch_num < total_batches - 1:
            print(f"\n  ⏳ Cooling down {BATCH_COOLDOWN}s before next batch...\n")
            time.sleep(BATCH_COOLDOWN)

    # Retry pass — single-threaded with longer sleeps (for rate-limited ones)
    retry_failed = set()
    if failed_tickers:
        print(f"\n── Retry pass for {len(failed_tickers)} failed stocks ──")
        print(f"   Waiting 30s before retry...")
        time.sleep(30)

        success_syms = {r['Symbol'] for r in results if 'Symbol' in r}

        for j, ticker in enumerate(sorted(failed_tickers), 1):
            try:
                data, fail = get_stock_data(ticker, nifty_close, nifty_daily_ret, nifty_monthly_ret)
                if data and data.get('Symbol') not in success_syms:
                    results.append(data)
                    success_syms.add(data['Symbol'])
                    print(f"  ✓ [RETRY {j}/{len(failed_tickers)}] {ticker}")
                else:
                    retry_failed.add(ticker)
                    print(f"  – [RETRY {j}/{len(failed_tickers)}] {ticker}  (still failed)")
            except Exception as e:
                retry_failed.add(ticker)
                print(f"  ✗ [RETRY {j}/{len(failed_tickers)}] {ticker}  ERROR: {e}")

            time.sleep(2)

    # BSE fallback — try .BO for anything still failing
    bse_recovered = 0
    if retry_failed:
        print(f"\n── BSE fallback for {len(retry_failed)} still-failing stocks ──")
        print(f"   Waiting 30s before BSE attempts...")
        time.sleep(30)

        success_syms = {r['Symbol'] for r in results if 'Symbol' in r}

        for k, ticker in enumerate(sorted(retry_failed), 1):
            bse_ticker = ticker.replace('.NS', '.BO')
            try:
                data, fail = get_stock_data(bse_ticker, nifty_close, nifty_daily_ret, nifty_monthly_ret)
                if data:
                    # Store under original .NS symbol so it merges with rest
                    data['Symbol'] = ticker
                    if ticker not in success_syms:
                        results.append(data)
                        success_syms.add(ticker)
                        bse_recovered += 1
                        print(f"  ✓ [BSE {k}/{len(retry_failed)}] {ticker} (via {bse_ticker})")
                    else:
                        print(f"  – [BSE {k}/{len(retry_failed)}] {ticker}  (already recovered)")
                else:
                    print(f"  – [BSE {k}/{len(retry_failed)}] {ticker}  (BSE also failed)")
            except Exception as e:
                print(f"  ✗ [BSE {k}/{len(retry_failed)}] {ticker}  ERROR: {e}")

            time.sleep(2)

        if bse_recovered > 0:
            print(f"\n   BSE fallback recovered {bse_recovered} stocks")

    # Save — merge with previous data + archive snapshot
    if results:
        df = pd.DataFrame(results)
        df = df.sort_values("Market Cap (Cr)", ascending=False, na_position="last").reset_index(drop=True)
        OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

        # Merge: keep old rows for stocks that failed today
        if OUTPUT_CSV.exists():
            try:
                prev = pd.read_csv(OUTPUT_CSV)
                new_syms = set(df['Symbol'].tolist())
                old_kept = prev[~prev['Symbol'].isin(new_syms)]
                if not old_kept.empty:
                    print(f"   Keeping {len(old_kept)} stocks from previous run (not in today's results)")
                    df = pd.concat([df, old_kept], ignore_index=True)
                    df = df.sort_values("Market Cap (Cr)", ascending=False, na_position="last").reset_index(drop=True)
            except Exception as e:
                print(f"   Merge warning: {e}")

        df.to_csv(OUTPUT_CSV, index=False)
        print(f"\n✅ Saved {len(df)} stocks → {OUTPUT_CSV}")

        # Archive daily snapshot
        try:
            from datetime import datetime, timedelta
            HISTORY_DIR.mkdir(parents=True, exist_ok=True)
            today_str = datetime.now().strftime("%Y-%m-%d")
            snapshot_path = HISTORY_DIR / f"{today_str}.csv"
            df.to_csv(snapshot_path, index=False)
            print(f"📸 Archived snapshot → {snapshot_path}")

            # Cleanup old snapshots (retention window)
            cutoff = datetime.now() - timedelta(days=HISTORY_RETENTION_DAYS)
            removed = 0
            for f in HISTORY_DIR.glob("*.csv"):
                try:
                    file_date = datetime.strptime(f.stem, "%Y-%m-%d")
                    if file_date < cutoff:
                        f.unlink()
                        removed += 1
                except ValueError:
                    continue
            if removed > 0:
                print(f"🧹 Cleaned up {removed} old snapshots (>{HISTORY_RETENTION_DAYS} days)")
        except Exception as e:
            print(f"⚠️  Snapshot archival failed: {e}")
    else:
        print("\n⚠️  No results to save. Keeping previous file.")

    if failed:
        pd.DataFrame(failed).to_csv(FAILED_CSV, index=False)
        print(f"⚠️  {len(failed)} failed → {FAILED_CSV}")

    print("\nDone.")


if __name__ == "__main__":
    main()
