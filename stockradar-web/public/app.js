// Alphascope — web app. Data is static JSON built daily by scripts/build_data.py (reuses the real scoring/insights).

// shared stock-identifier helpers: ticker (clean, .NS stripped) as primary, name muted beside it
const tk = s => (s || '').replace(/\.(NS|BO)$/, '');
const stockLabel = r => `<span class="tk">${tk(r.Symbol)}</span> <span class="nm">${r.Name || ''}</span>`;

const GREEN_RED = new Set(['Day Change %','ROC 1M %','ROC 3M %','ROC 6M %','1Y CAGR %','3Y CAGR %','5Y CAGR %',
  'RS vs Nifty 1M %','RS vs Nifty 3M %','RS vs Nifty 6M %','RS vs Nifty 12M %','% from 52W High','% from 52W Low',
  '1Y Max Drawdown %','Sales Growth 1Y %','Sales Growth 3Y %','Profit Growth 1Y %','Profit Growth 3Y %',
  'EPS Growth 1Y %','EPS Growth 3Y %','FCF Yield %','FII Change %','DII Change %','Momentum Acceleration','Capture Ratio']);

const numFmt = d => p => (p.value == null || p.value === '' || isNaN(p.value)) ? '' : Number(p.value).toFixed(d);
const grClass = p => (p.value == null || p.value === '') ? '' : p.value > 0 ? 'pos' : p.value < 0 ? 'neg' : '';

const INS = {'Strong Buy':'ins-sb','Buy':'ins-b','Hold':'ins-h','Sell':'ins-s','Strong Sell':'ins-ss'};
const insightRenderer = p => p.value ? `<span class="badge ${INS[p.value]||''}">${p.value}</span>` : '';
const REG = {'Strong Bull':'rg-sbull','Bull':'rg-bull','Bear':'rg-bear','Strong Bear':'rg-sbear'};
const regimeRenderer = p => p.value ? `<span class="${REG[p.value]||''}">${p.value}</span>` : '';
const DD = {'At High':'dd-high','Recovering':'dd-rec','Correcting':'dd-cor','Damaged':'dd-dam'};
const ddRenderer = p => p.value ? `<span class="${DD[p.value]||''}">${p.value}</span>` : '';

const C = (field, o = {}) => ({ field, headerName: o.h || field, ...o });
const numCol = (field, d = 2, w) => C(field, { type:'numericColumn', valueFormatter:numFmt(d), cellClass:GREEN_RED.has(field)?grClass:'', width:w, filter:'agNumberColumnFilter' });
const symCol = C('Symbol', { pinned:'left', width:100, cellClass:'cell-name', filter:'agTextColumnFilter', valueFormatter: p => (p.value || '').replace(/\.(NS|BO)$/,'') });
const nameCol = C('Name', { width:230, filter:'agTextColumnFilter' });

// view tab column sets (mirror config.py OVERVIEW/TECHNICAL/RETURNS/RISK/FUNDAMENTAL_COLS)
const VIEWS = {
  overview: [ symCol, nameCol, C('Sector',{width:130}), C('Industry',{width:160}), C('Cap Category',{h:'Cap',width:95}),
    numCol('Market Cap (Cr)',0,110), numCol('Current Price',2,105), numCol('Day Change %',2,100),
    C('Technical Insight',{h:'Tech',cellRenderer:insightRenderer,width:118}),
    C('Fundamental Insight',{h:'Fund',cellRenderer:insightRenderer,width:118}),
    C('Market Regime',{cellRenderer:regimeRenderer,width:112}), C('Drawdown Status',{h:'Drawdown',cellRenderer:ddRenderer,width:118}),
    numCol('Composite Score',1,115), numCol('Universe Rank',0,90), C('Index Membership',{width:160}) ],
  technicals: [ symCol, nameCol, numCol('Current Price',2,105), C('Technical Insight',{h:'Tech',cellRenderer:insightRenderer,width:118}),
    numCol('EMA 50',1), numCol('EMA 200',1), C('EMA Cross',{width:120}), numCol('Days Since EMA Cross',0,140),
    numCol('RSI 14',1,85), C('MACD Signal',{width:110}), C('Supertrend',{width:105}),
    numCol('Trend Consistency (12M)',1,150), numCol('Momentum Acceleration',2,160), C('Vol Trend',{width:95}), numCol('Technical Score',1,115) ],
  returns: [ symCol, nameCol, numCol('Current Price',2,105), numCol('ROC 1M %',2), numCol('ROC 3M %',2), numCol('ROC 6M %',2),
    numCol('1Y CAGR %',2), numCol('3Y CAGR %',2),
    numCol('RS vs Nifty 1M %',2,135), numCol('RS vs Nifty 3M %',2,135), numCol('RS vs Nifty 6M %',2,135), numCol('RS vs Nifty 12M %',2,140),
    numCol('Momentum Rank 1M',0,135), numCol('Momentum Score',1,115) ],
  risk: [ symCol, nameCol, numCol('Current Price',2,105), numCol('Beta 1Y (Daily)',2,130), numCol('Beta 5Y (Monthly)',2,140),
    numCol('SD 1Y %',2,100), numCol('ATR % (14D)',2,110), numCol('1Y Max Drawdown %',2,150), numCol('Days Since 52W High',0,150),
    numCol('52W High',1,105), numCol('52W Low',1,105), numCol('% from 52W High',2,140), numCol('% from 52W Low',2,140),
    numCol('Up Capture Ratio',1,130), numCol('Down Capture Ratio',1,140), numCol('Capture Ratio',1,120) ],
  fundamentals: [ symCol, nameCol, C('Sector',{width:130}), C('Fundamental Insight',{h:'Fund',cellRenderer:insightRenderer,width:118}),
    numCol('PE Ratio',1,90), numCol('Sector PE',1,100), numCol('PB Ratio',1,90), numCol('EV/EBITDA',1,110), numCol('PEG Ratio',2,95),
    numCol('ROE %',1,85), numCol('ROCE %',1,90), numCol('Net Profit Margin %',1,150),
    numCol('Sales Growth 3Y %',1,150), numCol('Profit Growth 3Y %',1,150), numCol('EPS Growth 3Y %',1,140),
    numCol('Debt/Equity',2,115), numCol('Interest Coverage',1,140), numCol('Dividend Yield %',2,125), numCol('Dividend Payout %',1,135),
    numCol('Promoter Holding %',1,150), numCol('Pledge %',1,90), numCol('Fundamental Score',1,140) ],
};

let ALL = [], gridApi = null, curView = 'overview';
let SCREENS_META = [], mode = 'all', selScreen = null, FILTER_COLS = [], externalRows = null;

const gridOptions = {
  columnDefs: VIEWS.overview,
  defaultColDef: { sortable:true, resizable:true, filter:true },
  rowSelection: 'single', animateRows: true,
  autoSizeStrategy: { type: 'fitCellContents' },   // size every column to its content
  onRowClicked: e => openPanel(e.data),
  onSortChanged: () => updateSortInfo(),
  onFirstDataRendered: p => { p.api.applyColumnState({ state: [{ colId: 'Composite Score', sort: 'desc' }] }); p.api.autoSizeAllColumns(); updateSortInfo(); },
  onModelUpdated: () => { if (gridApi) document.getElementById('count').textContent = `${gridApi.getDisplayedRowCount()} stocks`; },
};

// ── tab navigation ──
// expose grid helpers so index.js can reuse the same column styling
Object.assign(window, { VIEWS, numCol, grClass, numFmt, insightRenderer, regimeRenderer, ddRenderer, gridOptions, tk, stockLabel });

function activateMainTab(tab) {
  document.querySelectorAll('.mn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  document.querySelectorAll('.tabpane').forEach(p => { p.hidden = p.dataset.pane !== tab; });
  if (tab === 'stocks') initStocks();
  if (tab === 'dashboard' && window.initDashboard) window.initDashboard();
  if (tab === 'index' && window.initIndex) window.initIndex();
  if (tab === 'tools' && window.initTools) window.initTools();
  if (tab === 'events' && window.initEvents) window.initEvents();
}
document.getElementById('mainnav').addEventListener('click', e => {
  const btn = e.target.closest('.mn'); if (btn) activateMainTab(btn.dataset.tab);
});

// Dashboard is the default visible tab → render it on load
window.addEventListener('DOMContentLoaded', () => { if (window.initDashboard) window.initDashboard(); });

// ── Stocks tab ──
const $ = id => document.getElementById(id);
const val = id => $(id).value;

let _dataPromise = null;
function ensureData() {
  if (!_dataPromise) _dataPromise = Promise.all([
    fetch('data/stocks.json').then(r => r.json()),
    fetch('data/screens.json').then(r => r.json()).catch(() => []),
  ]).then(([a, s]) => { ALL = a; SCREENS_META = s; window.ALL = a; });
  return _dataPromise;
}

let _stocksInit = null;
function initStocks() {
  if (!_stocksInit) _stocksInit = (async () => {
    try { await ensureData(); }
    catch (e) { $('count').textContent = 'Failed to load data/stocks.json — serve over http'; throw e; }
    gridApi = agGrid.createGrid($('grid'), gridOptions);
    const sectors = [...new Set(ALL.map(r => r.Sector).filter(Boolean))].sort();
    $('sector').innerHTML = '<option value="">All sectors</option>' + sectors.map(s => `<option>${s}</option>`).join('');
    buildAdvancedFilters();
    buildScreens();
    FILTER_COLS = Object.keys(ALL[0]).filter(k => !['Screens', 'Description'].includes(k));
    addCondRow();
    computeRows();
  })();
  return _stocksInit;
}

// ── unified row computation (source → shared filters) ──
const getChecked = cid => [...document.querySelectorAll(`#${cid} input:checked`)].map(i => i.value);
function updateSortInfo() {
  const el = $('sortInfo'); if (!el || !gridApi) return;
  const s = gridApi.getColumnState().filter(c => c.sort).sort((a, b) => (a.sortIndex ?? 0) - (b.sortIndex ?? 0));
  el.textContent = s.length ? '· sorted by ' + s.map(c => `${c.colId} ${c.sort === 'desc' ? '▼' : '▲'}`).join(', ') : '';
}

function sourceRows() {
  if (mode === 'external') return externalRows || [];
  if (mode === 'screens') return selScreen ? ALL.filter(r => (r.Screens || []).includes(selScreen)) : [];
  if (mode === 'custom') return applyCustom(ALL);
  return ALL;
}

// jump into the full Stocks grid pre-loaded with a specific set (e.g. a Quick Pick / signal).
window.openInStocks = async function (rows, label) {
  activateMainTab('stocks');
  await initStocks();
  externalRows = rows; mode = 'external';
  document.querySelectorAll('#stocksub .sub').forEach(x => x.classList.remove('active'));
  $('screenwrap').hidden = true; $('custombuilder').hidden = true;
  $('extLabel').textContent = label ? `Showing: ${label} — pick a sub-tab to exit` : '';
  $('extLabel').hidden = !label;
  computeRows();
};
function computeRows() {
  if (!gridApi) return;
  const q = val('search').trim().toLowerCase(), sec = val('sector'), cap = val('cap'), ins = val('insight');
  const mcMin = parseFloat(val('mcMin')), mcMax = parseFloat(val('mcMax'));
  const rsiMin = parseFloat(val('rsiMin')), rsiMax = parseFloat(val('rsiMax'));
  const regime = val('regimeSel'), dd = val('ddSel'), idx = val('indexMem');
  const rows = sourceRows().filter(r =>
    (!q || `${r.Name} ${r.Symbol}`.toLowerCase().includes(q)) &&
    (!sec || r.Sector === sec) && (!cap || r['Cap Category'] === cap) && (!ins || r['Technical Insight'] === ins) &&
    (isNaN(mcMin) || r['Market Cap (Cr)'] >= mcMin) && (isNaN(mcMax) || r['Market Cap (Cr)'] <= mcMax) &&
    (isNaN(rsiMin) || r['RSI 14'] >= rsiMin) && (isNaN(rsiMax) || r['RSI 14'] <= rsiMax) &&
    (!regime || r['Market Regime'] === regime) &&
    (!dd || r['Drawdown Status'] === dd) &&
    (!idx || (r['Index Membership'] || '').includes(idx)));
  gridApi.setGridOption('rowData', rows);
}

// ── advanced filters ──
function buildAdvancedFilters() {
  $('regimeSel').innerHTML = '<option value="">All regimes</option>' + ['Strong Bull', 'Bull', 'Bear', 'Strong Bear'].map(r => `<option>${r}</option>`).join('');
  $('ddSel').innerHTML = '<option value="">All drawdown</option>' + ['At High', 'Recovering', 'Correcting', 'Damaged'].map(r => `<option>${r}</option>`).join('');
  const idxs = [...new Set(ALL.flatMap(r => (r['Index Membership'] || '').split(/[;,]/).map(s => s.trim()).filter(Boolean)))].sort();
  $('indexMem').innerHTML = '<option value="">Any index</option>' + idxs.map(i => `<option>${i}</option>`).join('');
}

// ── pre-built screens ──
function buildScreens() {
  const cats = [...new Set(SCREENS_META.map(s => s.tab))];
  const ct = $('cattabs');
  ct.innerHTML = cats.map((c, i) => `<button class="${i === 0 ? 'active' : ''}" data-cat="${c}">${c}</button>`).join('');
  ct.onclick = e => { const b = e.target.closest('button'); if (!b) return; ct.querySelectorAll('button').forEach(x => x.classList.remove('active')); b.classList.add('active'); renderScreenCards(b.dataset.cat); };
  if (cats.length) renderScreenCards(cats[0]);
}
function renderScreenCards(cat) {
  $('screencards').innerHTML = SCREENS_META.filter(s => s.tab === cat).map(s =>
    `<div class="scard ${s.name === selScreen ? 'active' : ''}" data-screen="${encodeURIComponent(s.name)}"><span class="cnt">${s.count}</span><h4>${s.name}</h4><p>${s.desc}</p></div>`).join('');
}
$('screencards').addEventListener('click', e => {
  const c = e.target.closest('.scard'); if (!c) return;
  selScreen = decodeURIComponent(c.dataset.screen);
  document.querySelectorAll('.scard').forEach(x => x.classList.toggle('active', x === c));
  const meta = SCREENS_META.find(s => s.name === selScreen);
  const info = $('screeninfo'); info.hidden = false;
  info.innerHTML = `<b>${meta.name}</b> — ${meta.desc}<br>${meta.rules.map(r => `<span class="rule">${r}</span>`).join('')}`;
  computeRows();
});

// ── custom screen builder ──
function addCondRow() {
  const div = document.createElement('div'); div.className = 'condrow';
  div.innerHTML = `<select class="col">${FILTER_COLS.map(c => `<option>${c}</option>`).join('')}</select>
    <select class="op"><option value=">">&gt;</option><option value=">=">&ge;</option><option value="<">&lt;</option><option value="<=">&le;</option><option value="=">=</option><option value="!=">&ne;</option><option value="contains">contains</option></select>
    <input class="val" placeholder="value">
    <button class="rm" title="remove">✕</button>`;
  div.querySelector('.rm').onclick = () => div.remove();
  $('condRows').appendChild(div);
}
function applyCustom(rows) {
  const conds = [...document.querySelectorAll('#condRows .condrow')].map(d => ({
    col: d.querySelector('.col').value, op: d.querySelector('.op').value, val: d.querySelector('.val').value.trim(),
  })).filter(c => c.val !== '');
  if (!conds.length) return rows;
  const logic = val('logic');
  const test = (r, c) => {
    const v = r[c.col], nv = parseFloat(v), nc = parseFloat(c.val);
    if (c.op === 'contains') return String(v ?? '').toLowerCase().includes(c.val.toLowerCase());
    if (!isNaN(nc) && !isNaN(nv)) return { '>': nv > nc, '>=': nv >= nc, '<': nv < nc, '<=': nv <= nc, '=': nv === nc, '!=': nv !== nc }[c.op];
    return c.op === '=' ? String(v) === c.val : c.op === '!=' ? String(v) !== c.val : false;
  };
  return rows.filter(r => logic === 'all' ? conds.every(c => test(r, c)) : conds.some(c => test(r, c)));
}

// ── sub-tabs + filter wiring ──
$('stocksub').addEventListener('click', e => {
  const b = e.target.closest('.sub'); if (!b) return;
  mode = b.dataset.sub;
  document.querySelectorAll('#stocksub .sub').forEach(x => x.classList.toggle('active', x === b));
  $('screenwrap').hidden = mode !== 'screens';
  $('custombuilder').hidden = mode !== 'custom';
  $('extLabel').hidden = true;
  computeRows();
});
$('moreBtn').addEventListener('click', () => { $('filterpanel').hidden = !$('filterpanel').hidden; });
$('addCond').addEventListener('click', addCondRow);
$('runCustom').addEventListener('click', computeRows);
$('resetFilters').addEventListener('click', () => {
  ['mcMin', 'mcMax', 'rsiMin', 'rsiMax'].forEach(id => $(id).value = '');
  ['indexMem', 'regimeSel', 'ddSel'].forEach(id => $(id).value = '');
  computeRows();
});

document.getElementById('viewtabs').addEventListener('click', e => {
  const btn = e.target.closest('.vt'); if (!btn) return;
  document.querySelectorAll('.vt').forEach(b => b.classList.remove('active'));
  btn.classList.add('active'); curView = btn.dataset.view;
  const sort = gridApi.getColumnState().filter(c => c.sort).map(c => ({colId:c.colId,sort:c.sort,sortIndex:c.sortIndex}));
  gridApi.setGridOption('columnDefs', VIEWS[curView]);
  if (sort.length) gridApi.applyColumnState({ state: sort });  // global sort persists across views
  setTimeout(() => gridApi.autoSizeAllColumns(), 30);          // re-fit widths to the new columns
});

['search', 'sector', 'cap', 'insight', 'mcMin', 'mcMax', 'rsiMin', 'rsiMax', 'indexMem', 'regimeSel', 'ddSel'].forEach(id => $(id).addEventListener('input', computeRows));
$('exportBtn').addEventListener('click', () => gridApi.exportDataAsCsv({ fileName: `alphascope_${curView}.csv` }));

// ── slide-in stock card ──
const panel = document.getElementById('panel'), scrim = document.getElementById('scrim');
const closePanel = () => { panel.classList.remove('open'); scrim.classList.remove('open'); };
window.closePanel = closePanel;
document.getElementById('panelClose').onclick = closePanel; scrim.onclick = closePanel;

const f2 = v => (v == null || v === '') ? '—' : Number(v).toFixed(2);
const row = (k, v) => `<div class="pc-row"><span class="k">${k}</span><span class="v">${v ?? '—'}</span></div>`;
const bar = (l, v) => `<div><div class="pc-row" style="border:none;padding-bottom:2px"><span class="k">${l}</span><span class="v">${v ?? '—'}</span></div><div class="pc-bar"><i style="width:${Math.max(0,Math.min(100,v||0))}%"></i></div></div>`;

const RECMAP = { strong_buy: 'Strong Buy', buy: 'Buy', hold: 'Hold', sell: 'Sell', strong_sell: 'Strong Sell', underperform: 'Underperform', outperform: 'Outperform', none: '—' };
function insightReason(d) {
  const p = [];
  if (d['Market Regime']) p.push(d['Market Regime']);
  if (d['Supertrend']) p.push('Supertrend ' + d['Supertrend']);
  if (d['MACD Signal']) p.push('MACD ' + d['MACD Signal']);
  if (d['EMA Cross']) p.push(d['EMA Cross']);
  if (d['RSI 14'] != null) p.push('RSI ' + f2(d['RSI 14']));
  return p.join(' · ');
}
function analystSection(d) {
  const rec = d['Analyst Recommendation']; if (!rec) return '';
  const tm = d['Target Mean Price'], cp = d['Current Price'], up = (tm && cp) ? (tm - cp) / cp * 100 : null;
  return `<div class="pc-sec">Analyst Consensus</div><div class="pc-grid">
    ${row('Rating', RECMAP[rec] || rec)}${row('Score', d['Analyst Score'] != null ? f2(d['Analyst Score']) + ' / 5' : '—')}
    ${row('Target Mean', tm ? '₹' + f2(tm) + (up != null ? ` (${up > 0 ? '+' : ''}${f2(up)}%)` : '') : '—')}${row('# Analysts', d['No. of Analysts'] ?? '—')}
    ${row('Target High', d['Target High Price'] ? '₹' + f2(d['Target High Price']) : '—')}${row('Target Low', d['Target Low Price'] ? '₹' + f2(d['Target Low Price']) : '—')}</div>`;
}
function screensSection(d) {
  const sc = d.Screens || []; if (!sc.length) return '';
  return `<div class="pc-sec">Screen Membership</div><div class="pc-chips">${sc.map(s => `<span class="chip-g">${s}</span>`).join('')}</div>`;
}
function peersSection(d) {
  const peers = (window.ALL || []).filter(r => r.Industry === d.Industry && r['Cap Category'] === d['Cap Category'] && r.Symbol !== d.Symbol)
    .sort((a, b) => (b['Composite Score'] || 0) - (a['Composite Score'] || 0)).slice(0, 8);
  if (!peers.length) return '';
  const PC = [['Price', 'Current Price', 2], ['Chg%', 'Day Change %', 2], ['Comp', 'Composite Score', 1], ['Tech', 'Technical Score', 1], ['Fund', 'Fundamental Score', 1], ['RSI', 'RSI 14', 1], ['ROC 3M', 'ROC 3M %', 2], ['1Y CAGR', '1Y CAGR %', 2], ['PE', 'PE Ratio', 1], ['PB', 'PB Ratio', 1], ['EV/EBITDA', 'EV/EBITDA', 1], ['ROE', 'ROE %', 1], ['ROCE', 'ROCE %', 1], ['D/E', 'Debt/Equity', 2], ['Div%', 'Dividend Yield %', 2], ['SD 1Y', 'SD 1Y %', 1]];
  const prow = (r, self) => `<tr ${self ? 'class="self"' : `data-sym="${r.Symbol}"`}><td>${stockLabel(r)}</td>${PC.map(([l, fld, dec]) => `<td>${f2(r[fld], dec)}</td>`).join('')}</tr>`;
  return `<div class="pc-sec">Peers — ${d.Industry || ''} · ${d['Cap Category'] || ''}</div>
    <div class="pc-scroll"><table class="pc-table"><thead><tr><th>Stock</th>${PC.map(([l]) => `<th>${l}</th>`).join('')}</tr></thead>
    <tbody>${prow(d, true)}${peers.map(r => prow(r, false)).join('')}</tbody></table></div>
    <button class="pc-live" style="background:transparent;border:1px solid var(--border);color:var(--text2)" onclick="closePanel();window.openInStocks([${JSON.stringify(d.Symbol)},${peers.map(p => JSON.stringify(p.Symbol)).join(',')}].map(s=>window.ALL.find(x=>x.Symbol===s)),'Peers of ${tk(d.Symbol)}')">Open peers in grid (all columns) →</button>`;
}
function openPanel(d) {
  const chg = d['Day Change %'];
  document.getElementById('panelBody').innerHTML = `
    <div class="pc-h1">${tk(d.Symbol)}</div>
    <div class="pc-name-row">${d.Name || ''}</div>
    <div class="pc-sub">${d.Sector||''} · ${d.Industry||''} · ${d['Cap Category']||''}</div>
    <span class="pc-price">₹${f2(d['Current Price'])}</span>
    <span class="${chg>0?'pos':chg<0?'neg':''}" style="font-family:'JetBrains Mono';font-weight:600;margin-left:8px">${chg>0?'+':''}${f2(chg)}%</span>
    <div class="pc-badges">
      <span class="badge ${INS[d['Technical Insight']]||''}">TECH: ${d['Technical Insight']||'—'}</span>
      <span class="badge ${INS[d['Fundamental Insight']]||''}">FUND: ${d['Fundamental Insight']||'—'}</span></div>
    <div class="pc-reason">${insightReason(d)}</div>
    ${d.Description ? `<div class="pc-desc">${d.Description}</div>` : ''}
    <div class="pc-sec">Scores &amp; Regime</div>
    <div class="pc-scores">${bar('Composite',d['Composite Score'])}${bar('Technical',d['Technical Score'])}${bar('Momentum',d['Momentum Score'])}${bar('Fundamental',d['Fundamental Score'])}</div>
    <div class="pc-grid" style="margin-top:10px">${row('Regime',d['Market Regime'])}${row('Drawdown',d['Drawdown Status'])}${row('Universe Rank',d['Universe Rank'])}${row('Mkt Cap (Cr)',d['Market Cap (Cr)'])}</div>
    <div class="pc-sec">Technicals</div>
    <div class="pc-grid">${row('RSI 14',f2(d['RSI 14']))}${row('Supertrend',d['Supertrend'])}${row('MACD',d['MACD Signal'])}${row('EMA Cross',d['EMA Cross'])}${row('EMA 50',f2(d['EMA 50']))}${row('EMA 200',f2(d['EMA 200']))}</div>
    <div class="pc-sec">Returns</div>
    <div class="pc-grid">${row('ROC 1M %',f2(d['ROC 1M %']))}${row('ROC 3M %',f2(d['ROC 3M %']))}${row('ROC 6M %',f2(d['ROC 6M %']))}${row('1Y CAGR %',f2(d['1Y CAGR %']))}${row('RS vs Nifty 3M',f2(d['RS vs Nifty 3M %']))}${row('3Y CAGR %',f2(d['3Y CAGR %']))}</div>
    <div class="pc-sec">Valuation &amp; Quality</div>
    <div class="pc-grid">${row('PE',f2(d['PE Ratio']))}${row('Sector PE',f2(d['Sector PE']))}${row('ROE %',f2(d['ROE %']))}${row('ROCE %',f2(d['ROCE %']))}${row('D/E',f2(d['Debt/Equity']))}${row('Div Yield %',f2(d['Dividend Yield %']))}</div>
    ${analystSection(d)}
    ${screensSection(d)}
    ${peersSection(d)}
    <div class="pc-sec">Live data (lazy)</div>
    <button class="pc-live" onclick="loadLive('${d.Symbol}',this)">Load financials &amp; news →</button>
    <div class="pc-note">Everything above is instant from the daily static JSON. This button calls the serverless function (functions/api/stock.js) for the few fields that must be live.</div>`;
  panel.classList.add('open'); scrim.classList.add('open');
  document.querySelectorAll('#panelBody .pc-table tr[data-sym]').forEach(tr => tr.onclick = () => { const r = (window.ALL || []).find(x => x.Symbol === tr.dataset.sym); if (r) openPanel(r); });
}
window.openPanel = openPanel;

window.loadLive = async (sym, btn) => {
  btn.disabled = true; btn.textContent = 'Loading…';
  try {
    const j = await fetch(`/api/stock?symbol=${encodeURIComponent(sym)}`).then(r => { if(!r.ok) throw new Error(r.status); return r.json(); });
    btn.insertAdjacentHTML('afterend', `<div class="pc-note">Live: price ₹${j.regularMarketPrice ?? '—'}, 52W ${j.fiftyTwoWeekLow ?? '—'}–${j.fiftyTwoWeekHigh ?? '—'}</div>`);
    btn.textContent = 'Loaded ✓';
  } catch (e) {
    btn.textContent = 'Load financials & news →'; btn.disabled = false;
    btn.insertAdjacentHTML('afterend', `<div class="pc-note">⚠ Serverless function not running locally — deploy to Cloudflare Pages / Vercel. (${e})</div>`);
  }
};

// data freshness stamp (build writes it; fallback to fetch time)
fetch('data/stocks.json', { method: 'HEAD' }).then(r => {
  const lm = r.headers.get('last-modified');
  if (lm) { const d = new Date(lm), p = n => String(n).padStart(2, '0'); document.getElementById('freshness').textContent = `Data: ${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()}`; }
}).catch(() => {});
