"""
build_data.py — authoritative daily build step for the static frontend.

Reuses the EXISTING backend modules verbatim (config, scoring, insights) so the
numbers are identical to the Streamlit app — single source of truth. Reproduces
app.py's load_stock_data() merge/derive logic, then dumps JSON the frontend loads.

In production this file lives in the StockRadar repo and runs as the last step of
the daily GitHub Action (after fetch_*.py), committing public/data/*.json.

Run locally:
    python scripts/build_data.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd

# ── locate the existing StockRadar repo (its modules + data) ──
# Works in both layouts automatically:
#   • production: stockradar-web/ is a subfolder of the repo  → repo root is ../../
#   • this workspace: repo sits next to stockradar-web        → ../../StockRadar-India-main/...
# Override anytime with env STOCKRADAR_REPO.
def _find_repo():
    if os.environ.get("STOCKRADAR_REPO"):
        return os.environ["STOCKRADAR_REPO"]
    here = os.path.dirname(os.path.abspath(__file__))
    for c in [os.path.join(here, "..", ".."),  # subfolder-of-repo (deployed layout)
              os.path.join(here, "..", "..", "StockRadar-India-main", "StockRadar-India-main")]:
        c = os.path.abspath(c)
        if os.path.exists(os.path.join(c, "scoring.py")):
            return c
    return os.path.abspath(os.path.join(here, "..", ".."))

REPO = _find_repo()
sys.path.insert(0, REPO)
DATA = os.path.join(REPO, "data")
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "public", "data"))
os.makedirs(OUT, exist_ok=True)

# reuse the real backend — identical scores/insights to Streamlit
from config import all_display_cols, SCREENS  # noqa: E402
from scoring import add_scores        # noqa: E402
from insights import add_insights     # noqa: E402
from screens import run_screen        # noqa: E402
import history                        # noqa: E402
history.HISTORY_DIR = os.path.join(DATA, "history")


def read_csv_safe(filename):
    for enc in ["utf-8", "utf-8-sig", "utf-16", "cp1252", "latin1"]:
        try:
            return pd.read_csv(os.path.join(DATA, filename), encoding=enc)
        except Exception:
            continue
    return None


def load_stock_data():
    """Mirror of app.py load_stock_data() (minus the Streamlit cache)."""
    tech = read_csv_safe("technicals.csv")
    fund = read_csv_safe("fundamentals.csv")
    const = read_csv_safe("index_constituents.csv")

    sym_col = tech.columns[0]
    tech[sym_col] = tech[sym_col].astype(str).str.strip()

    if fund is not None:
        fs = fund.columns[0]
        fund[fs] = fund[fs].astype(str).str.strip()
        fund = fund.rename(columns={fs: sym_col})
        fund = fund.drop(columns=[c for c in ["Name", "name", "Current Price", "CMP Rs."] if c in fund.columns],
                         errors="ignore")
        tech = pd.merge(tech, fund, on=sym_col, how="left")

    if const is not None:
        const["Symbol"] = const["Symbol"].astype(str).str.strip()
        const = const.rename(columns={"Symbol": sym_col})
        tech = pd.merge(tech, const[[sym_col, "Index Membership"]], on=sym_col, how="left")

    tech = tech.loc[:, ~tech.columns.str.contains("^Unnamed")]
    tech = tech.dropna(subset=["Current Price"])

    if "EPS Current" in tech.columns and "EPS Last Year" in tech.columns:
        ec = pd.to_numeric(tech["EPS Current"], errors="coerce")
        ep = pd.to_numeric(tech["EPS Last Year"], errors="coerce")
        tech["EPS Growth 1Y %"] = ((ec - ep) / ep.abs() * 100).round(2)

    if "Free Cash Flow (Cr)" in tech.columns and "Market Cap (Cr)" in tech.columns:
        fcf = pd.to_numeric(tech["Free Cash Flow (Cr)"], errors="coerce")
        mcap = pd.to_numeric(tech["Market Cap (Cr)"], errors="coerce")
        tech["FCF Yield %"] = (fcf / mcap * 100).round(4)

    for period, colname in [("1M", "ROC 1M %"), ("3M", "ROC 3M %"), ("6M", "ROC 6M %")]:
        if colname in tech.columns:
            tech[f"Momentum Rank {period}"] = tech[colname].rank(ascending=False, method="min").astype("Int64")

    return tech, sym_col


def dump(df, name):
    # NaN/NaT/Inf → null so JSON is valid; keep column order.
    df = df.replace([np.inf, -np.inf], np.nan)
    records = json.loads(df.to_json(orient="records", double_precision=4, date_format="iso"))
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, separators=(",", ":"), ensure_ascii=False)
    print(f"  [ok] {name}: {len(records)} rows, {len(df.columns)} cols")
    return records


def build_changes(enriched):
    """Emit changes.json from the two most recent history snapshots (mirrors app.py 'What Changed Today')."""
    snaps = history.list_snapshots()
    out = {"today": None, "prev": None, "groups": {}}
    if len(snaps) >= 2:
        today_df = pd.read_csv(snaps[0][1])
        yday_df = pd.read_csv(snaps[1][1])
        changes = history.compute_changes(today_df, yday_df, sym_col="Symbol")
        comp = dict(zip(enriched["Symbol"].astype(str), enriched["Composite Score"]))
        tins = dict(zip(enriched["Symbol"].astype(str), enriched["Technical Insight"]))
        KEEP = ["Symbol", "Name", "Sector", "Current Price", "ROC 3M %", "Market Regime"]
        for k, v in changes.items():
            if v is None or len(v) == 0:
                out["groups"][k] = []
                continue
            d2 = v[[c for c in KEEP if c in v.columns]].copy()
            d2["Composite Score"] = d2["Symbol"].astype(str).map(comp)
            d2["Technical Insight"] = d2["Symbol"].astype(str).map(tins)
            d2 = d2.sort_values("Composite Score", ascending=False, na_position="last")
            out["groups"][k] = json.loads(d2.to_json(orient="records", double_precision=2))
        out["today"], out["prev"] = snaps[0][0], snaps[1][0]
    with open(os.path.join(OUT, "changes.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    tot = sum(len(v) for v in out["groups"].values())
    print(f"  [ok] changes.json: {out['prev']} → {out['today']}, {tot} changes across {len(out['groups'])} groups")


def main():
    print(f"repo: {REPO}")
    df, sym_col = load_stock_data()

    # the real scoring + insights — same functions the Streamlit app calls
    add_scores(df)
    add_insights(df)
    df = df.drop(columns=[c for c in ["_rank_sort"] if c in df.columns], errors="ignore")

    # RS vs Nifty 12M % — stock ROC 12M − Nifty 12M return (an index's 1Y CAGR == its 12M return).
    # The pipeline ships RS vs Nifty 1M/3M/6M but not 12M; compute it here consistently.
    _idx = read_csv_safe("indices_technicals.csv")
    if _idx is not None and "ROC 12M %" in df.columns:
        _n = _idx[_idx["Index"] == "Nifty 50"]
        if not _n.empty:
            _n12 = pd.to_numeric(_n.iloc[0].get("1Y CAGR %"), errors="coerce")
            if pd.notna(_n12):
                df["RS vs Nifty 12M %"] = (pd.to_numeric(df["ROC 12M %"], errors="coerce") - _n12).round(2)

    # precompute pre-built screen membership via the real run_screen() (single source of truth)
    membership = {name: set(run_screen(name, df).index) for name in SCREENS}
    df["Screens"] = [[name for name in SCREENS if i in membership[name]] for i in df.index]
    screens_meta = [
        {"name": name, "desc": cfg["desc"], "rules": cfg["rules"], "tab": cfg["tab"],
         "count": len(membership[name])}
        for name, cfg in SCREENS.items()
    ]
    with open(os.path.join(OUT, "screens.json"), "w", encoding="utf-8") as f:
        json.dump(screens_meta, f, ensure_ascii=False)
    print(f"  [ok] screens.json: {len(screens_meta)} screens")

    # What Changed Today — day-over-day via the real compute_changes() on the two latest snapshots
    build_changes(df)

    # order columns: symbol first, then the app's canonical display order, then the rest
    display = [c for c in all_display_cols(sym_col) if c in df.columns]
    rest = [c for c in df.columns if c not in display]
    df = df[display + rest]

    stocks = dump(df, "stocks.json")

    # indices — pass through + merge Available ETF from etf_mapping.csv
    idx = read_csv_safe("indices_technicals.csv")
    if idx is not None:
        idx = idx.loc[:, ~idx.columns.str.contains("^Unnamed")]
        etf = read_csv_safe("etf_mapping.csv")
        if etf is not None:
            m = etf.groupby("Index")["ETF_Symbol"].apply(lambda s: ", ".join(sorted(set(s)))).to_dict()
            idx["Available ETF"] = idx["Index"].map(m)
        dump(idx, "indices.json")
    g = read_csv_safe("global_technicals.csv")
    if g is not None:
        dump(g.loc[:, ~g.columns.str.contains("^Unnamed")], "global.json")

    ins = pd.Series([r.get("Technical Insight") for r in stocks]).value_counts().to_dict()
    print(f"done → {OUT}")
    print(f"  Technical Insight: {ins}")


if __name__ == "__main__":
    main()
