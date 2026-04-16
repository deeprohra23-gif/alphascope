"""
styling.py
Unified DataFrame styling — replaces the three duplicate style functions.
"""

import numpy as np
from config import (
    REGIME_COLORS, DD_COLORS, CROSS_COLORS, VOL_COLORS,
    SIGNAL_COLORS, GREEN_RED_COLS,
)

# Insight colors (defined inline to avoid circular imports)
INSIGHT_STYLES = {
    'Strong Buy':  'background-color:#0d2e1f; color:#00d4aa; font-weight:600',
    'Buy':         'background-color:#0a1f35; color:#4da6ff; font-weight:600',
    'Hold':        'background-color:#1a1a2e; color:#aaaacc',
    'Sell':        'background-color:#2e1515; color:#ff8844',
    'Strong Sell': 'background-color:#3d0a0a; color:#ff4444; font-weight:600',
}


def _color_map(val, mapping):
    return mapping.get(str(val), '')


def _color_num(val):
    try:
        v = float(val)
        if v > 0:
            return 'color:#00d4aa'
        elif v < 0:
            return 'color:#ff4d4d'
    except Exception:
        pass
    return ''


def style_dataframe(data):
    """
    Universal styling function for stock, index, and global dataframes.
    Applies color maps for categorical columns and green/red for numeric columns.
    """
    styled = data.style

    # Categorical color maps
    col_fn_pairs = [
        ('Market Regime',       lambda v: _color_map(v, REGIME_COLORS)),
        ('Drawdown Status',     lambda v: _color_map(v, DD_COLORS)),
        ('EMA Cross',           lambda v: _color_map(v, CROSS_COLORS)),
        ('Vol Trend',           lambda v: _color_map(v, VOL_COLORS)),
        ('MACD Signal',         lambda v: _color_map(v, SIGNAL_COLORS)),
        ('Supertrend',          lambda v: _color_map(v, SIGNAL_COLORS)),
        ('Technical Insight',   lambda v: _color_map(v, INSIGHT_STYLES)),
        ('Fundamental Insight', lambda v: _color_map(v, INSIGHT_STYLES)),
    ]

    for col, fn in col_fn_pairs:
        if col in data.columns:
            styled = styled.map(fn, subset=[col])

    # Green/red for numeric columns
    gr_cols = [c for c in GREEN_RED_COLS if c in data.columns]
    if gr_cols:
        styled = styled.map(_color_num, subset=gr_cols)

    # Number formatting
    float_cols = data.select_dtypes(include=[np.number]).columns.tolist()
    fmt = {c: '{:.2f}' for c in float_cols}

    # Large numbers with commas
    for c in ['Market Cap (Cr)', 'Net Profit (Cr)', 'Net Profit Prev (Cr)', 'Free Cash Flow (Cr)']:
        if c in fmt:
            fmt[c] = '{:,.0f}'

    # Special precision
    if 'FCF Yield %' in fmt:
        fmt['FCF Yield %'] = '{:.4f}'

    # Integer columns
    for c in ['Momentum Rank 1M', 'Days Since 52W High', 'Days Since EMA Cross',
              'Trend Consistency (12M)', '_rank_sort', 'Universe Rank',
              'Momentum Rank 3M', 'Momentum Rank 6M']:
        if c in fmt:
            fmt[c] = '{:.0f}'

    # Score columns
    for c in ['Technical Score', 'Momentum Score', 'Fundamental Score', 'Composite Score']:
        if c in fmt:
            fmt[c] = '{:.1f}'

    styled = styled.format(fmt, na_rep='—')
    return styled
