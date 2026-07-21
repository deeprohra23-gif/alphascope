"""
fetch_fiidii.py
Fetches today's FII/DII provisional cash-market figures from NSE and APPENDS
them to public/data/fiidii.json, keeping a rolling window of recent days so the
website can show a multi-day history.

Best-effort: any failure leaves the existing archive untouched (never crashes
the pipeline). Run daily from the GitHub Action after the main build.
"""

import json
import time
from pathlib import Path

import requests

OUT = Path(__file__).resolve().parent.parent / "public" / "data" / "fiidii.json"
KEEP_DAYS = 10

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.nseindia.com/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}
API = "https://www.nseindia.com/api/fiidiiTradeReact"


def fetch_rows():
    s = requests.Session()
    # prime cookies
    try:
        s.get("https://www.nseindia.com", headers=HEADERS, timeout=15)
        time.sleep(1)
    except Exception:
        pass
    r = s.get(API, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()


def num(v):
    try:
        return round(float(str(v).replace(",", "")), 2)
    except Exception:
        return None


def to_day(rows):
    """NSE returns one FII row + one DII row for the latest date."""
    def pick(key):
        for row in rows:
            if key in (row.get("category") or ""):
                return row
        return {}
    fii = pick("FII") or pick("FPI")
    dii = pick("DII")
    date = fii.get("date") or dii.get("date")
    if not date:
        return None
    return {
        "date": date,
        "fii": {"buy": num(fii.get("buyValue")), "sell": num(fii.get("sellValue")), "net": num(fii.get("netValue"))},
        "dii": {"buy": num(dii.get("buyValue")), "sell": num(dii.get("sellValue")), "net": num(dii.get("netValue"))},
    }


def main():
    try:
        day = to_day(fetch_rows())
    except Exception as e:
        print(f"[fiidii] fetch failed ({e}); leaving archive unchanged")
        return
    if not day:
        print("[fiidii] no usable rows; leaving archive unchanged")
        return

    archive = []
    if OUT.exists():
        try:
            archive = json.loads(OUT.read_text())
            if not isinstance(archive, list):
                archive = []
        except Exception:
            archive = []

    # upsert by date, keep chronological, cap window
    by_date = {d["date"]: d for d in archive if isinstance(d, dict) and "date" in d}
    by_date[day["date"]] = day
    merged = sorted(by_date.values(), key=lambda d: d["date"])[-KEEP_DAYS:]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(merged, ensure_ascii=False))
    print(f"[fiidii] archived {day['date']} — {len(merged)} day(s) in {OUT.name}")


if __name__ == "__main__":
    main()
