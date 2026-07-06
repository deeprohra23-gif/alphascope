// Shared NSE fetch helper (underscore prefix = not a route).
// NSE requires priming a cookie from the homepage before hitting its /api endpoints.
// Note: may be blocked on some server IPs (Cloudflare Workers). UI degrades gracefully.
const UA = {
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
  'Accept': '*/*', 'Accept-Language': 'en-US,en;q=0.9',
};

export async function nseFetch(apiUrl) {
  const home = await fetch('https://www.nseindia.com/', { headers: UA });
  const raw = home.headers.getSetCookie ? home.headers.getSetCookie() : [home.headers.get('set-cookie')];
  const cookie = raw.filter(Boolean).map(c => c.split(';')[0]).join('; ');
  const res = await fetch(apiUrl, { headers: { ...UA, Referer: 'https://www.nseindia.com/', Cookie: cookie } });
  if (!res.ok) throw new Error('NSE ' + res.status);
  return res.json();
}

export function json(body, status = 200, maxAge = 0) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'content-type': 'application/json',
      'cache-control': maxAge ? `public, max-age=${maxAge}` : 'no-store',
      'access-control-allow-origin': '*',
    },
  });
}
