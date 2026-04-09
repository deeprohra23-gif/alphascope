"""
scoring.py
Composite scoring functions for stocks.
"""

import pandas as pd
import numpy as np


def percentile_rank(series):
    """Convert series to 0-100 percentile rank."""
    return series.rank(pct=True) * 100


def inverse_percentile_rank(series):
    """Inverse percentile — lower value = higher score."""
    return (1 - series.rank(pct=True)) * 100


def calc_technical_score(df_):
    score = pd.Series(0.0, index=df_.index)
    count = pd.Series(0.0, index=df_.index)

    # Market Regime (20%)
    if 'Market Regime' in df_.columns:
        s = df_['Market Regime'].map({'Strong Bull': 100, 'Bull': 66, 'Bear': 33, 'Strong Bear': 0})
        mask = s.notna()
        score[mask] += s[mask] * 0.20
        count[mask] += 0.20

    # EMA Cross (10%)
    if 'EMA Cross' in df_.columns:
        s = df_['EMA Cross'].map({'Golden Cross': 100, 'Death Cross': 0})
        mask = s.notna()
        score[mask] += s[mask] * 0.10
        count[mask] += 0.10

    # MACD Signal (10%)
    if 'MACD Signal' in df_.columns:
        s = df_['MACD Signal'].map({'Bullish': 100, 'Bearish': 0})
        mask = s.notna()
        score[mask] += s[mask] * 0.10
        count[mask] += 0.10

    # Supertrend (10%)
    if 'Supertrend' in df_.columns:
        s = df_['Supertrend'].map({'Bullish': 100, 'Bearish': 0})
        mask = s.notna()
        score[mask] += s[mask] * 0.10
        count[mask] += 0.10

    # Trend Consistency (15%)
    if 'Trend Consistency (12M)' in df_.columns:
        s = pd.to_numeric(df_['Trend Consistency (12M)'], errors='coerce')
        s_scaled = (s / 12 * 100).clip(0, 100)
        mask = s_scaled.notna()
        score[mask] += s_scaled[mask] * 0.15
        count[mask] += 0.15

    # Drawdown Status (15%)
    if 'Drawdown Status' in df_.columns:
        dd_map = {'At High': 100, 'Recovering': 66, 'Correcting': 33, 'Damaged': 0}
        s = df_['Drawdown Status'].map(dd_map)
        mask = s.notna()
        score[mask] += s[mask] * 0.15
        count[mask] += 0.15

    # Vol Trend (10%)
    if 'Vol Trend' in df_.columns:
        s = df_['Vol Trend'].map({'Falling': 100, 'Stable': 50, 'Rising': 0})
        mask = s.notna()
        score[mask] += s[mask] * 0.10
        count[mask] += 0.10

    # RSI (10%) — peaks at 65-70
    if 'RSI 14' in df_.columns:
        rsi = pd.to_numeric(df_['RSI 14'], errors='coerce')
        rsi_score = pd.Series(np.nan, index=df_.index)
        rsi_score[rsi.notna()] = np.where(
            rsi[rsi.notna()] <= 50,
            rsi[rsi.notna()] / 50 * 70,
            np.where(
                rsi[rsi.notna()] <= 70,
                70 + (rsi[rsi.notna()] - 50) / 20 * 30,
                100 - (rsi[rsi.notna()] - 70) / 30 * 50
            )
        )
        mask = rsi_score.notna()
        score[mask] += rsi_score[mask] * 0.10
        count[mask] += 0.10

    result = pd.Series(np.nan, index=df_.index)
    valid = count > 0
    result[valid] = (score[valid] / count[valid]).round(1)
    return result


def calc_momentum_score(df_):
    score = pd.Series(0.0, index=df_.index)
    count = pd.Series(0.0, index=df_.index)

    weights = {
        'ROC 1M %':         0.15,
        'ROC 3M %':         0.20,
        'ROC 6M %':         0.20,
        'RS vs Nifty 3M %': 0.20,
        'Momentum Quality': 0.15,
    }

    for col, w in weights.items():
        if col in df_.columns:
            s = pd.to_numeric(df_[col], errors='coerce')
            pr = percentile_rank(s)
            mask = pr.notna()
            score[mask] += pr[mask] * w
            count[mask] += w

    # Momentum Acceleration (10%)
    if 'Momentum Acceleration' in df_.columns:
        s = pd.to_numeric(df_['Momentum Acceleration'], errors='coerce')
        s_score = s.apply(lambda x: 75 if x > 0 else (25 if x < 0 else 50) if not pd.isna(x) else np.nan)
        mask = s_score.notna()
        score[mask] += s_score[mask] * 0.10
        count[mask] += 0.10

    result = pd.Series(np.nan, index=df_.index)
    valid = count > 0
    result[valid] = (score[valid] / count[valid]).round(1)
    return result


def calc_fundamental_score(df_):
    score = pd.Series(0.0, index=df_.index)
    count = pd.Series(0.0, index=df_.index)

    # Higher is better
    good_cols = {
        'ROCE %':              0.15,
        'ROE %':               0.15,
        'Net Profit Margin %': 0.10,
        'Sales Growth 3Y %':   0.10,
        'Profit Growth 3Y %':  0.10,
        'Promoter Holding %':  0.10,
    }
    for col, w in good_cols.items():
        if col in df_.columns:
            s = pd.to_numeric(df_[col], errors='coerce')
            pr = percentile_rank(s)
            mask = pr.notna()
            score[mask] += pr[mask] * w
            count[mask] += w

    # Lower is better
    bad_cols = {
        'Debt/Equity': 0.10,
        'Pledge %':    0.10,
    }
    for col, w in bad_cols.items():
        if col in df_.columns:
            s = pd.to_numeric(df_[col], errors='coerce')
            pr = inverse_percentile_rank(s)
            mask = pr.notna()
            score[mask] += pr[mask] * w
            count[mask] += w

    # PE vs Sector PE (10%)
    if 'PE Ratio' in df_.columns and 'Sector PE' in df_.columns:
        pe = pd.to_numeric(df_['PE Ratio'], errors='coerce')
        sec_pe = pd.to_numeric(df_['Sector PE'], errors='coerce')
        ratio = pe / sec_pe.replace(0, np.nan)
        s_score = ratio.apply(
            lambda x: 100 if x < 0.7 else
                      75  if x < 1.0 else
                      50  if x < 1.3 else
                      25  if not pd.isna(x) else np.nan
        )
        mask = s_score.notna()
        score[mask] += s_score[mask] * 0.10
        count[mask] += 0.10

    result = pd.Series(np.nan, index=df_.index)
    valid = count > 0
    result[valid] = (score[valid] / count[valid]).round(1)
    return result


def add_scores(df_, universe_df=None):
    """Calculate all scores. universe_df is the full filtered universe for relative ranking."""
    base = universe_df if universe_df is not None else df_

    df_['Technical Score']   = calc_technical_score(base).reindex(df_.index)
    df_['Momentum Score']    = calc_momentum_score(base).reindex(df_.index)
    df_['Fundamental Score'] = calc_fundamental_score(base).reindex(df_.index)

    t = pd.to_numeric(df_['Technical Score'],   errors='coerce')
    m = pd.to_numeric(df_['Momentum Score'],    errors='coerce')
    f = pd.to_numeric(df_['Fundamental Score'], errors='coerce')
    df_['Composite Score'] = ((t + m + f) / 3).round(1)

    rank_numeric = df_['Composite Score'].rank(ascending=False, method='first', na_option='bottom')
    df_['Universe Rank'] = rank_numeric.astype('Int64')
    df_['_rank_sort'] = rank_numeric

    return df_
