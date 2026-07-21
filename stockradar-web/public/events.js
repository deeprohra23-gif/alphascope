// events.js — Phase 4b (Events): FII/DII, Corporate Actions, Bulk & Block deals.
// Live from NSE via the serverless functions (/api/fiidii, /api/corpactions, /api/deals).
(function () {
  let inited = false, UNIV = new Set(), corpData = null, dealsData = null;
  const $ = id => document.getElementById(id);
  const err = msg => `<p class="empty" style="margin:14px 16px">⚠ ${msg}<br><span style="font-size:11px">NSE can block server IPs — if this fails after deploy, it's the NSE endpoint, not the app.</span></p>`;
  const SPIN = '<div class="ev-loading"><span class="spinner"></span> Loading…</div>';
  const money = v => { const n = parseFloat(v); return isNaN(n) ? (v ?? '—') : '₹' + n.toLocaleString('en-IN', { maximumFractionDigits: 0 }); };

  window.initEvents = async function () {
    if (inited) return; inited = true;
    try { await ensureData(); UNIV = new Set(window.ALL.map(r => r.Symbol.replace(/\.NS$/, ''))); } catch (e) { }
    $('evsub').addEventListener('click', e => {
      const b = e.target.closest('.sub'); if (!b) return;
      document.querySelectorAll('#evsub .sub').forEach(x => x.classList.toggle('active', x === b));
      document.querySelectorAll('.esec').forEach(p => { p.hidden = p.dataset.esec !== b.dataset.esub; });
      if (b.dataset.esub === 'corp') loadCorp();
      if (b.dataset.esub === 'deals') loadDeals();
    });
    ['caType', 'caUniverse', 'caUpcoming'].forEach(id => $(id).addEventListener('change', renderCorp));
    ['dealSide', 'dealUniverse'].forEach(id => $(id).addEventListener('change', renderDeals));
    loadFiiDii();
  };

  // ── FII / DII ──
  // one net/buy/sell card (latest day)
  const fdCard = (cat, date, o) => {
    const net = parseFloat(o.net);
    return `<div class="ev-card"><div class="ev-cat">${cat}</div><div class="ev-date">${date}</div>
      <div class="ev-net ${net >= 0 ? 'pos' : 'neg'}">${net >= 0 ? '+' : ''}${money(o.net)}<span>net</span></div>
      <div class="ev-bs"><span>Buy ${money(o.buy)}</span><span>Sell ${money(o.sell)}</span></div></div>`;
  };
  const netCell = v => { const n = parseFloat(v); return `<td class="${n >= 0 ? 'pos' : 'neg'}">${n >= 0 ? '+' : ''}${money(v)}</td>`; };
  function renderFiiDii(days) {
    const recent = days.slice(-5).reverse();           // newest first, up to 5
    const latest = recent[0];
    const cards = latest ? `<div class="ev-cards">${fdCard('FII / FPI', latest.date, latest.fii)}${fdCard('DII', latest.date, latest.dii)}</div>` : '';
    const table = recent.length > 1 ? `<h3 class="ev-h">Last ${recent.length} days <span class="cnt2">net · ₹ cr</span></h3>
      <div class="cmp-table-wrap"><table class="cmp-table"><thead><tr><th>Date</th><th>FII Buy</th><th>FII Sell</th><th>FII Net</th><th>DII Buy</th><th>DII Sell</th><th>DII Net</th></tr></thead><tbody>` +
      recent.map(d => `<tr><td>${d.date}</td><td>${money(d.fii.buy)}</td><td>${money(d.fii.sell)}</td>${netCell(d.fii.net)}<td>${money(d.dii.buy)}</td><td>${money(d.dii.sell)}</td>${netCell(d.dii.net)}</tr>`).join('') +
      '</tbody></table></div>' : '';
    $('fiidiiOut').innerHTML = cards + table + `<p class="idxhint" style="margin:12px 16px">₹ crore · provisional cash-market figures. History archived daily by the build pipeline.</p>`;
  }
  async function loadFiiDii() {
    $('fiidiiOut').innerHTML = SPIN;
    // prefer the daily-archived multi-day history; fall back to the live single-day API
    let hist = [];
    try { hist = await fetch('data/fiidii.json').then(r => r.ok ? r.json() : []); } catch (e) { hist = []; }
    if (Array.isArray(hist) && hist.length) return renderFiiDii(hist);
    try {
      const d = await fetch('/api/fiidii').then(r => r.json());
      if (!d.rows || !d.rows.length) return $('fiidiiOut').innerHTML = err('No FII/DII data returned.');
      // normalise the live NSE rows (FII row + DII row) into one day
      const pick = re => d.rows.find(r => re.test(r.category || '')) || {};
      const fii = pick(/FII|FPI/i), dii = pick(/DII/i);
      const day = { date: (fii.date || dii.date || ''), fii: { buy: fii.buyValue, sell: fii.sellValue, net: fii.netValue }, dii: { buy: dii.buyValue, sell: dii.sellValue, net: dii.netValue } };
      renderFiiDii([day]);
    } catch (e) { $('fiidiiOut').innerHTML = err('Could not reach /api/fiidii — is the dev server / deployment running?'); }
  }

  // ── Corporate Actions ──
  function caType(subject) {
    const s = (subject || '').toLowerCase();
    if (/dividend/.test(s)) return 'Dividend';
    if (/split|sub-division/.test(s)) return 'Split';
    if (/bonus/.test(s)) return 'Bonus';
    if (/rights/.test(s)) return 'Rights';
    if (/buy ?back/.test(s)) return 'Buyback';
    if (/agm|annual general/.test(s)) return 'AGM';
    return 'Other';
  }
  const parseDate = s => { const m = /(\d{2})-(\w{3})-(\d{4})/.exec(s || ''); if (!m) return null; return new Date(`${m[2]} ${m[1]} ${m[3]}`); };
  async function loadCorp() {
    if (corpData) return;
    $('corpOut').innerHTML = SPIN;
    try {
      const d = await fetch('/api/corpactions').then(r => r.json());
      corpData = (d.rows || []).map(r => ({ ...r, _type: caType(r.subject), _ex: parseDate(r.exDate) }));
      const types = [...new Set(corpData.map(r => r._type))].sort();
      $('caType').innerHTML = '<option value="">All actions</option>' + types.map(t => `<option>${t}</option>`).join('');
      renderCorp();
    } catch (e) { $('corpOut').innerHTML = err('Could not reach /api/corpactions.'); }
  }
  function renderCorp() {
    if (!corpData) return;
    const type = $('caType').value, uni = $('caUniverse').checked, up = $('caUpcoming').checked;
    const today = new Date(); today.setHours(0, 0, 0, 0);
    let rows = corpData.filter(r => (!type || r._type === type) && (!uni || UNIV.has(r.symbol)) && (!up || (r._ex && r._ex >= today)));
    rows.sort((a, b) => (a._ex || 0) - (b._ex || 0));
    if (!rows.length) return $('corpOut').innerHTML = '<p class="empty" style="margin:14px 16px">No matching corporate actions.</p>';
    $('corpOut').innerHTML = `<div class="ev-count">${rows.length} actions</div><div class="cmp-table-wrap"><table class="cmp-table"><thead><tr><th>Symbol</th><th>Company</th><th>Type</th><th>Purpose</th><th>Ex-Date</th></tr></thead><tbody>` +
      rows.slice(0, 400).map(r => `<tr><td>${r.symbol || '—'}</td><td>${r.comp || '—'}</td><td><span class="ev-tag t-${r._type.toLowerCase()}">${r._type}</span></td><td>${r.subject || '—'}</td><td>${r.exDate || '—'}</td></tr>`).join('') +
      '</tbody></table></div>';
  }

  // ── Bulk & Block deals ──
  async function loadDeals() {
    if (dealsData) return;
    $('dealsOut').innerHTML = SPIN;
    try {
      dealsData = await fetch('/api/deals').then(r => r.json());
      renderDeals();
    } catch (e) { $('dealsOut').innerHTML = err('Could not reach /api/deals.'); }
  }
  function renderDeals() {
    if (!dealsData) return;
    const side = $('dealSide').value, uni = $('dealUniverse').checked;
    const filt = arr => (arr || []).filter(r => (!side || (r.buySell || '').toUpperCase() === side) && (!uni || UNIV.has(r.symbol)));
    const tbl = (title, arr) => {
      const rows = filt(arr);
      if (!rows.length) return `<h3 class="ev-h">${title}</h3><p class="empty" style="margin:0 16px 12px">None today.</p>`;
      return `<h3 class="ev-h">${title} <span class="cnt2">${rows.length}</span></h3><div class="cmp-table-wrap"><table class="cmp-table"><thead><tr><th>Symbol</th><th>Security</th><th>Client</th><th>Side</th><th>Qty</th><th>Price</th></tr></thead><tbody>` +
        rows.map(r => `<tr><td>${r.symbol || '—'}</td><td>${r.name || '—'}</td><td>${r.clientName || '—'}</td><td class="${(r.buySell || '').toUpperCase() === 'BUY' ? 'pos' : 'neg'}">${r.buySell || '—'}</td><td>${(+r.qty || 0).toLocaleString('en-IN')}</td><td>₹${r.watp || '—'}</td></tr>`).join('') +
        '</tbody></table></div>';
    };
    $('dealsOut').innerHTML = `<div class="ev-count">as on ${dealsData.asOn || '—'}</div>` + tbl('Bulk Deals', dealsData.bulk) + tbl('Block Deals', dealsData.block);
  }
})();
