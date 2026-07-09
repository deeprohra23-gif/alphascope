// Cloudflare Worker entry point.
// Routes /api/* to the function handlers in functions/api/*; everything else is served
// from the static assets (public/) via the ASSETS binding.
// (This is the Workers-with-static-assets equivalent of Pages Functions — same handler code.)
import { onRequest as stock } from "./functions/api/stock.js";
import { onRequest as history } from "./functions/api/history.js";
import { onRequest as financials } from "./functions/api/financials.js";
import { onRequest as news } from "./functions/api/news.js";
import { onRequest as fiidii } from "./functions/api/fiidii.js";
import { onRequest as deals } from "./functions/api/deals.js";
import { onRequest as corpactions } from "./functions/api/corpactions.js";

const routes = {
  "/api/stock": stock,
  "/api/history": history,
  "/api/financials": financials,
  "/api/news": news,
  "/api/fiidii": fiidii,
  "/api/deals": deals,
  "/api/corpactions": corpactions,
};

// Edge-cache TTL (seconds) per endpoint — protects Yahoo/NSE upstreams under traffic and speeds up repeat hits.
const API_TTL = {
  "/api/history": 21600,     // 6h — monthly price history barely changes intraday
  "/api/financials": 3600,   // 1h — fundamentals timeseries
  "/api/corpactions": 3600,  // 1h — daily NSE feed
  "/api/fiidii": 1800,       // 30m — daily NSE feed
  "/api/deals": 1800,        // 30m — daily NSE feed
  "/api/news": 900,          // 15m — headlines
  "/api/stock": 300,         // 5m — live-ish quote
};

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const { pathname } = url;
    const handler = routes[pathname];
    if (handler) {
      const ttl = API_TTL[pathname] || 0;
      const cacheable = request.method === "GET" && ttl > 0;
      const cacheKey = new Request(url.toString(), { method: "GET" });
      if (cacheable) {
        const hit = await caches.default.match(cacheKey);
        if (hit) return hit;   // edge cache hit — upstream never touched
      }
      // hand the same context shape the Pages Functions expect
      const res = await handler({ request, env, ctx, waitUntil: (p) => ctx.waitUntil(p), next: () => env.ASSETS.fetch(request) });
      if (cacheable && res && res.status === 200) {
        const h = new Headers(res.headers);
        h.set("Cache-Control", `public, max-age=${ttl}, s-maxage=${ttl}`);
        const out = new Response(res.body, { status: res.status, statusText: res.statusText, headers: h });
        ctx.waitUntil(caches.default.put(cacheKey, out.clone()));   // store a copy; return the original
        return out;
      }
      return res;
    }
    // serve static assets — but force code files to revalidate so deploys show up on a normal refresh
    const res = await env.ASSETS.fetch(request);
    if (pathname === '/' || /\.(html|js|css)$/.test(pathname)) {
      const h = new Headers(res.headers);
      h.set('Cache-Control', 'no-cache');
      return new Response(res.body, { status: res.status, statusText: res.statusText, headers: h });
    }
    return res;
  },
};
