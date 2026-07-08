// dashboard.js — Phase 2. Spotlight + Market Overview, Quick Picks, Sector Rotation,
// Signals, Sector Top 5. All computed client-side from the same static stocks.json.
(function () {
  let inited = false, CHANGES = null, MARKET = null;
  const sec = k => document.querySelector(`.dsec[data-dsec="${k}"]`);
  const num = (v, d = 2) => (v == null || v === '' || isNaN(v)) ? '—' : Number(v).toFixed(d);
  const avg = a => { const x = a.filter(v => v != null && !isNaN(v)).map(Number); return x.length ? x.reduce((s, v) => s + v, 0) / x.length : null; };
  const pctOf = (arr, f) => arr.length ? 100 * arr.filter(f).length / arr.length : 0;
  const INSB = { 'Strong Buy': 'ins-sb', 'Buy': 'ins-b', 'Hold': 'ins-h', 'Sell': 'ins-s', 'Strong Sell': 'ins-ss' };
  const REGDOT = { 'Strong Bull': '#00d4aa', 'Bull': '#4da6ff', 'Bear': '#ff6b6b', 'Strong Bear': '#ff4444' };
  const open = sym => { const r = window.ALL.find(x => x.Symbol === sym); if (r && window.openPanel) window.openPanel(r); };
  const clickable = els => els.forEach(c => c.onclick = () => open(c.dataset.sym));

  window.initDashboard = async function () {
    if (inited) return;
    try { await ensureData(); } catch (e) { return; }
    try { CHANGES = await fetch('data/changes.json').then(r => r.json()); } catch (e) { CHANGES = { groups: {} }; }
    try { const [idx, glb] = await Promise.all([fetch('data/indices.json').then(r => r.json()), fetch('data/global.json').then(r => r.json())]); MARKET = { idx, glb }; } catch (e) { MARKET = null; }
    inited = true;
    renderSpotlight(); renderOverview(); renderPicks(); renderChanges(); renderRotation(); renderSignals(); renderTop5();
    document.getElementById('dashsub').addEventListener('click', e => {
      const b = e.target.closest('.sub'); if (!b) return;
      document.querySelectorAll('#dashsub .sub').forEach(x => x.classList.toggle('active', x === b));
      document.querySelectorAll('.dsec').forEach(p => { p.hidden = p.dataset.dsec !== b.dataset.dsub; });
    });
  };

  // ── Market Pulse (macro ribbon: key Indian indices, currency, volatility, commodities, US) ──
  // [source, lookup-key, display label] — idx=indices.json (by Index), glb=global.json (by Name)
  const PULSE = [
    ['idx', 'Nifty 50', 'NIFTY 50', 'landmark'],
    ['idx', 'Nifty Bank', 'NIFTY BANK', 'landmark'],
    ['glb', 'India VIX', 'INDIA VIX', 'activity'],
    ['glb', 'USD/INR', 'USD / INR', 'rupee'],
    ['glb', 'Gold', 'GOLD', 'gem'],
    ['glb', 'Silver', 'SILVER', 'gem'],
    ['glb', 'Crude Oil', 'CRUDE OIL', 'droplet'],
    ['glb', 'Nasdaq', 'NASDAQ', 'globe'],
  ];
  // level format: thousands→comma integer (indices), else 2dp (FX / VIX / commodities)
  const lvl = v => (v == null || v === '' || isNaN(v)) ? '—' : (Math.abs(+v) >= 1000 ? Math.round(+v).toLocaleString('en-IN') : (+v).toFixed(2));

  function renderSpotlight() {
    const el = document.getElementById('spotlight');
    if (!MARKET) { el.innerHTML = ''; return; }   // no macro data → hide the ribbon
    const find = (src, key) => src === 'idx' ? MARKET.idx.find(r => r.Index === key) : MARKET.glb.find(r => r.Name === key);
    const tiles = PULSE.map(([src, key, label, ic]) => {
      const r = find(src, key); if (!r) return '';
      const c = r['Day Change %'], cls = c > 0 ? 'pos' : c < 0 ? 'neg' : '', arrow = c > 0 ? '▲' : c < 0 ? '▼' : '·';
      return `<div class="pulse-tile">
        <div class="pt-label">${window.icon ? window.icon(ic) : ''}${label}</div>
        <div class="pt-val">${lvl(r['Current Price'])}</div>
        <div class="pt-chg ${cls}">${arrow} ${c > 0 ? '+' : ''}${num(c)}%</div>
      </div>`;
    }).join('');
    el.innerHTML = `<div class="spot-h">◆ Market Pulse <span>key indices, currency, volatility &amp; commodities · today's change</span></div>
      <div class="pulse">${tiles}</div>`;
  }

  // ── Market Overview ──
  const tile = (label, val, sub) => `<div class="tile"><div class="tl-v">${val}</div><div class="tl-l">${label}</div>${sub ? `<div class="tl-s">${sub}</div>` : ''}</div>`;
  function distBar(title, order, colors) {
    const A = window.ALL, counts = {}; order.forEach(o => counts[o] = 0);
    A.forEach(r => { if (r[title] in counts) counts[r[title]]++; });
    const total = order.reduce((s, o) => s + counts[o], 0) || 1;
    const seg = order.map(o => `<div class="seg" style="width:${100 * counts[o] / total}%;background:${colors[o]}" title="${o}: ${counts[o]}"></div>`).join('');
    const leg = order.map(o => `<span class="lg"><i style="background:${colors[o]}"></i>${o} <b>${counts[o]}</b> (${(100 * counts[o] / total).toFixed(0)}%)</span>`).join('');
    const heading = title === 'Market Regime' ? 'Regime Distribution' : 'Drawdown Status';
    return `<div class="dcard"><h3>${heading}</h3><div class="stackbar">${seg}</div><div class="legend">${leg}</div></div>`;
  }
  function renderOverview() {
    const A = window.ALL, g = f => pctOf(A, f).toFixed(0);
    const adv = A.filter(r => r['Day Change %'] > 0).length, dec = A.filter(r => r['Day Change %'] < 0).length;
    const breadth = `<div class="tiles">` +
      tile('% &gt; EMA 50', g(r => r['Current Price'] > r['EMA 50']) + '%') +
      tile('% &gt; EMA 200', g(r => r['Current Price'] > r['EMA 200']) + '%') +
      tile('Supertrend Bull', g(r => r['Supertrend'] === 'Bullish') + '%') +
      tile('MACD Bull', g(r => r['MACD Signal'] === 'Bullish') + '%') +
      tile('Golden Cross', g(r => r['EMA Cross'] === 'Golden Cross') + '%') +
      tile('Adv / Dec', dec ? (adv / dec).toFixed(2) : adv, `${adv} up · ${dec} down`) + `</div>`;
    const caps = ['Large', 'Mid', 'Small'].map(c => {
      const grp = A.filter(r => r['Cap Category'] === c);
      const bull = pctOf(grp, r => ['Bull', 'Strong Bull'].includes(r['Market Regime']));
      return `<tr><td>${c}</td><td>${grp.length}</td><td class="${bull >= 50 ? 'pos' : 'neg'}">${bull.toFixed(0)}%</td><td>${num(avg(grp.map(r => r['ROC 3M %'])))}</td><td>${num(avg(grp.map(r => r['RSI 14'])), 0)}</td></tr>`;
    }).join('');
    sec('overview').innerHTML = breadth +
      `<div class="dgrid2">${distBar('Market Regime', ['Strong Bull', 'Bull', 'Bear', 'Strong Bear'], REGDOT)}
        ${distBar('Drawdown Status', ['At High', 'Recovering', 'Correcting', 'Damaged'], { 'At High': '#00d4aa', 'Recovering': '#ffaa33', 'Correcting': '#ff8844', 'Damaged': '#ff4d4d' })}</div>
      <div class="dcard"><h3>Regime by Market Cap</h3><table class="dtable"><thead><tr><th>Cap</th><th>Count</th><th>Bullish %</th><th>Avg ROC 3M</th><th>Avg RSI</th></tr></thead><tbody>${caps}</tbody></table></div>`;
  }

  // ── Quick Picks ──
  const PICKS = [
    ['Short Term — Momentum', r => r['Supertrend'] === 'Bullish' && r['MACD Signal'] === 'Bullish' && r['ROC 1M %'] > 5 && r['RSI 14'] >= 50 && r['RSI 14'] <= 70],
    ['Medium Term — Trend + Quality', r => ['Bull', 'Strong Bull'].includes(r['Market Regime']) && r['ROC 3M %'] > 10 && r['Fundamental Score'] > 50],
    ['Long Term Compounder', r => r['ROCE %'] > 15 && r['ROE %'] > 12 && r['Debt/Equity'] < 1 && r['Sales Growth 3Y %'] > 10 && r['Promoter Holding %'] > 50],
    ['Dividend Pick', r => r['Dividend Yield %'] > 2 && r['Dividend Payout %'] >= 10 && r['Dividend Payout %'] <= 60 && r['Debt/Equity'] < 0.5 && r['Profit Growth 3Y %'] > 5],
    ['Value Pick', r => r['PE Ratio'] < r['Sector PE'] && r['ROCE %'] > 12 && r['Profit Growth 1Y %'] > 0],
  ];
  function miniTable(rows) {
    return `<table class="dtable mini"><thead><tr><th>Stock</th><th>Price</th><th>Chg%</th><th>Comp</th></tr></thead><tbody>` +
      rows.map(r => { const c = r['Day Change %']; return `<tr data-sym="${r.Symbol}"><td>${window.stockLabel(r)}</td><td>${num(r['Current Price'])}</td><td class="${c > 0 ? 'pos' : c < 0 ? 'neg' : ''}">${num(c)}</td><td>${num(r['Composite Score'], 1)}</td></tr>`; }).join('') + `</tbody></table>`;
  }
  function renderPicks() {
    const cards = PICKS.map(([name, f]) => ({ name, rows: window.ALL.filter(f).sort((a, b) => (b['Composite Score'] || 0) - (a['Composite Score'] || 0)) }));
    sec('picks').innerHTML = `<div class="dgrid">` + cards.map((c, i) =>
      `<div class="dcard"><h3>${c.name} <span class="cnt2">${c.rows.length}</span></h3>${c.rows.length ? miniTable(c.rows.slice(0, 6)) + `<button class="viewall" data-i="${i}">View all ${c.rows.length} in Stocks →</button>` : '<p class="empty">No stocks match today.</p>'}</div>`).join('') + `</div>`;
    clickable(sec('picks').querySelectorAll('tr[data-sym]'));
    sec('picks').querySelectorAll('.viewall').forEach(b => b.onclick = () => window.openInStocks(cards[+b.dataset.i].rows, cards[+b.dataset.i].name));
  }

  // ── What Changed Today ──
  const CHG_POS = [['new_golden_cross', 'Fresh Golden Cross'], ['regime_upgraded', 'Regime Upgraded'], ['entered_strong_bull', 'Entered Strong Bull'], ['newly_at_high', 'Newly At High'], ['supertrend_bullish_flip', 'Supertrend → Bullish']];
  const CHG_NEG = [['new_death_cross', 'Fresh Death Cross'], ['regime_downgraded', 'Regime Downgraded'], ['entered_strong_bear', 'Entered Strong Bear'], ['newly_damaged', 'Newly Damaged'], ['supertrend_bearish_flip', 'Supertrend → Bearish']];
  function chgTable(rows) {
    return `<table class="dtable mini"><thead><tr><th>Stock</th><th>Regime</th><th>ROC 3M</th><th>Comp</th></tr></thead><tbody>` +
      rows.map(r => { const v = r['ROC 3M %']; return `<tr data-sym="${r.Symbol}"><td>${window.stockLabel(r)}</td><td>${r['Market Regime'] || '—'}</td><td class="${v > 0 ? 'pos' : v < 0 ? 'neg' : ''}">${num(v)}</td><td>${num(r['Composite Score'], 1)}</td></tr>`; }).join('') + `</tbody></table>`;
  }
  function chgCol(list, kind) {
    const g = (CHANGES && CHANGES.groups) || {};
    return `<div class="dcard"><h3 class="${kind === 'pos' ? 'pos' : 'neg'}">${kind === 'pos' ? 'Positive Changes' : 'Negative Changes'}</h3>` +
      list.map(([key, label]) => {
        const rows = g[key] || [];
        return `<details class="sig"><summary>${label} <span class="cnt2">${rows.length}</span></summary>${rows.length ? chgTable(rows.slice(0, 10)) + (rows.length > 10 ? `<button class="viewall" data-chg="${key}" data-label="${label}">View all ${rows.length} →</button>` : '') : '<p class="empty">None.</p>'}</details>`;
      }).join('') + `</div>`;
  }
  function renderChanges() {
    if (!CHANGES || !CHANGES.today) { sec('changes').innerHTML = `<div class="dcard"><p class="empty">Not enough history snapshots yet to compute changes.</p></div>`; return; }
    const fmtd = s => { const m = /(\d{4})-(\d{2})-(\d{2})/.exec(s || ''); return m ? `${m[3]}/${m[2]}/${m[1]}` : s; };
    sec('changes').innerHTML = `<div class="chg-h">Comparing <b>${fmtd(CHANGES.prev)}</b> → <b>${fmtd(CHANGES.today)}</b></div><div class="dgrid2">${chgCol(CHG_POS, 'pos')}${chgCol(CHG_NEG, 'neg')}</div>`;
    sec('changes').addEventListener('toggle', e => { if (e.target.open) clickable(e.target.querySelectorAll('tr[data-sym]')); }, true);
    sec('changes').querySelectorAll('.viewall').forEach(b => b.onclick = () => {
      const syms = new Set((CHANGES.groups[b.dataset.chg] || []).map(r => r.Symbol));
      window.openInStocks(window.ALL.filter(r => syms.has(r.Symbol)), b.dataset.label);
    });
  }

  // ── Sector Rotation (flagship bar chart) ──
  function renderRotation() {
    const bySec = {};
    window.ALL.forEach(r => { if (r.Sector) (bySec[r.Sector] = bySec[r.Sector] || []).push(r); });
    const rows = Object.entries(bySec).map(([s, grp]) => ({
      sector: s, n: grp.length, rs: avg(grp.map(r => r['RS vs Nifty 3M %'])),
      roc3: avg(grp.map(r => r['ROC 3M %'])), bull: pctOf(grp, r => ['Bull', 'Strong Bull'].includes(r['Market Regime'])),
    })).filter(r => r.rs != null).sort((a, b) => b.rs - a.rs);
    const max = Math.max(...rows.map(r => Math.abs(r.rs)), 1);
    const bars = rows.map(r => {
      const w = 48 * Math.abs(r.rs) / max, pos = r.rs >= 0;
      return `<div class="rot-row" data-sector="${encodeURIComponent(r.sector)}">
        <div class="rot-name">${r.sector}</div>
        <div class="rot-track"><span class="rot-zero"></span><span class="rot-bar ${pos ? 'p' : 'n'}" style="width:${w}%;${pos ? 'left:50%' : `right:${50 - w}%`}"></span></div>
        <div class="rot-val ${pos ? 'pos' : 'neg'}">${num(r.rs)}</div>
        <div class="rot-meta">${r.n} stk · ROC3M ${num(r.roc3)} · Bull ${r.bull.toFixed(0)}%</div></div>`;
    }).join('');
    sec('rotation').innerHTML = `<div class="dcard"><h3>Sector Rotation <span class="sub2">avg RS vs Nifty 3M — click a sector for its top 5</span></h3><div class="rot">${bars}</div><div id="rotDrill" class="rotdrill" hidden></div></div>`;
    sec('rotation').querySelectorAll('.rot-row').forEach(row => row.onclick = () => {
      const s = decodeURIComponent(row.dataset.sector);
      const top = bySec[s].slice().sort((a, b) => (b['Composite Score'] || 0) - (a['Composite Score'] || 0)).slice(0, 5);
      const d = document.getElementById('rotDrill'); d.hidden = false;
      d.innerHTML = `<h4>${s} — top 5 by Composite</h4>${miniTable(top)}`;
      clickable(d.querySelectorAll('tr[data-sym]'));
      sec('rotation').querySelectorAll('.rot-row').forEach(x => x.classList.toggle('sel', x === row));
    });
  }

  // ── Signals ──
  const SIG = {
    Bullish: [
      ['Fresh Golden Cross', r => r['EMA Cross'] === 'Golden Cross' && r['Days Since EMA Cross'] != null && r['Days Since EMA Cross'] <= 10],
      ['Full Bullish Alignment', r => r['Current Price'] > r['EMA 50'] && r['EMA 50'] > r['EMA 200'] && r['Supertrend'] === 'Bullish' && r['MACD Signal'] === 'Bullish'],
      ['Near 52W High', r => r['% from 52W High'] >= -5],
      ['Volume Surge + MACD Bull', r => r['Vol ROC 1M %'] > 50 && r['MACD Signal'] === 'Bullish'],
      ['At High + Strong Momentum', r => r['Drawdown Status'] === 'At High' && r['ROC 3M %'] > 10],
    ],
    Bearish: [
      ['Fresh Death Cross', r => r['EMA Cross'] === 'Death Cross' && r['Days Since EMA Cross'] != null && r['Days Since EMA Cross'] <= 10],
      ['Full Bearish Alignment', r => r['Current Price'] < r['EMA 50'] && r['EMA 50'] < r['EMA 200'] && r['Supertrend'] === 'Bearish' && r['MACD Signal'] === 'Bearish'],
      ['Damaged', r => r['Drawdown Status'] === 'Damaged'],
      ['RSI Overbought (>75)', r => r['RSI 14'] > 75],
      ['RSI Oversold (<30)', r => r['RSI 14'] < 30],
      ['Rising Volatility', r => r['Vol Trend'] === 'Rising'],
    ],
  };
  function renderSignals() {
    const reg = {};
    const col = kind => `<div class="dcard"><h3 class="${kind === 'Bullish' ? 'pos' : 'neg'}">${kind} Signals</h3>` + SIG[kind].map(([name, f]) => {
      const rows = window.ALL.filter(f).sort((a, b) => (b['Composite Score'] || 0) - (a['Composite Score'] || 0));
      reg[name] = rows;
      return `<details class="sig"><summary>${name} <span class="cnt2">${rows.length}</span></summary>${rows.length ? miniTable(rows.slice(0, 8)) + `<button class="viewall" data-sig="${encodeURIComponent(name)}">View all ${rows.length} →</button>` : '<p class="empty">None.</p>'}</details>`;
    }).join('') + `</div>`;
    sec('signals').innerHTML = `<div class="dgrid2">${col('Bullish')}${col('Bearish')}</div>`;
    sec('signals').addEventListener('toggle', e => { if (e.target.open) clickable(e.target.querySelectorAll('tr[data-sym]')); }, true);
    sec('signals').querySelectorAll('.viewall').forEach(b => b.onclick = () => window.openInStocks(reg[decodeURIComponent(b.dataset.sig)], decodeURIComponent(b.dataset.sig)));
  }

  // ── Sector Top 5 (rank by ANY numeric column, either direction) ──
  function renderTop5() {
    const A = window.ALL;
    const numericCols = Object.keys(A[0]).filter(k => k !== 'Screens' && A.some(r => typeof r[k] === 'number'));
    const PREF = ['Composite Score', 'Momentum Score', 'Technical Score', 'Fundamental Score', 'ROC 3M %', 'RS vs Nifty 3M %'];
    const metrics = [...PREF.filter(c => numericCols.includes(c)), ...numericCols.filter(c => !PREF.includes(c)).sort()];
    sec('top5').innerHTML = `<div class="t5-ctl">Rank by
      <select id="t5metric" class="ctl">${metrics.map(m => `<option>${m}</option>`).join('')}</select>
      <select id="t5order" class="ctl"><option value="desc">High → Low</option><option value="asc">Low → High</option></select></div>
      <div id="t5grid" class="dgrid"></div>`;
    const draw = (metric, order) => {
      const bySec = {};
      A.forEach(r => { if (r.Sector) (bySec[r.Sector] = bySec[r.Sector] || []).push(r); });
      const cmp = order === 'asc'
        ? (a, b) => (a[metric] ?? Infinity) - (b[metric] ?? Infinity)
        : (a, b) => (b[metric] ?? -Infinity) - (a[metric] ?? -Infinity);
      document.getElementById('t5grid').innerHTML = Object.keys(bySec).sort().map(s => {
        const top = bySec[s].slice().sort(cmp).slice(0, 5);
        return `<div class="dcard"><h3>${s}</h3>` + top.map(r =>
          `<div class="t5-row" data-sym="${r.Symbol}"><span class="dot" style="background:${REGDOT[r['Market Regime']] || '#555'}"></span><span class="t5-name">${window.stockLabel(r)}</span><span class="badge ${INSB[r['Technical Insight']]}">${(r['Technical Insight'] || '').split(' ').map(w => w[0]).join('')}</span><span class="t5-val">${num(r[metric], 2)}</span></div>`).join('') + `</div>`;
      }).join('');
      clickable(document.querySelectorAll('#t5grid .t5-row'));
    };
    const rerun = () => draw(document.getElementById('t5metric').value, document.getElementById('t5order').value);
    draw(metrics[0], 'desc');
    document.getElementById('t5metric').addEventListener('change', rerun);
    document.getElementById('t5order').addEventListener('change', rerun);
  }
})();
