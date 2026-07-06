// /api/fiidii → FII/DII trade activity (today). Mirrors nsepython nse_fiidii().
import { nseFetch, json } from '../_nse.js';

export async function onRequest() {
  try {
    const data = await nseFetch('https://www.nseindia.com/api/fiidiiTradeReact');
    return json({ rows: data }, 200, 900);
  } catch (e) {
    return json({ error: String(e), rows: [] }, 502);
  }
}
