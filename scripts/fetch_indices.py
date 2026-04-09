"""
fetch_indices.py
Downloads 5 years of daily index bhav copy CSVs from NSE archives,
builds OHLCV history, calculates technical indicators,
saves to indices_technicals.csv

Usage:
    python scripts/fetch_indices.py
"""

from pathlib import Path
from datetime import datetime, timedelta
import io
import time

import requests
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
    market_regime_index, rs_vs_benchmark, capture_ratios, beta_cov,
    vol_trend,
)

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_CSV = ROOT / "data" / "indices_technicals.csv"

# ─────────────────────────────────────────────
# INDEX LIST
# ─────────────────────────────────────────────
INDICES = {
    # Broad Market
    "Nifty 50":                         "Broad Market",
    "Nifty 100":                        "Broad Market",
    "Nifty 200":                        "Broad Market",
    "Nifty 500":                        "Broad Market",
    "Nifty Midcap 150":                 "Broad Market",
    "Nifty Smallcap 250":               "Broad Market",
    "Nifty Total Market":               "Broad Market",
    # Sectoral
    "Nifty Bank":                       "Sectoral",
    "Nifty IT":                         "Sectoral",
    "Nifty Auto":                       "Sectoral",
    "Nifty FMCG":                       "Sectoral",
    "Nifty Pharma":                     "Sectoral",
    "Nifty Metal":                      "Sectoral",
    "Nifty Realty":                     "Sectoral",
    "Nifty Energy":                     "Sectoral",
    "Nifty PSU Bank":                   "Sectoral",
    "Nifty Private Bank":               "Sectoral",
    "Nifty Financial Services":         "Sectoral",
    "Nifty Healthcare Index":           "Sectoral",
    "Nifty Oil & Gas":                  "Sectoral",
    # Strategy
    "Nifty Alpha 50":                   "Strategy",
    "Nifty High Beta 50":               "Strategy",
    "Nifty Low Volatility 50":          "Strategy",
    "Nifty200 Momentum 30":             "Strategy",
    "NIFTY100 Quality 30":              "Strategy",
    # Thematic
    "Nifty Commodities":                "Thematic",
    "Nifty India Consumption":          "Thematic",
    "Nifty CPSE":                       "Thematic",
    "Nifty Infrastructure":             "Thematic",
    "Nifty MNC":                        "Thematic",
    "Nifty PSE":                        "Thematic",
    "Nifty Services Sector":            "Thematic",
    "Nifty India Digital":              "Thematic",
    "NIFTY100 ESG":                     "Thematic",
    "Nifty India Manufacturing":        "Thematic",
    "Nifty India Defence":              "Thematic",
    "Nifty India Tourism":              "Thematic",
    "Nifty Capital Markets":            "Thematic",
    "Nifty EV & New Age Automotive":    "Thematic",
    "Nifty India New Age Consumption":  "Thematic",
    "Nifty Mobility":                   "Thematic",
    "Nifty Housing":                    "Thematic",
    "Nifty IPO":                        "Thematic",
    "Nifty Non-Cyclical Consumer":      "Thematic",
    "Nifty Rural":                      "Thematic",
    "Nifty Transportation & Logistics": "Thematic",
    "Nifty India Internet":             "Thematic",
    "Nifty Waves":                      "Thematic",
    "Nifty India Railways PSU":         "Thematic",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.nseindia.com/",
    "Accept-Language": "en-US,en;q=0.9",
}
ARCHIVE_URL = "https://nsearchives.nseindia.com/content/indices/ind_close_all_{date}.csv"


# ─────────────────────────────────────────────
# DATA DOWNLOAD
# ─────────────────────────────────────────────

def get_session():
    session = requests.Session()
    try:
        session.get("https://www.nseindia.com", headers=HEADERS, timeout=15)
    except Exception:
        pass
    return session


def get_date_range(years=5):
    today = datetime.today()
    start = today - timedelta(days=years * 365)
    dates = []
    current = start
    while current <= today:
        if current.weekday() < 5:
            dates.append(current)
        current += timedelta(days=1)
    return dates


def fetch_day(session, date):
    url = ARCHIVE_URL.format(date=date.strftime("%d%m%Y"))
    try:
        r = session.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200 and len(r.text) > 100:
            df = pd.read_csv(io.StringIO(r.text))
            df.columns = [c.strip() for c in df.columns]
            return df
    except Exception:
        pass
    return None


def build_history(years=5):
    session = get_session()
    dates = get_date_range(years)
    all_rows = []
    total = len(dates)
    success = 0

    print(f"Downloading {total} daily CSVs ({years} years)...")

    for i, date in enumerate(dates):
        df = fetch_day(session, date)
        if df is not None:
            all_rows.append(df)
            success += 1
        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{total} — {success} trading days found")
        time.sleep(0.15)

    print(f"\n✓ Download complete — {success} trading days\n")

    if not all_rows:
        return None

    master = pd.concat(all_rows, ignore_index=True)
    master.columns = [c.strip() for c in master.columns]

    col_map = {
        "Index Name": "Index Name",
        "Index Date": "Date",
        "Open Index Value": "Open",
        "High Index Value": "High",
        "Low Index Value": "Low",
        "Closing Index Value": "Close",
        "Volume": "Volume",
        "Turnover (Rs. Cr.)": "Turnover",
        "P/E": "PE Ratio",
        "P/B": "PB Ratio",
        "Div Yield": "Dividend Yield %",
    }
    master = master.rename(columns=col_map)
    master["Date"] = pd.to_datetime(master["Date"], dayfirst=True, errors="coerce")

    for c in ["Open", "High", "Low", "Close", "Volume", "PE Ratio", "PB Ratio", "Dividend Yield %"]:
        if c in master.columns:
            master[c] = pd.to_numeric(master[c], errors="coerce")

    master = master.dropna(subset=["Date", "Close"]).sort_values("Date").reset_index(drop=True)
    return master


# ─────────────────────────────────────────────
# CALC ALL INDICATORS FOR ONE INDEX
# ─────────────────────────────────────────────

def calc_all(df, nifty_df=None):
    c = df["Close"]
    h = df.get("High", c)
    lo = df.get("Low", c)

    # Date-indexed series for time-based calcs
    if "Date" in df.columns:
        c_dated = pd.Series(c.values, index=pd.to_datetime(df["Date"]))
        h_dated = pd.Series(h.values, index=pd.to_datetime(df["Date"]))
        lo_dated = pd.Series(lo.values, index=pd.to_datetime(df["Date"]))
    else:
        c_dated, h_dated, lo_dated = c, h, lo

    e50 = ema(c, 50)
    e200 = ema(c, 200)

    # 52W
    w52 = c.tail(252)
    high52 = w52.max()
    low52 = w52.min()
    pct_high = round((c.iloc[-1] - high52) / high52 * 100, 2)
    pct_low = round((c.iloc[-1] - low52) / low52 * 100, 2)

    ds_high = days_since_52w_high(c_dated)
    dd_stat = drawdown_status(pct_high, ds_high)
    cross_label, cross_days = ema_cross(c_dated)
    vol_r, vol_t = vol_trend(c)
    tc = trend_consistency(c_dated)
    roc6 = roc(c, 126)
    sd_1y = annualized_sd(c, 252)
    mq = round(roc6 / sd_1y, 2) if sd_1y and sd_1y != 0 and not np.isnan(roc6 or np.nan) else np.nan

    row = {
        "Current Price": round(c.iloc[-1], 2),
        "Day Change %": day_change_pct(c),
        "EMA 50": round(e50.iloc[-1], 2),
        "EMA 200": round(e200.iloc[-1], 2),
        "RSI 14": round(rsi(c).iloc[-1], 2),
        "MACD Signal": macd_signal_label(c),
        "Supertrend": supertrend(h, lo, c) if len(df) > 20 else np.nan,
        "ROC 1M %": roc(c, 21),
        "ROC 3M %": roc(c, 63),
        "ROC 6M %": roc6,
        "1Y CAGR %": cagr(c, 1),
        "3Y CAGR %": cagr(c, 3),
        "52W High": round(high52, 2),
        "52W Low": round(low52, 2),
        "% from 52W High": pct_high,
        "% from 52W Low": pct_low,
        "1Y Max Drawdown %": max_drawdown(c),
        "Days Since 52W High": ds_high,
        "Drawdown Status": dd_stat,
        "SD 1Y %": sd_1y,
        "ATR % (14D)": atr_pct(h, lo, c) if len(df) > 14 else np.nan,
        "Vol Ratio (20D/60D)": vol_r,
        "Vol Trend": vol_t,
        "Trend Consistency (12M)": tc,
        "Momentum Acceleration": momentum_acceleration(c),
        "Momentum Quality": mq,
        "EMA Cross": cross_label,
        "Days Since EMA Cross": cross_days,
    }

    # Nifty-relative metrics
    if nifty_df is not None:
        nifty_s = pd.Series(nifty_df["Close"].values, index=pd.to_datetime(nifty_df["Date"]))
        b, corr = beta_cov(c_dated, nifty_s)
        up_cap, down_cap, cap_ratio = capture_ratios(c_dated, nifty_s)

        row["Beta vs Nifty"] = b
        row["Correlation vs Nifty (1Y)"] = corr
        row["Up Capture Ratio"] = up_cap
        row["Down Capture Ratio"] = down_cap
        row["Capture Ratio"] = cap_ratio
        row["RS vs Nifty 1M %"] = rs_vs_benchmark(c_dated, nifty_s, 21)
        row["RS vs Nifty 3M %"] = rs_vs_benchmark(c_dated, nifty_s, 63)
        row["RS vs Nifty 6M %"] = rs_vs_benchmark(c_dated, nifty_s, 126)
    else:
        # Nifty 50 itself
        for k in ["Beta vs Nifty", "Correlation vs Nifty (1Y)"]:
            row[k] = 1.0
        row["Up Capture Ratio"] = 100.0
        row["Down Capture Ratio"] = 100.0
        row["Capture Ratio"] = 1.0
        for k in ["RS vs Nifty 1M %", "RS vs Nifty 3M %", "RS vs Nifty 6M %"]:
            row[k] = 0.0

    # Market Regime (index version with up_capture)
    row["Market Regime"] = market_regime_index(
        c.iloc[-1], row["EMA 200"], pct_high, roc6,
        row.get("Up Capture Ratio", np.nan), tc,
    )

    # Valuation from NSE bhav
    for col in ["PE Ratio", "PB Ratio", "Dividend Yield %"]:
        if col in df.columns:
            val = pd.to_numeric(df[col], errors="coerce").dropna()
            row[col] = round(val.iloc[-1], 2) if not val.empty else np.nan

    return row


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("=" * 60)
    print("NSE Index Technical Screener — Data Fetch")
    print("=" * 60)

    master = build_history(years=5)
    if master is None:
        print("No data downloaded.")
        return

    available = set(master["Index Name"].unique())
    print(f"Indices found in NSE data: {len(available)}")

    nifty_df = master[master["Index Name"] == "Nifty 50"].copy().reset_index(drop=True)

    print("\nCalculating indicators...")
    print("-" * 60)

    results = []
    not_found = []

    for index_name, category in INDICES.items():
        df = master[master["Index Name"] == index_name].copy()
        if df.empty:
            match = [n for n in available if n.lower() == index_name.lower()]
            if match:
                df = master[master["Index Name"] == match[0]].copy()

        if df.empty or len(df) < 30:
            print(f"  ⚠ {index_name} — not found ({len(df)} rows)")
            not_found.append(index_name)
            continue

        df = df.sort_values("Date").reset_index(drop=True)
        if "Date" not in df.columns and df.index.name == "Date":
            df = df.reset_index()

        try:
            is_nifty50 = (index_name == "Nifty 50")
            tech = calc_all(df, nifty_df=None if is_nifty50 else nifty_df)
            tech["Index"] = index_name
            tech["Category"] = category
            results.append(tech)
            print(f"  ✓ {index_name} — {len(df)} days | Regime: {tech['Market Regime']}")
        except Exception as e:
            print(f"  ✗ {index_name} — ERROR: {e}")
            not_found.append(index_name)

    if not results:
        print("No results. Exiting.")
        return

    out = pd.DataFrame(results)

    # Momentum ranks
    for period, col in [("1M", "ROC 1M %"), ("3M", "ROC 3M %"), ("6M", "ROC 6M %")]:
        if col in out.columns:
            out[f"Momentum Rank {period}"] = out[col].rank(ascending=False, method="min").astype("Int64")

    # Sort by category
    cat_order = {"Broad Market": 0, "Sectoral": 1, "Strategy": 2, "Thematic": 3}
    out["_sort"] = out["Category"].map(cat_order)
    out = out.sort_values(["_sort", "Index"]).drop(columns="_sort").reset_index(drop=True)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_CSV, index=False)

    print(f"\n✅ Done — {len(out)} indices saved to {OUTPUT_CSV}")

    print("\nMarket Regime Summary:")
    print(out["Market Regime"].value_counts().to_string())

    if not_found:
        print(f"\n⚠️  Not found ({len(not_found)}):")
        for n in not_found:
            print(f"   - {n}")

    print(f"\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
