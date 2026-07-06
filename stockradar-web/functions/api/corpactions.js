// /api/corpactions → corporate actions (dividends, splits, bonus, etc.) for the current year.
import { nseFetch, json } from '../_nse.js';

export async function onRequest(context) {
  const url = new URL(context.request.url);
  const y = new Date().getFullYear();
  const from = url.searchParams.get('from') || `01-01-${y}`;
  const to = url.searchParams.get('to') || `31-12-${y}`;
  try {
    const data = await nseFetch(`https://www.nseindia.com/api/corporates-corporateActions?index=equities&from_date=${from}&to_date=${to}`);
    return json({ rows: data }, 200, 3600);
  } catch (e) {
    return json({ error: String(e), rows: [] }, 502);
  }
}
