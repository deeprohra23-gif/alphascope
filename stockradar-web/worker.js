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

export default {
  async fetch(request, env, ctx) {
    const { pathname } = new URL(request.url);
    const handler = routes[pathname];
    if (handler) {
      // hand the same context shape the Pages Functions expect
      return handler({ request, env, ctx, waitUntil: (p) => ctx.waitUntil(p), next: () => env.ASSETS.fetch(request) });
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
