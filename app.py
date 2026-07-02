import streamlit as st
import pandas as pd
import numpy as np
import re
import os
from datetime import datetime
import yfinance as yf

from config import (
    OVERVIEW_COLS, TECHNICAL_COLS, RETURNS_COLS, RISK_COLS, FUNDAMENTAL_COLS,
    INDEX_COLS, GLOBAL_COLS, SCREENS, all_display_cols,
)
from scoring import add_scores
from styling import style_dataframe
from screens import run_screen
from insights import add_insights, INSIGHT_COLORS
from trade_setup import calc_trade_levels, get_key_levels
from history import get_previous_snapshot, compute_changes, get_screen_performance, list_snapshots


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
    .dash-section { margin-bottom: 1.5rem; }
    .dash-section-title { font-family: 'IBM Plex Mono', monospace; font-size: 0.85rem; font-weight: 600; color: #00d4aa; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 0.8rem; border-bottom: 1px solid #2a2a2a; padding-bottom: 0.3rem; }
    .breadth-bar { background: #16181f; border: 1px solid #2a2a2a; border-radius: 6px; overflow: hidden; height: 22px; display: flex; margin-bottom: 0.3rem; }
    .breadth-seg { height: 100%; display: flex; align-items: center; justify-content: center; font-size: 0.6rem; font-family: 'IBM Plex Mono', monospace; font-weight: 600; }
    .sector-row { background: #16181f; border: 1px solid #2a2a2a; border-radius: 8px; padding: 0.6rem 0.8rem; margin-bottom: 0.5rem; }
    .sector-name { font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem; color: #e0e0e0; font-weight: 600; }
    .sector-stat { font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; }
    .signal-card { background: #16181f; border: 1px solid #2a2a2a; border-left: 3px solid #00d4aa; border-radius: 0 6px 6px 0; padding: 0.5rem 0.8rem; margin-bottom: 0.4rem; font-family: 'IBM Plex Mono', monospace; font-size: 0.75rem; }
    .signal-card.bearish { border-left-color: #ff4d4d; }
    .signal-card.neutral { border-left-color: #ffaa33; }
    .top5-card { background: #16181f; border: 1px solid #2a2a2a; border-radius: 8px; padding: 0.8rem; margin-bottom: 0.6rem; }
    .top5-header { font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem; color: #00d4aa; font-weight: 600; margin-bottom: 0.5rem; }
    .top5-row { display: flex; justify-content: space-between; padding: 0.15rem 0; font-family: 'IBM Plex Mono', monospace; font-size: 0.73rem; }
    .top5-rank { color: #555; width: 1.5rem; }
    .top5-sym { color: #e0e0e0; flex: 1; }
    .top5-val { font-weight: 600; }
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


def _file_mtime(path):
    """Get file modification time — used as cache key to auto-invalidate on file change."""
    try:
        return os.path.getmtime(path) if os.path.exists(path) else 0
    except Exception:
        return 0


@st.cache_data(ttl=600, show_spinner=False)
def load_stock_data(mtime_tech=0, mtime_fund=0, mtime_const=0):
    """Load technicals + fundamentals + constituents. Cache invalidates when any file changes."""
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
def load_index_data(mtime=0):
    return read_csv_safe('data/indices_technicals.csv')


@st.cache_data(ttl=600, show_spinner=False)

def load_global_data(mtime=0):
    return read_csv_safe('data/global_technicals.csv')
def load_etf_mapping():
    try:
        etf_df = pd.read_csv('data/etf_mapping.csv')
        mapping = {}
        for _, row in etf_df.iterrows():
            idx = row['Index'].strip()
            sym = row['ETF_Symbol'].strip()
            if idx in mapping:
                mapping[idx].append(sym)
            else:
                mapping[idx] = [sym]
        return mapping
    except Exception:
        return {}

etf_mapping = load_etf_mapping()

with st.spinner("Loading data..."):
    df = load_stock_data(
        mtime_tech=_file_mtime('data/technicals.csv'),
        mtime_fund=_file_mtime('data/fundamentals.csv'),
        mtime_const=_file_mtime('data/index_constituents.csv'),
    )
    idx_df = load_index_data(mtime=_file_mtime('data/indices_technicals.csv'))
    glob_df = load_global_data(mtime=_file_mtime('data/global_technicals.csv'))


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

    # Sort on FULL dataframe first (so sort works even if column isn't displayed)
    sorted_df = data_df.copy()
    if sort_by and sort_by in sorted_df.columns:
        try:
            actual_sort = '_rank_sort' if sort_by == 'Universe Rank' and '_rank_sort' in sorted_df.columns else sort_by
            sorted_df = sorted_df.sort_values(actual_sort, ascending=sort_asc, na_position='last')
        except Exception:
            pass

    # Then slice to display columns
    disp = sorted_df[disp_cols].copy()
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
    if '_rank_sort' in data_df.columns and '_rank_sort' not in disp_cols:
        disp = data_df[disp_cols + ['_rank_sort']].copy()
    else:
        disp = data_df[disp_cols].copy()

    if sort_by and sort_by in data_df.columns:
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
    <p class="screener-subtitle">Technical + Fundamental Stock Screener for Indian Markets</p>
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
# SCORE + INSIGHTS (once, reuse across tabs)
# ────────────────────────────────────────────────
scored = add_scores(filtered.copy(), universe_df=filtered)
scored = add_insights(scored)


# ────────────────────────────────────────────────
# MAIN TABS
# ────────────────────────────────────────────────
main_tab0, main_tab1, main_tab2, main_tab3, main_tab4 = st.tabs(["🏠 Dashboard", "📊 Stocks", "📈 Index Dashboard", "📰 Events", "🔍 Tools"])


# ══════════════════════════════════════════════
# TAB 0 — DASHBOARD
# ══════════════════════════════════════════════
with main_tab0:
    dash_sub0, dash_sub1, dash_sub2, dash_sub3, dash_sub4, dash_sub5 = st.tabs([
        "🔔 What Changed Today", "📊 Market Overview", "🔄 Sector Rotation", "⚡ Signals", "🏅 Sector Top 5", "🎯 Quick Picks"
    ])
    # ── WHAT CHANGED TODAY ──────────────────────
    with dash_sub0:
        snapshots = list_snapshots()
        if len(snapshots) >= 2:
            # Load most recent as "today" and second most recent as "yesterday"
            try:
                today_snap = pd.read_csv(snapshots[0][1])
                yday_date = snapshots[1][0]
                yday_df = pd.read_csv(snapshots[1][1])
                # Use today's snapshot for comparison instead of live scored data
                scored_for_changes = today_snap
            except Exception:
                yday_date, yday_df = None, None
                scored_for_changes = scored
        else:
            yday_date, yday_df = None, None
            scored_for_changes = scored

        if yday_df is None:
            st.info("📅 No previous snapshot available yet. Daily snapshots will start accumulating once the automated pipeline runs. Check back tomorrow to see day-over-day changes.")
        else:
            st.markdown(f"<p style='color:#888;font-size:0.75rem;font-family:IBM Plex Mono,monospace'>Comparing today's data against snapshot from <strong>{yday_date}</strong>. Signals shown are fresh changes, not static counts.</p>", unsafe_allow_html=True)

            changes = compute_changes(scored_for_changes, yday_df, sym_col=sym_col)

            def render_change_signal(label, sig_df, extra_desc="", kind="bullish", key_suffix=""):
                if sig_df is None or sig_df.empty:
                    return
                icon_prefix = {"bullish": "🟢", "bearish": "🔴", "neutral": "🟡"}[kind]
                header = f"{icon_prefix} **{label}** — {len(sig_df)} stocks"
                if extra_desc:
                    header += f"  \n*{extra_desc}*"
                with st.expander(header, expanded=False):
                    disp_cols = [c for c in ['Name', 'Sector', 'Current Price', 'Composite Score', 'ROC 3M %', 'Market Regime'] if c in sig_df.columns]
                    show_table(sig_df, disp_cols, 'Composite Score', False, f'chg_{key_suffix}')

            chg_col1, chg_col2 = st.columns(2)

            with chg_col1:
                st.markdown('<div class="dash-section-title">🟢 Positive Changes</div>', unsafe_allow_html=True)
                render_change_signal("Fresh Golden Cross", changes.get('new_golden_cross'),
                                     "EMA 50 crossed above EMA 200 today", "bullish", "gc")
                render_change_signal("Entered Strong Bull", changes.get('entered_strong_bull'),
                                     "Regime upgraded to Strong Bull", "bullish", "esb")
                render_change_signal("Regime Upgraded", changes.get('regime_upgraded'),
                                     "Market regime improved", "bullish", "ru")
                render_change_signal("Newly At 52W High", changes.get('newly_at_high'),
                                     "Reached 52-week high today", "bullish", "nah")
                render_change_signal("Supertrend Flipped Bullish", changes.get('supertrend_bullish_flip'),
                                     "Supertrend turned Bullish today", "bullish", "stbf")

            with chg_col2:
                st.markdown('<div class="dash-section-title">🔴 Negative Changes</div>', unsafe_allow_html=True)
                render_change_signal("Fresh Death Cross", changes.get('new_death_cross'),
                                     "EMA 50 crossed below EMA 200 today", "bearish", "dc")
                render_change_signal("Entered Strong Bear", changes.get('entered_strong_bear'),
                                     "Regime downgraded to Strong Bear", "bearish", "esbr")
                render_change_signal("Regime Downgraded", changes.get('regime_downgraded'),
                                     "Market regime worsened", "bearish", "rd")
                render_change_signal("Newly Damaged", changes.get('newly_damaged'),
                                     "Moved to Damaged drawdown status", "bearish", "nd")
                render_change_signal("Supertrend Flipped Bearish", changes.get('supertrend_bearish_flip'),
                                     "Supertrend turned Bearish today", "bearish", "stbrf")

    # Helper for dashboard
    def pct_of(series, condition):
        total = len(series.dropna())
        if total == 0:
            return 0
        return round(condition.sum() / total * 100, 1)

    # ── MARKET OVERVIEW ─────────────────────────
    with dash_sub1:
        st.markdown('<div class="dash-section">', unsafe_allow_html=True)
        st.markdown('<div class="dash-section-title">Market Breadth</div>', unsafe_allow_html=True)

        # Breadth metrics
        price = pd.to_numeric(scored.get('Current Price', pd.Series()), errors='coerce')
        ema50_vals = pd.to_numeric(scored.get('EMA 50', pd.Series()), errors='coerce')
        ema200_vals = pd.to_numeric(scored.get('EMA 200', pd.Series()), errors='coerce')

        above_ema50 = pct_of(price, price > ema50_vals) if 'EMA 50' in scored.columns else 0
        above_ema200 = pct_of(price, price > ema200_vals) if 'EMA 200' in scored.columns else 0

        bc1, bc2, bc3, bc4, bc5, bc6 = st.columns(6)
        with bc1:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Above EMA 50</div><div class="metric-value">{above_ema50}%</div></div>', unsafe_allow_html=True)
        with bc2:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Above EMA 200</div><div class="metric-value">{above_ema200}%</div></div>', unsafe_allow_html=True)
        with bc3:
            if has_col(scored, 'Supertrend'):
                st_bull_pct = pct_of(scored['Supertrend'], scored['Supertrend'] == 'Bullish')
                st.markdown(f'<div class="metric-card"><div class="metric-label">Supertrend Bullish</div><div class="metric-value">{st_bull_pct}%</div></div>', unsafe_allow_html=True)
        with bc4:
            if has_col(scored, 'MACD Signal'):
                macd_bull_pct = pct_of(scored['MACD Signal'], scored['MACD Signal'] == 'Bullish')
                st.markdown(f'<div class="metric-card"><div class="metric-label">MACD Bullish</div><div class="metric-value">{macd_bull_pct}%</div></div>', unsafe_allow_html=True)
        with bc5:
            if has_col(scored, 'EMA Cross'):
                gc_pct = pct_of(scored['EMA Cross'], scored['EMA Cross'] == 'Golden Cross')
                st.markdown(f'<div class="metric-card"><div class="metric-label">Golden Cross</div><div class="metric-value">{gc_pct}%</div></div>', unsafe_allow_html=True)

        with bc6:
            day_chg = pd.to_numeric(scored.get('Day Change %', pd.Series()), errors='coerce')
            advances = (day_chg > 0).sum()
            declines = (day_chg < 0).sum()
            ad_ratio = round(advances / declines, 2) if declines > 0 else 0
            ad_color = "#00d4aa" if ad_ratio > 1 else "#ff4d4d"
            st.markdown(f'<div class="metric-card"><div class="metric-label">Adv/Dec Ratio</div><div class="metric-value" style="color:{ad_color}">{ad_ratio} ({advances}/{declines})</div></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # Regime distribution bar
        if has_col(scored, 'Market Regime'):
            regime_counts = scored['Market Regime'].value_counts()
            total_r = regime_counts.sum()
            sb_n = regime_counts.get('Strong Bull', 0)
            b_n = regime_counts.get('Bull', 0)
            br_n = regime_counts.get('Bear', 0)
            sbr_n = regime_counts.get('Strong Bear', 0)
            sb_p = sb_n / total_r * 100 if total_r > 0 else 0
            b_p = b_n / total_r * 100 if total_r > 0 else 0
            br_p = br_n / total_r * 100 if total_r > 0 else 0
            sbr_p = sbr_n / total_r * 100 if total_r > 0 else 0

            st.markdown(f"""
            <div class="dash-section-title">Regime Distribution</div>
            <div class="breadth-bar">
                <div class="breadth-seg" style="width:{sb_p}%;background:#00d4aa;color:#0f1117">SB {sb_n}</div>
                <div class="breadth-seg" style="width:{b_p}%;background:#4da6ff;color:#0f1117">B {b_n}</div>
                <div class="breadth-seg" style="width:{br_p}%;background:#ff6b6b;color:#0f1117">Br {br_n}</div>
                <div class="breadth-seg" style="width:{sbr_p}%;background:#ff4444;color:#0f1117">SBr {sbr_n}</div>
            </div>
            <div style="display:flex;gap:1.5rem;font-size:0.65rem;font-family:IBM Plex Mono,monospace;color:#888;margin-top:0.2rem">
                <span><span style="color:#00d4aa">●</span> Strong Bull {sb_p:.0f}%</span>
                <span><span style="color:#4da6ff">●</span> Bull {b_p:.0f}%</span>
                <span><span style="color:#ff6b6b">●</span> Bear {br_p:.0f}%</span>
                <span><span style="color:#ff4444">●</span> Strong Bear {sbr_p:.0f}%</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Drawdown distribution
        if has_col(scored, 'Drawdown Status'):
            dd_counts = scored['Drawdown Status'].value_counts()
            total_dd = dd_counts.sum()
            ah_n = dd_counts.get('At High', 0)
            rc_n = dd_counts.get('Recovering', 0)
            co_n = dd_counts.get('Correcting', 0)
            dm_n = dd_counts.get('Damaged', 0)
            ah_p = ah_n / total_dd * 100 if total_dd > 0 else 0
            rc_p = rc_n / total_dd * 100 if total_dd > 0 else 0
            co_p = co_n / total_dd * 100 if total_dd > 0 else 0
            dm_p = dm_n / total_dd * 100 if total_dd > 0 else 0

            st.markdown(f"""
            <div class="dash-section-title">Drawdown Status</div>
            <div class="breadth-bar">
                <div class="breadth-seg" style="width:{ah_p}%;background:#00d4aa;color:#0f1117">AH {ah_n}</div>
                <div class="breadth-seg" style="width:{rc_p}%;background:#ffaa33;color:#0f1117">Rec {rc_n}</div>
                <div class="breadth-seg" style="width:{co_p}%;background:#ff8844;color:#0f1117">Cor {co_n}</div>
                <div class="breadth-seg" style="width:{dm_p}%;background:#ff4d4d;color:#0f1117">Dmg {dm_n}</div>
            </div>
            <div style="display:flex;gap:1.5rem;font-size:0.65rem;font-family:IBM Plex Mono,monospace;color:#888;margin-top:0.2rem">
                <span><span style="color:#00d4aa">●</span> At High {ah_p:.0f}%</span>
                <span><span style="color:#ffaa33">●</span> Recovering {rc_p:.0f}%</span>
                <span><span style="color:#ff8844">●</span> Correcting {co_p:.0f}%</span>
                <span><span style="color:#ff4d4d">●</span> Damaged {dm_p:.0f}%</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Cap-wise breakdown
        if has_col(scored, 'Cap Category') and has_col(scored, 'Market Regime'):
            st.markdown('<div class="dash-section-title">Regime by Market Cap</div>', unsafe_allow_html=True)
            cap_cols = st.columns(3)
            for i, cap in enumerate(['Large', 'Mid', 'Small']):
                cap_df = scored[scored['Cap Category'] == cap]
                if cap_df.empty:
                    continue
                cap_total = len(cap_df)
                cap_bull = (cap_df['Market Regime'].isin(['Bull', 'Strong Bull'])).sum()
                cap_bull_pct = round(cap_bull / cap_total * 100, 1) if cap_total > 0 else 0
                avg_roc3 = pd.to_numeric(cap_df.get('ROC 3M %', pd.Series()), errors='coerce').mean()
                avg_rsi_val = pd.to_numeric(cap_df.get('RSI 14', pd.Series()), errors='coerce').mean()
                color = "#00d4aa" if cap_bull_pct >= 50 else "#ff6b6b"
                with cap_cols[i]:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">{cap} Cap ({cap_total})</div>
                        <div class="metric-value" style="color:{color}">{cap_bull_pct}% Bullish</div>
                        <div style="font-size:0.7rem;color:#888;font-family:IBM Plex Mono,monospace;margin-top:0.3rem">
                            Avg ROC 3M: <span style="color:{'#00d4aa' if avg_roc3 > 0 else '#ff4d4d'}">{avg_roc3:.1f}%</span> · Avg RSI: {avg_rsi_val:.1f}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # ── SECTOR ROTATION ─────────────────────────
    with dash_sub2:
        if has_col(scored, 'Sector'):
            st.markdown('<div class="dash-section-title">Sector Momentum Ranking</div>', unsafe_allow_html=True)
            st.markdown("<p style='color:#888;font-size:0.75rem;font-family:IBM Plex Mono,monospace'>Sectors ranked by average 3M relative strength vs Nifty. Green = outperforming, Red = underperforming.</p>", unsafe_allow_html=True)

            sector_stats = []
            for sector in scored['Sector'].dropna().unique():
                s_df = scored[scored['Sector'] == sector]
                if len(s_df) < 3:
                    continue
                avg_rs3 = pd.to_numeric(s_df.get('RS vs Nifty 3M %', pd.Series()), errors='coerce').mean()
                avg_roc3 = pd.to_numeric(s_df.get('ROC 3M %', pd.Series()), errors='coerce').mean()
                avg_roc1 = pd.to_numeric(s_df.get('ROC 1M %', pd.Series()), errors='coerce').mean()
                bull_pct = round((s_df.get('Market Regime', pd.Series()).isin(['Bull', 'Strong Bull'])).sum() / len(s_df) * 100, 1)
                st_bull_pct = round((s_df.get('Supertrend', pd.Series()) == 'Bullish').sum() / len(s_df) * 100, 1) if has_col(s_df, 'Supertrend') else 0
                avg_score = pd.to_numeric(s_df.get('Composite Score', pd.Series()), errors='coerce').mean()
                sector_stats.append({
                    'Sector': sector,
                    'Stocks': len(s_df),
                    'RS vs Nifty 3M': avg_rs3,
                    'ROC 3M': avg_roc3,
                    'ROC 1M': avg_roc1,
                    'Bullish %': bull_pct,
                    'ST Bullish %': st_bull_pct,
                    'Avg Score': avg_score,
                })

            if sector_stats:
                sector_df = pd.DataFrame(sector_stats).sort_values('RS vs Nifty 3M', ascending=False).reset_index(drop=True)

                for _, row in sector_df.iterrows():
                    rs3 = row['RS vs Nifty 3M']
                    rs_color = "#00d4aa" if rs3 > 0 else "#ff4d4d"
                    roc3_color = "#00d4aa" if row['ROC 3M'] > 0 else "#ff4d4d"
                    roc1_color = "#00d4aa" if row['ROC 1M'] > 0 else "#ff4d4d"
                    bull_color = "#00d4aa" if row['Bullish %'] >= 50 else "#ff6b6b"
                    bar_width = min(abs(rs3) * 3, 100)
                    bar_dir = "right" if rs3 >= 0 else "left"

                    st.markdown(f"""
                    <div class="sector-row" style="display:flex;align-items:center;gap:1rem">
                        <div style="width:160px">
                            <div class="sector-name">{row['Sector']}</div>
                            <div style="font-size:0.65rem;color:#555;font-family:IBM Plex Mono,monospace">{row['Stocks']} stocks</div>
                        </div>
                        <div style="flex:1">
                            <div style="display:flex;gap:1.5rem;flex-wrap:wrap">
                                <span class="sector-stat">RS 3M: <span style="color:{rs_color};font-weight:600">{rs3:+.1f}%</span></span>
                                <span class="sector-stat">ROC 3M: <span style="color:{roc3_color}">{row['ROC 3M']:+.1f}%</span></span>
                                <span class="sector-stat">ROC 1M: <span style="color:{roc1_color}">{row['ROC 1M']:+.1f}%</span></span>
                                <span class="sector-stat">Bullish: <span style="color:{bull_color}">{row['Bullish %']:.0f}%</span></span>
                                <span class="sector-stat">ST Bull: {row['ST Bullish %']:.0f}%</span>
                                <span class="sector-stat">Avg Score: {row['Avg Score']:.1f}</span>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.warning("Sector data not available.")

    # ── SIGNAL DASHBOARD ────────────────────────
    with dash_sub3:
        st.markdown("<p style='color:#888;font-size:0.75rem;font-family:IBM Plex Mono,monospace'>Key signals detected in the current data snapshot. Click any signal to expand the full list.</p>", unsafe_allow_html=True)

        def render_signal(label, sig_df, extra_desc="", kind="bullish", cols_to_show=None, key_suffix=""):
            """Render a signal card with expandable stock list."""
            if sig_df is None or sig_df.empty:
                return
            icon_prefix = {"bullish": "🟢", "bearish": "🔴", "neutral": "🟡"}[kind]
            header = f"{icon_prefix} **{label}** — {len(sig_df)} stocks"
            if extra_desc:
                header += f"  \n*{extra_desc}*"

            with st.expander(header, expanded=False):
                if cols_to_show is None:
                    cols_to_show = ['Name', 'Sector', 'Current Price', 'Composite Score', 'ROC 3M %', 'Market Regime']
                disp_cols = [c for c in cols_to_show if c in sig_df.columns]
                show_table(sig_df, disp_cols, 'Composite Score', False, f'sig_{key_suffix}')

        sig_col1, sig_col2 = st.columns(2)

        with sig_col1:
            st.markdown('<div class="dash-section-title">🟢 Bullish Signals</div>', unsafe_allow_html=True)

            # Fresh Golden Crosses
            if has_col(scored, 'EMA Cross') and has_col(scored, 'Days Since EMA Cross'):
                fresh_gc = scored[
                    (scored['EMA Cross'] == 'Golden Cross') &
                    (pd.to_numeric(scored['Days Since EMA Cross'], errors='coerce') <= 5)
                ]
                render_signal("Fresh Golden Cross", fresh_gc,
                              "EMA 50 crossed above EMA 200 in last 5 days", "bullish", key_suffix="fgc")

            # Full Bullish Alignment
            if has_col(scored, 'Market Regime') and has_col(scored, 'Supertrend') and has_col(scored, 'MACD Signal'):
                full_bull = scored[
                    (scored['Market Regime'] == 'Strong Bull') &
                    (scored['Supertrend'] == 'Bullish') &
                    (scored['MACD Signal'] == 'Bullish')
                ]
                render_signal("Full Bullish Alignment", full_bull,
                              "Strong Bull + Supertrend Bull + MACD Bull", "bullish", key_suffix="fba")

            # Near 52W High
            if has_col(scored, '% from 52W High'):
                near_high = scored[pd.to_numeric(scored['% from 52W High'], errors='coerce') >= -5]
                render_signal("Near 52W High", near_high,
                              "Within 5% of 52-week high", "bullish", key_suffix="nh")

            # Volume Surge
            if has_col(scored, 'Vol ROC 1M %') and has_col(scored, 'MACD Signal'):
                vol_surge = scored[
                    (pd.to_numeric(scored['Vol ROC 1M %'], errors='coerce') > 50) &
                    (scored['MACD Signal'] == 'Bullish')
                ]
                render_signal("Volume Surge + Bullish MACD", vol_surge,
                              "Volume ROC 1M > 50% with bullish MACD", "bullish", key_suffix="vs")

            # At High + Strong Momentum
            if has_col(scored, 'Drawdown Status') and has_col(scored, 'ROC 3M %'):
                at_high_momentum = scored[
                    (scored['Drawdown Status'] == 'At High') &
                    (pd.to_numeric(scored['ROC 3M %'], errors='coerce') > 15)
                ]
                render_signal("At High + Strong Momentum", at_high_momentum,
                              "At 52W high with ROC 3M > 15%", "bullish", key_suffix="ahm")

        with sig_col2:
            st.markdown('<div class="dash-section-title">🔴 Bearish / Caution Signals</div>', unsafe_allow_html=True)

            # Fresh Death Crosses
            if has_col(scored, 'EMA Cross') and has_col(scored, 'Days Since EMA Cross'):
                fresh_dc = scored[
                    (scored['EMA Cross'] == 'Death Cross') &
                    (pd.to_numeric(scored['Days Since EMA Cross'], errors='coerce') <= 5)
                ]
                render_signal("Fresh Death Cross", fresh_dc,
                              "EMA 50 crossed below EMA 200 in last 5 days", "bearish", key_suffix="fdc")

            # Full Bearish Alignment
            if has_col(scored, 'Market Regime') and has_col(scored, 'Supertrend') and has_col(scored, 'MACD Signal'):
                full_bear = scored[
                    (scored['Market Regime'] == 'Strong Bear') &
                    (scored['Supertrend'] == 'Bearish') &
                    (scored['MACD Signal'] == 'Bearish')
                ]
                render_signal("Full Bearish Alignment", full_bear,
                              "Strong Bear + Supertrend Bear + MACD Bear", "bearish", key_suffix="fber")

            # Damaged
            if has_col(scored, 'Drawdown Status'):
                damaged = scored[scored['Drawdown Status'] == 'Damaged']
                render_signal("Damaged", damaged,
                              "Down 20%+ from 52W high", "bearish", key_suffix="dmg")

            # RSI Overbought
            if has_col(scored, 'RSI 14'):
                overbought = scored[pd.to_numeric(scored['RSI 14'], errors='coerce') > 75]
                render_signal("RSI Overbought (>75)", overbought,
                              "Potentially overextended", "neutral", key_suffix="ob")

            # RSI Oversold
            if has_col(scored, 'RSI 14'):
                oversold = scored[pd.to_numeric(scored['RSI 14'], errors='coerce') < 30]
                render_signal("RSI Oversold (<30)", oversold,
                              "Potentially oversold", "neutral", key_suffix="os")

            # Rising volatility
            if has_col(scored, 'Vol Trend'):
                rising_vol = scored[scored['Vol Trend'] == 'Rising']
                render_signal("Rising Volatility", rising_vol,
                              "Short-term vol > long-term vol", "bearish", key_suffix="rv")

    # ── SECTOR TOP 5 ────────────────────────────
    with dash_sub4:
        if has_col(scored, 'Sector'):
            st.markdown("<p style='color:#888;font-size:0.75rem;font-family:IBM Plex Mono,monospace'>Top 5 stocks in each sector by Composite Score.</p>", unsafe_allow_html=True)

            sort_metric = st.selectbox(
                "Rank by",
                ['Composite Score', 'Momentum Score', 'Technical Score', 'Fundamental Score', 'ROC 3M %', 'RS vs Nifty 3M %'],
                key='top5_metric'
            )

            sectors_sorted = sorted(scored['Sector'].dropna().unique().tolist())

            # Display in 2-column grid
            for i in range(0, len(sectors_sorted), 2):
                cols = st.columns(2)
                for j, col in enumerate(cols):
                    idx = i + j
                    if idx >= len(sectors_sorted):
                        break
                    sector = sectors_sorted[idx]
                    s_df = scored[scored['Sector'] == sector].copy()

                    if sort_metric in s_df.columns:
                        s_df['_sort_val'] = pd.to_numeric(s_df[sort_metric], errors='coerce')
                        top5 = s_df.nlargest(5, '_sort_val')
                    else:
                        top5 = s_df.head(5)

                    rows_html = ""
                    for rank, (_, r) in enumerate(top5.iterrows(), 1):
                        val = r.get(sort_metric, np.nan)
                        val_str = f"{val:.1f}" if not pd.isna(val) else "—"
                        val_color = "#00d4aa" if not pd.isna(val) and float(val) > 0 else "#ff4d4d" if not pd.isna(val) and float(val) < 0 else "#ccc"
                        regime = r.get('Market Regime', '')
                        regime_dot = "🟢" if regime in ['Bull', 'Strong Bull'] else "🔴" if regime in ['Bear', 'Strong Bear'] else "🟡"
                        tech_i = r.get('Technical Insight', 'Hold')
                        fund_i = r.get('Fundamental Insight', 'Hold')
                        # Short codes for space
                        def insight_code(i):
                            return {'Strong Buy': 'SB', 'Buy': 'B', 'Hold': 'H', 'Sell': 'S', 'Strong Sell': 'SS'}.get(i, '—')
                        def insight_color(i):
                            return {'Strong Buy': '#00d4aa', 'Buy': '#4da6ff', 'Hold': '#888', 'Sell': '#ff8844', 'Strong Sell': '#ff4d4d'}.get(i, '#888')
                        tech_badge = f'<span style="color:{insight_color(tech_i)};font-size:0.65rem;padding:0 0.25rem;border:1px solid {insight_color(tech_i)};border-radius:3px">{insight_code(tech_i)}</span>'
                        fund_badge = f'<span style="color:{insight_color(fund_i)};font-size:0.65rem;padding:0 0.25rem;border:1px solid {insight_color(fund_i)};border-radius:3px">{insight_code(fund_i)}</span>'
                        rows_html += f'<div class="top5-row"><span class="top5-rank">{rank}.</span><span class="top5-sym">{regime_dot} {r[sym_col]} <span style="margin-left:0.4rem">{tech_badge} {fund_badge}</span></span><span class="top5-val" style="color:{val_color}">{val_str}</span></div>'

                    with col:
                        st.markdown(f"""
                        <div class="top5-card">
                            <div class="top5-header">{sector} ({len(s_df)})</div>
                            {rows_html}
                        </div>
                        """, unsafe_allow_html=True)
        else:
            st.warning("Sector data not available.")


# ── QUICK PICKS ─────────────────────────────
    with dash_sub5:
        st.markdown("<p style='color:#888;font-size:0.75rem;font-family:IBM Plex Mono,monospace'>Stocks categorised by investment horizon. Top 10 shown per category, ranked by Composite Score. Click to expand full list.</p>", unsafe_allow_html=True)

        horizons = {
            "📈 Short Term (Momentum)": scored[
                (scored.get('Supertrend', pd.Series()) == 'Bullish') &
                (scored.get('MACD Signal', pd.Series()) == 'Bullish') &
                (pd.to_numeric(scored.get('ROC 1M %', pd.Series()), errors='coerce') > 5) &
                (pd.to_numeric(scored.get('RSI 14', pd.Series()), errors='coerce').between(50, 70))
            ] if has_col(scored, 'Supertrend') else pd.DataFrame(),

            "📊 Medium Term (Trend + Quality)": scored[
                (scored.get('Market Regime', pd.Series()).isin(['Bull', 'Strong Bull'])) &
                (pd.to_numeric(scored.get('ROC 3M %', pd.Series()), errors='coerce') > 10) &
                (pd.to_numeric(scored.get('Fundamental Score', pd.Series()), errors='coerce') > 50)
            ] if has_col(scored, 'Market Regime') else pd.DataFrame(),

            "🏦 Long Term Compounder": scored[
                (pd.to_numeric(scored.get('ROCE %', pd.Series()), errors='coerce') > 15) &
                (pd.to_numeric(scored.get('ROE %', pd.Series()), errors='coerce') > 12) &
                (pd.to_numeric(scored.get('Debt/Equity', pd.Series()), errors='coerce') < 1) &
                (pd.to_numeric(scored.get('Sales Growth 3Y %', pd.Series()), errors='coerce') > 10) &
                (pd.to_numeric(scored.get('Promoter Holding %', pd.Series()), errors='coerce') > 50)
            ] if has_col(scored, 'ROCE %') else pd.DataFrame(),

            "💰 Dividend Pick": scored[
                (pd.to_numeric(scored.get('Dividend Yield %', pd.Series()), errors='coerce') > 2) &
                (pd.to_numeric(scored.get('Dividend Payout %', pd.Series()), errors='coerce').between(10, 60)) &
                (pd.to_numeric(scored.get('Debt/Equity', pd.Series()), errors='coerce') < 0.5) &
                (pd.to_numeric(scored.get('Profit Growth 3Y %', pd.Series()), errors='coerce') > 5)
            ] if has_col(scored, 'Dividend Yield %') else pd.DataFrame(),

            "💎 Value Pick": scored[
                (pd.to_numeric(scored.get('PE Ratio', pd.Series()), errors='coerce') < pd.to_numeric(scored.get('Sector PE', pd.Series()), errors='coerce')) &
                (pd.to_numeric(scored.get('ROCE %', pd.Series()), errors='coerce') > 12) &
                (pd.to_numeric(scored.get('Profit Growth 1Y %', pd.Series()), errors='coerce') > 0)
            ] if has_col(scored, 'PE Ratio') else pd.DataFrame(),
        }

        for horizon_name, horizon_df in horizons.items():
            if horizon_df is None or horizon_df.empty:
                continue
            top = horizon_df.nlargest(10, 'Composite Score') if 'Composite Score' in horizon_df.columns else horizon_df.head(10)
            with st.expander(f"{horizon_name} — {len(horizon_df)} stocks", expanded=False):
                show_table(horizon_df, OVERVIEW_COLS, 'Composite Score', False, f'qp_{horizon_name[:8]}')

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

                    # Screen performance (requires snapshots)
                    perf_row_html = ""
                    for days_back, label in [(30, "1M"), (90, "3M"), (180, "6M")]:
                        try:
                            perf = get_screen_performance(active, days_back, run_screen, scored, sym_col=sym_col)
                        except Exception:
                            perf = None
                        if perf is None:
                            continue
                        color = "#00d4aa" if perf['avg_return'] > 0 else "#ff4d4d"
                        perf_row_html += (
                            f'<div style="flex:1; min-width:130px; padding:0.5rem 0.7rem; background:#0f1117; border-radius:4px; border:1px solid #2a2a2a">'
                            f'<div style="font-size:0.6rem; color:#888; font-family:IBM Plex Mono,monospace; text-transform:uppercase; letter-spacing:1px">{label} Performance</div>'
                            f'<div style="font-size:1rem; color:{color}; font-family:IBM Plex Mono,monospace; font-weight:600">{perf["avg_return"]:+.2f}%</div>'
                            f'<div style="font-size:0.65rem; color:#888; font-family:IBM Plex Mono,monospace">{perf["winners"]}W / {perf["losers"]}L · {perf["win_rate"]}% win rate · {perf["survivors"]} picks</div>'
                            f'</div>'
                        )
                    if perf_row_html:
                        st.markdown(f'<div style="display:flex; gap:0.6rem; flex-wrap:wrap; margin-bottom:1rem">{perf_row_html}</div>', unsafe_allow_html=True)

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
            # Add ETF column
            idx_display['Available ETF'] = idx_display['Index'].map(
                lambda x: ', '.join(etf_mapping.get(x, [])) if etf_mapping.get(x) else '—'
            )
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
            st.markdown("<p style='color:#888;font-size:0.75rem;font-family:IBM Plex Mono,monospace'>▸ Select an index below to analyse its constituent stocks, view advances/declines, and compare relative strength.</p>", unsafe_allow_html=True)

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
                    # Advance / Decline summary
                    day_chg_col = pd.to_numeric(idx_stocks.get('Day Change %', pd.Series()), errors='coerce')
                    adv = (day_chg_col > 0).sum()
                    dec = (day_chg_col < 0).sum()
                    unch = (day_chg_col == 0).sum()
                    ad_ratio = round(adv / dec, 2) if dec > 0 else adv
                    ad_color = "#00d4aa" if adv > dec else "#ff4d4d" if dec > adv else "#888"

                    st.markdown(f"### 📊 {selected_index} — {len(idx_stocks)} stocks")
                    st.markdown(f"""
                    <div style="display:flex; gap:0.8rem; margin-bottom:1rem; flex-wrap:wrap">
                        <div class="metric-card" style="flex:1;min-width:100px"><div class="metric-label">Advances</div><div class="metric-value" style="color:#00d4aa">{adv}</div></div>
                        <div class="metric-card" style="flex:1;min-width:100px"><div class="metric-label">Declines</div><div class="metric-value" style="color:#ff4d4d">{dec}</div></div>
                        <div class="metric-card" style="flex:1;min-width:100px"><div class="metric-label">Unchanged</div><div class="metric-value" style="color:#888">{unch}</div></div>
                        <div class="metric-card" style="flex:1;min-width:100px"><div class="metric-label">A/D Ratio</div><div class="metric-value" style="color:{ad_color}">{ad_ratio}</div></div>
                    </div>
                    """, unsafe_allow_html=True)
                    # Compute RS vs the selected index (stock ROC - index ROC)
                    if idx_df is not None:
                        idx_row = idx_df[idx_df['Index'] == selected_index]
                        if not idx_row.empty:
                            idx_roc_1m = pd.to_numeric(idx_row['ROC 1M %'].iloc[0], errors='coerce') if 'ROC 1M %' in idx_row.columns else None
                            idx_roc_3m = pd.to_numeric(idx_row['ROC 3M %'].iloc[0], errors='coerce') if 'ROC 3M %' in idx_row.columns else None
                            idx_roc_6m = pd.to_numeric(idx_row['ROC 6M %'].iloc[0], errors='coerce') if 'ROC 6M %' in idx_row.columns else None

                            # Short label for column names (strip "Nifty " prefix)
                            short_name = selected_index.replace('Nifty ', '').replace('NIFTY', '').strip() or selected_index

                            if idx_roc_1m is not None and not pd.isna(idx_roc_1m) and 'ROC 1M %' in idx_stocks.columns:
                                idx_stocks[f'RS vs {short_name} 1M %'] = (
                                    pd.to_numeric(idx_stocks['ROC 1M %'], errors='coerce') - idx_roc_1m
                                ).round(2)
                            if idx_roc_3m is not None and not pd.isna(idx_roc_3m) and 'ROC 3M %' in idx_stocks.columns:
                                idx_stocks[f'RS vs {short_name} 3M %'] = (
                                    pd.to_numeric(idx_stocks['ROC 3M %'], errors='coerce') - idx_roc_3m
                                ).round(2)
                            if idx_roc_6m is not None and not pd.isna(idx_roc_6m) and 'ROC 6M %' in idx_stocks.columns:
                                idx_stocks[f'RS vs {short_name} 6M %'] = (
                                    pd.to_numeric(idx_stocks['ROC 6M %'], errors='coerce') - idx_roc_6m
                                ).round(2)

                    # Build list of RS vs index cols we just added (for display)
                    rs_vs_index_cols = [c for c in idx_stocks.columns if c.startswith('RS vs ') and c not in ['RS vs Nifty 1M %', 'RS vs Nifty 3M %', 'RS vs Nifty 6M %']]

                    # Extended RETURNS cols for drill-down (adds RS vs selected index)
                    RETURNS_COLS_DRILL = [
                        'Name', 'Current Price',
                        'ROC 1M %', 'ROC 3M %', 'ROC 6M %',
                        '1Y CAGR %', '3Y CAGR %',
                        'RS vs Nifty 1M %', 'RS vs Nifty 3M %', 'RS vs Nifty 6M %',
                    ] + rs_vs_index_cols + ['Momentum Rank 1M', 'Momentum Score']

                    # Top 5 Gainers & Losers
                    day_chg_sorted = idx_stocks.dropna(subset=['Day Change %']).copy()
                    day_chg_sorted['Day Change %'] = pd.to_numeric(day_chg_sorted['Day Change %'], errors='coerce')

                    top5_gain = day_chg_sorted.nlargest(5, 'Day Change %')
                    top5_lose = day_chg_sorted.nsmallest(5, 'Day Change %')

                    gl_col1, gl_col2 = st.columns(2)
                    with gl_col1:
                        gain_html = '<div class="top5-card"><div class="top5-header">🟢 Top 5 Gainers</div>'
                        for _, r in top5_gain.iterrows():
                            chg = r['Day Change %']
                            gain_html += f'<div class="top5-row"><span class="top5-sym">{r[sym_col]}</span><span class="top5-val" style="color:#00d4aa">+{chg:.2f}%</span></div>'
                        gain_html += '</div>'
                        st.markdown(gain_html, unsafe_allow_html=True)
                    with gl_col2:
                        lose_html = '<div class="top5-card"><div class="top5-header">🔴 Top 5 Losers</div>'
                        for _, r in top5_lose.iterrows():
                            chg = r['Day Change %']
                            lose_html += f'<div class="top5-row"><span class="top5-sym">{r[sym_col]}</span><span class="top5-val" style="color:#ff4d4d">{chg:.2f}%</span></div>'
                        lose_html += '</div>'
                        st.markdown(lose_html, unsafe_allow_html=True)

                    ds1, ds2 = st.columns([3, 1])
                    with ds1:
                        drill_sort_default_opts = ['ROC 3M %', 'ROC 1M %', 'Market Cap (Cr)', 'RSI 14', 'Momentum Quality', 'RS vs Nifty 3M %']
                        # Add the newly computed RS cols as sort options
                        drill_sort_default_opts = drill_sort_default_opts + rs_vs_index_cols
                        drill_sort_opts = [c for c in drill_sort_default_opts if c in idx_stocks.columns]
                        drill_sort = st.selectbox("Sort by", drill_sort_opts, key='drill_sort')
                    with ds2:
                        drill_order = st.selectbox("Order", ["Descending", "Ascending"], key='drill_order')
                    drill_asc = drill_order == "Ascending"

                    st.download_button(
                        f"⬇ Export {selected_index} stocks",
                        data=idx_stocks[[c for c in [sym_col] + OVERVIEW_COLS + rs_vs_index_cols if c in idx_stocks.columns]].to_csv(index=False).encode('utf-8'),
                        file_name=f'{selected_index.replace(" ", "_")}_stocks.csv',
                        mime='text/csv', key='dl_drill'
                    )

                    d_ov, d_tech, d_ret, d_risk, d_fund, d_custom = st.tabs([
                        "Overview", "Technicals", "Returns", "Risk", "Fundamentals", "⚙ Custom View"
                    ])
                    idx_scored = add_scores(idx_stocks.copy(), universe_df=idx_stocks)
                    idx_scored = add_insights(idx_scored)
                    with d_ov:   show_table(idx_scored, OVERVIEW_COLS, drill_sort, drill_asc, 'drill_ov')
                    with d_tech: show_table(idx_scored, TECHNICAL_COLS, drill_sort, drill_asc, 'drill_tech')
                    with d_ret:  show_table(idx_scored, RETURNS_COLS_DRILL, drill_sort, drill_asc, 'drill_ret')
                    with d_risk: show_table(idx_scored, RISK_COLS, drill_sort, drill_asc, 'drill_risk')
                    with d_fund: show_table(idx_scored, FUNDAMENTAL_COLS, drill_sort, drill_asc, 'drill_fund')
                    with d_custom:
                        all_avail_idx = [c for c in ALL_DISPLAY_COLS + rs_vs_index_cols if c in idx_scored.columns]
                        # Deduplicate
                        seen = set()
                        all_avail_idx = [c for c in all_avail_idx if not (c in seen or seen.add(c))]
                        score_cols_idx = ['Technical Score', 'Momentum Score', 'Fundamental Score', 'Composite Score', 'Universe Rank']
                        all_with_scores_idx = score_cols_idx + [c for c in all_avail_idx if c not in score_cols_idx]
                        default_custom = [sym_col, 'Name', 'Composite Score', 'Universe Rank', 'Market Regime', 'ROC 3M %', 'ROCE %'] + rs_vs_index_cols[:1]
                        custom_idx_cols = st.multiselect(
                            "Select columns", options=all_with_scores_idx,
                            default=[c for c in default_custom if c in idx_scored.columns],
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
# TAB 3.5 — EVENTS
# ══════════════════════════════════════════════
with main_tab3:
    ev_sub1, ev_sub2, ev_sub3 = st.tabs(["📋 Corporate Actions", "💰 FII / DII Activity", "📊 Bulk & Block Deals"])

    with ev_sub1:
        try:
            from nsepython import nsefetch
            url = "https://www.nseindia.com/api/corporates-corporateActions?index=equities&from_date=01-01-2026&to_date=31-12-2026"
            ca_data = nsefetch(url)

            if ca_data and len(ca_data) > 0:
                ca_df = pd.DataFrame(ca_data)
                st.markdown(f"<p style='color:#888;font-size:0.75rem;font-family:IBM Plex Mono,monospace'>{len(ca_df)} corporate actions in 2026 from NSE</p>", unsafe_allow_html=True)

                # Categorize actions
                def categorize_action(subject):
                    s = str(subject).lower()
                    if 'dividend' in s:
                        return '💰 Dividend'
                    elif 'split' in s or 'sub-division' in s:
                        return '✂️ Split'
                    elif 'bonus' in s:
                        return '🎁 Bonus'
                    elif 'right' in s:
                        return '📄 Rights'
                    elif 'buyback' in s or 'buy back' in s:
                        return '🔄 Buyback'
                    elif 'agm' in s or 'annual general' in s:
                        return '📅 AGM'
                    else:
                        return '📌 Other'

                ca_df['Action Type'] = ca_df['subject'].apply(categorize_action)

                # Filters
                fc1, fc2, fc3 = st.columns(3)
                with fc1:
                    action_types = ["All"] + sorted(ca_df['Action Type'].unique().tolist())
                    sel_action = st.selectbox("Action Type", action_types, key='ca_type')
                with fc2:
                    show_universe = st.checkbox("Only screener universe", value=True, key='ca_universe')
                with fc3:
                    show_upcoming = st.checkbox("Only upcoming (ex-date today or later)", value=True, key='ca_upcoming')

                filtered_ca = ca_df.copy()
                if sel_action != "All":
                    filtered_ca = filtered_ca[filtered_ca['Action Type'] == sel_action]
                if show_universe and sym_col in df.columns:
                    our_syms = set(df[sym_col].str.replace('.NS', '').str.strip().tolist())
                    filtered_ca = filtered_ca[filtered_ca['symbol'].isin(our_syms)]
                if show_upcoming:
                    filtered_ca['_exDate'] = pd.to_datetime(filtered_ca['exDate'], format='%d-%b-%Y', errors='coerce')
                    filtered_ca = filtered_ca[filtered_ca['_exDate'] >= pd.Timestamp.now().normalize()]
                    filtered_ca = filtered_ca.drop(columns=['_exDate'])

                st.markdown(f"**{len(filtered_ca)} actions**")

                if not filtered_ca.empty:
                    disp_ca = filtered_ca[['symbol', 'comp', 'Action Type', 'subject', 'exDate', 'recDate', 'faceVal']].copy()
                    disp_ca.columns = ['Symbol', 'Company', 'Type', 'Details', 'Ex-Date', 'Record Date', 'Face Value']
                    disp_ca['Ex-Date'] = pd.to_datetime(disp_ca['Ex-Date'], format='%d-%b-%Y', errors='coerce')
                    disp_ca['Record Date'] = pd.to_datetime(disp_ca['Record Date'], format='%d-%b-%Y', errors='coerce')
                    disp_ca = disp_ca.sort_values('Ex-Date').reset_index(drop=True)
                    disp_ca['Ex-Date'] = disp_ca['Ex-Date'].dt.strftime('%d-%b-%Y').fillna('—')
                    disp_ca['Record Date'] = disp_ca['Record Date'].dt.strftime('%d-%b-%Y').fillna('—')
                    disp_ca.index = disp_ca.index + 1
                    disp_ca.index.name = 'Sr No'
                    st.dataframe(disp_ca, use_container_width=True, height=500, key='ca_table')
                else:
                    st.info("No corporate actions match the selected filters.")
            else:
                st.info("No corporate actions data available.")
        except Exception as e:
            st.warning(f"Could not fetch corporate actions from NSE. Error: {e}")
    with ev_sub2:
        try:
            from nsepython import nse_fiidii
            fii_dii = nse_fiidii()
            if fii_dii is not None and not fii_dii.empty:
                st.markdown(f"<p style='color:#888;font-size:0.75rem;font-family:IBM Plex Mono,monospace'>Latest FII/DII trading activity from NSE (values in ₹ Cr)</p>", unsafe_allow_html=True)

                for _, row in fii_dii.iterrows():
                    cat = row.get('category', '')
                    buy = float(row.get('buyValue', 0))
                    sell = float(row.get('sellValue', 0))
                    net = float(row.get('netValue', 0))
                    net_color = "#00d4aa" if net > 0 else "#ff4d4d"
                    date_val = row.get('date', '')

                    st.markdown(f"""
                    <div style="background:#16181f;border:1px solid #2a2a2a;border-radius:8px;padding:0.8rem;margin-bottom:0.6rem">
                        <div style="display:flex;justify-content:space-between;align-items:center">
                            <span style="font-family:IBM Plex Mono,monospace;font-size:0.9rem;color:#e0e0e0;font-weight:600">{cat}</span>
                            <span style="font-family:IBM Plex Mono,monospace;font-size:0.7rem;color:#888">{date_val}</span>
                        </div>
                        <div style="display:flex;gap:1.5rem;margin-top:0.5rem">
                            <div>
                                <div style="font-size:0.6rem;color:#888;font-family:IBM Plex Mono,monospace;text-transform:uppercase;letter-spacing:1px">Buy</div>
                                <div style="font-size:0.95rem;color:#00d4aa;font-family:IBM Plex Mono,monospace;font-weight:600">₹{buy:,.2f} Cr</div>
                            </div>
                            <div>
                                <div style="font-size:0.6rem;color:#888;font-family:IBM Plex Mono,monospace;text-transform:uppercase;letter-spacing:1px">Sell</div>
                                <div style="font-size:0.95rem;color:#ff4d4d;font-family:IBM Plex Mono,monospace;font-weight:600">₹{sell:,.2f} Cr</div>
                            </div>
                            <div>
                                <div style="font-size:0.6rem;color:#888;font-family:IBM Plex Mono,monospace;text-transform:uppercase;letter-spacing:1px">Net</div>
                                <div style="font-size:1.1rem;color:{net_color};font-family:IBM Plex Mono,monospace;font-weight:700">₹{net:,.2f} Cr</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No FII/DII data available.")
        except Exception as e:
            st.warning(f"Could not fetch FII/DII data from NSE. Error: {e}")

with ev_sub3:
        try:
            from nsepython import get_bulkdeals, get_blockdeals
            bulk = get_bulkdeals()
            block = get_blockdeals()
           

            bd_col1, bd_col2 = st.tabs(["Bulk Deals", "Block Deals"])

            with bd_col1:
                if bulk is not None and not bulk.empty:
                    st.markdown(f"<p style='color:#888;font-size:0.75rem;font-family:IBM Plex Mono,monospace'>{len(bulk)} bulk deals today</p>", unsafe_allow_html=True)

                    show_univ_bulk = st.checkbox("Only screener universe", value=False, key='bulk_universe')
                    if show_univ_bulk and sym_col in df.columns:
                        our_syms = set(df[sym_col].str.replace('.NS', '').str.strip().tolist())
                        bulk = bulk[bulk['Symbol'].isin(our_syms)]

                    buy_filter = st.selectbox("Filter", ["All", "Buy Only", "Sell Only"], key='bulk_filter')
                    if buy_filter == "Buy Only":
                        bulk = bulk[bulk['Buy/Sell'].str.strip().str.upper() == 'BUY']
                    elif buy_filter == "Sell Only":
                        bulk = bulk[bulk['Buy/Sell'].str.strip().str.upper() == 'SELL']

                    if not bulk.empty:
                        disp_bulk = bulk[['Date', 'Symbol', 'Security Name', 'Client Name', 'Buy/Sell', 'Quantity Traded', 'Trade Price / Wght. Avg. Price']].copy()
                        disp_bulk.columns = ['Date', 'Symbol', 'Company', 'Client', 'Buy/Sell', 'Quantity', 'Avg Price']
                        disp_bulk['Quantity'] = pd.to_numeric(disp_bulk['Quantity'], errors='coerce').apply(lambda x: f"{x:,.0f}" if not pd.isna(x) else '—')
                        disp_bulk['Avg Price'] = pd.to_numeric(disp_bulk['Avg Price'], errors='coerce').apply(lambda x: f"₹{x:,.2f}" if not pd.isna(x) else '—')
                        disp_bulk = disp_bulk.reset_index(drop=True)
                        disp_bulk.index = disp_bulk.index + 1
                        disp_bulk.index.name = 'Sr No'
                        st.dataframe(disp_bulk, use_container_width=True, height=500, key='bulk_table')
                    else:
                        st.info("No bulk deals match the selected filters.")
                else:
                    st.info("No bulk deals today.")

            with bd_col2:
                if block is not None and not block.empty:
                    st.markdown(f"<p style='color:#888;font-size:0.75rem;font-family:IBM Plex Mono,monospace'>{len(block)} block deals today</p>", unsafe_allow_html=True)

                    show_univ_block = st.checkbox("Only screener universe", value=False, key='block_universe')
                    if show_univ_block and sym_col in df.columns:
                        our_syms = set(df[sym_col].str.replace('.NS', '').str.strip().tolist())
                        block = block[block['Symbol'].isin(our_syms)]

                    if not block.empty:
                        disp_block = block[['Date', 'Symbol', 'Security Name', 'Client Name', 'Buy/Sell', 'Quantity Traded', 'Trade Price / Wght. Avg. Price']].copy()
                        disp_block.columns = ['Date', 'Symbol', 'Company', 'Client', 'Buy/Sell', 'Quantity', 'Avg Price']
                        disp_block['Quantity'] = pd.to_numeric(disp_block['Quantity'], errors='coerce').apply(lambda x: f"{x:,.0f}" if not pd.isna(x) else '—')
                        disp_block['Avg Price'] = pd.to_numeric(disp_block['Avg Price'], errors='coerce').apply(lambda x: f"₹{x:,.2f}" if not pd.isna(x) else '—')
                        disp_block = disp_block.reset_index(drop=True)
                        disp_block.index = disp_block.index + 1
                        disp_block.index.name = 'Sr No'
                        st.dataframe(disp_block, use_container_width=True, height=500, key='block_table')
                    else:
                        st.info("No block deals match the selected filters.")
                else:
                    st.info("No block deals today.")
        except Exception as e:
            st.warning(f"Could not fetch deals data from NSE. Error: {e}")

# ══════════════════════════════════════════════
# TAB 3 — TOOLS (Stock Card, Compare, Watchlist)
# ══════════════════════════════════════════════
with main_tab4:
    tools_sub1, tools_sub2, tools_sub3, tools_sub4 = st.tabs(["🪪 Stock Card", "⚖ Compare", "📌 Watchlist", "📚 Methodology"])

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
        tech_insight = row.get('Technical Insight', 'Hold')
        fund_insight = row.get('Fundamental Insight', 'Hold')
        chg_class = color_class(day_chg)

        tech_style = INSIGHT_COLORS.get(tech_insight, 'color:#aaa')
        fund_style = INSIGHT_COLORS.get(fund_insight, 'color:#aaa')

        # Header with insight badges
        st.markdown(f"""
        <div class="stock-card">
            <div class="stock-card-header">{sym}</div>
            <div class="stock-card-sub">{name} · {sector} · {industry} · {cap_cat}</div>
            <div style="display:flex; gap:2rem; align-items:baseline; margin-bottom:0.8rem;">
                <span style="font-size:1.6rem; font-weight:700; color:#e0e0e0; font-family:'IBM Plex Mono',monospace">₹{fmt_val(price, ',.2f')}</span>
                <span class="stock-card-val {chg_class}" style="font-size:0.9rem">{fmt_val(day_chg, '.2f', '%')}</span>
                <span style="font-size:0.75rem; color:#888; font-family:'IBM Plex Mono',monospace">Mkt Cap: ₹{fmt_val(mcap, ',.0f')} Cr</span>
            </div>
            <div style="display:flex; gap:0.6rem; flex-wrap:wrap;">
                <span style="padding:0.35rem 0.8rem; border-radius:4px; font-family:'IBM Plex Mono',monospace; font-size:0.75rem; {tech_style}">TECH: {tech_insight.upper()}</span>
                <span style="padding:0.35rem 0.8rem; border-radius:4px; font-family:'IBM Plex Mono',monospace; font-size:0.75rem; {fund_style}">FUND: {fund_insight.upper()}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)


    # ── Company Description ──
        desc = row.get('Description', '')
        if desc and str(desc) not in ('', 'nan', 'None'):
            st.markdown(f"""
            <div class="stock-card" style="margin-top:0.5rem">
                <div class="stock-card-section">About</div>
                <div style="font-size:0.75rem;color:#aaa;font-family:IBM Plex Mono,monospace;line-height:1.5">{str(desc)}</div>
            </div>
            """, unsafe_allow_html=True)

        # ── Analyst Consensus ──
        analyst_rec = row.get('Analyst Recommendation', '')
        target_mean = row.get('Target Mean Price', np.nan)
        target_high = row.get('Target High Price', np.nan)
        target_low = row.get('Target Low Price', np.nan)
        num_analysts = row.get('No. of Analysts', np.nan)
        analyst_score = row.get('Analyst Score', np.nan)

        has_rec = analyst_rec and str(analyst_rec) not in ('', 'nan', 'None', 'none')
        has_targets = not pd.isna(target_mean) or not pd.isna(target_high) or not pd.isna(target_low)

        if has_rec or has_targets:
            rec_colors = {'strong_buy': '#00d4aa', 'buy': '#4da6ff', 'hold': '#ffaa33', 'sell': '#ff8844', 'strong_sell': '#ff4d4d'}
            rec_color = rec_colors.get(str(analyst_rec).lower(), '#888') if has_rec else '#888'
            rec_label = str(analyst_rec).replace('_', ' ').title() if has_rec else '—'
            n_analysts = int(num_analysts) if not pd.isna(num_analysts) else '?'
            coverage_note = "" if not pd.isna(num_analysts) and num_analysts >= 3 else '<div style="font-size:0.6rem;color:#ff8844;margin-top:0.3rem">⚠ Limited analyst coverage — data may be outdated</div>'

            upside = ((float(target_mean) - float(price)) / float(price) * 100) if not pd.isna(target_mean) and not pd.isna(price) and float(price) > 0 else np.nan
            upside_color = "#00d4aa" if not pd.isna(upside) and upside > 0 else "#ff4d4d"
            upside_str = f"{upside:+.1f}% {'upside' if upside > 0 else 'downside'}" if not pd.isna(upside) else '—'
            score_str = f"Score: {analyst_score:.2f}/5" if not pd.isna(analyst_score) else ''

            st.markdown(f"""
            <div class="stock-card" style="margin-top:0.5rem">
                <div class="stock-card-section">Analyst Consensus ({n_analysts} analysts)</div>
                <div style="display:flex;gap:1rem;flex-wrap:wrap">
                    <div style="flex:1;min-width:100px;padding:0.5rem;background:#0f1117;border-radius:4px">
                        <div style="font-size:0.6rem;color:#888;font-family:IBM Plex Mono,monospace;text-transform:uppercase;letter-spacing:1px">Rating</div>
                        <div style="font-size:1rem;color:{rec_color};font-family:IBM Plex Mono,monospace;font-weight:600">{rec_label}</div>
                        <div style="font-size:0.65rem;color:#888;font-family:IBM Plex Mono,monospace">{score_str}</div>
                    </div>
                    <div style="flex:1;min-width:100px;padding:0.5rem;background:#0f1117;border-radius:4px">
                        <div style="font-size:0.6rem;color:#888;font-family:IBM Plex Mono,monospace;text-transform:uppercase;letter-spacing:1px">Target Mean</div>
                        <div style="font-size:1rem;color:#e0e0e0;font-family:IBM Plex Mono,monospace;font-weight:600">₹{fmt_val(target_mean, ',.2f')}</div>
                        <div style="font-size:0.65rem;color:{upside_color};font-family:IBM Plex Mono,monospace">{upside_str}</div>
                    </div>
                    <div style="flex:1;min-width:100px;padding:0.5rem;background:#0f1117;border-radius:4px">
                        <div style="font-size:0.6rem;color:#888;font-family:IBM Plex Mono,monospace;text-transform:uppercase;letter-spacing:1px">Target High</div>
                        <div style="font-size:0.95rem;color:#00d4aa;font-family:IBM Plex Mono,monospace;font-weight:600">₹{fmt_val(target_high, ',.2f')}</div>
                    </div>
                    <div style="flex:1;min-width:100px;padding:0.5rem;background:#0f1117;border-radius:4px">
                        <div style="font-size:0.6rem;color:#888;font-family:IBM Plex Mono,monospace;text-transform:uppercase;letter-spacing:1px">Target Low</div>
                        <div style="font-size:0.95rem;color:#ff4d4d;font-family:IBM Plex Mono,monospace;font-weight:600">₹{fmt_val(target_low, ',.2f')}</div>
                    </div>
                </div>
                {coverage_note}
            </div>
            """, unsafe_allow_html=True)
            
        # ── Screen Membership ──
        matched_screens = []
        for screen_name in SCREENS:
            try:
                result = run_screen(screen_name, scored)
                if result is not None and not result.empty and sym in result[sym_col].values:
                    matched_screens.append(screen_name)
            except Exception:
                continue

        if matched_screens:
            badges = " ".join([f'<span style="display:inline-block;padding:0.25rem 0.6rem;margin:0.15rem;border-radius:4px;background:#0d2e1f;border:1px solid #00d4aa33;color:#00d4aa;font-family:IBM Plex Mono,monospace;font-size:0.7rem">{s}</span>' for s in matched_screens])
            st.markdown(f"""
            <div class="stock-card" style="margin-top:0.5rem">
                <div class="stock-card-section">Appears in Screens ({len(matched_screens)})</div>
                <div style="display:flex;flex-wrap:wrap;gap:0.2rem">{badges}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="stock-card" style="margin-top:0.5rem">
                <div class="stock-card-section">Appears in Screens</div>
                <div style="font-size:0.75rem;color:#555;font-family:IBM Plex Mono,monospace">Does not match any pre-built screen currently</div>
            </div>
            """, unsafe_allow_html=True)

        # ── Peer Comparison ──
        stock_industry = row.get('Industry', '')
        stock_cap = row.get('Cap Category', '')
        if stock_industry and str(stock_industry) not in ('', 'nan', 'None', 'N/A'):
            peers = scored[
                (scored.get('Industry', pd.Series()) == stock_industry) &
                (scored[sym_col] != sym)
            ].copy()
            if not peers.empty:
                # Split into same cap and other cap peers
                same_cap_peers = peers[peers.get('Cap Category', pd.Series()) == stock_cap] if stock_cap else peers
                
                peer_label = f"Industry Peers — {stock_industry}"
                if stock_cap:
                    peer_label += f" ({stock_cap} Cap)"

                st.markdown(f"""
                <div class="stock-card" style="margin-top:0.5rem">
                    <div class="stock-card-section">{peer_label} — {len(same_cap_peers)} peers</div>
                </div>
                """, unsafe_allow_html=True)

                if not same_cap_peers.empty:
                    with st.expander(f"View {len(same_cap_peers)} peers", expanded=False):
                        p_ov, p_tech, p_ret, p_risk, p_fund = st.tabs(["Overview", "Technicals", "Returns", "Risk", "Fundamentals"])
                        with p_ov:   show_table(same_cap_peers, OVERVIEW_COLS, 'Composite Score', False, 'peer_sc_ov')
                        with p_tech: show_table(same_cap_peers, TECHNICAL_COLS, 'Composite Score', False, 'peer_sc_tech')
                        with p_ret:  show_table(same_cap_peers, RETURNS_COLS, 'Composite Score', False, 'peer_sc_ret')
                        with p_risk: show_table(same_cap_peers, RISK_COLS, 'Composite Score', False, 'peer_sc_risk')
                        with p_fund: show_table(same_cap_peers, FUNDAMENTAL_COLS, 'Composite Score', False, 'peer_sc_fund')
                
                # Show other cap peers in expander
                other_cap_peers = peers[peers.get('Cap Category', pd.Series()) != stock_cap] if stock_cap else pd.DataFrame()
                if not other_cap_peers.empty:
                    with st.expander(f"Other {stock_industry} peers (different cap size) — {len(other_cap_peers)} stocks", expanded=False):
                        po_ov, po_tech, po_ret, po_risk, po_fund = st.tabs(["Overview", "Technicals", "Returns", "Risk", "Fundamentals"])
                        with po_ov:   show_table(other_cap_peers, OVERVIEW_COLS, 'Composite Score', False, 'peer_oc_ov')
                        with po_tech: show_table(other_cap_peers, TECHNICAL_COLS, 'Composite Score', False, 'peer_oc_tech')
                        with po_ret:  show_table(other_cap_peers, RETURNS_COLS, 'Composite Score', False, 'peer_oc_ret')
                        with po_risk: show_table(other_cap_peers, RISK_COLS, 'Composite Score', False, 'peer_oc_risk')
                        with po_fund: show_table(other_cap_peers, FUNDAMENTAL_COLS, 'Composite Score', False, 'peer_oc_fund')
        # ── News + Analyst Distribution (single yfinance call) ──
        try:
            _yf_ticker = yf.Ticker(sym)
            
            # Analyst distribution
            recs = _yf_ticker.recommendations
            if recs is not None and not recs.empty:
                latest = recs.iloc[0]
                sb = int(latest.get('strongBuy', 0))
                b = int(latest.get('buy', 0))
                h = int(latest.get('hold', 0))
                s = int(latest.get('sell', 0))
                ss = int(latest.get('strongSell', 0))
                total = sb + b + h + s + ss
                if total > 0:
                    sb_w = sb/total*100
                    b_w = b/total*100
                    h_w = h/total*100
                    s_w = s/total*100
                    ss_w = ss/total*100
                    st.markdown(f"""
                    <div class="stock-card" style="margin-top:0.5rem">
                        <div class="stock-card-section">Analyst Distribution</div>
                        <div class="breadth-bar" style="height:24px">
                            <div class="breadth-seg" style="width:{sb_w}%;background:#00d4aa;color:#0f1117">SB {sb}</div>
                            <div class="breadth-seg" style="width:{b_w}%;background:#4da6ff;color:#0f1117">B {b}</div>
                            <div class="breadth-seg" style="width:{h_w}%;background:#ffaa33;color:#0f1117">H {h}</div>
                            <div class="breadth-seg" style="width:{s_w}%;background:#ff8844;color:#0f1117">S {s}</div>
                            <div class="breadth-seg" style="width:{ss_w}%;background:#ff4d4d;color:#0f1117">SS {ss}</div>
                        </div>
                        <div style="display:flex;gap:1rem;font-size:0.6rem;font-family:IBM Plex Mono,monospace;color:#888;margin-top:0.2rem">
                            <span><span style="color:#00d4aa">●</span> Strong Buy {sb}</span>
                            <span><span style="color:#4da6ff">●</span> Buy {b}</span>
                            <span><span style="color:#ffaa33">●</span> Hold {h}</span>
                            <span><span style="color:#ff8844">●</span> Sell {s}</span>
                            <span><span style="color:#ff4d4d">●</span> Strong Sell {ss}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            # Recent News
            news_items = _yf_ticker.news[:5] if _yf_ticker.news else []
            if news_items:
                news_html = '<div class="stock-card" style="margin-top:0.5rem"><div class="stock-card-section">Recent News</div>'
                for item in news_items:
                    content = item.get('content', {})
                    n_title = content.get('title', '')
                    n_summary = content.get('summary', '')
                    n_date = content.get('pubDate', '')[:10]
                    n_provider = content.get('provider', {}).get('displayName', '')
                    n_link = content.get('clickThroughUrl', {}).get('url', '')
                    if n_title:
                        news_html += f'<div style="padding:0.5rem 0;border-bottom:1px solid #2a2a2a"><a href="{n_link}" target="_blank" style="color:#4da6ff;font-family:IBM Plex Mono,monospace;font-size:0.78rem;text-decoration:none;font-weight:600">{n_title[:120]}{"..." if len(n_title) > 120 else ""}</a><div style="font-size:0.65rem;color:#888;font-family:IBM Plex Mono,monospace;margin-top:0.2rem">{n_provider} · {n_date}</div><div style="font-size:0.7rem;color:#aaa;font-family:IBM Plex Mono,monospace;margin-top:0.2rem">{n_summary[:200]}{"..." if len(n_summary) > 200 else ""}</div></div>'
                news_html += '</div>'
                st.markdown(news_html, unsafe_allow_html=True)
        except Exception:
            pass
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

        # Trade Setup (ATR-based)
        trade_levels = calc_trade_levels(row)
        key_levels = get_key_levels(row)

        if trade_levels:
            atr_pct_val = row.get('ATR % (14D)', np.nan)
            st.markdown(f"""
            <div class="stock-card">
                <div class="stock-card-section">Trade Setup (Reference Only)</div>
                <div style="display:flex; gap:1rem; flex-wrap:wrap; margin-bottom:0.6rem;">
                    <div style="flex:1; min-width:110px; padding:0.5rem; background:#0f1117; border-radius:4px">
                        <div style="font-size:0.6rem; color:#888; font-family:'IBM Plex Mono',monospace; text-transform:uppercase; letter-spacing:1px">Entry</div>
                        <div style="font-size:0.95rem; color:#e0e0e0; font-family:'IBM Plex Mono',monospace; font-weight:600">₹{trade_levels['entry']:,.2f}</div>
                    </div>
                    <div style="flex:1; min-width:110px; padding:0.5rem; background:#0f1117; border-radius:4px">
                        <div style="font-size:0.6rem; color:#888; font-family:'IBM Plex Mono',monospace; text-transform:uppercase; letter-spacing:1px">Stop Loss</div>
                        <div style="font-size:0.95rem; color:#ff4d4d; font-family:'IBM Plex Mono',monospace; font-weight:600">₹{trade_levels['stop']:,.2f}</div>
                        <div style="font-size:0.65rem; color:#888; font-family:'IBM Plex Mono',monospace">-{trade_levels['risk_pct']:.2f}%</div>
                    </div>
                    <div style="flex:1; min-width:110px; padding:0.5rem; background:#0f1117; border-radius:4px">
                        <div style="font-size:0.6rem; color:#888; font-family:'IBM Plex Mono',monospace; text-transform:uppercase; letter-spacing:1px">Target 1 (2R)</div>
                        <div style="font-size:0.95rem; color:#00d4aa; font-family:'IBM Plex Mono',monospace; font-weight:600">₹{trade_levels['target1']:,.2f}</div>
                        <div style="font-size:0.65rem; color:#888; font-family:'IBM Plex Mono',monospace">+{trade_levels['reward1_pct']:.2f}%</div>
                    </div>
                    <div style="flex:1; min-width:110px; padding:0.5rem; background:#0f1117; border-radius:4px">
                        <div style="font-size:0.6rem; color:#888; font-family:'IBM Plex Mono',monospace; text-transform:uppercase; letter-spacing:1px">Target 2 (3R)</div>
                        <div style="font-size:0.95rem; color:#00d4aa; font-family:'IBM Plex Mono',monospace; font-weight:600">₹{trade_levels['target2']:,.2f}</div>
                        <div style="font-size:0.65rem; color:#888; font-family:'IBM Plex Mono',monospace">+{trade_levels['reward2_pct']:.2f}%</div>
                    </div>
                </div>
                <div style="font-size:0.7rem; color:#666; font-family:'IBM Plex Mono',monospace; margin-bottom:0.5rem">
                    Based on ATR ({fmt_val(atr_pct_val, '.2f', '%')}) · Stop = 1.5× ATR below entry · Levels are illustrative, not investment advice
                </div>
                <div class="stock-card-section" style="font-size:0.6rem; margin-top:0.8rem">Key Reference Levels</div>
                <div class="stock-card-row"><span class="stock-card-label">52W High</span><span class="stock-card-val">₹{fmt_val(key_levels['high_52w'], ',.2f')}</span></div>
                <div class="stock-card-row"><span class="stock-card-label">52W Low</span><span class="stock-card-val">₹{fmt_val(key_levels['low_52w'], ',.2f')}</span></div>
                <div class="stock-card-row"><span class="stock-card-label">EMA 50</span><span class="stock-card-val">₹{fmt_val(key_levels['ema_50'], ',.2f')}</span></div>
                <div class="stock-card-row"><span class="stock-card-label">EMA 200</span><span class="stock-card-val">₹{fmt_val(key_levels['ema_200'], ',.2f')}</span></div>
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
                    ("Sector", "Sector", "{}", None),
                    ("Industry", "Industry", "{}", None),
                    ("Market Regime", "Market Regime", "{}", None),
                    ("─── Insights ───", None, None, None),
                    ("Technical Insight", "Technical Insight", "{}", None),
                    ("Fundamental Insight", "Fundamental Insight", "{}", None),
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

    # ── METHODOLOGY ─────────────────────────────
    with tools_sub4:
        methodology_path = None
        for p in ['METHODOLOGY.md', 'docs/METHODOLOGY.md']:
            if os.path.exists(p):
                methodology_path = p
                break

        if methodology_path is None:
            st.warning("METHODOLOGY.md not found. Please ensure the file is in the repo root.")
        else:
            try:
                with open(methodology_path, 'r', encoding='utf-8') as f:
                    methodology_content = f.read()
                st.markdown(methodology_content, unsafe_allow_html=False)
            except Exception as e:
                st.error(f"Could not load methodology file: {e}")
