// Local dev server: serves public/ AND executes Cloudflare Pages Functions in functions/
// so /api/* works locally exactly as it will on Cloudflare Pages.  node dev-server.mjs → :5056
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(HERE, 'public');
const FNS = path.join(HERE, 'functions');
const PORT = process.env.PORT || 5056;
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.md': 'text/markdown', '.svg': 'image/svg+xml', '.ico': 'image/x-icon', '.png': 'image/png' };

http.createServer(async (req, res) => {
  const p = decodeURIComponent(req.url.split('?')[0]);

  // /api/* → functions/api/<name>.js  (Cloudflare Pages Functions, run locally)
  if (p.startsWith('/api/')) {
    const fnPath = path.join(FNS, p + '.js');
    if (!fnPath.startsWith(FNS) || !fs.existsSync(fnPath)) { res.writeHead(404); return res.end('no function'); }
    try {
      const mod = await import(pathToFileURL(fnPath).href + '?t=' + fs.statSync(fnPath).mtimeMs);
      const handler = mod.onRequest || mod.onRequestGet || mod.default;
      const request = new Request('http://localhost' + req.url, { method: req.method, headers: req.headers });
      const response = await handler({ request, env: {}, params: {}, waitUntil() { }, next() { } });
      res.writeHead(response.status, Object.fromEntries(response.headers));
      res.end(Buffer.from(await response.arrayBuffer()));
    } catch (e) {
      res.writeHead(500, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ error: String(e) }));
    }
    return;
  }

  // static
  let f = path.join(ROOT, p === '/' ? '/index.html' : p);
  if (!f.startsWith(ROOT) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end('not found'); }
  const st = fs.statSync(f);
  res.writeHead(200, { 'content-type': TYPES[path.extname(f)] || 'application/octet-stream', 'last-modified': st.mtime.toUTCString(), 'cache-control': 'no-cache' });
  if (req.method === 'HEAD') return res.end();
  fs.createReadStream(f).pipe(res);
}).listen(PORT, () => console.log(`stockradar-web on http://localhost:${PORT} (static + /api functions)`));
