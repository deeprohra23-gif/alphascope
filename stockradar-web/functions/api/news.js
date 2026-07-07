// /api/news?q=Reliance Industries → recent India-market news via Google News RSS.
import { json } from '../_nse.js';

export async function onRequest(context) {
  const url = new URL(context.request.url);
  const q = url.searchParams.get('q');
  if (!q) return json({ error: 'q required', items: [] }, 400);
  const u = `https://news.google.com/rss/search?q=${encodeURIComponent(q + ' share')}&hl=en-IN&gl=IN&ceid=IN:en`;
  try {
    const r = await fetch(u, { headers: { 'User-Agent': 'Mozilla/5.0' } });
    if (!r.ok) return json({ error: 'upstream', status: r.status, items: [] }, 502);
    const xml = await r.text();
    const clean = s => (s || '').replace(/<!\[CDATA\[|\]\]>/g, '').replace(/&amp;/g, '&').replace(/&#39;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').trim();
    const items = [...xml.matchAll(/<item>([\s\S]*?)<\/item>/g)].slice(0, 10).map(m => {
      const b = m[1], g = re => { const mm = re.exec(b); return mm ? mm[1] : ''; };
      return {
        title: clean(g(/<title>([\s\S]*?)<\/title>/)),
        link: clean(g(/<link>([\s\S]*?)<\/link>/)),
        source: clean(g(/<source[^>]*>([\s\S]*?)<\/source>/)),
        pub: clean(g(/<pubDate>([\s\S]*?)<\/pubDate>/)),
      };
    });
    return json({ items }, 200, 1800);  // cache 30 min
  } catch (e) {
    return json({ error: String(e), items: [] }, 500);
  }
}
