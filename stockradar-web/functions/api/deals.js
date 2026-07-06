// /api/deals → today's bulk & block deals. Mirrors nsepython get_bulkdeals()/get_blockdeals().
import { nseFetch, json } from '../_nse.js';

export async function onRequest() {
  try {
    const data = await nseFetch('https://www.nseindia.com/api/snapshot-capital-market-largedeal');
    return json({
      asOn: data.as_on_date || null,
      bulk: data.BULK_DEALS_DATA || [],
      block: data.BLOCK_DEALS_DATA || [],
    }, 200, 900);
  } catch (e) {
    return json({ error: String(e), bulk: [], block: [] }, 502);
  }
}
