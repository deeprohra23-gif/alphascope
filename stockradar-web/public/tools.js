// tools.js — Phase 4 (Tools): Stock Card selector, Compare, Watchlist (localStorage), Methodology.
// SIP Calculator ships next with Events (both need the live serverless data layer).
(function () {
  let inited = false, cmpList = [], wlList = [], sipList = [];
  const WL_KEY = 'sr_watchlist';
  const $ = id => document.getElementById(id);
  const f = (v, d = 2) => (v == null || v === '' || isNaN(v)) ? '—' : Number(v).toFixed(d);
  const bySym = s => (window.ALL || []).find(r => r.Symbol === s);

  window.initTools = async function () {
    if (inited) return;
    try { await ensureData(); } catch (e) { return; }
    inited = true;
    const opts = '<option value="">Select a stock…</option>' +
      window.ALL.slice().sort((a, b) => a.Name.localeCompare(b.Name)).map(r => `<option value="${r.Symbol}">${window.tk(r.Symbol)} — ${r.Name}</option>`).join('');
    ['cardSelect', 'cmpAdd', 'wlAdd', 'sipAdd'].forEach(id => $(id).innerHTML = opts);
    $('sipDur').innerHTML = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(y => `<option value="${y}"${y === 5 ? ' selected' : ''}>${y}Y</option>`).join('');
    try { wlList = JSON.parse(localStorage.getItem(WL_KEY)) || []; } catch (e) { wlList = []; }

    $('toolsub').addEventListener('click', e => {
      const b = e.target.closest('.sub'); if (!b) return;
      document.querySelectorAll('#toolsub .sub').forEach(x => x.classList.toggle('active', x === b));
      document.querySelectorAll('.tsec').forEach(p => { p.hidden = p.dataset.tsec !== b.dataset.tsub; });
      if (b.dataset.tsub === 'method') renderMethod();
    });

    // Stock Card
    $('cardSelect').addEventListener('change', e => { const r = bySym(e.target.value); if (r && window.openPanel) window.openPanel(r); });
    // Compare
    $('cmpAdd').addEventListener('change', e => { const s = e.target.value; if (s && !cmpList.includes(s) && cmpList.length < 4) cmpList.push(s); e.target.value = ''; renderCompare(); });
    // Watchlist
    $('wlAdd').addEventListener('change', e => { const s = e.target.value; if (s && !wlList.includes(s)) { wlList.push(s); saveWL(); } e.target.value = ''; renderWatchlist(); });
    $('wlClear').addEventListener('click', () => { wlList = []; saveWL(); renderWatchlist(); });
    // SIP
    $('sipAdd').addEventListener('change', e => { const s = e.target.value; if (s && !sipList.includes(s) && sipList.length < 10) sipList.push(s); e.target.value = ''; renderSipChips(); });
    $('sipRun').addEventListener('click', runSip);

    renderCompare(); renderWatchlist(); renderSipChips();
  };

  // ── SIP Calculator (serverless price history + JS XIRR) ──
  function renderSipChips() {
    $('sipChips').innerHTML = sipList.map(s => { const r = bySym(s); return `<span class="cmp-chip" title="${r ? r.Name : ''}"><b>${window.tk(s)}</b><span class="x" data-s="${s}">✕</span></span>`; }).join('');
    $('sipChips').querySelectorAll('.x').forEach(x => x.onclick = () => { sipList = sipList.filter(s => s !== x.dataset.s); renderSipChips(); });
  }
  function xirr(cf) {
    if (cf.length < 2) return null;
    const t0 = cf[0].date, yr = 365.25 * 86400;
    const npv = rate => cf.reduce((s, c) => s + c.amount / Math.pow(1 + rate, (c.date - t0) / yr), 0);
    let lo = -0.9999, hi = 10, flo = npv(lo), fhi = npv(hi);
    if (flo * fhi > 0) return null;
    for (let i = 0; i < 200; i++) { const mid = (lo + hi) / 2, fm = npv(mid); if (Math.abs(fm) < 1e-4) return mid; if (flo * fm < 0) { hi = mid; fhi = fm; } else { lo = mid; flo = fm; } }
    return (lo + hi) / 2;
  }
  function simulate(points, amount) {
    const pts = points.filter(p => p.c > 0);
    if (pts.length < 2) return null;
    let units = 0; const cf = [];
    pts.forEach(p => { units += amount / p.c; cf.push({ amount: -amount, date: p.t }); });
    const cmp = pts[pts.length - 1].c, value = units * cmp, invested = amount * pts.length;
    cf.push({ amount: value, date: pts[pts.length - 1].t });
    const rets = []; for (let i = 1; i < pts.length; i++) rets.push(pts[i].c / pts[i - 1].c - 1);
    const mean = rets.reduce((a, b) => a + b, 0) / rets.length;
    const vol = Math.sqrt(rets.reduce((a, b) => a + (b - mean) ** 2, 0) / rets.length) * Math.sqrt(12) * 100;
    let peak = pts[0].c, mdd = 0; pts.forEach(p => { if (p.c > peak) peak = p.c; const dd = (p.c - peak) / peak * 100; if (dd < mdd) mdd = dd; });
    const x = xirr(cf);
    return { invested, value, units, avgCost: invested / units, cmp, ret: (value - invested) / invested * 100, xirr: x != null ? x * 100 : null, maxDD: mdd, vol, best: Math.max(...rets) * 100, worst: Math.min(...rets) * 100, months: pts.length, cf };
  }
  async function runSip() {
    if (!sipList.length) { $('sipOut').innerHTML = '<p class="empty" style="margin:12px 16px">Add at least one stock.</p>'; return; }
    const amount = Math.max(100, +$('sipAmt').value || 5000), years = +$('sipDur').value;
    $('sipOut').innerHTML = '<p class="empty" style="margin:12px 16px">Fetching price history…</p>';
    const results = [];
    for (const sym of sipList) {
      const name = (bySym(sym) || {}).Name || sym;
      try {
        const base = sym.replace(/\.NS$/, '');
        const d = await fetch(`/api/history?symbol=${encodeURIComponent(base)}&years=${years}`).then(r => r.json());
        const sim = d.points ? simulate(d.points, amount) : null;
        results.push({ sym, name, sim });
      } catch (e) { results.push({ sym, name, sim: null }); }
    }
    renderSip(results, amount, years);
  }
  function renderSip(results, amount, years) {
    const ok = results.filter(r => r.sim);
    if (!ok.length) { $('sipOut').innerHTML = '<p class="empty" style="margin:12px 16px">No price history available (needs the serverless function — deploy, or run the dev server).</p>'; return; }
    const inv = ok.reduce((s, r) => s + r.sim.invested, 0), val = ok.reduce((s, r) => s + r.sim.value, 0);
    const allCf = []; ok.forEach(r => r.sim.cf.forEach(c => allCf.push(c)));
    allCf.sort((a, b) => a.date - b.date);
    const px = xirr(allCf);
    const cards = [['Invested', '₹' + Math.round(inv).toLocaleString('en-IN')], ['Value', '₹' + Math.round(val).toLocaleString('en-IN')],
      ['Return', ((val - inv) / inv * 100).toFixed(1) + '%'], ['Portfolio XIRR', px != null ? (px * 100).toFixed(1) + '%' : '—']];
    let h = '<div class="wl-summary">' + cards.map(([l, v]) => `<div class="wl-stat"><div class="v ${l === 'Return' && val < inv ? 'neg' : ''}">${v}</div><div class="l">${l}</div></div>`).join('') + '</div>';
    h += '<div class="cmp-table-wrap"><table class="cmp-table"><thead><tr><th>Stock</th><th>Invested</th><th>Value</th><th>Return</th><th>XIRR</th><th>Avg Cost</th><th>CMP</th><th>Max DD</th><th>Volatility</th><th>Months</th></tr></thead><tbody>';
    for (const r of ok) { const s = r.sim; h += `<tr><td><span class="tk">${window.tk(r.sym)}</span> <span class="nm">${r.name}</span></td><td>₹${Math.round(s.invested).toLocaleString('en-IN')}</td><td>₹${Math.round(s.value).toLocaleString('en-IN')}</td><td class="${s.ret >= 0 ? 'pos' : 'neg'}">${s.ret.toFixed(1)}%</td><td>${s.xirr != null ? s.xirr.toFixed(1) + '%' : '—'}</td><td>₹${s.avgCost.toFixed(2)}</td><td>₹${s.cmp.toFixed(2)}</td><td class="neg">${s.maxDD.toFixed(1)}%</td><td>${s.vol.toFixed(1)}%</td><td>${s.months}</td></tr>`; }
    const failed = results.filter(r => !r.sim).map(r => r.name);
    h += `<tr class="cmp-sec"><td>Portfolio</td><td>₹${Math.round(inv).toLocaleString('en-IN')}</td><td>₹${Math.round(val).toLocaleString('en-IN')}</td><td class="${val >= inv ? 'pos' : 'neg'}">${((val - inv) / inv * 100).toFixed(1)}%</td><td>${px != null ? (px * 100).toFixed(1) + '%' : '—'}</td><td colspan="4"></td></tr>`;
    h += '</tbody></table></div>';
    if (failed.length) h += `<p class="empty" style="margin:8px 16px">No data for: ${failed.join(', ')}</p>`;
    $('sipOut').innerHTML = h;
  }

  // ── Compare ──
  const CMP = [
    ['section', 'Overview'],
    ['Current Price', 'Current Price', 'none', 2], ['Day Change %', 'Day Change %', 'high', 2],
    ['Market Cap (Cr)', 'Market Cap (Cr)', 'high', 0], ['Sector', 'Sector', 'txt'], ['Industry', 'Industry', 'txt'], ['Market Regime', 'Market Regime', 'txt'],
    ['section', 'Insights & Scores'],
    ['Technical Insight', 'Technical Insight', 'txt'], ['Fundamental Insight', 'Fundamental Insight', 'txt'],
    ['Composite Score', 'Composite Score', 'high', 1], ['Technical Score', 'Technical Score', 'high', 1], ['Momentum Score', 'Momentum Score', 'high', 1], ['Fundamental Score', 'Fundamental Score', 'high', 1],
    ['section', 'Technicals'],
    ['RSI 14', 'RSI 14', 'none', 1], ['MACD Signal', 'MACD Signal', 'txt'], ['Supertrend', 'Supertrend', 'txt'], ['EMA Cross', 'EMA Cross', 'txt'],
    ['section', 'Returns'],
    ['ROC 1M %', 'ROC 1M %', 'high', 2], ['ROC 3M %', 'ROC 3M %', 'high', 2], ['ROC 6M %', 'ROC 6M %', 'high', 2], ['ROC 12M %', 'ROC 12M %', 'high', 2],
    ['1Y CAGR %', '1Y CAGR %', 'high', 2], ['3Y CAGR %', '3Y CAGR %', 'high', 2],
    ['RS vs Nifty 3M %', 'RS vs Nifty 3M %', 'high', 2], ['RS vs Nifty 12M %', 'RS vs Nifty 12M %', 'high', 2],
    ['section', 'Risk'],
    ['Beta 1Y (Daily)', 'Beta 1Y (Daily)', 'none', 2], ['SD 1Y %', 'SD 1Y %', 'low', 2], ['1Y Max Drawdown %', '1Y Max Drawdown %', 'high', 2],
    ['section', 'Fundamentals'],
    ['PE Ratio', 'PE Ratio', 'low', 1], ['PB Ratio', 'PB Ratio', 'low', 1], ['EV/EBITDA', 'EV/EBITDA', 'low', 1], ['PEG Ratio', 'PEG Ratio', 'low', 2],
    ['ROE %', 'ROE %', 'high', 1], ['ROCE %', 'ROCE %', 'high', 1], ['Net Profit Margin %', 'Net Profit Margin %', 'high', 1],
    ['Sales Growth 3Y %', 'Sales Growth 3Y %', 'high', 1], ['Profit Growth 3Y %', 'Profit Growth 3Y %', 'high', 1],
    ['Debt/Equity', 'Debt/Equity', 'low', 2], ['Dividend Yield %', 'Dividend Yield %', 'high', 2], ['Dividend Payout %', 'Dividend Payout %', 'none', 1],
    ['Promoter Holding %', 'Promoter Holding %', 'high', 1],
  ];
  function renderCompare() {
    $('cmpChips').innerHTML = cmpList.map(s => { const r = bySym(s); return `<span class="cmp-chip" title="${r ? r.Name : ''}"><b>${window.tk(s)}</b><span class="x" data-s="${s}">✕</span></span>`; }).join('');
    $('cmpChips').querySelectorAll('.x').forEach(x => x.onclick = () => { cmpList = cmpList.filter(s => s !== x.dataset.s); renderCompare(); });
    const stocks = cmpList.map(bySym).filter(Boolean);
    if (stocks.length < 2) { $('cmpTable').innerHTML = '<p class="empty" style="margin:12px 16px">Add at least 2 stocks to compare.</p>'; return; }
    let h = '<table class="cmp-table"><thead><tr><th>Metric</th>' + stocks.map(s => `<th title="${s.Name}">${window.tk(s.Symbol)}</th>`).join('') + '</tr></thead><tbody>';
    for (const rw of CMP) {
      if (rw[0] === 'section') { h += `<tr class="cmp-sec"><td colspan="${stocks.length + 1}">${rw[1]}</td></tr>`; continue; }
      const [label, field, dir, dec] = rw, vals = stocks.map(s => s[field]);
      let best = -1;
      if (dir === 'high' || dir === 'low') {
        const nums = vals.map(v => typeof v === 'number' ? v : NaN), valid = nums.filter(v => !isNaN(v));
        if (valid.length) best = nums.indexOf(dir === 'high' ? Math.max(...valid) : Math.min(...valid));
      }
      h += `<tr><td class="cmp-label">${label}</td>` + vals.map((v, i) =>
        `<td class="${i === best ? 'cmp-best' : ''}">${dir === 'txt' ? (v ?? '—') : f(v, dec)}</td>`).join('') + '</tr>';
    }
    $('cmpTable').innerHTML = h + '</tbody></table>';
  }

  // ── Watchlist (localStorage) ──
  function saveWL() { try { localStorage.setItem(WL_KEY, JSON.stringify(wlList)); } catch (e) { } }
  function renderWatchlist() {
    const stocks = wlList.map(bySym).filter(Boolean);
    $('wlChips').innerHTML = stocks.map(r => `<span class="cmp-chip" title="${r.Name}"><b>${window.tk(r.Symbol)}</b><span class="x" data-s="${r.Symbol}">✕</span></span>`).join('');
    $('wlChips').querySelectorAll('.x').forEach(x => x.onclick = () => { wlList = wlList.filter(s => s !== x.dataset.s); saveWL(); renderWatchlist(); });
    if (!stocks.length) { $('wlSummary').innerHTML = ''; $('wlTable').innerHTML = '<p class="empty" style="margin:12px 16px">Your watchlist is empty. Add stocks above — they save to this browser.</p>'; return; }
    const avg = a => { const x = a.filter(v => typeof v === 'number'); return x.length ? (x.reduce((s, v) => s + v, 0) / x.length) : null; };
    const buys = stocks.filter(r => ['Buy', 'Strong Buy'].includes(r['Technical Insight'])).length;
    $('wlSummary').innerHTML = [['Stocks', stocks.length], ['Avg Composite', f(avg(stocks.map(r => r['Composite Score'])), 1)],
      ['Tech Buys', buys], ['Avg ROC 3M', f(avg(stocks.map(r => r['ROC 3M %'])), 1) + '%']]
      .map(([l, v]) => `<div class="wl-stat"><div class="v">${v}</div><div class="l">${l}</div></div>`).join('');
    const INS = { 'Strong Buy': 'ins-sb', 'Buy': 'ins-b', 'Hold': 'ins-h', 'Sell': 'ins-s', 'Strong Sell': 'ins-ss' };
    let h = '<table class="cmp-table"><thead><tr><th>Stock</th><th>Price</th><th>Chg%</th><th>Regime</th><th>Tech</th><th>Fund</th><th>Composite</th></tr></thead><tbody>';
    for (const r of stocks) { const c = r['Day Change %']; h += `<tr data-sym="${r.Symbol}" style="cursor:pointer"><td>${window.stockLabel(r)}</td><td>${f(r['Current Price'])}</td><td class="${c > 0 ? 'pos' : c < 0 ? 'neg' : ''}">${f(c)}</td><td>${r['Market Regime'] || '—'}</td><td><span class="badge ${INS[r['Technical Insight']] || ''}">${r['Technical Insight'] || '—'}</span></td><td><span class="badge ${INS[r['Fundamental Insight']] || ''}">${r['Fundamental Insight'] || '—'}</span></td><td>${f(r['Composite Score'], 1)}</td></tr>`; }
    $('wlTable').innerHTML = h + '</tbody></table>';
    $('wlTable').querySelectorAll('tr[data-sym]').forEach(tr => tr.onclick = () => { const r = bySym(tr.dataset.sym); if (r && window.openPanel) window.openPanel(r); });
  }

  // ── Methodology ──
  let methodLoaded = false;
  async function renderMethod() {
    if (methodLoaded) return; methodLoaded = true;
    try {
      const md = await fetch('METHODOLOGY.md').then(r => r.text());
      $('methodBody').innerHTML = window.marked ? window.marked.parse(md) : `<pre>${md}</pre>`;
    } catch (e) { $('methodBody').innerHTML = '<p class="empty">Could not load METHODOLOGY.md</p>'; methodLoaded = false; }
  }
})();
