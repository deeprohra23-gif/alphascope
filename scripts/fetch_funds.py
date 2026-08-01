"""
fetch_funds.py
Mutual-fund screener data, sourced entirely from AMFI (free, no auth).

  • latest NAV + scheme master  → https://www.amfiindia.com/spages/NAVAll.txt
  • month-end NAV history       → portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx

One request per month-end (last business day, walking back over holidays) for the
last MONTHS_BACK months gives every scheme a monthly NAV series — enough for
point-to-point returns, annualised SD from monthly returns, Sharpe and max
drawdown. Stateless by design: no cache to keep in sync, a full run is ~60 small
requests.

Writes:
    data/funds.csv                       (audit trail / reproducibility)
    stockradar-web/public/data/funds.json (what the site loads)

Usage:
    python scripts/fetch_funds.py
"""

from datetime import date, timedelta
from pathlib import Path

import calendar
import json
import math
import sys
import time

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT_CSV = ROOT / "data" / "funds.csv"
OUT_JSON = ROOT / "stockradar-web" / "public" / "data" / "funds.json"

NAV_ALL = "https://www.amfiindia.com/spages/NAVAll.txt"
NAV_HIST = "https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx?frmdt={d}&todt={d}"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36"}

MONTHS_BACK = 63          # 61 completed month-ends: 60 months back plus the base point for 5Y
RISK_FREE = 6.5           # % — used for Sharpe
REQ_TIMEOUT = 60
# Liquid/overnight funds publish a NAV every calendar day, equity funds only on
# business days — so a weekend date still returns ~1,900 schemes. Demand a full
# business-day file (~8,500) or walk back, otherwise equity series lose months.
MIN_SCHEMES = 5000

# Only categories a retail equity audience screens on. AMFI category headers are
# matched on the text inside the brackets.
KEEP_CATEGORY_PREFIXES = ("Equity Scheme", "Hybrid Scheme", "Solution Oriented Scheme")
KEEP_CATEGORY_EXACT = ("Other Scheme - Index Funds",)

# Payout options make NAV series non-comparable (NAV drops on each distribution).
DROP_NAME_TOKENS = ("idcw", "dividend", "bonus", "payout", "unclaimed", "segregated")


# ─────────────────────────────────────────────
# FETCH + PARSE
# ─────────────────────────────────────────────

def _get(url, tries=3):
    for i in range(tries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=REQ_TIMEOUT)
            if r.status_code == 200 and r.text:
                return r.text
        except Exception as e:
            if i == tries - 1:
                print(f"   ! {type(e).__name__}: {e}")
        time.sleep(2 * (i + 1))
    return None


def clean_category(raw):
    """'Open Ended Schemes ( Equity Scheme - Mid Cap Fund )' → 'Equity Scheme - Mid Cap Fund'."""
    if not raw:
        return ""
    if "(" in raw and ")" in raw:
        raw = raw[raw.index("(") + 1:raw.rindex(")")]
    return " ".join(raw.split())


def parse_navall(body):
    """NAVAll.txt → {code: dict}. Tracks the current category header and AMC line."""
    funds, cat, amc = {}, "", ""
    for line in body.splitlines():
        s = line.strip()
        if not s:
            continue
        if ";" not in s:
            # section headers alternate: category (has brackets) then fund house
            if "(" in s and "Scheme" in s:
                cat = clean_category(s)
            else:
                amc = s
            continue
        p = s.split(";")
        if p[0].strip() == "Scheme Code":
            continue
        try:
            code = int(p[0])
        except ValueError:
            continue
        try:
            nav = float(p[4])
        except (ValueError, IndexError):
            continue
        funds[code] = {
            "code": code, "isin": p[1].strip(), "name": " ".join(p[3].split()),
            "nav": nav, "nav_date": p[5].strip(), "category": cat, "amc": amc,
        }
    return funds


def parse_hist(body):
    """Historical report → {code: nav}. Same layout, different column order."""
    out = {}
    for line in body.splitlines():
        s = line.strip()
        if not s or ";" not in s:
            continue
        p = s.split(";")
        if p[0].strip() == "Scheme Code":
            continue
        try:
            out[int(p[0])] = float(p[4])
        except (ValueError, IndexError):
            continue
    return out


def month_end_dates(anchor, months):
    """Last calendar day of each of the `months` months ending at `anchor`'s month."""
    out, y, m = [], anchor.year, anchor.month
    for _ in range(months):
        out.append(date(y, m, calendar.monthrange(y, m)[1]))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return out


def fetch_month_end(d, back=6):
    """NAVs for the last reporting day on/before `d` (walks back over weekends/holidays)."""
    for i in range(back):
        day = d - timedelta(days=i)
        body = _get(NAV_HIST.format(d=day.strftime("%d-%b-%Y")))
        if not body:
            continue
        navs = parse_hist(body)
        if len(navs) >= MIN_SCHEMES:
            return day, navs
    return None, {}


# ─────────────────────────────────────────────
# METRICS
# ─────────────────────────────────────────────

def years_ago(d, n):
    try:
        return d.replace(year=d.year - n)
    except ValueError:      # 29 Feb
        return d.replace(year=d.year - n, day=28)


def nav_near(pts, target, tol_days=45):
    """NAV at the point closest to `target`. Date-based, so a fund that missed a
    month-end report still gets its returns measured over the right window."""
    best, best_diff = None, None
    for dt, v in pts:
        diff = abs((dt - target).days)
        if diff <= tol_days and (best_diff is None or diff < best_diff):
            best, best_diff = v, diff
    return best


def cagr(end, start, years):
    if not start or not end or start <= 0 or end <= 0:
        return None
    return round(((end / start) ** (1 / years) - 1) * 100, 2)


def series_metrics(navs):
    """navs = NAV list, oldest→newest, monthly. Returns SD%, max drawdown%, positive-month %."""
    rets = []
    for a, b in zip(navs, navs[1:]):
        if a and b and a > 0:
            rets.append(b / a - 1)
    if len(rets) < 12:
        return None, None, None
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    sd = round(math.sqrt(var) * math.sqrt(12) * 100, 2)

    peak, mdd = navs[0], 0.0
    for v in navs:
        if v > peak:
            peak = v
        if peak > 0:
            mdd = min(mdd, v / peak - 1)
    pos = round(sum(1 for r in rets if r > 0) / len(rets) * 100, 1)
    return sd, round(mdd * 100, 2), pos


def plan_of(name):
    n = name.lower()
    if "direct" in n:
        return "Direct"
    if "regular" in n:
        return "Regular"
    return "Regular"


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Mutual Fund Data Fetch (AMFI)")
    print("=" * 60)

    body = _get(NAV_ALL)
    if not body:
        print("FATAL — could not fetch NAVAll.txt; keeping previous output")
        return 1
    master = parse_navall(body)
    print(f"  NAVAll: {len(master)} schemes")

    universe = {}
    for code, f in master.items():
        cat = f["category"]
        if not (cat.startswith(KEEP_CATEGORY_PREFIXES) or cat in KEEP_CATEGORY_EXACT):
            continue
        low = f["name"].lower()
        if any(t in low for t in DROP_NAME_TOKENS):
            continue
        universe[code] = f
    print(f"  Universe after category + growth-option filter: {len(universe)}")
    if not universe:
        print("FATAL — empty universe")
        return 1

    anchor = date.today()
    dates = month_end_dates(anchor, MONTHS_BACK)
    # the current month-end is in the future for most of the month — start from last month
    dates = [d for d in dates if d < anchor][:MONTHS_BACK - 2]
    dates.reverse()   # oldest → newest

    history = {}      # code → {date: nav}
    got = []
    print(f"  Fetching {len(dates)} month-end snapshots…")
    for d in dates:
        actual, navs = fetch_month_end(d)
        if not navs:
            print(f"    {d}  MISS")
            continue
        got.append(actual)
        for code in universe:
            v = navs.get(code)
            if v:
                history.setdefault(code, {})[actual] = v
    print(f"  Got {len(got)} snapshots: {got[0]} … {got[-1]}" if got else "  No snapshots")
    if len(got) < 13:
        print("FATAL — too little history to compute returns; keeping previous output")
        return 1

    rows = []
    for code, f in universe.items():
        h = history.get(code, {})
        pts = sorted(h.items())
        navs = [v for _, v in pts]
        latest = f["nav"]

        last_dt = pts[-1][0] if pts else None
        r1 = cagr(latest, nav_near(pts, years_ago(last_dt, 1)), 1) if last_dt else None
        r3 = cagr(latest, nav_near(pts, years_ago(last_dt, 3)), 3) if last_dt else None
        r5 = cagr(latest, nav_near(pts, years_ago(last_dt, 5)), 5) if last_dt else None
        sd, mdd, pos = series_metrics(navs)
        sharpe = round((r3 - RISK_FREE) / sd, 2) if (r3 is not None and sd) else None

        rows.append({
            "Scheme Code": code,
            "Scheme Name": f["name"],
            "Fund House": f["amc"],
            "Category": f["category"],
            "Plan": plan_of(f["name"]),
            "NAV": round(latest, 4),
            "NAV Date": f["nav_date"],
            "1Y Return %": r1,
            "3Y CAGR %": r3,
            "5Y CAGR %": r5,
            "SD (Annualised) %": sd,
            "Sharpe (3Y)": sharpe,
            "Max Drawdown %": mdd,
            "Positive Months %": pos,
            "History (Months)": len(navs),
            "ISIN": f["isin"],
        })

    # category percentile ranks on 1Y and 3Y (only against funds with the same category+plan)
    for key, col in (("1Y Return %", "1Y Rank in Category"), ("3Y CAGR %", "3Y Rank in Category")):
        buckets = {}
        for r in rows:
            if r[key] is not None:
                buckets.setdefault((r["Category"], r["Plan"]), []).append(r)
        for group in buckets.values():
            group.sort(key=lambda r: r[key], reverse=True)
            for i, r in enumerate(group, 1):
                r[col] = i
                r[col.replace("Rank in Category", "Category Size")] = len(group)

    rows.sort(key=lambda r: (r["Category"], -(r["3Y CAGR %"] if r["3Y CAGR %"] is not None else -999)))

    cols = ["Scheme Code", "Scheme Name", "Fund House", "Category", "Plan", "NAV", "NAV Date",
            "1Y Return %", "3Y CAGR %", "5Y CAGR %", "SD (Annualised) %", "Sharpe (3Y)",
            "Max Drawdown %", "Positive Months %", "1Y Rank in Category", "3Y Rank in Category",
            "1Y Category Size", "3Y Category Size", "History (Months)", "ISIN"]
    for r in rows:
        for c in cols:
            r.setdefault(c, None)

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump([{c: r[c] for c in cols} for r in rows], fh, separators=(",", ":"), ensure_ascii=False)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as fh:
        import csv
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r[c] for c in cols})

    with_3y = sum(1 for r in rows if r["3Y CAGR %"] is not None)
    print(f"\n[ok] {len(rows)} funds → {OUT_JSON}")
    print(f"     {with_3y} with a 3Y CAGR · NAV as of {rows[0]['NAV Date'] if rows else '?'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
