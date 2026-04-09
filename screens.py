"""
screens.py
Screen execution logic — applies filter conditions from config.SCREENS.
"""

import pandas as pd
import numpy as np


def _num(df, col):
    if col not in df.columns:
        return pd.Series(np.nan, index=df.index)
    return pd.to_numeric(df[col], errors='coerce')


def _sig(df, col):
    if col not in df.columns:
        return pd.Series('', index=df.index)
    return df[col].fillna('')


def run_screen(screen_name, base_df):
    """Apply a named screen and return matching rows."""
    d = base_df.copy()
    n = lambda c: _num(d, c)
    s = lambda c: _sig(d, c)

    screens = {
        "🚀 Momentum Leaders": (
            (s('Supertrend') == 'Bullish') & (s('MACD Signal') == 'Bullish') &
            (n('ROC 3M %') > 10) & (n('ROC 12M %') > 20) &
            (n('Current Price') > n('EMA 50')) & (n('Current Price') > n('EMA 200'))
        ),
        "📈 Breakout Candidates": (
            (n('% from 52W High') >= -5) & (n('RSI 14') >= 55) & (n('RSI 14') <= 75) &
            (s('MACD Signal') == 'Bullish') & (n('Vol ROC 1M %') > 20)
        ),
        "🔄 Reversal Watch": (
            (n('RSI 14') < 40) & (n('% from 52W Low') <= 20) &
            (s('MACD Signal') == 'Bullish')
        ),
        "📊 Volume Surge": (
            (n('Vol ROC 1M %') > 50) & (n('RSI 14') > 50) &
            (s('MACD Signal') == 'Bullish')
        ),
        "🏆 Quality Compounders": (
            (n('ROCE %') > 20) & (n('ROCE 3Y Avg %') > 15) & (n('ROE %') > 15) &
            (n('Debt/Equity') < 0.5) & (n('Sales Growth 3Y %') > 10)
        ),
        "💎 Hidden Gems": (
            (n('Market Cap (Cr)') < 20000) & (n('ROCE %') > 15) &
            (n('Debt/Equity') < 0.5) & (n('Sales Growth 3Y %') > 15) &
            (n('Promoter Holding %') > 50)
        ),
        "🧱 Consistent Growers": (
            (n('Sales Growth 1Y %') > 10) & (n('Sales Growth 3Y %') > 10) &
            (n('Profit Growth 1Y %') > 10) & (n('Profit Growth 3Y %') > 10) &
            (n('EPS Growth 3Y %') > 10)
        ),
        "🏗️ Debt Free": (
            (n('Debt/Equity') < 0.1) & (n('Interest Coverage') > 10) &
            (n('ROCE %') > 15) & (n('Profit Growth 1Y %') > 0)
        ),
        "💰 Value Picks": (
            (n('PE Ratio') < n('Sector PE')) & (n('PB Ratio') < n('Sector PB')) &
            (n('ROE %') > 12) & (n('Profit Growth 1Y %') > 0)
        ),
        "📉 Fallen Angels": (
            (n('% from 52W High') < -30) & (n('ROE %') > 12) & (n('ROCE %') > 12) &
            (n('Debt/Equity') < 1) & (n('Profit Growth 1Y %') > 0)
        ),
        "🎯 Low PEG": (
            (n('PEG Ratio') > 0) & (n('PEG Ratio') < 1) &
            (n('EPS Growth 3Y %') > 10) & (n('PE Ratio') < n('Sector PE'))
        ),
        "🔍 Undervalued Small Caps": (
            (n('Market Cap (Cr)') < 5000) & (n('PE Ratio') < n('Sector PE')) &
            (n('ROCE %') > 15) & (n('Debt/Equity') < 0.5)
        ),
        "🎁 Dividend Aristocrats": (
            (n('Dividend Yield %') > 2) & (n('Dividend Payout %') < 60) &
            (n('Dividend Payout %') > 10) & (n('Debt/Equity') < 0.5) & (n('Profit Growth 3Y %') > 5)
        ),
        "💵 High FCF Yield": (
            (n('FCF Yield %') > 3) & (n('Free Cash Flow (Cr)') > 0) & (n('ROCE %') > 12)
        ),
        "📆 Consistent Dividend Growers": (
            (n('Dividend Yield %') > 1) & (n('Dividend Payout %') < 50) &
            (n('Profit Growth 3Y %') > 10) & (n('Debt/Equity') < 0.5) & (n('Net Profit (Cr)') > 0)
        ),
        "⭐ SIP Worthy": (
            (n('ROCE 3Y Avg %') > 15) & (n('ROE 3Y Avg %') > 15) & (n('Debt/Equity') < 0.5) &
            (n('Sales Growth 3Y %') > 12) & (n('Profit Growth 3Y %') > 12) &
            (n('Promoter Holding %') > 50) & (n('Pledge %') < 5) & (n('SD 1Y %') < 35)
        ),
        "🌟 All Rounder": (
            (s('Supertrend') == 'Bullish') & (s('MACD Signal') == 'Bullish') &
            (n('ROCE %') > 15) & (n('PE Ratio') < n('Sector PE')) &
            (n('Debt/Equity') < 0.5) & (n('Profit Growth 1Y %') > 10)
        ),
        "👥 Operator Favorites": (
            (n('Promoter Holding %') > 60) & (n('Pledge %') < 2) &
            (n('FII Change %') > 0) & (n('ROCE %') > 12)
        ),
        "🔃 Turnaround Candidates": (
            (n('Net Profit Prev (Cr)') < 0) & (n('Net Profit (Cr)') > 0) &
            (n('Sales Growth 1Y %') > 0) & (n('Debt/Equity') < 2)
        ),
        "💪 Strong Bull Regime": (
            (s('Market Regime') == 'Strong Bull') &
            (n('Momentum Acceleration') > 0) & (s('Supertrend') == 'Bullish')
        ),
        "🛡️ Defensive Quality": (
            (n('SD 1Y %') < 20) & (n('ROCE %') > 15) & (n('Debt/Equity') < 0.3) &
            (n('Down Capture Ratio') < 90) &
            (s('Market Regime').isin(['Bull', 'Strong Bull']))
        ),
    }

    mask = screens.get(screen_name)
    if mask is None:
        return d
    return d[mask.fillna(False)]
