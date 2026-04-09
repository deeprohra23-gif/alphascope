"""
indicators.py
Shared technical indicator calculations used by all data scripts.
Single source of truth — no more duplicate functions across files.
"""

import pandas as pd
import numpy as np


# ────────────────────────────────────────────────
# CORE INDICATORS
# ────────────────────────────────────────────────

def ema(series, span):
    """Exponential Moving Average."""
    return series.ewm(span=span, adjust=False).mean()


def rsi(close, period=14):
    """Relative Strength Index (Wilder smoothing)."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def macd(close, fast=12, slow=26, signal=9):
    """MACD line and signal line."""
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    return macd_line, signal_line


def macd_signal_label(close, fast=12, slow=26, signal=9):
    """Returns 'Bullish' or 'Bearish'."""
    macd_line, signal_line = macd(close, fast, slow, signal)
    return "Bullish" if macd_line.iloc[-1] > signal_line.iloc[-1] else "Bearish"


def true_range(high, low, close):
    """True Range."""
    prev_close = close.shift(1)
    return pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)


def atr(high, low, close, period=14):
    """Average True Range (Wilder smoothing)."""
    return true_range(high, low, close).ewm(alpha=1 / period, adjust=False).mean()


def atr_pct(high, low, close, period=14):
    """ATR as percentage of current price."""
    atr_val = atr(high, low, close, period)
    return round((atr_val / close).iloc[-1] * 100, 2)


def supertrend(high, low, close, atr_period=10, multiplier=3.0):
    """
    Supertrend matching TradingView's Pine Script implementation.
    Returns 'Bullish' / 'Bearish' for the last bar.
    """
    atr_vals = atr(high, low, close, atr_period)
    hl2 = (high + low) / 2

    raw_upper = hl2 + multiplier * atr_vals
    raw_lower = hl2 - multiplier * atr_vals

    final_upper = raw_upper.copy()
    final_lower = raw_lower.copy()
    direction = pd.Series(1, index=close.index)  # 1 = bullish, -1 = bearish

    for i in range(1, len(close)):
        # Lower band: only move up
        if raw_lower.iloc[i] > final_lower.iloc[i - 1] or close.iloc[i - 1] < final_lower.iloc[i - 1]:
            final_lower.iloc[i] = raw_lower.iloc[i]
        else:
            final_lower.iloc[i] = final_lower.iloc[i - 1]

        # Upper band: only move down
        if raw_upper.iloc[i] < final_upper.iloc[i - 1] or close.iloc[i - 1] > final_upper.iloc[i - 1]:
            final_upper.iloc[i] = raw_upper.iloc[i]
        else:
            final_upper.iloc[i] = final_upper.iloc[i - 1]

        # Direction flip
        if direction.iloc[i - 1] == -1:
            direction.iloc[i] = 1 if close.iloc[i] > final_upper.iloc[i] else -1
        else:
            direction.iloc[i] = -1 if close.iloc[i] < final_lower.iloc[i] else 1

    return "Bullish" if direction.iloc[-1] == 1 else "Bearish"


# ────────────────────────────────────────────────
# RETURNS & MOMENTUM
# ────────────────────────────────────────────────

def roc(close, days):
    """Rate of Change over N trading days."""
    if len(close) <= days:
        return np.nan
    return round((close.iloc[-1] - close.iloc[-1 - days]) / close.iloc[-1 - days] * 100, 2)


def cagr(close, years):
    """Compound Annual Growth Rate."""
    days = int(years * 252)
    if len(close) <= days:
        return np.nan
    start = close.iloc[-1 - days]
    end = close.iloc[-1]
    if start <= 0:
        return np.nan
    return round(((end / start) ** (1 / years) - 1) * 100, 2)


def day_change_pct(close):
    """Percentage change from previous close."""
    if len(close) < 2:
        return np.nan
    return round((close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100, 2)


def trend_consistency(close, months=12):
    """Count of positive return months in last N months."""
    monthly = close.resample("ME").last().pct_change().dropna()
    recent = monthly.tail(months)
    if len(recent) < 6:
        return np.nan
    return int((recent > 0).sum())


def momentum_acceleration(close):
    """ROC 1M vs average monthly ROC over 3M — positive = accelerating."""
    roc1 = roc(close, 21)
    roc3 = roc(close, 63)
    if pd.isna(roc1) or pd.isna(roc3):
        return np.nan
    return round(roc1 - (roc3 / 3), 2)


def momentum_quality(close):
    """ROC 6M / SD 1Y — momentum per unit of volatility."""
    roc6 = roc(close, 126)
    sd = annualized_sd(close, 252)
    if pd.isna(roc6) or pd.isna(sd) or sd == 0:
        return np.nan
    return round(roc6 / sd, 2)


# ────────────────────────────────────────────────
# RISK & VOLATILITY
# ────────────────────────────────────────────────

def annualized_sd(close, days=252):
    """Annualized standard deviation of returns."""
    ret = close.pct_change().tail(days).dropna()
    if len(ret) < 20:
        return np.nan
    return round(ret.std() * np.sqrt(252) * 100, 2)


def max_drawdown(close, days=252):
    """Max peak-to-trough drawdown over last N trading days."""
    subset = close.iloc[-days:] if len(close) >= days else close
    roll_max = subset.cummax()
    dd = (subset - roll_max) / roll_max * 100
    return round(dd.min(), 2)


def vol_trend(close, short=20, long=60):
    """
    Volatility trend: ratio of short-term vs long-term annualized SD.
    Returns (ratio, label).
    """
    sd_short = close.pct_change().tail(short).dropna().std() * np.sqrt(252) * 100
    sd_long = close.pct_change().tail(long).dropna().std() * np.sqrt(252) * 100
    if pd.isna(sd_short) or pd.isna(sd_long) or sd_long == 0:
        return np.nan, np.nan
    ratio = round(sd_short / sd_long, 2)
    label = "Rising" if ratio > 1.15 else "Falling" if ratio < 0.85 else "Stable"
    return ratio, label


# ────────────────────────────────────────────────
# 52-WEEK & DRAWDOWN STATUS
# ────────────────────────────────────────────────

def days_since_52w_high(close):
    """Trading days since 52-week high."""
    w52 = close.tail(252)
    peak_loc = w52.idxmax()
    cal_days = (w52.index[-1] - peak_loc).days
    return int(cal_days * 5 / 7)


def drawdown_status(pct_from_high, days_since_high):
    """Classify drawdown recovery status."""
    if pd.isna(pct_from_high) or pd.isna(days_since_high):
        return np.nan
    if pct_from_high >= -2:
        return "At High"
    elif pct_from_high >= -10 and days_since_high <= 60:
        return "Recovering"
    elif pct_from_high >= -20:
        return "Correcting"
    else:
        return "Damaged"


# ────────────────────────────────────────────────
# EMA CROSS
# ────────────────────────────────────────────────

def ema_cross(close, short=50, long=200):
    """
    Returns (label, days_since_cross).
    label: 'Golden Cross' or 'Death Cross'
    """
    e_short = ema(close, short)
    e_long = ema(close, long)
    diff = e_short - e_long
    signs = np.sign(diff)
    cross = signs.diff().fillna(0)
    cross_idx = cross[cross != 0].index
    label = "Golden Cross" if diff.iloc[-1] > 0 else "Death Cross"
    if len(cross_idx) == 0:
        return label, len(close)
    last = cross_idx[-1]
    days = int((close.index[-1] - last).days * 5 / 7)
    return label, days


# ────────────────────────────────────────────────
# MARKET REGIME
# ────────────────────────────────────────────────

def market_regime(price, ema200, pct_from_high, roc6m, trend_cons):
    """
    Classify market regime based on multiple factors.
    Returns: 'Strong Bull', 'Bull', 'Bear', 'Strong Bear'
    """
    score = 0
    if not pd.isna(ema200):
        score += 1 if price > ema200 else -1
    if not pd.isna(pct_from_high):
        if pct_from_high > -10:
            score += 1
        elif pct_from_high <= -20:
            score -= 1
    if not pd.isna(roc6m):
        score += 1 if roc6m > 0 else -1
    if not pd.isna(trend_cons):
        if trend_cons >= 8:
            score += 1
        elif trend_cons <= 4:
            score -= 1
    if score >= 3:
        return "Strong Bull"
    elif score >= 1:
        return "Bull"
    elif score >= -1:
        return "Bear"
    else:
        return "Strong Bear"


def market_regime_index(price, ema200, pct_from_high, roc6m, up_capture, trend_cons):
    """
    Index-specific regime: adds Up Capture as a 5th factor,
    so thresholds shift to ±4/±2.
    """
    score = 0
    if not np.isnan(ema200):
        score += 1 if price > ema200 else -1
    if not np.isnan(pct_from_high):
        if pct_from_high > -10:
            score += 1
        elif pct_from_high <= -20:
            score -= 1
    if not np.isnan(roc6m):
        score += 1 if roc6m > 0 else -1
    if not np.isnan(up_capture):
        if up_capture > 100:
            score += 1
        elif up_capture < 80:
            score -= 1
    if not np.isnan(trend_cons):
        if trend_cons >= 8:
            score += 1
        elif trend_cons <= 4:
            score -= 1
    if score >= 4:
        return "Strong Bull"
    elif score >= 2:
        return "Bull"
    elif score >= 0:
        return "Bear"
    else:
        return "Strong Bear"


# ────────────────────────────────────────────────
# RELATIVE STRENGTH & CAPTURE RATIOS
# ────────────────────────────────────────────────

def rs_vs_benchmark(close, bench_close, days):
    """Relative Strength vs benchmark over N days."""
    if len(close) <= days or len(bench_close) <= days:
        return np.nan
    stock_roc = (close.iloc[-1] - close.iloc[-1 - days]) / close.iloc[-1 - days] * 100
    common = close.index.intersection(bench_close.index)
    if len(common) <= days:
        return np.nan
    nc = bench_close.loc[common]
    bench_roc = (nc.iloc[-1] - nc.iloc[-1 - days]) / nc.iloc[-1 - days] * 100
    return round(stock_roc - bench_roc, 2)


def capture_ratios(close, bench_close, days=252):
    """
    Up/Down capture ratios vs benchmark.
    Returns (up_capture, down_capture, ratio).
    """
    common = close.index.intersection(bench_close.index)
    if len(common) < 60:
        return np.nan, np.nan, np.nan
    c = close.loc[common].tail(days).pct_change().dropna()
    nc = bench_close.loc[common].tail(days).pct_change().dropna()
    c, nc = c.align(nc, join='inner')
    if len(c) < 30:
        return np.nan, np.nan, np.nan
    up = nc > 0
    down = nc < 0
    if up.sum() < 10 or down.sum() < 10:
        return np.nan, np.nan, np.nan
    up_cap = round((c[up].mean() / nc[up].mean()) * 100, 1) if nc[up].mean() != 0 else np.nan
    down_cap = round((c[down].mean() / nc[down].mean()) * 100, 1) if nc[down].mean() != 0 else np.nan
    ratio = round(up_cap / down_cap, 2) if not pd.isna(up_cap) and not pd.isna(down_cap) and down_cap != 0 else np.nan
    return up_cap, down_cap, ratio


def beta(stock_ret, market_ret):
    """OLS beta of stock vs market returns."""
    common = stock_ret.index.intersection(market_ret.index)
    if len(common) < 10:
        return np.nan
    s = stock_ret.loc[common].values
    m = market_ret.loc[common].values
    try:
        import statsmodels.api as sm
        X = sm.add_constant(m)
        return sm.OLS(s, X).fit().params[1]
    except Exception:
        # Fallback: covariance-based
        cov = np.cov(s, m)
        return cov[0][1] / cov[1][1] if cov[1][1] != 0 else np.nan


def beta_cov(idx_close, bench_close, days=252):
    """Covariance-based beta + correlation (for index scripts)."""
    idx_s = idx_close[~idx_close.index.duplicated(keep="last")]
    nifty_s = bench_close[~bench_close.index.duplicated(keep="last")]
    merged = pd.DataFrame({"idx": idx_s, "nifty": nifty_s}).dropna()
    if len(merged) < 60:
        return np.nan, np.nan
    merged = merged.tail(days)
    ir = merged["idx"].pct_change().dropna()
    nr = merged["nifty"].pct_change().dropna()
    ir, nr = ir.align(nr, join="inner")
    if len(ir) < 30:
        return np.nan, np.nan
    cov_mat = np.cov(ir, nr)
    b = round(cov_mat[0][1] / cov_mat[1][1], 2) if cov_mat[1][1] != 0 else np.nan
    corr = round(ir.corr(nr), 2)
    return b, corr
