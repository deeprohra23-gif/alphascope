// Cloudflare Pages Function → serves at  /api/stock?symbol=RELIANCE
//
// This is the ENTIRE "backend" the static app needs. It runs only when a user opens a
// stock card and clicks "Load live" — the other ~95% of the app is pure static JSON.
// Free tier: Cloudflare Workers = 100,000 requests/day free. Deploys automatically when
// you push the static-aggrid folder to Cloudflare Pages. (Vercel/Netlify equivalents are
// nearly identical — export a default handler.)
//
// Mirrors the 3 live features in the Streamlit app:
//   • Stock Card financials + news   (yfinance)
//   • SIP Calculator price history   (yfinance)
//   • Events tab                     (NSE)
// Here we proxy Yahoo's public quote endpoint as a minimal, dependency-free example.

export async function onRequest(context) {
  const url = new URL(context.request.url);
  const symbol = url.searchParams.get('symbol');
  if (!symbol) return json({ error: 'symbol required' }, 400);

  // Yahoo uses .NS suffix for NSE listings
  const yhoo = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}.NS?range=1y&interval=1mo`;

  try {
    const res = await fetch(yhoo, { headers: { 'User-Agent': 'Mozilla/5.0' } });
    if (!res.ok) return json({ error: 'upstream', status: res.status }, 502);
    const data = await res.json();
    const r = data?.chart?.result?.[0];
    const closes = (r?.indicators?.quote?.[0]?.close || []).filter(v => v != null);
    return json({
      symbol,
      currency: r?.meta?.currency,
      regularMarketPrice: r?.meta?.regularMarketPrice,
      fiftyTwoWeekHigh: r?.meta?.fiftyTwoWeekHigh,
      fiftyTwoWeekLow: r?.meta?.fiftyTwoWeekLow,
      monthlyCloses: closes.slice(-12),   // enough to drive the SIP calculator
    }, 200, 300); // cache 5 min at the edge — cuts upstream calls dramatically
  } catch (e) {
    return json({ error: String(e) }, 500);
  }
}

function json(body, status = 200, maxAge = 0) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'content-type': 'application/json',
      'cache-control': maxAge ? `public, max-age=${maxAge}` : 'no-store',
      'access-control-allow-origin': '*',
    },
  });
}
