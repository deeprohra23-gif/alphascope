"""
run_daily.py
Orchestrator that runs all three daily data scripts in sequence,
then optionally commits and pushes to GitHub.

Usage:
    python scripts/run_daily.py              # fetch only
    python scripts/run_daily.py --push       # fetch + git push
"""

import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parent


def run_script(name):
    script = SCRIPTS_DIR / name
    print(f"\n{'=' * 60}")
    print(f"Running {name}...")
    print(f"{'=' * 60}\n")

    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(SCRIPTS_DIR),
    )

    if result.returncode != 0:
        print(f"\n⚠️  {name} exited with code {result.returncode}")
        return False
    return True


def git_push():
    data_dir = ROOT / "data"
    files = ["technicals.csv", "indices_technicals.csv", "global_technicals.csv"]
    existing = [str(data_dir / f) for f in files if (data_dir / f).exists()]

    if not existing:
        print("No data files to push.")
        return

    print(f"\n{'=' * 60}")
    print("Pushing to GitHub...")
    print(f"{'=' * 60}\n")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    subprocess.run(["git", "add"] + existing, cwd=str(ROOT))
    subprocess.run(
        ["git", "commit", "-m", f"Daily data update {timestamp}"],
        cwd=str(ROOT),
    )
    subprocess.run(["git", "push"], cwd=str(ROOT))
    print("✅ Pushed to GitHub")


def main():
    parser = argparse.ArgumentParser(description="Run daily data pipeline")
    parser.add_argument("--push", action="store_true", help="Git commit & push after fetch")
    parser.add_argument("--skip-stocks", action="store_true", help="Skip stock technicals")
    parser.add_argument("--skip-indices", action="store_true", help="Skip index technicals")
    parser.add_argument("--skip-global", action="store_true", help="Skip global technicals")
    args = parser.parse_args()

    start = datetime.now()
    print(f"StockRadar Daily Pipeline — {start.strftime('%Y-%m-%d %H:%M:%S')}")

    # Run in order: global (fast) → indices (slow download) → stocks (slowest)
    if not args.skip_global:
        run_script("fetch_global.py")

    if not args.skip_indices:
        run_script("fetch_indices.py")

    if not args.skip_stocks:
        run_script("fetch_technicals.py")

    elapsed = (datetime.now() - start).total_seconds()
    print(f"\n{'=' * 60}")
    print(f"Pipeline complete in {elapsed / 60:.1f} minutes")
    print(f"{'=' * 60}")

    if args.push:
        git_push()


if __name__ == "__main__":
    main()
