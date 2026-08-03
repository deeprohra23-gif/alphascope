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
import re
import sys
import time

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT_CSV = ROOT / "data" / "funds.csv"
OUT_JSON = ROOT / "stockradar-web" / "public" / "data" / "funds.json"
NAV_CACHE = ROOT / "data" / "nav_cache"

NAV_ALL = "https://www.amfiindia.com/spages/NAVAll.txt"
NAV_HIST = "https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx?frmdt={d}&todt={d}"
# TER (expense ratio) — the JSON API behind amfiindia.com/ter-of-mf-schemes.
# Rows are daily per scheme and carry BOTH plans: D_TER (Direct) and R_TER (Regular).
TER_MONTHS = "https://www.amfiindia.com/api/populate-ter-month?year={fy}"
TER_DATA = ("https://www.amfiindia.com/api/populate-te-rdata-revised"
            "?MF_ID=All&Month={m}&strCat=-1&strType=-1&page={p}&pageSize=2000")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36"}
TER_HEADERS = dict(HEADERS, Referer="https://www.amfiindia.com/ter-of-mf-schemes",
                   Accept="application/json, text/plain, */*")

MONTHS_BACK = 63          # 61 completed month-ends: 60 months back plus the base point for 5Y
# Month-end NAVs never change once published, so they are cached in the repo — one
# file per month-end. A weekly run then fetches only the month-end it is missing
# (usually none), instead of re-downloading five years of history every time.
# Delete the folder to force a full rebuild.
MAX_FETCH_SECONDS = 600   # stop fetching snapshots past this and use what we have
RISK_FREE = 6.5           # % — used for Sharpe
REQ_TIMEOUT = 25          # AMFI answers in seconds when healthy; a long wait means trouble
# Liquid/overnight funds publish a NAV every calendar day, equity funds only on
# business days — so a weekend date still returns ~1,900 schemes. Demand a full
# business-day file (~8,500) or walk back, otherwise equity series lose months.
MIN_SCHEMES = 5000

# Only categories a retail equity audience screens on. AMFI category headers are
# matched on the text inside the brackets.
KEEP_CATEGORY_PREFIXES = ("Equity Scheme", "Hybrid Scheme", "Solution Oriented Scheme")
KEEP_CATEGORY_EXACT = ("Other Scheme - Index Funds",)

# Payout options make NAV series non-comparable (NAV drops on each distribution).
# "Income Distribution cum capital withdrawal" is IDCW spelled out — same thing,
# and it slips past a plain "idcw" check.
DROP_NAME_TOKENS = ("idcw", "dividend", "bonus", "payout", "unclaimed", "segregated",
                    "income distribution", "reinvestment")


# ─────────────────────────────────────────────
# FETCH + PARSE
# ─────────────────────────────────────────────

def _get(url, tries=3, headers=None):
    for i in range(tries):
        try:
            r = requests.get(url, headers=headers or HEADERS, timeout=REQ_TIMEOUT)
            if r.status_code == 200 and r.text:
                # AMFI serves UTF-8 as "text/plain" with no charset, and the HTTP spec
                # makes requests fall back to ISO-8859-1 — which turns the curly
                # apostrophe in "Children's Fund" into "Childrenâ\x80\x99s Fund".
                if "charset=" not in (r.headers.get("Content-Type") or "").lower():
                    r.encoding = "utf-8"
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


def load_snapshot(d):
    """Cached NAVs for month-end `d`, or (None, None). Keyed by the nominal
    month-end so lookups are deterministic; the resolved trading day is inside."""
    p = NAV_CACHE / f"{d.isoformat()}.json"
    if not p.exists():
        return None, None
    try:
        j = json.loads(p.read_text(encoding="utf-8"))
        return date.fromisoformat(j["as_of"]), {int(k): v for k, v in j["navs"].items()}
    except Exception as e:
        print(f"    {d}  cache unreadable ({e}) — refetching")
        return None, None


def save_snapshot(d, actual, navs):
    NAV_CACHE.mkdir(parents=True, exist_ok=True)
    (NAV_CACHE / f"{d.isoformat()}.json").write_text(
        json.dumps({"as_of": actual.isoformat(), "navs": navs}, separators=(",", ":")),
        encoding="utf-8")


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
# EXPENSE RATIO (TER)
# ─────────────────────────────────────────────

# TER rows are keyed by NSDL scheme code and name the *base* scheme ("HDFC Flexi Cap
# Fund") while NAV rows name the plan+option ("HDFC Flexi Cap Fund - Direct - Growth"),
# and there is no shared identifier — so the join is by normalised name.
_PLAN_JUNK = re.compile(
    r"\b(direct|regular|growth|option|plan|payout|reinvestment|idcw|dividend|bonus|cumulative|and)\b")


def norm_name(n):
    n = n.lower().replace("income distribution cum capital withdrawal", " ").replace("&", " and ")
    n = re.sub(r"\(.*?\)", " ", n)          # "(erstwhile Bluechip Fund)"
    n = re.sub(r"[-–—]", " ", n)
    n = _PLAN_JUNK.sub(" ", n)
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def tight_name(n):
    """Space-insensitive fallback key with a trailing 'fund' dropped — catches
    'Flexicap' vs 'Flexi Cap' and 'Motilal Oswal Large Cap' vs '… Large Cap Fund'."""
    k = norm_name(n).replace(" ", "")
    return k[:-4] if k.endswith("fund") else k


MIN_TER_SCHEMES = 1500    # a complete month lists ~2,100; anything far below is part-published


def fetch_ter():
    """{normalised name: row} for the most recent COMPLETE month AMFI has published.

    The current month is skipped outright: AMCs file through the month, so on the 3rd
    it listed 808 schemes against July's 2,110 — taking it would have cut expense-ratio
    coverage from 96% to 38%. A month is only accepted once it looks fully populated.
    """
    today = date.today()
    fy = f"{today.year}-{today.year + 1}" if today.month >= 4 else f"{today.year - 1}-{today.year}"
    body = _get(TER_MONTHS.format(fy=fy), headers=TER_HEADERS)
    months = json.loads(body) if body else []
    if not months:
        print("   ! TER: no months listed for FY", fy)
        return {}, {}, None

    this_month = today.strftime("%m-%Y")
    months = [m for m in months if m.get("MonthNumber") != this_month]
    best = None                             # fall back to the fullest month seen
    for m in months:                        # newest first
        mn = m.get("MonthNumber")
        rows, page = {}, 1
        while True:
            body = _get(TER_DATA.format(m=mn, p=page), headers=TER_HEADERS)
            if not body:
                break
            j = json.loads(body)
            for r in j.get("data", []):
                k = r["NSDLSchemeCode"]     # keep the latest day in the month
                if k not in rows or r["TER_Date"] > rows[k]["TER_Date"]:
                    rows[k] = r
            meta = j.get("meta", {})
            if page >= meta.get("pageCount", 0):
                break
            page += 1
        if best is None or len(rows) > len(best[0]):
            best = (rows, m.get("MonthYear"))
        if len(rows) >= MIN_TER_SCHEMES:
            break
        print(f"   . TER: {m.get('MonthYear')} has only {len(rows)} schemes "
              f"(part-published) — trying the previous month")

    if not best or len(best[0]) < 200:
        return {}, {}, None
    rows, label = best
    by_norm, by_tight = {}, {}
    for r in rows.values():
        by_norm.setdefault(norm_name(r["Scheme_Name"]), r)
        by_tight.setdefault(tight_name(r["Scheme_Name"]), r)
    print(f"  TER: {len(rows)} schemes for {label}")
    return by_norm, by_tight, label


MAX_PLAUSIBLE_TER = 5.0   # SEBI caps the fee near 2.25%; see below


def ter_for(fund, by_norm, by_tight):
    """(expense ratio, all-in TER) for this fund's plan — None where unmatched.

    "Expense Ratio" is AMFI's Base Expense Ratio: the recurring fee SEBI caps and
    the number investors compare. The all-in TER adds brokerage, transaction cost
    and statutory levies, and AMFI annualises those over the reference period — on
    a fund that has only traded for days that produces nonsense (levies of 23% on
    one hybrid fund), so implausible all-in values are dropped rather than shown.
    """
    row = by_norm.get(norm_name(fund["name"])) or by_tight.get(tight_name(fund["name"]))
    if not row:
        return None, None
    p = "D" if plan_of(fund["name"]) == "Direct" else "R"

    def val(key, ceiling=None):
        try:
            v = float(row.get(key))
        except (TypeError, ValueError):
            return None
        if v <= 0 or (ceiling and v > ceiling):
            return None
        return round(v, 2)

    return val(f"{p}_BER"), val(f"{p}_TER", MAX_PLAUSIBLE_TER)


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
    cached = fetched = 0
    t0 = time.time()
    print(f"  {len(dates)} month-end snapshots needed…")
    for d in dates:
        actual, navs = load_snapshot(d)
        if navs:
            cached += 1
        else:
            if time.time() - t0 > MAX_FETCH_SECONDS:
                print(f"    {d}  SKIPPED — {MAX_FETCH_SECONDS}s fetch budget spent")
                continue
            actual, navs = fetch_month_end(d)
            if navs:
                fetched += 1
                # cache only the universe: the whole file is ~14k schemes, most of
                # which are payout variants and categories we never screen
                save_snapshot(d, actual, {c: navs[c] for c in universe if c in navs})
        if not navs:
            print(f"    {d}  MISS")
            continue
        got.append(actual)
        for code in universe:
            v = navs.get(code)
            if v:
                history.setdefault(code, {})[actual] = v
    print(f"  {cached} from cache, {fetched} fetched ({time.time() - t0:.0f}s)")
    print(f"  Got {len(got)} snapshots: {got[0]} … {got[-1]}" if got else "  No snapshots")
    if len(got) < 13:
        print("FATAL — too little history to compute returns; keeping previous output")
        return 1

    ter_norm, ter_tight, ter_month = fetch_ter()

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
        expense, all_in_ter = ter_for(f, ter_norm, ter_tight)

        rows.append({
            "Scheme Code": code,
            "Scheme Name": f["name"],
            "Fund House": f["amc"],
            "Category": f["category"],
            "Plan": plan_of(f["name"]),
            "NAV": round(latest, 4),
            "NAV Date": f["nav_date"],
            "Expense Ratio %": expense,
            "TER incl. Costs %": all_in_ter,
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
            "Expense Ratio %", "TER incl. Costs %",
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
        # force LF: csv defaults to CRLF, and git normalises that differently on
        # Windows and on the Linux runner, so every other run rewrote all 2,339 lines
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: r[c] for c in cols})

    with_3y = sum(1 for r in rows if r["3Y CAGR %"] is not None)
    with_ter = sum(1 for r in rows if r["Expense Ratio %"] is not None)
    print(f"\n[ok] {len(rows)} funds → {OUT_JSON}")
    print(f"     {with_3y} with a 3Y CAGR · NAV as of {rows[0]['NAV Date'] if rows else '?'}")
    print(f"     {with_ter} with an expense ratio ({with_ter / len(rows) * 100:.1f}%)"
          f"{f' · TER month {ter_month}' if ter_month else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
