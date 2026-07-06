# Deploy StockRadar-web (free, always-on)

The app is a **static site** (`public/`) + a few **serverless functions** (`functions/`). Cloudflare
Pages hosts both for free with no cold starts. Everything flows through GitHub, exactly like your
current Streamlit Cloud setup.

## The picture
```
Daily GitHub Action (Mon–Fri)
  fetch_technicals/indices/global.py        (unchanged — produces data/*.csv)
  → python stockradar-web/scripts/build_data.py   (reuses scoring/insights/screens/history → public/data/*.json)
  → git commit + push
        │
        └─►  Cloudflare Pages auto-builds & deploys on push.  Live URL updates. No cold starts.
```

## One-time setup (the parts only you can do)

### 1. Put stockradar-web inside your repo
Move the `stockradar-web/` folder into the **StockRadar-India** repo root and push it. (It needs to sit
alongside `scoring.py`, `insights.py`, `data/`, etc. so the build step can import them.)

### 2. Wire the daily build
Replace your existing `.github/workflows/daily_update.yml` with [`deploy/daily_update.yml`](deploy/daily_update.yml)
— it's your current workflow plus one step (`build_data.py`) and `stockradar-web/public/data/` added to
the commit. No new dependencies (your `requirements-scripts.txt` already has pandas + numpy).

Then run it once manually: GitHub → **Actions → Daily Data Update → Run workflow**. This generates and
commits `stockradar-web/public/data/*.json`.

### 3. Connect Cloudflare Pages (free account)
1. Sign in at **dash.cloudflare.com** → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**.
2. Pick the **StockRadar-India** repo.
3. Build settings:
   - **Framework preset:** None
   - **Build command:** *(leave empty — data is prebuilt and committed)*
   - **Build output directory:** `stockradar-web/public`
   - **Root directory:** `/` (repo root, so `functions/` is found — see note below)
4. Deploy. You get a `*.pages.dev` URL. Every push redeploys automatically.

> **Functions path note:** Cloudflare Pages looks for `functions/` at the *project root directory* you
> set. Since the output dir is `stockradar-web/public`, set the **Root directory** to `stockradar-web`
> so both `public/` and `functions/` are found. (Output dir then becomes just `public`.)

That's it — free tier is always-on (no Render-style sleep), Workers give 100k function requests/day free.

## Local development
```bash
python scripts/build_data.py      # rebuild data (needs the StockRadar repo alongside; or set STOCKRADAR_REPO)
node dev-server.mjs               # → http://localhost:5056  (serves public/ AND runs functions/ locally)
```

## What runs where
- **~95% static**: dashboards, tables, screens, compare, watchlist, methodology — pure JSON, no server.
- **Serverless functions** (`functions/api/*`): only the live bits —
  - `history` → Yahoo monthly prices (SIP calculator)
  - `fiidii`, `deals`, `corpactions` → NSE (Events tab)
- **Note:** NSE may throttle/deny some datacenter IPs. If Events fails after deploy while working
  locally, that's NSE rate-limiting the Cloudflare IP, not the app — the UI degrades gracefully with a message.

## Alternatives (also free)
Vercel or Netlify work the same way — point at the repo, set output dir to `stockradar-web/public`,
and port the functions (Vercel: `api/` dir with `export default handler`; Cloudflare's `onRequest` is nearly identical).
