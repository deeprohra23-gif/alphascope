"""
history.py
Helpers for reading daily snapshots and computing day-over-day changes.
"""

import os
import glob
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path


HISTORY_DIR = 'data/history'


def list_snapshots():
    """Return sorted list of (date_str, filepath) tuples, most recent first."""
    if not os.path.isdir(HISTORY_DIR):
        return []
    files = glob.glob(f'{HISTORY_DIR}/*.csv')
    snapshots = []
    for f in files:
        basename = os.path.basename(f).replace('.csv', '')
        try:
            dt = datetime.strptime(basename, '%Y-%m-%d')
            snapshots.append((basename, f, dt))
        except ValueError:
            continue
    snapshots.sort(key=lambda x: x[2], reverse=True)
    return [(s[0], s[1]) for s in snapshots]


def load_snapshot(date_str):
    """Load a specific snapshot by date string (YYYY-MM-DD)."""
    path = f'{HISTORY_DIR}/{date_str}.csv'
    if not os.path.exists(path):
        return None
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def get_previous_snapshot(today_df):
    """
    Get the two most recent snapshots for comparison.
    Returns (date_str, df) of the second-most-recent snapshot.
    """
    snapshots = list_snapshots()
    if len(snapshots) < 2:
        return None, None

    # Most recent is snapshots[0], second most recent is snapshots[1]
    try:
        df = pd.read_csv(snapshots[1][1])
        return snapshots[1][0], df
    except Exception:
        return None, None

def compute_changes(today_df, yday_df, sym_col='Symbol'):
    """
    Compute day-over-day changes.

    Returns dict with:
    - new_golden_cross: stocks with Golden Cross today but not yesterday
    - new_death_cross: same for Death Cross
    - regime_upgraded: stocks whose regime improved
    - regime_downgraded: stocks whose regime worsened
    - newly_damaged: Drawdown Status moved to Damaged
    - newly_at_high: Drawdown Status moved to At High
    - entered_strong_bull: regime changed to Strong Bull
    - entered_strong_bear: regime changed to Strong Bear
    """
    if today_df is None or yday_df is None:
        return {}

    # Regime ordering for upgrade/downgrade detection
    regime_order = {
        'Strong Bear': 0, 'Bear': 1, 'Bull': 2, 'Strong Bull': 3
    }

    # Merge on symbol
    merged = today_df[[sym_col, 'Name']].copy() if 'Name' in today_df.columns else today_df[[sym_col]].copy()

    cols_to_compare = ['EMA Cross', 'Market Regime', 'Drawdown Status', 'Supertrend', 'MACD Signal']
    for col in cols_to_compare:
        if col in today_df.columns and col in yday_df.columns:
            today_map = today_df.set_index(sym_col)[col]
            yday_map = yday_df.set_index(sym_col)[col]
            merged[f'{col}_today'] = merged[sym_col].map(today_map)
            merged[f'{col}_yday'] = merged[sym_col].map(yday_map)

    # Attach today's snapshot data for rendering
    for col in ['Sector', 'Current Price', 'ROC 3M %', 'Composite Score', 'Market Regime']:
        if col in today_df.columns:
            col_map = today_df.set_index(sym_col)[col]
            merged[col] = merged[sym_col].map(col_map)

    changes = {}

    # Fresh Golden Cross (today's Golden Cross, yday's was Death Cross or NaN)
    if 'EMA Cross_today' in merged.columns and 'EMA Cross_yday' in merged.columns:
        new_gc = merged[
            (merged['EMA Cross_today'] == 'Golden Cross') &
            (merged['EMA Cross_yday'] != 'Golden Cross') &
            merged['EMA Cross_yday'].notna()
        ]
        changes['new_golden_cross'] = new_gc

        new_dc = merged[
            (merged['EMA Cross_today'] == 'Death Cross') &
            (merged['EMA Cross_yday'] != 'Death Cross') &
            merged['EMA Cross_yday'].notna()
        ]
        changes['new_death_cross'] = new_dc

    # Regime upgrades / downgrades
    if 'Market Regime_today' in merged.columns and 'Market Regime_yday' in merged.columns:
        merged['_regime_today_n'] = merged['Market Regime_today'].map(regime_order)
        merged['_regime_yday_n'] = merged['Market Regime_yday'].map(regime_order)

        upgraded = merged[merged['_regime_today_n'] > merged['_regime_yday_n']]
        downgraded = merged[merged['_regime_today_n'] < merged['_regime_yday_n']]
        changes['regime_upgraded'] = upgraded
        changes['regime_downgraded'] = downgraded

        # Into Strong Bull / Strong Bear
        entered_sb = merged[
            (merged['Market Regime_today'] == 'Strong Bull') &
            (merged['Market Regime_yday'] != 'Strong Bull')
        ]
        entered_sbr = merged[
            (merged['Market Regime_today'] == 'Strong Bear') &
            (merged['Market Regime_yday'] != 'Strong Bear')
        ]
        changes['entered_strong_bull'] = entered_sb
        changes['entered_strong_bear'] = entered_sbr

    # Drawdown status changes
    if 'Drawdown Status_today' in merged.columns and 'Drawdown Status_yday' in merged.columns:
        newly_damaged = merged[
            (merged['Drawdown Status_today'] == 'Damaged') &
            (merged['Drawdown Status_yday'] != 'Damaged') &
            merged['Drawdown Status_yday'].notna()
        ]
        newly_at_high = merged[
            (merged['Drawdown Status_today'] == 'At High') &
            (merged['Drawdown Status_yday'] != 'At High') &
            merged['Drawdown Status_yday'].notna()
        ]
        changes['newly_damaged'] = newly_damaged
        changes['newly_at_high'] = newly_at_high

    # Supertrend flips
    if 'Supertrend_today' in merged.columns and 'Supertrend_yday' in merged.columns:
        st_bull_flip = merged[
            (merged['Supertrend_today'] == 'Bullish') &
            (merged['Supertrend_yday'] == 'Bearish')
        ]
        st_bear_flip = merged[
            (merged['Supertrend_today'] == 'Bearish') &
            (merged['Supertrend_yday'] == 'Bullish')
        ]
        changes['supertrend_bullish_flip'] = st_bull_flip
        changes['supertrend_bearish_flip'] = st_bear_flip

    return changes


def get_screen_performance(screen_name, days_ago, screen_fn, today_df, sym_col='Symbol'):
    """
    Compute performance of a screen's picks N days ago vs today.

    Returns dict with:
    - picks_count: stocks that matched the screen N days ago
    - survivors: how many still have price data today
    - avg_return: average return of picks from N days ago to today
    - winners: count with positive return
    - losers: count with negative return
    - or None if snapshot unavailable
    """
    target_date = datetime.now() - timedelta(days=days_ago)
    # Find the nearest available snapshot on or before target_date
    snapshots = list_snapshots()
    if not snapshots:
        return None

    past_snapshot = None
    past_date = None
    for date_str, path in snapshots:
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            if dt <= target_date:
                past_snapshot = pd.read_csv(path)
                past_date = date_str
                break
        except Exception:
            continue

    if past_snapshot is None:
        return None

    # Run the screen on past snapshot
    try:
        past_picks = screen_fn(screen_name, past_snapshot)
    except Exception:
        return None

    if past_picks is None or past_picks.empty:
        return None

    # Match against today's data
    past_syms = past_picks[sym_col].tolist()
    past_prices = past_picks.set_index(sym_col)['Current Price'].to_dict()

    today_matched = today_df[today_df[sym_col].isin(past_syms)].copy()
    today_prices = today_matched.set_index(sym_col)['Current Price'].to_dict()

    returns = []
    for sym in past_syms:
        if sym in today_prices and sym in past_prices:
            p0 = past_prices[sym]
            p1 = today_prices[sym]
            if p0 > 0:
                ret = (p1 - p0) / p0 * 100
                returns.append(ret)

    if not returns:
        return None

    avg_ret = sum(returns) / len(returns)
    winners = sum(1 for r in returns if r > 0)
    losers = sum(1 for r in returns if r <= 0)

    return {
        'picks_count': len(past_syms),
        'survivors': len(returns),
        'avg_return': round(avg_ret, 2),
        'winners': winners,
        'losers': losers,
        'win_rate': round(winners / len(returns) * 100, 1) if returns else 0,
        'snapshot_date': past_date,
    }
