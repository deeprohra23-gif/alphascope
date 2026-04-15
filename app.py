import streamlit as st
import pandas as pd
import numpy as np
import re
import os
from datetime import datetime

from config import (
    OVERVIEW_COLS, TECHNICAL_COLS, RETURNS_COLS, RISK_COLS, FUNDAMENTAL_COLS,
    INDEX_COLS, GLOBAL_COLS, SCREENS, all_display_cols,
)
from scoring import add_scores
from styling import style_dataframe
from screens import run_screen


def get_data_timestamp():
    """Get last modified time of technicals.csv as data freshness indicator."""
    from datetime import timezone, timedelta
    IST = timezone(timedelta(hours=5, minutes=30))
    for path in ['data/technicals.csv', 'technicals.csv']:
        if os.path.exists(path):
            mtime = os.path.getmtime(path)
            dt = datetime.fromtimestamp(mtime, tz=IST)
            return dt.strftime('%d %b %Y, %I:%M %p IST')
    return 'Unknown'
# ────────────────────────────────────────────────
# PAGE CONFIG & STYLES
# ────────────────────────────────────────────────
st.set_page_config(
    page_title="StockRadar India",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
    .main { background-color: #0f1117; }
    .stApp { background-color: #0f1117; color: #e0e0e0; }
    .screener-header { padding: 1.2rem 0 0.8rem 0; border-bottom: 1px solid #2a2a2a; margin-bottom: 1.2rem; }
    .screener-title { font-family: 'IBM Plex Mono', monospace; font-size: 1.4rem; font-weight: 600; color: #00d4aa; letter-spacing: -0.5px; margin: 0; }
    .screener-subtitle { font-size: 0.75rem; color: #555; margin-top: 0.2rem; font-family: 'IBM Plex Mono', monospace; }
    .metric-card { background: #16181f; border: 1px solid #2a2a2a; border-radius: 8px; padding: 0.7rem 1rem; }
    .metric-label { font-size: 0.65rem; color: #555; text-transform: uppercase; letter-spacing: 1px; font-family: 'IBM Plex Mono', monospace; }
    .metric-value { font-size: 1.4rem; font-weight: 600; color: #00d4aa; font-family: 'IBM Plex Mono', monospace; margin-top: 0.1rem; }
    .screen-desc { background: #16181f; border: 1px solid #2a2a2a; border-left: 3px solid #00d4aa; border-radius: 0; padding: 0.8rem 1rem; margin-bottom: 1rem; font-size: 0.8rem; color: #aaa; font-family: 'IBM Plex Mono', monospace; }
    .screen-rule { color: #00d4aa; }
    .pulse-banner { background: #0d2e1f; border: 1px solid #00d4aa33; border-radius: 8px; padding: 0.8rem 1.2rem; margin-bottom: 1rem; }
    [data-testid="stSidebar"] { background-color: #13151c; border-right: 1px solid #2a2a2a; }
    [data-testid="stSidebar"] .stMarkdown h3 { font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; color: #00d4aa; text-transform: uppercase; letter-spacing: 2px; margin-top: 1rem; margin-bottom: 0.4rem; }
    [data-testid="stDataFrame"] { border: 1px solid #2a2a2a; border-radius: 8px; }
    .stButton button { background: #16181f; border: 1px solid #2a2a2a; color: #e0e0e0; font-family: 'IBM Plex Mono', monospace; font-size: 0.75rem; width: 100%; }
    .stButton button:hover { border-color: #00d4aa; color: #00d4aa; }
    .stTabs [data-baseweb="tab"] { font-family: 'IBM Plex Mono', monospace; font-size: 0.78rem; }
    .stTabs [aria-selected="true"] { color: #00d4aa; }
    div[data-testid="stSelectbox"] label, div[data-testid="stMultiSelect"] label, div[data-testid="stSlider"] label { font-size: 0.72rem; color: #777; font-family: 'IBM Plex Mono', monospace; }
    .index-click-hint { font-size: 0.7rem; color: #444; font-family: 'IBM Plex Mono', monospace; margin-top: 0.4rem; }
    .filter-active { font-size: 0.7rem; color: #00d4aa; font-family: 'IBM Plex Mono', monospace; padding: 0.2rem 0.5rem; background: #0d2e1f; border-radius: 4px; display: inline-block; margin-bottom: 0.5rem; }
    .data-timestamp { font-size: 0.65rem; color: #444; font-family: 'IBM Plex Mono', monospace; margin-top: 0.1rem; }
    .stock-card { background: #16181f; border: 1px solid #2a2a2a; border-radius: 10px; padding: 1.2rem; margin-bottom: 0.8rem; }
    .stock-card-header { font-family: 'IBM Plex Mono', monospace; font-size: 1.1rem; font-weight: 600; color: #00d4aa; margin-bottom: 0.3rem; }
    .stock-card-sub { font-size: 0.75rem; color: #777; font-family: 'IBM Plex Mono', monospace; margin-bottom: 0.8rem; }
    .stock-card-section { font-family: 'IBM Plex Mono', monospace; font-size: 0.65rem; color: #00d4aa; text-transform: uppercase; letter-spacing: 1.5px; margin-top: 1rem; margin-bottom: 0.4rem; border-bottom: 1px solid #2a2a2a; padding-bottom: 0.2rem; }
    .stock-card-row { display: flex; justify-content: space-between; padding: 0.2rem 0; font-family: 'IBM Plex Mono', monospace; font-size: 0.78rem; }
    .stock-card-label { color: #888; }
    .stock-card-val { color: #e0e0e0; font-weight: 600; }
    .stock-card-val.green { color: #00d4aa; }
    .stock-card-val.red { color: #ff4d4d; }
    .score-bar-container { background: #0f1117; border-radius: 4px; height: 8px; margin-top: 0.2rem; overflow: hidden; }
    .score-bar { height: 100%; border-radius: 4px; }
    .compare-highlight { background: #0d2e1f; border: 1px solid #00d4aa33; border-radius: 6px; padding: 0.3rem 0.6rem; text-align: center; }
</style>
""", unsafe_allow_html=True)


# ────────────────────────────────────────────────
# SESSION STATE
# ────────────────────────────────────────────────
if 'index_filter' not in st.session_state:
    st.session_state.index_filter = None


# ────────────────────────────────────────────────
# DATA LOADING
# ────────────────────────────────────────────────
def read_csv_safe(filename):
    for enc in ['utf-8', 'utf-8-sig', 'utf-16', 'cp1252', 'latin1']:
        try:
            return pd.read_csv(filename, encoding=enc)
        except Exception:
            continue
    return None


@st.cache_data(ttl=600, show_spinner=False)
def load_stock_data(version=1):
    tech = read_csv_safe('data/technicals.csv')
    if tech is None:
        try:
            tech = pd.read_excel('data/technicals.xlsx')
        except Exception:
            st.error("Could not load technicals data.")
            st.stop()

    fund = read_csv_safe('data/fundamentals.csv')
    const = read_csv_safe('data/index_constituents.csv')

    sym_col = tech.columns[0]
    tech[sym_col] = tech[sym_col].astype(str).str.strip()

    if fund is not None:
        fund_sym = fund.columns[0]
        fund[fund_sym] = fund[fund_sym].astype(str).str.strip()
        fund = fund.rename(columns={fund_sym: sym_col})
        fund = fund.drop(columns=[c for c in ['Name', 'name', 'Current Price', 'CMP Rs.'] if c in fund.columns], errors='ignore')
        tech = pd.merge(tech, fund, on=sym_col, how='left')

    if const is not None:
        const['Symbol'] = const['Symbol'].astype(str).str.strip()
        const = const.rename(columns={'Symbol': sym_col})
        tech = pd.merge(tech, const[[sym_col, 'Index Membership']], on=sym_col, how='left')

    tech = tech.loc[:, ~tech.columns.str.contains('^Unnamed')]
    tech = tech.dropna(subset=['Current Price'])

    # Derived columns
    if 'EPS Current' in tech.columns and 'EPS Last Year' in tech.columns:
        ec = pd.to_numeric(tech['EPS Current'], errors='coerce')
        ep = pd.to_numeric(tech['EPS Last Year'], errors='coerce')
        tech['EPS Growth 1Y %'] = ((ec - ep) / ep.abs() * 100).round(2)

    if 'Free Cash Flow (Cr)' in tech.columns and 'Market Cap (Cr)' in tech.columns:
        fcf = pd.to_numeric(tech['Free Cash Flow (Cr)'], errors='coerce')
        mcap = pd.to_numeric(tech['Market Cap (Cr)'], errors='coerce')
        tech['FCF Yield %'] = (fcf / mcap * 100).round(4)

    for period, col in [('1M', 'ROC 1M %'), ('3M', 'ROC 3M %'), ('6M', 'ROC 6M %')]:
        if col in tech.columns:
            tech[f'Momentum Rank {period}'] = tech[col].rank(ascending=False, method='min').astype('Int64')

    return tech


@st.cache_data(ttl=600, show_spinner=False)
def load_index_data(version=1):
    return read_csv_safe('data/indices_technicals.csv')


@st.cache_data(ttl=600, show_spinner=False)
def load_global_data(version=1):
    return read_csv_safe('data/global_technicals.csv')


with st.spinner("Loading data..."):
    df = load_stock_data(version=1)
    idx_df = load_index_data(version=1)
    glob_df = load_global_data(version=1)

sym_col = df.columns[0]
ALL_DISPLAY_COLS = all_display_cols(sym_col)


# ────────────────────────────────────────────────
# HELPERS
# ────────────────────────────────────────────────
def has_col(df_, name):
    return name in df_.columns

def safe_range(df_, col):
    s = pd.to_numeric(df_[col], errors='coerce').dropna()
    if s.empty:
        return 0.0, 1.0
    return float(s.min()), float(s.max())

def apply_slider_filter(fdf, col, val, df_):
    if val is None or not has_col(df_, col):
        return fdf
    dmin, dmax = safe_range(df_, col)
    if abs(val[0] - dmin) < 0.001 and abs(val[1] - dmax) < 0.001:
        return fdf
    s = pd.to_numeric(fdf[col], errors='coerce')
    return fdf[((s >= val[0]) & (s <= val[1])) | s.isna()]


def show_table(data_df, cols, sort_by, sort_asc, key_suffix=""):
    disp_cols = [c for c in [sym_col] + cols if c in data_df.columns]
    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for c in disp_cols:
        if c not in seen:
            seen.add(c)
            deduped.append(c)
    disp_cols = deduped

    if '_rank_sort' in data_df.columns and '_rank_sort' not in disp_cols:
        disp = data_df[disp_cols + ['_rank_sort']].copy()
    else:
        disp = data_df[disp_cols].copy()

    if sort_by and sort_by in disp.columns:
        try:
            actual_sort = '_rank_sort' if sort_by == 'Universe Rank' and '_rank_sort' in disp.columns else sort_by
            disp = disp.sort_values(actual_sort, ascending=sort_asc, na_position='last')
        except Exception:
            pass

    disp = disp.drop(columns=['_rank_sort'], errors='ignore')
    disp = disp.reset_index(drop=True)
    disp.index = disp.index + 1
    disp.index.name = 'Sr No'

    col_config = {sym_col: st.column_config.Column(pinned=True)}
    st.dataframe(
        style_dataframe(disp),
        use_container_width=True,
        height=560,
        column_config=col_config,
        key=f"table_{key_suffix}"
    )
    return disp


def export_btn(data, cols, filename, key):
    valid_cols = [c for c in [sym_col] + cols if c in data.columns]
    st.download_button(
        "⬇ Export", data[valid_cols].to_csv(index=False).encode('utf-8'),
        filename, 'text/csv', key=key
    )


# ────────────────────────────────────────────────
# SIDEBAR FILTERS
# ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 Filters")

    if st.session_state.index_filter:
        st.markdown(f'<div class="filter-active">📈 {st.session_state.index_filter}</div>', unsafe_allow_html=True)
        if st.button("✕ Clear index filter"):
            st.session_state.index_filter = None
            st.rerun()

    st.markdown("### 🔍 Search")
    search = st.text_input("Symbol or Name", placeholder="RELIANCE, Infosys...")

    st.markdown("### Identity")
    sectors = ["All"] + sorted(df['Sector'].dropna().unique().tolist()) if has_col(df, 'Sector') else ["All"]
    sel_sector = st.selectbox("Sector", sectors)

    if sel_sector != "All" and has_col(df, 'Industry'):
        industries = ["All"] + sorted(df[df['Sector'] == sel_sector]['Industry'].dropna().unique().tolist())
    elif has_col(df, 'Industry'):
        industries = ["All"] + sorted(df['Industry'].dropna().unique().tolist())
    else:
        industries = ["All"]
    sel_industry = st.selectbox("Industry", industries)

    cap_cats = sorted(df['Cap Category'].dropna().unique().tolist()) if has_col(df, 'Cap Category') else []
    sel_cap = st.multiselect("Cap Category", cap_cats, default=[])

    if has_col(df, 'Index Membership'):
        all_indices = set()
        df['Index Membership'].dropna().str.split(', ').apply(all_indices.update)
        all_indices = sorted(all_indices)
        sel_index = st.multiselect("Index Membership", all_indices, default=[])
    else:
        sel_index = []

    st.markdown("### Regime")
    regime_opts = sorted(df['Market Regime'].dropna().unique().tolist()) if has_col(df, 'Market Regime') else []
    sel_regime = st.multiselect("Market Regime", regime_opts, default=[])

    dd_opts = sorted(df['Drawdown Status'].dropna().unique().tolist()) if has_col(df, 'Drawdown Status') else []
    sel_dd = st.multiselect("Drawdown Status", dd_opts, default=[])

    ema_cross_opts = ["All", "Golden Cross", "Death Cross"]
    sel_cross = st.selectbox("EMA Cross", ema_cross_opts) if has_col(df, 'EMA Cross') else "All"

    vol_trend_opts = ["All", "Rising", "Stable", "Falling"]
    sel_vol_trend = st.selectbox("Vol Trend", vol_trend_opts) if has_col(df, 'Vol Trend') else "All"

    st.markdown("### Technical Signals")
    macd_filter = st.selectbox("MACD Signal", ["All", "Bullish", "Bearish"]) if has_col(df, 'MACD Signal') else "All"
    st_filter = st.selectbox("Supertrend", ["All", "Bullish", "Bearish"]) if has_col(df, 'Supertrend') else "All"
    ema_filter = st.selectbox("Price vs EMA", ["All", "Above EMA 50 & 200", "Above EMA 200 only", "Below EMA 50 & 200"])

    rsi_range = None
    if has_col(df, 'RSI 14'):
        rmi, rma = safe_range(df, 'RSI 14')
        rsi_range = st.slider("RSI 14", float(max(0, rmi)), float(min(100, rma)), (float(max(0, rmi)), float(min(100, rma))), step=0.5)

    trend_cons_range = None
    if has_col(df, 'Trend Consistency (12M)'):
        trend_cons_range = st.slider("Trend Consistency (months)", 0, 12, (0, 12))

    st.markdown("### Momentum")
    roc3_range = None
    if has_col(df, 'ROC 3M %'):
        r3i, r3a = safe_range(df, 'ROC 3M %')
        roc3_range = st.slider("ROC 3M %", r3i, r3a, (r3i, r3a), step=0.5)

    rs_range = None
    if has_col(df, 'RS vs Nifty 3M %'):
        rsi2, rsa = safe_range(df, 'RS vs Nifty 3M %')
        rs_range = st.slider("RS vs Nifty 3M %", rsi2, rsa, (rsi2, rsa), step=0.5)

    st.markdown("### Valuation")
    pe_range = None
    if has_col(df, 'PE Ratio'):
        pei, pea = safe_range(df, 'PE Ratio')
        pe_range = st.slider("P/E Ratio", pei, pea, (pei, pea), step=0.5)

    pb_range = None
    if has_col(df, 'PB Ratio'):
        pbi, pba = safe_range(df, 'PB Ratio')
        pb_range = st.slider("P/B Ratio", pbi, pba, (pbi, pba), step=0.1)

    st.markdown("### Profitability")
    roe_range = None
    if has_col(df, 'ROE %'):
        ri, ra = safe_range(df, 'ROE %')
        roe_range = st.slider("ROE %", ri, ra, (ri, ra), step=0.5)

    roce_range = None
    if has_col(df, 'ROCE %'):
        rci, rca = safe_range(df, 'ROCE %')
        roce_range = st.slider("ROCE %", rci, rca, (rci, rca), step=0.5)

    st.markdown("### Financial Health")
    de_range = None
    if has_col(df, 'Debt/Equity'):
        dei, dea = safe_range(df, 'Debt/Equity')
        de_range = st.slider("Debt/Equity", dei, dea, (dei, dea), step=0.1)

    st.markdown("### Ownership")
    ph_range = None
    if has_col(df, 'Promoter Holding %'):
        phi, pha = safe_range(df, 'Promoter Holding %')
        ph_range = st.slider("Promoter Holding %", phi, pha, (phi, pha), step=0.5)

    pp_range = None
    if has_col(df, 'Pledge %'):
        ppi, ppa = safe_range(df, 'Pledge %')
        pp_range = st.slider("Pledge %", ppi, ppa, (ppi, ppa), step=0.1)

    st.markdown("---")
    if st.button("↺  Reset All Filters"):
        st.session_state.index_filter = None
        st.rerun()


# ────────────────────────────────────────────────
# APPLY FILTERS
# ────────────────────────────────────────────────
filtered = df.copy()

if st.session_state.index_filter and has_col(filtered, 'Index Membership'):
    idx_f = st.session_state.index_filter
    filtered = filtered[filtered['Index Membership'].fillna('').str.contains(idx_f, case=False, na=False)]

if search:
    mask = pd.Series(False, index=filtered.index)
    if has_col(df, 'Name'):
        mask |= filtered['Name'].astype(str).str.contains(search, case=False, na=False)
    mask |= filtered[sym_col].astype(str).str.contains(search, case=False, na=False)
    filtered = filtered[mask]

if sel_sector != "All" and has_col(df, 'Sector'):
    filtered = filtered[filtered['Sector'] == sel_sector]
if sel_industry != "All" and has_col(df, 'Industry'):
    filtered = filtered[filtered['Industry'] == sel_industry]
if sel_cap and has_col(df, 'Cap Category'):
    filtered = filtered[filtered['Cap Category'].isin(sel_cap)]
if sel_index and has_col(df, 'Index Membership'):
    mask = pd.Series(False, index=filtered.index)
    for idx in sel_index:
        mask |= filtered['Index Membership'].fillna('').str.contains(
            r'(?:^|, )' + re.escape(idx) + r'(?:,|$)', regex=True, na=False
        )
    filtered = filtered[mask]

if sel_regime and has_col(df, 'Market Regime'):
    filtered = filtered[filtered['Market Regime'].isin(sel_regime)]
if sel_dd and has_col(df, 'Drawdown Status'):
    filtered = filtered[filtered['Drawdown Status'].isin(sel_dd)]
if sel_cross != "All" and has_col(df, 'EMA Cross'):
    filtered = filtered[filtered['EMA Cross'] == sel_cross]
if sel_vol_trend != "All" and has_col(df, 'Vol Trend'):
    filtered = filtered[filtered['Vol Trend'] == sel_vol_trend]

if macd_filter != "All" and has_col(df, 'MACD Signal'):
    filtered = filtered[filtered['MACD Signal'] == macd_filter]
if st_filter != "All" and has_col(df, 'Supertrend'):
    filtered = filtered[filtered['Supertrend'] == st_filter]
if ema_filter != "All" and has_col(df, 'EMA 50') and has_col(df, 'EMA 200'):
    price = pd.to_numeric(filtered['Current Price'], errors='coerce')
    ema50 = pd.to_numeric(filtered['EMA 50'], errors='coerce')
    ema200 = pd.to_numeric(filtered['EMA 200'], errors='coerce')
    if ema_filter == "Above EMA 50 & 200":
        filtered = filtered[(price > ema50) & (price > ema200)]
    elif ema_filter == "Above EMA 200 only":
        filtered = filtered[price > ema200]
    elif ema_filter == "Below EMA 50 & 200":
        filtered = filtered[(price < ema50) & (price < ema200)]

for col, val in [('RSI 14', rsi_range), ('Trend Consistency (12M)', trend_cons_range),
                 ('ROC 3M %', roc3_range), ('RS vs Nifty 3M %', rs_range),
                 ('PE Ratio', pe_range), ('PB Ratio', pb_range),
                 ('ROE %', roe_range), ('ROCE %', roce_range),
                 ('Debt/Equity', de_range), ('Promoter Holding %', ph_range), ('Pledge %', pp_range)]:
    filtered = apply_slider_filter(filtered, col, val, df)


# ────────────────────────────────────────────────
# HEADER & MARKET PULSE
# ────────────────────────────────────────────────
data_ts = get_data_timestamp()
st.markdown(f"""
<div class="screener-header">
    <p class="screener-title">▸ STOCKRADAR INDIA</p>
    <p class="screener-subtitle">Technical + Fundamental · 880+ Stocks · 50 Indices · Daily refresh</p>
    <p class="data-timestamp">Data as of: {data_ts}</p>
</div>
""", unsafe_allow_html=True)


def market_pulse_banner(stock_df, idx_df_):
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Stocks</div><div class="metric-value">{len(stock_df)}</div></div>', unsafe_allow_html=True)
    with c2:
        if has_col(stock_df, 'Market Regime'):
            sb = (stock_df['Market Regime'] == 'Strong Bull').sum()
            st.markdown(f'<div class="metric-card"><div class="metric-label">Strong Bull</div><div class="metric-value">{sb}</div></div>', unsafe_allow_html=True)
    with c3:
        if has_col(stock_df, 'MACD Signal'):
            bull = (stock_df['MACD Signal'] == 'Bullish').sum()
            st.markdown(f'<div class="metric-card"><div class="metric-label">MACD Bullish</div><div class="metric-value">{bull}</div></div>', unsafe_allow_html=True)
    with c4:
        if has_col(stock_df, 'Supertrend'):
            st_bull = (stock_df['Supertrend'] == 'Bullish').sum()
            st.markdown(f'<div class="metric-card"><div class="metric-label">Supertrend Bull</div><div class="metric-value">{st_bull}</div></div>', unsafe_allow_html=True)
    with c5:
        if has_col(stock_df, 'RSI 14'):
            avg_rsi = pd.to_numeric(stock_df['RSI 14'], errors='coerce').mean()
            st.markdown(f'<div class="metric-card"><div class="metric-label">Avg RSI</div><div class="metric-value">{avg_rsi:.1f}</div></div>', unsafe_allow_html=True)
    with c6:
        if idx_df_ is not None and has_col(idx_df_, 'Market Regime'):
            bull_idx = (idx_df_['Market Regime'].isin(['Bull', 'Strong Bull'])).sum()
            total_idx = len(idx_df_)
            st.markdown(f'<div class="metric-card"><div class="metric-label">Indices Bullish</div><div class="metric-value">{bull_idx}/{total_idx}</div></div>', unsafe_allow_html=True)


market_pulse_banner(filtered, idx_df)
st.markdown("<br>", unsafe_allow_html=True)


# ────────────────────────────────────────────────
# SORT CONTROLS
# ────────────────────────────────────────────────
sc1, sc2 = st.columns([3, 1])
with sc1:
    numeric_cols_for_sort = [c for c in ALL_DISPLAY_COLS if c in df.columns and
                              pd.to_numeric(df[c], errors='coerce').notna().sum() > 50]
    default_sort = 'Market Cap (Cr)' if 'Market Cap (Cr)' in numeric_cols_for_sort else numeric_cols_for_sort[0]
    sort_by = st.selectbox("Sort by", numeric_cols_for_sort, index=numeric_cols_for_sort.index(default_sort))
with sc2:
    sort_order = st.selectbox("Order", ["Descending", "Ascending"])

sort_asc = sort_order == "Ascending"


# ────────────────────────────────────────────────
# SCORE ONCE (reuse across all tabs)
# ────────────────────────────────────────────────
scored = add_scores(filtered.copy(), universe_df=filtered)


# ────────────────────────────────────────────────
# MAIN TABS
# ────────────────────────────────────────────────
main_tab1, main_tab2, main_tab3 = st.tabs(["📊 Stocks", "📈 Index Dashboard", "🔍 Tools"])


# ══════════════════════════════════════════════
# TAB 1 — STOCKS
# ══════════════════════════════════════════════
with main_tab1:
    if st.session_state.index_filter:
        st.markdown(f'<div class="filter-active">📈 Filtered: {st.session_state.index_filter} · {len(filtered)} stocks</div>', unsafe_allow_html=True)

    stocks_sub1, stocks_sub2, stocks_sub3 = st.tabs(["📋 All Stocks", "🎯 Pre-built Screens", "🔧 Custom Screen"])

    # ── ALL STOCKS ──────────────────────────────
    with stocks_sub1:
        ov_tab, tech_tab, ret_tab, risk_tab, fund_tab, custom_tab = st.tabs([
            "Overview", "Technicals", "Returns", "Risk", "Fundamentals", "⚙ Custom View"
        ])

        def col_selector(default_cols, key):
            all_avail = [c for c in ALL_DISPLAY_COLS if c in filtered.columns]
            score_cols = ['Technical Score', 'Momentum Score', 'Fundamental Score', 'Composite Score', 'Universe Rank']
            all_with_scores = score_cols + [c for c in all_avail if c not in score_cols]
            return st.multiselect("Select columns", options=all_with_scores,
                                  default=[c for c in default_cols if c in filtered.columns], key=key)

        with ov_tab:
            cc1, cc2 = st.columns([5, 1])
            with cc2:
                export_btn(scored, OVERVIEW_COLS, 'overview.csv', 'dl_ov')
            show_table(scored, OVERVIEW_COLS, sort_by, sort_asc, 'ov')

        with tech_tab:
            cc1, cc2 = st.columns([5, 1])
            with cc2:
                export_btn(scored, TECHNICAL_COLS, 'technicals.csv', 'dl_tech')
            show_table(scored, TECHNICAL_COLS, sort_by, sort_asc, 'tech')

        with ret_tab:
            cc1, cc2 = st.columns([5, 1])
            with cc2:
                export_btn(scored, RETURNS_COLS, 'returns.csv', 'dl_ret')
            show_table(scored, RETURNS_COLS, sort_by, sort_asc, 'ret')

        with risk_tab:
            cc1, cc2 = st.columns([5, 1])
            with cc2:
                export_btn(scored, RISK_COLS, 'risk.csv', 'dl_risk')
            show_table(scored, RISK_COLS, sort_by, sort_asc, 'risk')

        with fund_tab:
            cc1, cc2 = st.columns([5, 1])
            with cc2:
                export_btn(scored, FUNDAMENTAL_COLS, 'fundamentals.csv', 'dl_fund')
            show_table(scored, FUNDAMENTAL_COLS, sort_by, sort_asc, 'fund')

        with custom_tab:
            custom_cols = col_selector(
                [sym_col, 'Name', 'Composite Score', 'Universe Rank', 'Market Regime', 'ROC 3M %', 'ROCE %'],
                'custom_cols'
            )
            if custom_cols:
                cc1, cc2 = st.columns([5, 1])
                with cc2:
                    export_btn(scored, custom_cols, 'custom_view.csv', 'dl_custom_view')
                show_table(scored, custom_cols, sort_by, sort_asc, 'custom_view')

    # ── PRE-BUILT SCREENS ───────────────────────
    with stocks_sub2:
        scr_t1, scr_t2, scr_t3, scr_t4, scr_t5 = st.tabs([
            "🚀 Momentum", "🏆 Quality", "💎 Value", "🎁 Income", "⭐ Combined"
        ])

        def render_screen_tab(tab_name, tab_obj):
            with tab_obj:
                tab_screens = {k: v for k, v in SCREENS.items() if v['tab'] == tab_name}
                btn_cols = st.columns(min(len(tab_screens), 4))
                active = st.session_state.get(f'active_screen_{tab_name}')

                for i, (name, _) in enumerate(tab_screens.items()):
                    with btn_cols[i % 4]:
                        if st.button(name, key=f"btn_{name}"):
                            st.session_state[f'active_screen_{tab_name}'] = name
                            active = name

                if active and active in SCREENS:
                    info = SCREENS[active]
                    rules_html = "".join([f'<span class="screen-rule">▸ {r}</span><br>' for r in info['rules']])
                    st.markdown(f"""
                    <div class="screen-desc">
                        <strong style="color:#e0e0e0">{active}</strong><br>
                        <span style="color:#888">{info['desc']}</span><br><br>
                        {rules_html}
                    </div>""", unsafe_allow_html=True)

                    result = run_screen(active, filtered)
                    rc1, rc2 = st.columns([5, 1])
                    with rc1:
                        st.markdown(f"**{len(result)} stocks** matched")
                    with rc2:
                        export_btn(result, OVERVIEW_COLS, f'{active[:20]}.csv', f'dl_{active[:10]}')

                    ov2, tech2, ret2, risk2, fund2 = st.tabs(["Overview", "Technicals", "Returns", "Risk", "Fundamentals"])
                    with ov2:   show_table(result, OVERVIEW_COLS, sort_by, sort_asc, f'scr_ov_{active[:8]}')
                    with tech2: show_table(result, TECHNICAL_COLS, sort_by, sort_asc, f'scr_tech_{active[:8]}')
                    with ret2:  show_table(result, RETURNS_COLS, sort_by, sort_asc, f'scr_ret_{active[:8]}')
                    with risk2: show_table(result, RISK_COLS, sort_by, sort_asc, f'scr_risk_{active[:8]}')
                    with fund2: show_table(result, FUNDAMENTAL_COLS, sort_by, sort_asc, f'scr_fund_{active[:8]}')

        render_screen_tab("🚀 Momentum", scr_t1)
        render_screen_tab("🏆 Quality", scr_t2)
        render_screen_tab("💎 Value", scr_t3)
        render_screen_tab("🎁 Income", scr_t4)
        render_screen_tab("⭐ Combined", scr_t5)

    # ── CUSTOM SCREEN ───────────────────────────
    with stocks_sub3:
        st.markdown("### 🔧 Custom Screen")
        st.markdown("<p style='color:#888; font-size:0.8rem; font-family:IBM Plex Mono,monospace'>Add up to 8 conditions.</p>", unsafe_allow_html=True)

        numeric_cols = [c for c in ALL_DISPLAY_COLS if c in df.columns and
                        pd.to_numeric(df[c], errors='coerce').notna().sum() > 100]
        n_conds = st.slider("Number of conditions", 1, 8, 3)
        conditions = []

        for i in range(n_conds):
            cc1, cc2, cc3 = st.columns([3, 2, 2])
            with cc1: col_c = st.selectbox(f"Column {i + 1}", numeric_cols, key=f"cc_{i}")
            with cc2: op_c = st.selectbox(f"Operator {i + 1}", [">", ">=", "<", "<=", "=="], key=f"op_{i}")
            with cc3:
                cmin, cmax = safe_range(df, col_c)
                val_c = st.number_input(f"Value {i + 1}", value=float(round((cmin + cmax) / 2, 2)), key=f"val_{i}")
            conditions.append((col_c, op_c, val_c))

        if st.button("▶ Run Custom Screen", key="run_custom"):
            cr = filtered.copy()
            for col_name, op, val in conditions:
                s_ = pd.to_numeric(cr[col_name], errors='coerce')
                ops = {">": s_ > val, ">=": s_ >= val, "<": s_ < val, "<=": s_ <= val, "==": s_ == val}
                cr = cr[ops[op]]

            st.markdown(f"**{len(cr)} stocks** matched")
            crc1, crc2 = st.columns([5, 1])
            with crc2:
                export_btn(cr, OVERVIEW_COLS, 'custom_screen.csv', 'dl_custom')

            cov, ctech, cret, crisk, cfund = st.tabs(["Overview", "Technicals", "Returns", "Risk", "Fundamentals"])
            with cov:   show_table(cr, OVERVIEW_COLS, sort_by, sort_asc, 'cust_ov')
            with ctech: show_table(cr, TECHNICAL_COLS, sort_by, sort_asc, 'cust_tech')
            with cret:  show_table(cr, RETURNS_COLS, sort_by, sort_asc, 'cust_ret')
            with crisk: show_table(cr, RISK_COLS, sort_by, sort_asc, 'cust_risk')
            with cfund: show_table(cr, FUNDAMENTAL_COLS, sort_by, sort_asc, 'cust_fund')


# ══════════════════════════════════════════════
# TAB 2 — INDEX DASHBOARD
# ══════════════════════════════════════════════
with main_tab2:
    idx_sub1, idx_sub2 = st.tabs(["🇮🇳 Indian Indices", "🌍 Global & Commodities"])

    # ── INDIAN INDICES ──────────────────────────
    with idx_sub1:
        if idx_df is None:
            st.warning("indices_technicals.csv not found. Run `python scripts/fetch_indices.py` first.")
        else:
            idx_display = idx_df.copy()
            for period, col in [('1M', 'ROC 1M %'), ('3M', 'ROC 3M %')]:
                if col in idx_display.columns:
                    idx_display[f'Momentum Rank {period}'] = idx_display[col].rank(ascending=False, method='min').astype('Int64')

            if has_col(idx_display, 'Category'):
                cats = ["All"] + sorted(idx_display['Category'].dropna().unique().tolist())
                sel_cat = st.selectbox("Filter by Category", cats, key='idx_cat')
                if sel_cat != "All":
                    idx_display = idx_display[idx_display['Category'] == sel_cat]

            ic1, ic2 = st.columns([3, 1])
            with ic1:
                idx_num_cols = [c for c in INDEX_COLS if c in idx_display.columns and
                                pd.to_numeric(idx_display[c], errors='coerce').notna().sum() > 0]
                idx_sort = st.selectbox("Sort indices by", idx_num_cols,
                                        index=idx_num_cols.index('ROC 3M %') if 'ROC 3M %' in idx_num_cols else 0,
                                        key='idx_sort')
            with ic2:
                idx_sort_order = st.selectbox("Order", ["Descending", "Ascending"], key='idx_sort_order')

            disp_idx_cols = [c for c in INDEX_COLS if c in idx_display.columns]
            idx_sorted = idx_display[disp_idx_cols].sort_values(
                idx_sort, ascending=(idx_sort_order == "Ascending"), na_position='last'
            ).reset_index(drop=True)
            idx_sorted.index = idx_sorted.index + 1
            idx_sorted.index.name = 'Sr No'

            st.dataframe(
                style_dataframe(idx_sorted),
                use_container_width=True,
                height=500,
                column_config={'Index': st.column_config.Column(pinned=True)},
                key='idx_table'
            )

            # Drill-down
            st.markdown('<div class="index-click-hint">▸ Select an index below to analyse its constituent stocks</div>', unsafe_allow_html=True)

            all_index_names = sorted(idx_df['Index'].dropna().tolist()) if idx_df is not None else []
            drill_col1, drill_col2 = st.columns([3, 1])
            with drill_col1:
                selected_index = st.selectbox(
                    "Select index to drill down",
                    ["— Select an index —"] + all_index_names,
                    key='drill_index'
                )
            with drill_col2:
                st.markdown("<br>", unsafe_allow_html=True)
                drill_clicked = st.button("📊 Analyse Stocks", key='drill_btn')

            if selected_index != "— Select an index —":
                if has_col(df, 'Index Membership'):
                    idx_stocks = df[df['Index Membership'].fillna('').str.contains(
                        r'(?:^|, )' + re.escape(selected_index.title()) + r'(?:,|$)',
                        regex=True, na=False
                    )].copy()
                else:
                    idx_stocks = pd.DataFrame()

                if idx_stocks.empty:
                    st.warning(f"No constituent stocks found for {selected_index}.")
                else:
                    st.markdown(f"### 📊 {selected_index} — {len(idx_stocks)} stocks")

                    ds1, ds2 = st.columns([3, 1])
                    with ds1:
                        drill_sort_opts = [c for c in ['ROC 3M %', 'ROC 1M %', 'Market Cap (Cr)', 'RSI 14', 'Momentum Quality', 'RS vs Nifty 3M %'] if c in idx_stocks.columns]
                        drill_sort = st.selectbox("Sort by", drill_sort_opts, key='drill_sort')
                    with ds2:
                        drill_order = st.selectbox("Order", ["Descending", "Ascending"], key='drill_order')
                    drill_asc = drill_order == "Ascending"

                    st.download_button(
                        f"⬇ Export {selected_index} stocks",
                        data=idx_stocks[[c for c in [sym_col] + OVERVIEW_COLS if c in idx_stocks.columns]].to_csv(index=False).encode('utf-8'),
                        file_name=f'{selected_index.replace(" ", "_")}_stocks.csv',
                        mime='text/csv', key='dl_drill'
                    )

                    d_ov, d_tech, d_ret, d_risk, d_fund, d_custom = st.tabs([
                        "Overview", "Technicals", "Returns", "Risk", "Fundamentals", "⚙ Custom View"
                    ])
                    idx_scored = add_scores(idx_stocks.copy(), universe_df=idx_stocks)
                    with d_ov:   show_table(idx_scored, OVERVIEW_COLS, drill_sort, drill_asc, 'drill_ov')
                    with d_tech: show_table(idx_stocks, TECHNICAL_COLS, drill_sort, drill_asc, 'drill_tech')
                    with d_ret:  show_table(idx_stocks, RETURNS_COLS, drill_sort, drill_asc, 'drill_ret')
                    with d_risk: show_table(idx_stocks, RISK_COLS, drill_sort, drill_asc, 'drill_risk')
                    with d_fund: show_table(idx_stocks, FUNDAMENTAL_COLS, drill_sort, drill_asc, 'drill_fund')
                    with d_custom:
                        all_avail_idx = [c for c in ALL_DISPLAY_COLS if c in idx_scored.columns]
                        score_cols_idx = ['Technical Score', 'Momentum Score', 'Fundamental Score', 'Composite Score', 'Universe Rank']
                        all_with_scores_idx = score_cols_idx + [c for c in all_avail_idx if c not in score_cols_idx]
                        custom_idx_cols = st.multiselect(
                            "Select columns", options=all_with_scores_idx,
                            default=[sym_col, 'Name', 'Composite Score', 'Universe Rank', 'Market Regime', 'ROC 3M %', 'ROCE %'],
                            key='drill_custom_cols'
                        )
                        if custom_idx_cols:
                            show_table(idx_scored, custom_idx_cols, drill_sort, drill_asc, 'drill_custom')

    # ── GLOBAL & COMMODITIES ───────────────────
    with idx_sub2:
        if glob_df is None:
            st.warning("global_technicals.csv not found. Run `python scripts/fetch_global.py` first.")
        else:
            glob_display = glob_df.copy()

            if has_col(glob_display, 'Category'):
                gcats = ["All"] + sorted(glob_display['Category'].dropna().unique().tolist())
                sel_gcat = st.selectbox("Filter by Category", gcats, key='glob_cat')
                if sel_gcat != "All":
                    glob_display = glob_display[glob_display['Category'] == sel_gcat]

            gc1, gc2 = st.columns([3, 1])
            with gc1:
                glob_num_cols = [c for c in GLOBAL_COLS if c in glob_display.columns and
                                 pd.to_numeric(glob_display[c], errors='coerce').notna().sum() > 0]
                glob_sort = st.selectbox("Sort by", glob_num_cols,
                                         index=glob_num_cols.index('ROC 3M %') if 'ROC 3M %' in glob_num_cols else 0,
                                         key='glob_sort')
            with gc2:
                glob_sort_order = st.selectbox("Order", ["Descending", "Ascending"], key='glob_sort_order')

            disp_glob_cols = [c for c in GLOBAL_COLS if c in glob_display.columns]
            glob_sorted = glob_display[disp_glob_cols].sort_values(
                glob_sort, ascending=(glob_sort_order == "Ascending"), na_position='last'
            ).reset_index(drop=True)
            glob_sorted.index = glob_sorted.index + 1
            glob_sorted.index.name = 'Sr No'

            st.dataframe(
                style_dataframe(glob_sorted),
                use_container_width=True, height=500,
                column_config={'Name': st.column_config.Column(pinned=True)},
                key='glob_table'
            )
            st.markdown('<div class="index-click-hint">Global indices and commodities — technical analysis only</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════
# TAB 3 — TOOLS (Stock Card, Compare, Watchlist)
# ══════════════════════════════════════════════
with main_tab3:
    tools_sub1, tools_sub2, tools_sub3 = st.tabs(["🪪 Stock Card", "⚖ Compare", "📌 Watchlist"])

    # Build stock lookup list
    stock_options = []
    if has_col(scored, 'Name'):
        stock_options = sorted(
            scored.apply(lambda r: f"{r[sym_col]} — {r['Name']}", axis=1).tolist()
        )

    def get_stock_row(selection):
        """Extract symbol from 'SYMBOL — Name' format and return the row."""
        sym = selection.split(" — ")[0].strip()
        match = scored[scored[sym_col] == sym]
        if match.empty:
            return None
        return match.iloc[0]

    def fmt_val(val, fmt=".2f", suffix="", prefix=""):
        """Format a value, return '—' for NaN."""
        if pd.isna(val):
            return "—"
        try:
            return f"{prefix}{val:{fmt}}{suffix}"
        except (ValueError, TypeError):
            return str(val)

    def color_class(val):
        """Return CSS class based on sign."""
        try:
            v = float(val)
            if v > 0: return "green"
            if v < 0: return "red"
        except (ValueError, TypeError):
            pass
        return ""

    def score_bar_html(score, label):
        """Render a score bar with label."""
        s = float(score) if not pd.isna(score) else 0
        color = "#00d4aa" if s >= 60 else "#ffaa33" if s >= 40 else "#ff4d4d"
        return f'<div class="stock-card-row"><span class="stock-card-label">{label}</span><span class="stock-card-val">{fmt_val(score, ".1f")}</span></div><div class="score-bar-container"><div class="score-bar" style="width:{min(s, 100):.0f}%; background:{color}"></div></div>'

    def render_stock_card(row):
        """Render a comprehensive stock card."""
        sym = row[sym_col]
        name = row.get('Name', sym)
        price = row.get('Current Price', np.nan)
        day_chg = row.get('Day Change %', np.nan)
        sector = row.get('Sector', '—')
        industry = row.get('Industry', '—')
        cap_cat = row.get('Cap Category', '—')
        mcap = row.get('Market Cap (Cr)', np.nan)
        regime = row.get('Market Regime', '—')
        dd_status = row.get('Drawdown Status', '—')
        chg_class = color_class(day_chg)

        # Header
        st.markdown(f"""
        <div class="stock-card">
            <div class="stock-card-header">{sym}</div>
            <div class="stock-card-sub">{name} · {sector} · {industry} · {cap_cat}</div>
            <div style="display:flex; gap:2rem; align-items:baseline; margin-bottom:0.5rem;">
                <span style="font-size:1.6rem; font-weight:700; color:#e0e0e0; font-family:'IBM Plex Mono',monospace">₹{fmt_val(price, ',.2f')}</span>
                <span class="stock-card-val {chg_class}" style="font-size:0.9rem">{fmt_val(day_chg, '.2f', '%')}</span>
                <span style="font-size:0.75rem; color:#888; font-family:'IBM Plex Mono',monospace">Mkt Cap: ₹{fmt_val(mcap, ',.0f')} Cr</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Scores
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"""
            <div class="stock-card">
                <div class="stock-card-section">Scores & Regime</div>
                {score_bar_html(row.get('Technical Score', np.nan), 'Technical')}
                {score_bar_html(row.get('Momentum Score', np.nan), 'Momentum')}
                {score_bar_html(row.get('Fundamental Score', np.nan), 'Fundamental')}
                {score_bar_html(row.get('Composite Score', np.nan), 'Composite')}
                <div class="stock-card-row" style="margin-top:0.6rem">
                    <span class="stock-card-label">Universe Rank</span>
                    <span class="stock-card-val">{fmt_val(row.get('Universe Rank', np.nan), '.0f')}</span>
                </div>
                <div class="stock-card-row">
                    <span class="stock-card-label">Market Regime</span>
                    <span class="stock-card-val">{regime}</span>
                </div>
                <div class="stock-card-row">
                    <span class="stock-card-label">Drawdown Status</span>
                    <span class="stock-card-val">{dd_status}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col_b:
            st.markdown(f"""
            <div class="stock-card">
                <div class="stock-card-section">Technical Signals</div>
                <div class="stock-card-row"><span class="stock-card-label">EMA 50 / 200</span><span class="stock-card-val">{fmt_val(row.get('EMA 50', np.nan))} / {fmt_val(row.get('EMA 200', np.nan))}</span></div>
                <div class="stock-card-row"><span class="stock-card-label">EMA Cross</span><span class="stock-card-val">{row.get('EMA Cross', '—')}</span></div>
                <div class="stock-card-row"><span class="stock-card-label">RSI 14</span><span class="stock-card-val">{fmt_val(row.get('RSI 14', np.nan))}</span></div>
                <div class="stock-card-row"><span class="stock-card-label">MACD</span><span class="stock-card-val">{row.get('MACD Signal', '—')}</span></div>
                <div class="stock-card-row"><span class="stock-card-label">Supertrend</span><span class="stock-card-val">{row.get('Supertrend', '—')}</span></div>
                <div class="stock-card-row"><span class="stock-card-label">Trend Consistency</span><span class="stock-card-val">{fmt_val(row.get('Trend Consistency (12M)', np.nan), '.0f')}/12</span></div>
                <div class="stock-card-row"><span class="stock-card-label">Vol Trend</span><span class="stock-card-val">{row.get('Vol Trend', '—')}</span></div>
            </div>
            """, unsafe_allow_html=True)

        # Row 2: Momentum + Risk
        col_c, col_d = st.columns(2)
        with col_c:
            rs1 = row.get('RS vs Nifty 1M %', np.nan)
            rs3 = row.get('RS vs Nifty 3M %', np.nan)
            rs6 = row.get('RS vs Nifty 6M %', np.nan)
            st.markdown(f"""
            <div class="stock-card">
                <div class="stock-card-section">Returns & Momentum</div>
                <div class="stock-card-row"><span class="stock-card-label">ROC 1M</span><span class="stock-card-val {color_class(row.get('ROC 1M %', np.nan))}">{fmt_val(row.get('ROC 1M %', np.nan), '.2f', '%')}</span></div>
                <div class="stock-card-row"><span class="stock-card-label">ROC 3M</span><span class="stock-card-val {color_class(row.get('ROC 3M %', np.nan))}">{fmt_val(row.get('ROC 3M %', np.nan), '.2f', '%')}</span></div>
                <div class="stock-card-row"><span class="stock-card-label">ROC 6M</span><span class="stock-card-val {color_class(row.get('ROC 6M %', np.nan))}">{fmt_val(row.get('ROC 6M %', np.nan), '.2f', '%')}</span></div>
                <div class="stock-card-row"><span class="stock-card-label">1Y CAGR</span><span class="stock-card-val {color_class(row.get('1Y CAGR %', np.nan))}">{fmt_val(row.get('1Y CAGR %', np.nan), '.2f', '%')}</span></div>
                <div class="stock-card-row"><span class="stock-card-label">3Y CAGR</span><span class="stock-card-val {color_class(row.get('3Y CAGR %', np.nan))}">{fmt_val(row.get('3Y CAGR %', np.nan), '.2f', '%')}</span></div>
                <div class="stock-card-row"><span class="stock-card-label">RS vs Nifty 1M/3M/6M</span><span class="stock-card-val">{fmt_val(rs1, '.1f')} / {fmt_val(rs3, '.1f')} / {fmt_val(rs6, '.1f')}</span></div>
                <div class="stock-card-row"><span class="stock-card-label">Momentum Quality</span><span class="stock-card-val">{fmt_val(row.get('Momentum Quality', np.nan))}</span></div>
            </div>
            """, unsafe_allow_html=True)

        with col_d:
            st.markdown(f"""
            <div class="stock-card">
                <div class="stock-card-section">Risk</div>
                <div class="stock-card-row"><span class="stock-card-label">Beta 1Y</span><span class="stock-card-val">{fmt_val(row.get('Beta 1Y (Daily)', np.nan), '.2f')}</span></div>
                <div class="stock-card-row"><span class="stock-card-label">SD 1Y</span><span class="stock-card-val">{fmt_val(row.get('SD 1Y %', np.nan), '.2f', '%')}</span></div>
                <div class="stock-card-row"><span class="stock-card-label">ATR %</span><span class="stock-card-val">{fmt_val(row.get('ATR % (14D)', np.nan), '.2f', '%')}</span></div>
                <div class="stock-card-row"><span class="stock-card-label">Max Drawdown 1Y</span><span class="stock-card-val red">{fmt_val(row.get('1Y Max Drawdown %', np.nan), '.2f', '%')}</span></div>
                <div class="stock-card-row"><span class="stock-card-label">52W High / Low</span><span class="stock-card-val">₹{fmt_val(row.get('52W High', np.nan), ',.2f')} / ₹{fmt_val(row.get('52W Low', np.nan), ',.2f')}</span></div>
                <div class="stock-card-row"><span class="stock-card-label">From 52W High</span><span class="stock-card-val {color_class(row.get('% from 52W High', np.nan))}">{fmt_val(row.get('% from 52W High', np.nan), '.2f', '%')}</span></div>
                <div class="stock-card-row"><span class="stock-card-label">Capture Ratio</span><span class="stock-card-val">{fmt_val(row.get('Capture Ratio', np.nan))}</span></div>
            </div>
            """, unsafe_allow_html=True)

        # Row 3: Fundamentals + Ownership
        col_e, col_f = st.columns(2)
        with col_e:
            st.markdown(f"""
            <div class="stock-card">
                <div class="stock-card-section">Valuation & Profitability</div>
                <div class="stock-card-row"><span class="stock-card-label">PE / Sector PE</span><span class="stock-card-val">{fmt_val(row.get('PE Ratio', np.nan))} / {fmt_val(row.get('Sector PE', np.nan))}</span></div>
                <div class="stock-card-row"><span class="stock-card-label">PB / Sector PB</span><span class="stock-card-val">{fmt_val(row.get('PB Ratio', np.nan))} / {fmt_val(row.get('Sector PB', np.nan))}</span></div>
                <div class="stock-card-row"><span class="stock-card-label">EV/EBITDA</span><span class="stock-card-val">{fmt_val(row.get('EV/EBITDA', np.nan))}</span></div>
                <div class="stock-card-row"><span class="stock-card-label">PEG Ratio</span><span class="stock-card-val">{fmt_val(row.get('PEG Ratio', np.nan))}</span></div>
                <div class="stock-card-row"><span class="stock-card-label">ROE / ROCE</span><span class="stock-card-val">{fmt_val(row.get('ROE %', np.nan))}% / {fmt_val(row.get('ROCE %', np.nan))}%</span></div>
                <div class="stock-card-row"><span class="stock-card-label">Net Profit Margin</span><span class="stock-card-val">{fmt_val(row.get('Net Profit Margin %', np.nan), '.2f', '%')}</span></div>
                <div class="stock-card-row"><span class="stock-card-label">D/E Ratio</span><span class="stock-card-val">{fmt_val(row.get('Debt/Equity', np.nan))}</span></div>
            </div>
            """, unsafe_allow_html=True)

        with col_f:
            st.markdown(f"""
            <div class="stock-card">
                <div class="stock-card-section">Growth & Ownership</div>
                <div class="stock-card-row"><span class="stock-card-label">Sales Growth 1Y / 3Y</span><span class="stock-card-val">{fmt_val(row.get('Sales Growth 1Y %', np.nan))}% / {fmt_val(row.get('Sales Growth 3Y %', np.nan))}%</span></div>
                <div class="stock-card-row"><span class="stock-card-label">Profit Growth 1Y / 3Y</span><span class="stock-card-val">{fmt_val(row.get('Profit Growth 1Y %', np.nan))}% / {fmt_val(row.get('Profit Growth 3Y %', np.nan))}%</span></div>
                <div class="stock-card-row"><span class="stock-card-label">EPS Growth 1Y</span><span class="stock-card-val {color_class(row.get('EPS Growth 1Y %', np.nan))}">{fmt_val(row.get('EPS Growth 1Y %', np.nan), '.2f', '%')}</span></div>
                <div class="stock-card-row"><span class="stock-card-label">FCF Yield</span><span class="stock-card-val">{fmt_val(row.get('FCF Yield %', np.nan), '.4f', '%')}</span></div>
                <div class="stock-card-row"><span class="stock-card-label">Div Yield / Payout</span><span class="stock-card-val">{fmt_val(row.get('Dividend Yield %', np.nan))}% / {fmt_val(row.get('Dividend Payout %', np.nan))}%</span></div>
                <div class="stock-card-row"><span class="stock-card-label">Promoter Holding</span><span class="stock-card-val">{fmt_val(row.get('Promoter Holding %', np.nan), '.2f', '%')}</span></div>
                <div class="stock-card-row"><span class="stock-card-label">Pledge %</span><span class="stock-card-val">{fmt_val(row.get('Pledge %', np.nan), '.2f', '%')}</span></div>
                <div class="stock-card-row"><span class="stock-card-label">FII / DII Change</span><span class="stock-card-val {color_class(row.get('FII Change %', np.nan))}">{fmt_val(row.get('FII Change %', np.nan), '.2f', '%')}</span> / <span class="stock-card-val {color_class(row.get('DII Change %', np.nan))}">{fmt_val(row.get('DII Change %', np.nan), '.2f', '%')}</span></div>
            </div>
            """, unsafe_allow_html=True)

        # Index membership
        idx_mem = row.get('Index Membership', '—')
        if not pd.isna(idx_mem) and idx_mem != '—':
            st.markdown(f"""
            <div class="stock-card">
                <div class="stock-card-section">Index Membership</div>
                <div style="font-size:0.78rem; color:#aaa; font-family:'IBM Plex Mono',monospace">{idx_mem}</div>
            </div>
            """, unsafe_allow_html=True)


    # ── STOCK CARD ──────────────────────────────
    with tools_sub1:
        st.markdown("<p style='color:#888;font-size:0.8rem;font-family:IBM Plex Mono,monospace'>Select a stock to see its complete profile.</p>", unsafe_allow_html=True)

        selected_stock = st.selectbox(
            "Select stock",
            ["— Select a stock —"] + stock_options,
            key='card_stock'
        )

        if selected_stock != "— Select a stock —":
            row = get_stock_row(selected_stock)
            if row is not None:
                render_stock_card(row)

    # ── COMPARE ─────────────────────────────────
    with tools_sub2:
        st.markdown("<p style='color:#888;font-size:0.8rem;font-family:IBM Plex Mono,monospace'>Select 2-4 stocks to compare side by side.</p>", unsafe_allow_html=True)

        compare_selections = st.multiselect(
            "Select stocks to compare",
            stock_options,
            max_selections=4,
            key='compare_stocks'
        )

        if len(compare_selections) >= 2:
            compare_rows = []
            for sel in compare_selections:
                row = get_stock_row(sel)
                if row is not None:
                    compare_rows.append(row)

            if len(compare_rows) >= 2:
                compare_df = pd.DataFrame(compare_rows)

                # Metrics to compare (label, column, format, higher_is_better)
                compare_metrics = [
                    ("Price", "Current Price", "₹{:,.2f}", None),
                    ("Day Change %", "Day Change %", "{:.2f}%", True),
                    ("Market Cap (Cr)", "Market Cap (Cr)", "₹{:,.0f}", None),
                    ("Market Regime", "Market Regime", "{}", None),
                    ("─── Scores ───", None, None, None),
                    ("Technical Score", "Technical Score", "{:.1f}", True),
                    ("Momentum Score", "Momentum Score", "{:.1f}", True),
                    ("Fundamental Score", "Fundamental Score", "{:.1f}", True),
                    ("Composite Score", "Composite Score", "{:.1f}", True),
                    ("Universe Rank", "Universe Rank", "{:.0f}", False),
                    ("─── Momentum ───", None, None, None),
                    ("ROC 1M %", "ROC 1M %", "{:.2f}%", True),
                    ("ROC 3M %", "ROC 3M %", "{:.2f}%", True),
                    ("ROC 6M %", "ROC 6M %", "{:.2f}%", True),
                    ("1Y CAGR %", "1Y CAGR %", "{:.2f}%", True),
                    ("RS vs Nifty 3M", "RS vs Nifty 3M %", "{:.2f}%", True),
                    ("─── Technicals ───", None, None, None),
                    ("RSI 14", "RSI 14", "{:.2f}", None),
                    ("MACD", "MACD Signal", "{}", None),
                    ("Supertrend", "Supertrend", "{}", None),
                    ("EMA Cross", "EMA Cross", "{}", None),
                    ("─── Risk ───", None, None, None),
                    ("Beta 1Y", "Beta 1Y (Daily)", "{:.2f}", None),
                    ("SD 1Y %", "SD 1Y %", "{:.2f}%", False),
                    ("Max Drawdown 1Y", "1Y Max Drawdown %", "{:.2f}%", False),
                    ("% from 52W High", "% from 52W High", "{:.2f}%", True),
                    ("─── Fundamentals ───", None, None, None),
                    ("PE Ratio", "PE Ratio", "{:.2f}", False),
                    ("PB Ratio", "PB Ratio", "{:.2f}", False),
                    ("ROE %", "ROE %", "{:.2f}%", True),
                    ("ROCE %", "ROCE %", "{:.2f}%", True),
                    ("D/E Ratio", "Debt/Equity", "{:.2f}", False),
                    ("Net Profit Margin", "Net Profit Margin %", "{:.2f}%", True),
                    ("Sales Growth 3Y", "Sales Growth 3Y %", "{:.2f}%", True),
                    ("Profit Growth 3Y", "Profit Growth 3Y %", "{:.2f}%", True),
                    ("─── Ownership ───", None, None, None),
                    ("Promoter Holding", "Promoter Holding %", "{:.2f}%", True),
                    ("Pledge %", "Pledge %", "{:.2f}%", False),
                    ("Dividend Yield", "Dividend Yield %", "{:.2f}%", True),
                ]

                # Build comparison table HTML
                symbols = [r[sym_col] for r in compare_rows]
                header = "<tr><th style='text-align:left;padding:0.4rem 0.8rem;color:#888;font-size:0.7rem;font-family:IBM Plex Mono,monospace;border-bottom:1px solid #2a2a2a'>METRIC</th>"
                for sym in symbols:
                    header += f"<th style='text-align:center;padding:0.4rem 0.8rem;color:#00d4aa;font-size:0.78rem;font-family:IBM Plex Mono,monospace;border-bottom:1px solid #2a2a2a'>{sym}</th>"
                header += "</tr>"

                rows_html = ""
                for label, col, fmt, higher_better in compare_metrics:
                    if col is None:
                        # Section separator
                        rows_html += f"<tr><td colspan='{len(symbols)+1}' style='padding:0.6rem 0.8rem 0.2rem;color:#00d4aa;font-size:0.65rem;font-family:IBM Plex Mono,monospace;text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid #1a1a2e'>{label}</td></tr>"
                        continue

                    rows_html += f"<tr><td style='padding:0.3rem 0.8rem;color:#888;font-size:0.75rem;font-family:IBM Plex Mono,monospace'>{label}</td>"

                    # Get values for comparison highlighting
                    vals = []
                    for r in compare_rows:
                        v = r.get(col, np.nan)
                        vals.append(v)

                    # Find best value for highlighting
                    numeric_vals = [v for v in vals if not pd.isna(v) and isinstance(v, (int, float, np.integer, np.floating))]
                    best_val = None
                    if higher_better is not None and numeric_vals:
                        best_val = max(numeric_vals) if higher_better else min(numeric_vals)

                    for v in vals:
                        try:
                            if pd.isna(v):
                                display = "—"
                            else:
                                display = fmt.format(v)
                        except (ValueError, TypeError):
                            display = str(v) if not pd.isna(v) else "—"

                        # Highlight best
                        is_best = (best_val is not None and not pd.isna(v) and isinstance(v, (int, float, np.integer, np.floating)) and abs(v - best_val) < 0.001)
                        style = "text-align:center;padding:0.3rem 0.8rem;font-size:0.78rem;font-family:IBM Plex Mono,monospace;"
                        if is_best:
                            style += "color:#00d4aa;font-weight:600;"
                        else:
                            style += "color:#ccc;"

                        rows_html += f"<td style='{style}'>{display}</td>"
                    rows_html += "</tr>"

                st.markdown(f"""
                <div style="overflow-x:auto">
                <table style="width:100%;border-collapse:collapse;background:#16181f;border:1px solid #2a2a2a;border-radius:8px">
                {header}
                {rows_html}
                </table>
                </div>
                """, unsafe_allow_html=True)

        elif len(compare_selections) == 1:
            st.info("Select at least 2 stocks to compare.")

    # ── WATCHLIST ────────────────────────────────
    with tools_sub3:
        st.markdown("<p style='color:#888;font-size:0.8rem;font-family:IBM Plex Mono,monospace'>Build your watchlist. Select stocks to track in one view.</p>", unsafe_allow_html=True)

        watchlist_selections = st.multiselect(
            "Add stocks to watchlist",
            stock_options,
            key='watchlist_stocks'
        )

        if watchlist_selections:
            watchlist_syms = [s.split(" — ")[0].strip() for s in watchlist_selections]
            watchlist_df = scored[scored[sym_col].isin(watchlist_syms)].copy()

            if not watchlist_df.empty:
                st.markdown(f"**{len(watchlist_df)} stocks** in watchlist")

                # Quick stats
                wc1, wc2, wc3, wc4 = st.columns(4)
                with wc1:
                    avg_score = pd.to_numeric(watchlist_df['Composite Score'], errors='coerce').mean()
                    st.markdown(f'<div class="metric-card"><div class="metric-label">Avg Composite</div><div class="metric-value">{avg_score:.1f}</div></div>', unsafe_allow_html=True)
                with wc2:
                    bull_count = (watchlist_df.get('Market Regime', pd.Series()).isin(['Bull', 'Strong Bull'])).sum()
                    st.markdown(f'<div class="metric-card"><div class="metric-label">Bullish</div><div class="metric-value">{bull_count}/{len(watchlist_df)}</div></div>', unsafe_allow_html=True)
                with wc3:
                    avg_roc3 = pd.to_numeric(watchlist_df.get('ROC 3M %', pd.Series()), errors='coerce').mean()
                    st.markdown(f'<div class="metric-card"><div class="metric-label">Avg ROC 3M</div><div class="metric-value">{avg_roc3:.1f}%</div></div>', unsafe_allow_html=True)
                with wc4:
                    avg_rsi = pd.to_numeric(watchlist_df.get('RSI 14', pd.Series()), errors='coerce').mean()
                    st.markdown(f'<div class="metric-card"><div class="metric-label">Avg RSI</div><div class="metric-value">{avg_rsi:.1f}</div></div>', unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # Watchlist tabs
                wl_ov, wl_tech, wl_ret, wl_risk, wl_fund = st.tabs([
                    "Overview", "Technicals", "Returns", "Risk", "Fundamentals"
                ])

                wl_sort_col1, wl_sort_col2 = st.columns([3, 1])
                with wl_sort_col1:
                    wl_sort_opts = [c for c in ['Composite Score', 'ROC 3M %', 'Market Cap (Cr)', 'RSI 14', 'ROCE %'] if c in watchlist_df.columns]
                    wl_sort = st.selectbox("Sort watchlist by", wl_sort_opts, key='wl_sort')
                with wl_sort_col2:
                    wl_order = st.selectbox("Order", ["Descending", "Ascending"], key='wl_order')
                wl_asc = wl_order == "Ascending"

                cc1, cc2 = st.columns([5, 1])
                with cc2:
                    export_btn(watchlist_df, OVERVIEW_COLS, 'watchlist.csv', 'dl_watchlist')

                with wl_ov:   show_table(watchlist_df, OVERVIEW_COLS, wl_sort, wl_asc, 'wl_ov')
                with wl_tech: show_table(watchlist_df, TECHNICAL_COLS, wl_sort, wl_asc, 'wl_tech')
                with wl_ret:  show_table(watchlist_df, RETURNS_COLS, wl_sort, wl_asc, 'wl_ret')
                with wl_risk: show_table(watchlist_df, RISK_COLS, wl_sort, wl_asc, 'wl_risk')
                with wl_fund: show_table(watchlist_df, FUNDAMENTAL_COLS, wl_sort, wl_asc, 'wl_fund')
