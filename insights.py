"""
insights.py
Technical and Fundamental Insight ratings (Strong Buy / Buy / Hold / Sell / Strong Sell).
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


def calc_technical_insight(df):
    """
    Returns a series with Technical Insight rating for each row.
    Rules:
    - Strong Buy: Strong Bull + Supertrend Bull + MACD Bull + Price > EMA50 > EMA200 + RSI 50-70
    - Buy: Bull/Strong Bull + Supertrend Bull + (MACD Bull OR Price > EMA50) + RSI > 45
    - Sell: Bear/Strong Bear + Supertrend Bear + (MACD Bear OR Price < EMA50)
    - Strong Sell: Strong Bear + Supertrend Bear + MACD Bear + Damaged
    - Hold: everything else (including missing data cases)
    """
    regime = _sig(df, 'Market Regime')
    st_sig = _sig(df, 'Supertrend')
    macd = _sig(df, 'MACD Signal')
    dd = _sig(df, 'Drawdown Status')

    price = _num(df, 'Current Price')
    ema50 = _num(df, 'EMA 50')
    ema200 = _num(df, 'EMA 200')
    rsi = _num(df, 'RSI 14')

    above_both_ema = (price > ema50) & (ema50 > ema200)
    above_ema50 = price > ema50
    below_ema50 = price < ema50

    # Strong Buy
    strong_buy = (
        (regime == 'Strong Bull') &
        (st_sig == 'Bullish') &
        (macd == 'Bullish') &
        above_both_ema.fillna(False) &
        (rsi >= 50) & (rsi <= 70)
    )

    # Buy
    buy = (
        regime.isin(['Bull', 'Strong Bull']) &
        (st_sig == 'Bullish') &
        ((macd == 'Bullish') | above_ema50.fillna(False)) &
        (rsi > 45)
    )

    # Strong Sell
    strong_sell = (
        (regime == 'Strong Bear') &
        (st_sig == 'Bearish') &
        (macd == 'Bearish') &
        (dd == 'Damaged')
    )

    # Sell
    sell = (
        regime.isin(['Bear', 'Strong Bear']) &
        (st_sig == 'Bearish') &
        ((macd == 'Bearish') | below_ema50.fillna(False))
    )

    # Assign in order of priority (strongest first)
    result = pd.Series('Hold', index=df.index)
    result[sell] = 'Sell'
    result[strong_sell] = 'Strong Sell'
    result[buy] = 'Buy'
    result[strong_buy] = 'Strong Buy'

    # If critical data missing, mark as Hold
    missing = regime.isin(['', np.nan]) | (price.isna() & ema50.isna())
    result[missing] = 'Hold'

    return result


def calc_fundamental_insight(df):
    """
    Returns a series with Fundamental Insight rating for each row.
    Rules:
    - Strong Buy: ROCE>20 & ROE>18 & D/E<0.5 & Profit Growth 3Y>15 & EPS Growth 3Y>15 & PE<Sector PE & Promoter>50
    - Buy: ROCE>15 & ROE>12 & D/E<1 & Profit Growth 3Y>10 & EPS Growth 3Y>10 & Sales Growth 3Y>8
    - Strong Sell: ROCE<5 & Profit Growth 3Y<0 & EPS Growth 3Y<0 & D/E>2 & Pledge>30
    - Sell: ROCE<8 OR Profit Growth 3Y<0 OR EPS Growth 3Y<-10 OR D/E>2 OR PE>3×Sector PE
    - Hold: everything else
    """
    roce = _num(df, 'ROCE %')
    roe = _num(df, 'ROE %')
    de = _num(df, 'Debt/Equity')
    pg3 = _num(df, 'Profit Growth 3Y %')
    eg3 = _num(df, 'EPS Growth 3Y %')
    sg3 = _num(df, 'Sales Growth 3Y %')
    pe = _num(df, 'PE Ratio')
    sector_pe = _num(df, 'Sector PE')
    promoter = _num(df, 'Promoter Holding %')
    pledge = _num(df, 'Pledge %')

    pe_ratio_to_sector = pe / sector_pe.replace(0, np.nan)

    # Strong Buy — all stringent criteria met
    strong_buy = (
        (roce > 20) &
        (roe > 18) &
        (de < 0.5) &
        (pg3 > 15) &
        (eg3 > 15) &
        (pe < sector_pe) &
        (promoter > 50)
    )

    # Buy — solid quality & growth
    buy = (
        (roce > 15) &
        (roe > 12) &
        (de < 1) &
        (pg3 > 10) &
        (eg3 > 10) &
        (sg3 > 8)
    )

    # Strong Sell — multiple red flags
    strong_sell = (
        (roce < 5) &
        (pg3 < 0) &
        (eg3 < 0) &
        (de > 2) &
        (pledge > 30)
    )

    # Sell — any single major red flag
    sell = (
        (roce < 8) |
        (pg3 < 0) |
        (eg3 < -10) |
        (de > 2) |
        (pe_ratio_to_sector > 3)
    )

    # Assign in priority order
    result = pd.Series('Hold', index=df.index)
    result[sell.fillna(False)] = 'Sell'
    result[strong_sell.fillna(False)] = 'Strong Sell'
    result[buy.fillna(False)] = 'Buy'
    result[strong_buy.fillna(False)] = 'Strong Buy'

    # If core fundamental data is missing, mark as Hold
    missing = roce.isna() & roe.isna() & pg3.isna()
    result[missing] = 'Hold'

    return result


def add_insights(df):
    """Add Technical Insight and Fundamental Insight columns to dataframe."""
    df['Technical Insight'] = calc_technical_insight(df)
    df['Fundamental Insight'] = calc_fundamental_insight(df)
    return df


# Color map for the insight ratings
INSIGHT_COLORS = {
    'Strong Buy':  'background-color:#0d2e1f; color:#00d4aa; font-weight:600',
    'Buy':         'background-color:#0a1f35; color:#4da6ff; font-weight:600',
    'Hold':        'background-color:#1a1a2e; color:#aaaacc',
    'Sell':        'background-color:#2e1515; color:#ff8844',
    'Strong Sell': 'background-color:#3d0a0a; color:#ff4444; font-weight:600',
}
