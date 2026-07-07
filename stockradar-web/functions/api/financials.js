// /api/financials?symbol=RELIANCE → multi-year annual financials from Yahoo's
// fundamentals-timeseries (revenue, net income, EPS, EBITDA, EBIT, interest, debt,
// equity, cash, FCF). The client aligns by fiscal year and computes projections.
import { json } from '../_nse.js';

const TYPES = [
  'annualTotalRevenue', 'annualNetIncome', 'annualBasicEPS', 'annualEBITDA', 'annualEBIT',
  'annualInterestExpense', 'annualTotalDebt', 'annualStockholdersEquity',
  'annualCashAndCashEquivalents', 'annualFreeCashFlow',
];

export async function onRequest(context) {
  const url = new URL(context.request.url);
  const base = (url.searchParams.get('symbol') || '').replace(/\.(NS|BO)$/i, '');
  if (!base) return json({ error: 'symbol required' }, 400);
  const now = Math.floor(Date.now() / 1000), p1 = now - 8 * 365 * 86400;
  const u = `https://query1.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/${encodeURIComponent(base)}.NS?type=${TYPES.join(',')}&period1=${p1}&period2=${now}&merge=false`;
  try {
    const r = await fetch(u, { headers: { 'User-Agent': 'Mozilla/5.0' } });
    if (!r.ok) return json({ error: 'upstream', status: r.status }, 502);
    const jj = await r.json();
    const series = jj?.timeseries?.result || [];
    const out = {};
    for (const s of series) {
      const t = s?.meta?.type?.[0]; if (!t) continue;
      out[t] = (s[t] || []).filter(Boolean).map(v => ({ d: v.asOfDate, v: v.reportedValue?.raw ?? null }));
    }
    return json({ symbol: base, series: out }, 200, 86400);  // cache 1 day at the edge
  } catch (e) {
    return json({ error: String(e) }, 500);
  }
}
