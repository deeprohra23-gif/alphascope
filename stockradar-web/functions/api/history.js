// /api/history?symbol=RELIANCE&years=5  → monthly adjusted-close series for the SIP calculator.
import { json } from '../_nse.js';

export async function onRequest(context) {
  const url = new URL(context.request.url);
  const symbol = url.searchParams.get('symbol');
  const years = Math.min(10, Math.max(1, parseInt(url.searchParams.get('years') || '5', 10)));
  if (!symbol) return json({ error: 'symbol required' }, 400);
  const y = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}.NS?range=${years}y&interval=1mo`;
  try {
    const res = await fetch(y, { headers: { 'User-Agent': 'Mozilla/5.0' } });
    if (!res.ok) return json({ error: 'upstream', status: res.status }, 502);
    const data = await res.json();
    const r = data?.chart?.result?.[0];
    if (!r) return json({ error: 'no data' }, 404);
    const ts = r.timestamp || [];
    const closes = r.indicators?.quote?.[0]?.close || [];
    const adj = r.indicators?.adjclose?.[0]?.adjclose || closes;
    const points = ts.map((t, i) => ({ t, c: adj[i] ?? closes[i] })).filter(p => p.c != null);
    return json({ symbol, currency: r.meta?.currency, points }, 200, 3600);
  } catch (e) {
    return json({ error: String(e) }, 500);
  }
}
