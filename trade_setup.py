"""
trade_setup.py
ATR-based trade setup: entry zone, stop loss, targets, R:R.
"""

import pandas as pd
import numpy as np


def calc_trade_levels(row, atr_mult_sl=1.5, target_r_multiples=(2.0, 3.0)):
    """
    Calculate trade levels for a single stock based on ATR.

    Returns dict with:
    - entry, stop, target1, target2
    - risk_pct, reward_pct
    - rr_ratio
    - suggested stop (max of ATR-based and EMA 200 if trending)
    """
    price = row.get('Current Price', np.nan)
    atr_pct = row.get('ATR % (14D)', np.nan)
    ema200 = row.get('EMA 200', np.nan)
    regime = row.get('Market Regime', '')

    if pd.isna(price) or pd.isna(atr_pct) or price <= 0:
        return None

    # ATR in absolute terms
    atr_abs = (atr_pct / 100) * price

    # Entry = current price (screener view)
    entry = price

    # ATR-based stop
    atr_stop = price - (atr_mult_sl * atr_abs)

    # If in bullish regime and EMA 200 is below current price,
    # use max(ATR stop, EMA 200 - small buffer) as a sensible SL
    if regime in ('Bull', 'Strong Bull') and not pd.isna(ema200) and ema200 < price:
        # Give 2% buffer below EMA 200
        ema_stop = ema200 * 0.98
        stop = max(atr_stop, ema_stop)
    else:
        stop = atr_stop

    risk_per_share = entry - stop
    if risk_per_share <= 0:
        return None

    # Targets based on R multiples
    target1 = entry + (target_r_multiples[0] * risk_per_share)
    target2 = entry + (target_r_multiples[1] * risk_per_share)

    risk_pct = (risk_per_share / entry) * 100
    reward1_pct = ((target1 - entry) / entry) * 100
    reward2_pct = ((target2 - entry) / entry) * 100

    return {
        'entry': round(entry, 2),
        'stop': round(stop, 2),
        'target1': round(target1, 2),
        'target2': round(target2, 2),
        'risk_pct': round(risk_pct, 2),
        'reward1_pct': round(reward1_pct, 2),
        'reward2_pct': round(reward2_pct, 2),
        'rr1': f"1:{target_r_multiples[0]:.1f}",
        'rr2': f"1:{target_r_multiples[1]:.1f}",
    }


def get_key_levels(row):
    """Returns key reference levels for a stock."""
    return {
        'high_52w':  row.get('52W High', np.nan),
        'low_52w':   row.get('52W Low', np.nan),
        'ema_50':    row.get('EMA 50', np.nan),
        'ema_200':   row.get('EMA 200', np.nan),
        'current':   row.get('Current Price', np.nan),
    }
