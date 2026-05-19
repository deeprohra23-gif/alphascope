"""
config.py
Column definitions, screen rules, color maps, and constants.
"""

# ────────────────────────────────────────────────
# COLUMN GROUPS FOR SUB-TABS
# ────────────────────────────────────────────────

# sym_col is set at runtime after loading data; these use placeholder
# The app prepends sym_col dynamically

OVERVIEW_COLS = [
    'Name', 'Sector', 'Industry', 'Cap Category', 'Market Cap (Cr)',
    'Current Price', 'Day Change %',
    'Technical Insight', 'Fundamental Insight',
    'Market Regime', 'Drawdown Status',
    'Technical Score', 'Momentum Score', 'Fundamental Score',
    'Composite Score', 'Universe Rank',
    'Index Membership',
]

TECHNICAL_COLS = [
    'Name', 'Current Price',
    'Technical Insight',
    'EMA 50', 'EMA 200', 'EMA Cross', 'Days Since EMA Cross',
    'RSI 14', 'MACD Signal', 'Supertrend',
    'Trend Consistency (12M)', 'Momentum Acceleration', 'Momentum Quality',
    'Vol Trend', 'Vol Ratio (20D/60D)',
    'Technical Score',
]

RETURNS_COLS = [
    'Name', 'Current Price',
    'ROC 1M %', 'ROC 3M %', 'ROC 6M %',
    '1Y CAGR %', '3Y CAGR %',
    'RS vs Nifty 1M %', 'RS vs Nifty 3M %', 'RS vs Nifty 6M %',
    'Momentum Rank 1M', 'Momentum Score',
]

RISK_COLS = [
    'Name', 'Current Price',
    'Beta 1Y (Daily)', 'Beta 5Y (Monthly)', 'SD 1Y %', 'ATR % (14D)',
    '1Y Max Drawdown %', 'Days Since 52W High',
    '52W High', '52W Low', '% from 52W High', '% from 52W Low',
    'Up Capture Ratio', 'Down Capture Ratio', 'Capture Ratio',
]

FUNDAMENTAL_COLS = [
    'Name', 'Sector',
    'Fundamental Insight',
    'PE Ratio', 'Sector PE', 'PB Ratio', 'Sector PB', 'EV/EBITDA', 'PEG Ratio',
    'ROE %', 'ROCE %', 'ROCE 3Y Avg %', 'ROE 3Y Avg %', 'ROA %', 'Net Profit Margin %',
    'Sales Growth 1Y %', 'Sales Growth 3Y %', 'Profit Growth 1Y %', 'Profit Growth 3Y %',
    'EPS Current', 'EPS Last Year', 'EPS Growth 1Y %', 'EPS Growth 3Y %',
    'Net Profit (Cr)', 'Net Profit Prev (Cr)', 'Debt/Equity', 'Interest Coverage',
    'Free Cash Flow (Cr)', 'FCF Yield %',
    'Dividend Yield %', 'Dividend Payout %',
    'Promoter Holding %', 'Pledge %', 'FII Change %', 'DII Change %',
    'Fundamental Score',
]

INDEX_COLS = [
    'Index', 'Category', 'Available ETF', 'Market Regime', 'Current Price', 'Day Change %',
    'EMA 50', 'EMA 200', 'EMA Cross',
    'RSI 14', 'MACD Signal', 'Supertrend',
    'ROC 1M %', 'ROC 3M %', 'ROC 6M %',
    '1Y CAGR %', '3Y CAGR %',
    'RS vs Nifty 1M %', 'RS vs Nifty 3M %', 'RS vs Nifty 6M %',
    'Momentum Rank 1M', 'Momentum Rank 3M',
    'Trend Consistency (12M)', 'Momentum Acceleration', 'Momentum Quality',
    'Up Capture Ratio', 'Down Capture Ratio', 'Capture Ratio',
    'Beta vs Nifty', 'Correlation vs Nifty (1Y)',
    'SD 1Y %', 'ATR % (14D)', 'Vol Trend', 'Vol Ratio (20D/60D)',
    '52W High', '52W Low', '% from 52W High', '% from 52W Low',
    '1Y Max Drawdown %', 'Days Since 52W High', 'Drawdown Status',
    'PE Ratio', 'PB Ratio', 'Dividend Yield %',
]

GLOBAL_COLS = [
    'Name', 'Category', 'Market Regime', 'Current Price', 'Day Change %',
    'EMA 50', 'EMA 200', 'EMA Cross',
    'RSI 14', 'MACD Signal', 'Supertrend',
    'ROC 1M %', 'ROC 3M %', 'ROC 6M %',
    '1Y CAGR %', '3Y CAGR %',
    'Trend Consistency (12M)', 'Momentum Acceleration', 'Momentum Quality',
    'SD 1Y %', 'ATR % (14D)', 'Vol Trend',
    '52W High', '52W Low', '% from 52W High', '% from 52W Low',
    '1Y Max Drawdown %', 'Days Since 52W High', 'Drawdown Status',
]


def all_display_cols(sym_col):
    """Ordered union of all column groups, with sym_col first."""
    seen = set()
    result = []
    for c in [sym_col] + OVERVIEW_COLS + TECHNICAL_COLS + RETURNS_COLS + RISK_COLS + FUNDAMENTAL_COLS:
        if c not in seen:
            seen.add(c)
            result.append(c)
    return result


# ────────────────────────────────────────────────
# COLOR MAPS
# ────────────────────────────────────────────────

REGIME_COLORS = {
    'Strong Bull': 'background-color:#0d2e1f; color:#00d4aa',
    'Bull':        'background-color:#0a1f35; color:#4da6ff',
    'Bear':        'background-color:#2e1515; color:#ff6b6b',
    'Strong Bear': 'background-color:#3d0a0a; color:#ff4444',
}

DD_COLORS = {
    'At High':    'background-color:#0d2e1f; color:#00d4aa',
    'Recovering': 'background-color:#2a1f0a; color:#ffaa33',
    'Correcting': 'background-color:#2e1a0a; color:#ff8844',
    'Damaged':    'background-color:#2e0d0d; color:#ff4d4d',
}

CROSS_COLORS = {
    'Golden Cross': 'background-color:#0d2e1f; color:#00d4aa',
    'Death Cross':  'background-color:#2e0d0d; color:#ff4d4d',
}

VOL_COLORS = {
    'Rising':  'background-color:#2e1515; color:#ff6b6b',
    'Stable':  'background-color:#1a1a2e; color:#aaaacc',
    'Falling': 'background-color:#0d2e1f; color:#00d4aa',
}

SIGNAL_COLORS = {
    'Bullish': 'background-color:#0d2e1f; color:#00d4aa',
    'Bearish': 'background-color:#2e0d0d; color:#ff4d4d',
}

# Columns that get green/red coloring based on sign
GREEN_RED_COLS = [
    'Day Change %', 'ROC 1M %', 'ROC 3M %', 'ROC 6M %', 'Vol ROC 1M %',
    '% from 52W High', '% from 52W Low', '1Y Max Drawdown %',
    '1Y CAGR %', '3Y CAGR %',
    'RS vs Nifty 1M %', 'RS vs Nifty 3M %', 'RS vs Nifty 6M %',
    'Momentum Acceleration', 'Momentum Quality',
    'Sales Growth 1Y %', 'Sales Growth 3Y %',
    'Profit Growth 1Y %', 'Profit Growth 3Y %',
    'EPS Growth 1Y %', 'EPS Growth 3Y %',
    'FCF Yield %', 'FII Change %', 'DII Change %',
    'Net Profit (Cr)', 'Net Profit Prev (Cr)',
    'Capture Ratio',
]


# ────────────────────────────────────────────────
# SCREEN DEFINITIONS
# ────────────────────────────────────────────────

SCREENS = {
    "🚀 Momentum Leaders": {
        "desc": "Strong price momentum with bullish technical setup.",
        "rules": ["Supertrend = Bullish", "MACD Signal = Bullish", "Price > EMA 50 & EMA 200", "ROC 3M > 10%", "ROC 12M > 20%"],
        "tab": "🚀 Momentum"
    },
    "📈 Breakout Candidates": {
        "desc": "Near 52W high with increasing volume — potential breakouts.",
        "rules": ["Within 5% of 52W High", "RSI 55-75", "MACD = Bullish", "Vol ROC 1M > 20%"],
        "tab": "🚀 Momentum"
    },
    "🔄 Reversal Watch": {
        "desc": "Oversold stocks showing early bullish reversal signs.",
        "rules": ["RSI < 40", "Within 20% of 52W Low", "MACD = Bullish"],
        "tab": "🚀 Momentum"
    },
    "📊 Volume Surge": {
        "desc": "Unusual volume spike with bullish momentum.",
        "rules": ["Vol ROC 1M > 50%", "RSI > 50", "MACD = Bullish"],
        "tab": "🚀 Momentum"
    },
    "🏆 Quality Compounders": {
        "desc": "High quality businesses with consistent profitability.",
        "rules": ["ROCE > 20%", "ROCE 3Y Avg > 15%", "ROE > 15%", "D/E < 0.5", "Sales Growth 3Y > 10%"],
        "tab": "🏆 Quality"
    },
    "💎 Hidden Gems": {
        "desc": "Under-radar small/mid caps with strong fundamentals.",
        "rules": ["Mkt Cap < 20,000 Cr", "ROCE > 15%", "D/E < 0.5", "Sales Growth 3Y > 15%", "Promoter > 50%"],
        "tab": "🏆 Quality"
    },
    "🧱 Consistent Growers": {
        "desc": "Companies growing consistently across short and long term.",
        "rules": ["Sales Growth 1Y & 3Y > 10%", "Profit Growth 1Y & 3Y > 10%", "EPS Growth 3Y > 10%"],
        "tab": "🏆 Quality"
    },
    "🏗️ Debt Free": {
        "desc": "Financially clean companies with negligible debt.",
        "rules": ["D/E < 0.1", "Interest Coverage > 10x", "ROCE > 15%", "Profit Growth 1Y > 0%"],
        "tab": "🏆 Quality"
    },
    "💰 Value Picks": {
        "desc": "Fundamentally sound stocks below sector valuation.",
        "rules": ["PE < Sector PE", "PB < Sector PB", "ROE > 12%", "Profit Growth 1Y > 0%"],
        "tab": "💎 Value"
    },
    "📉 Fallen Angels": {
        "desc": "Fundamentally strong stocks beaten down from highs.",
        "rules": ["Down > 30% from 52W High", "ROE > 12%", "ROCE > 12%", "D/E < 1"],
        "tab": "💎 Value"
    },
    "🎯 Low PEG": {
        "desc": "Growth stocks at reasonable valuations.",
        "rules": ["PEG 0-1", "EPS Growth 3Y > 10%", "PE < Sector PE"],
        "tab": "💎 Value"
    },
    "🔍 Undervalued Small Caps": {
        "desc": "Small caps below sector PE with strong returns.",
        "rules": ["Mkt Cap < 5,000 Cr", "PE < Sector PE", "ROCE > 15%", "D/E < 0.5"],
        "tab": "💎 Value"
    },
    "🎁 Dividend Aristocrats": {
        "desc": "High yield with sustainable payout and low debt.",
        "rules": ["Div Yield > 2%", "Payout 10-60%", "D/E < 0.5", "Profit Growth 3Y > 5%"],
        "tab": "🎁 Income"
    },
    "💵 High FCF Yield": {
        "desc": "Strong free cash flow relative to market cap.",
        "rules": ["FCF Yield > 3%", "FCF > 0", "ROCE > 12%"],
        "tab": "🎁 Income"
    },
    "📆 Consistent Dividend Growers": {
        "desc": "Companies likely to grow dividends.",
        "rules": ["Div Yield > 1%", "Payout < 50%", "Profit Growth 3Y > 10%", "D/E < 0.5"],
        "tab": "🎁 Income"
    },
    "⭐ SIP Worthy": {
        "desc": "Best for systematic investment — quality + consistency + safety.",
        "rules": ["ROCE 3Y Avg > 15%", "ROE 3Y Avg > 15%", "D/E < 0.5", "Sales Growth 3Y > 12%", "Promoter > 50%", "SD 1Y < 35%"],
        "tab": "⭐ Combined"
    },
    "🌟 All Rounder": {
        "desc": "Strong on technicals, fundamentals and valuation.",
        "rules": ["Supertrend = Bullish", "MACD = Bullish", "ROCE > 15%", "PE < Sector PE", "D/E < 0.5"],
        "tab": "⭐ Combined"
    },
    "👥 Operator Favorites": {
        "desc": "High promoter conviction with institutional interest.",
        "rules": ["Promoter > 60%", "Pledge < 2%", "FII Change > 0%", "ROCE > 12%"],
        "tab": "⭐ Combined"
    },
    "🔃 Turnaround Candidates": {
        "desc": "Loss-making last year, profitable now.",
        "rules": ["Net Profit Prev < 0", "Net Profit > 0", "Sales Growth 1Y > 0%", "D/E < 2"],
        "tab": "⭐ Combined"
    },
    "💪 Strong Bull Regime": {
        "desc": "Stocks in Strong Bull market regime with accelerating momentum.",
        "rules": ["Market Regime = Strong Bull", "Momentum Acceleration > 0", "Supertrend = Bullish"],
        "tab": "⭐ Combined"
    },
    "🛡️ Defensive Quality": {
        "desc": "Low volatility quality stocks — ideal in uncertain markets.",
        "rules": ["SD 1Y < 20%", "ROCE > 15%", "D/E < 0.3", "Down Capture < 90", "Market Regime = Bull or Strong Bull"],
        "tab": "⭐ Combined"
    },
}
