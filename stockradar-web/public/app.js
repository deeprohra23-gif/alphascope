// ScreenEdge — web app. Data is static JSON built daily by scripts/build_data.py (reuses the real scoring/insights).

// shared stock-identifier helpers: ticker (clean, .NS stripped) as primary, name muted beside it
const tk = s => (s || '').replace(/\.(NS|BO)$/, '');
const stockLabel = r => `<span class="tk">${tk(r.Symbol)}</span> <span class="nm">${r.Name || ''}</span>`;

const GREEN_RED = new Set(['Day Change %','ROC 1M %','ROC 3M %','ROC 6M %','1Y CAGR %','3Y CAGR %','5Y CAGR %',
  'RS vs Nifty 1M %','RS vs Nifty 3M %','RS vs Nifty 6M %','RS vs Nifty 12M %','% from 52W High','% from 52W Low',
  '1Y Max Drawdown %','Sales Growth 1Y %','Sales Growth 3Y %','Profit Growth 1Y %','Profit Growth 3Y %',
  'EPS Growth 1Y %','EPS Growth 3Y %','FCF Yield %','FII Change %','DII Change %','Momentum Acceleration','Capture Ratio']);

const numFmt = d => p => (p.value == null || p.value === '' || isNaN(p.value)) ? '' : Number(p.value).toFixed(d);
// keep numbers right-aligned (matches the numericColumn header) AND add the green/red class.
// A colDef cellClass overrides numericColumn's built-in 'ag-right-aligned-cell', so we must re-add it.
const grClass = p => 'ag-right-aligned-cell' + (p.value > 0 ? ' pos' : p.value < 0 ? ' neg' : '');

const INS = {'Strong Buy':'ins-sb','Buy':'ins-b','Hold':'ins-h','Sell':'ins-s','Strong Sell':'ins-ss'};
const insightRenderer = p => p.value ? `<span class="badge ${INS[p.value]||''}">${p.value}</span>` : '';
const REG = {'Strong Bull':'rg-sbull','Bull':'rg-bull','Bear':'rg-bear','Strong Bear':'rg-sbear'};
const regimeRenderer = p => p.value ? `<span class="${REG[p.value]||''}">${p.value}</span>` : '';
const DD = {'At High':'dd-high','Recovering':'dd-rec','Correcting':'dd-cor','Damaged':'dd-dam'};
const ddRenderer = p => p.value ? `<span class="${DD[p.value]||''}">${p.value}</span>` : '';

const C = (field, o = {}) => ({ field, headerName: o.h || field, ...o });
const numCol = (field, d = 2, w) => C(field, { type:'numericColumn', valueFormatter:numFmt(d), cellClass:GREEN_RED.has(field)?grClass:'ag-right-aligned-cell', width:w, filter:'agNumberColumnFilter' });
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
let SCREENS_META = [], mode = 'all', selScreen = null, FILTER_COLS = [], SORT_ORDER = [], externalRows = null;
let curSortCol = 'Composite Score', curSortDir = 'desc';
// columns whose values are ;/,-joined lists → matched with "contains" and expanded in the value dropdown
const MULTI_COLS = new Set(['Index Membership']);

const gridOptions = {
  columnDefs: VIEWS.overview,
  defaultColDef: { sortable:false, resizable:true, filter:true },   // sorting is driven by the Sort-by dropdown
  rowSelection: 'single', animateRows: true,
  autoSizeStrategy: { type: 'fitCellContents' },   // size every column to its content
  onRowClicked: e => openPanel(e.data),
  onFirstDataRendered: p => p.api.autoSizeAllColumns(),
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
    buildScreens();
    FILTER_COLS = Object.keys(ALL[0]).filter(k => !['Screens', 'Description'].includes(k));
    // shared column order (used by both the Sort-by dropdown and the "+ Filter" column picker) — key ones first
    const SORT_PREF = ['Composite Score', 'Momentum Score', 'Technical Score', 'Fundamental Score', 'Universe Rank', 'Market Cap (Cr)', 'Current Price', 'Day Change %', 'RSI 14', 'ROC 1M %', 'ROC 3M %', 'ROC 6M %', '1Y CAGR %', '3Y CAGR %', 'PE Ratio', 'ROE %', 'ROCE %', 'Debt/Equity', 'Dividend Yield %', 'Name', 'Sector', 'Industry'];
    SORT_ORDER = [...SORT_PREF.filter(c => FILTER_COLS.includes(c)), ...FILTER_COLS.filter(c => !SORT_PREF.includes(c)).sort()];
    $('sortCol').innerHTML = SORT_ORDER.map(c => `<option value="${c}"${c === curSortCol ? ' selected' : ''}>${c}</option>`).join('');
    $('sortDir').value = curSortDir;
    addCondRow();
    computeRows();
  })();
  return _stocksInit;
}

// ── unified row computation (source → shared filters) ──
const getChecked = cid => [...document.querySelectorAll(`#${cid} input:checked`)].map(i => i.value);
function sortRows(rows) {
  const col = curSortCol, sign = curSortDir === 'asc' ? 1 : -1;
  return rows.slice().sort((a, b) => {
    let x = a[col], y = b[col];
    const xn = x == null || x === '', yn = y == null || y === '';
    if (xn && yn) return 0; if (xn) return 1; if (yn) return -1;   // blanks always last
    if (typeof x === 'number' && typeof y === 'number') return sign * (x - y);
    return sign * String(x).localeCompare(String(y));
  });
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
  const q = val('search').trim().toLowerCase();
  const filters = readFilters();
  const rows = sourceRows().filter(r =>
    (!q || `${r.Name} ${r.Symbol}`.toLowerCase().includes(q)) &&
    filters.every(f => matchFilter(r, f)));
  gridApi.setGridOption('rowData', sortRows(rows));
  const si = $('sortInfo'); if (si) si.textContent = `· sorted by ${curSortCol} ${curSortDir === 'desc' ? '▼' : '▲'}`;
}

// ── dynamic "+ Filter" builder (pick any column → categorical dropdown or numeric min/max) ──
function colIsNumeric(col) {
  let num = 0, tot = 0;
  for (const r of ALL) {
    const v = r[col]; if (v == null || v === '') continue;
    tot++; if (typeof v === 'number' || (!isNaN(parseFloat(v)) && isFinite(v))) num++;
    if (tot >= 300) break;
  }
  return tot > 0 && num / tot > 0.9;
}
function colValues(col) {
  const raw = MULTI_COLS.has(col)
    ? ALL.flatMap(r => String(r[col] ?? '').split(/[;,]/).map(s => s.trim()))
    : ALL.map(r => r[col]);
  return [...new Set(raw.filter(v => v != null && v !== ''))].sort((a, b) => String(a).localeCompare(String(b)));
}
function buildValControl(wrap, col) {
  wrap.innerHTML = '';
  if (!col) return;
  if (colIsNumeric(col)) {
    wrap.innerHTML = `<input class="ctl fp-num f-min" type="number" placeholder="min"><span class="f-dash">–</span><input class="ctl fp-num f-max" type="number" placeholder="max">`;
    wrap.querySelectorAll('input').forEach(i => i.addEventListener('input', computeRows));
  } else {
    wrap.innerHTML = `<select class="ctl f-sel"><option value="">Any value</option>${colValues(col).map(v => `<option>${v}</option>`).join('')}</select>`;
    wrap.querySelector('select').addEventListener('change', computeRows);
  }
}
function addFilterRow(preCol) {
  const div = document.createElement('div'); div.className = 'filtrow';
  const colSel = document.createElement('select'); colSel.className = 'ctl f-col';
  colSel.innerHTML = `<option value="">Choose column…</option>` + SORT_ORDER.map(c => `<option value="${c}">${c}</option>`).join('');
  const valWrap = document.createElement('span'); valWrap.className = 'f-val';
  const rm = document.createElement('button'); rm.className = 'rm'; rm.title = 'remove'; rm.textContent = '✕';
  rm.onclick = () => { div.remove(); if (!$('filterbar').children.length) $('filterbar').hidden = true; computeRows(); };
  colSel.onchange = () => { buildValControl(valWrap, colSel.value); computeRows(); };
  div.append(colSel, valWrap, rm);
  $('filterbar').appendChild(div);
  $('filterbar').hidden = false;
  if (preCol) { colSel.value = preCol; buildValControl(valWrap, preCol); }
}
function readFilters() {
  return [...document.querySelectorAll('#filterbar .filtrow')].map(d => {
    const col = d.querySelector('.f-col').value; if (!col) return null;
    const sel = d.querySelector('.f-sel');
    if (sel) return { col, type: 'cat', v: sel.value };
    return { col, type: 'num', min: (d.querySelector('.f-min') || {}).value || '', max: (d.querySelector('.f-max') || {}).value || '' };
  }).filter(Boolean);
}
function matchFilter(r, f) {
  if (f.type === 'cat') {
    if (!f.v) return true;
    if (MULTI_COLS.has(f.col)) return String(r[f.col] ?? '').split(/[;,]/).map(s => s.trim()).includes(f.v);
    return String(r[f.col]) === f.v;
  }
  const v = parseFloat(r[f.col]), mn = parseFloat(f.min), mx = parseFloat(f.max);
  if (!isNaN(mn) && !(v >= mn)) return false;
  if (!isNaN(mx) && !(v <= mx)) return false;
  return true;
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
$('addFilterBtn').addEventListener('click', () => addFilterRow());
$('addCond').addEventListener('click', addCondRow);
$('runCustom').addEventListener('click', computeRows);

document.getElementById('viewtabs').addEventListener('click', e => {
  const btn = e.target.closest('.vt'); if (!btn) return;
  document.querySelectorAll('.vt').forEach(b => b.classList.remove('active'));
  btn.classList.add('active'); curView = btn.dataset.view;
  gridApi.setGridOption('columnDefs', VIEWS[curView]);   // row order (sort) is preserved automatically
  setTimeout(() => gridApi.autoSizeAllColumns(), 30);    // re-fit widths to the new columns
});

$('search').addEventListener('input', computeRows);
$('sortCol').addEventListener('change', () => { curSortCol = $('sortCol').value; computeRows(); });
$('sortDir').addEventListener('change', () => { curSortDir = $('sortDir').value; computeRows(); });
$('exportBtn').addEventListener('click', () => gridApi.exportDataAsCsv({ fileName: `screenedge_${curView}.csv` }));

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
  return `<div class="pc-sec">Projections &amp; Analyst Targets</div><div class="pc-grid">
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
    <button class="pc-live" style="background:transparent;border:1px solid var(--border);color:var(--text2)" id="peerGridBtn" data-syms="${[d.Symbol, ...peers.map(p => p.Symbol)].join(',')}" data-label="Peers of ${tk(d.Symbol)}">Open peers in grid (all columns) →</button>`;
}
// full ratios table (all from the daily static data)
function ratiosSection(d) {
  const G = [
    ['Valuation', ['PE Ratio', 'Sector PE', 'PB Ratio', 'Sector PB', 'EV/EBITDA', 'PEG Ratio']],
    ['Profitability', ['ROE %', 'ROE 3Y Avg %', 'ROCE %', 'ROCE 3Y Avg %', 'ROA %', 'Net Profit Margin %']],
    ['Growth', ['Sales Growth 1Y %', 'Sales Growth 3Y %', 'Profit Growth 1Y %', 'Profit Growth 3Y %', 'EPS Growth 1Y %', 'EPS Growth 3Y %']],
    ['Earnings', ['EPS Current', 'EPS Last Year', 'Net Profit (Cr)', 'Net Profit Prev (Cr)']],
    ['Balance Sheet & Cash', ['Debt/Equity', 'Interest Coverage', 'Free Cash Flow (Cr)', 'FCF Yield %']],
    ['Ownership', ['Promoter Holding %', 'Pledge %', 'FII Change %', 'DII Change %']],
    ['Dividends', ['Dividend Yield %', 'Dividend Payout %']],
  ];
  const has = G.map(([t, fs]) => [t, fs.filter(f => f in d)]).filter(([t, fs]) => fs.length);
  if (!has.length) return '';
  return `<div class="pc-sec">Financials &amp; Ratios</div>` + has.map(([title, fs]) =>
    `<div class="pc-subh">${title}</div><div class="pc-grid">${fs.map(f => row(f, f2(d[f], 2))).join('')}</div>`).join('');
}

// ── multi-year Earnings Trajectory + projections (live from /api/financials) ──
const fyLabel = ds => 'FY' + String(ds).slice(2, 4);
function finTable(cols, rows, estCount) {
  const est = i => (estCount && i >= cols.length - estCount) ? ' class="est"' : '';
  const head = cols.map((c, i) => `<th${est(i)}>${c}</th>`).join('');
  const body = rows.map(([lab, cells]) => `<tr><td class="fin-lab">${lab}</td>${cells.map((c, i) => `<td${est(i)}>${c}</td>`).join('')}</tr>`).join('');
  return `<div class="pc-scroll"><table class="fin-table"><thead><tr><th></th>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}
function renderFinancials(d, S) {
  const rev = S.annualTotalRevenue || [];
  if (rev.length < 2) return null;
  const dates = rev.map(x => x.d);
  const map = arr => { const m = {}; (arr || []).forEach(x => m[x.d] = x.v); return m; };
  const R = map(S.annualTotalRevenue), NI = map(S.annualNetIncome), EPS = map(S.annualBasicEPS), EBITDA = map(S.annualEBITDA),
    EBIT = map(S.annualEBIT), INT = map(S.annualInterestExpense), DEBT = map(S.annualTotalDebt),
    EQ = map(S.annualStockholdersEquity), CASH = map(S.annualCashAndCashEquivalents), FCF = map(S.annualFreeCashFlow);
  const cr = v => v == null ? null : v / 1e7;
  const fys = dates.map(fyLabel);
  const revA = dates.map(dt => cr(R[dt])), niA = dates.map(dt => cr(NI[dt])), epsA = dates.map(dt => EPS[dt] ?? null);
  const cagr = a => { const x = a.filter(v => v != null && !isNaN(v)); if (x.length < 2 || x[0] <= 0) return null; return Math.pow(x[x.length - 1] / x[0], 1 / (x.length - 1)) - 1; };
  const revCAGR = cagr(revA), profCAGR = cagr(niA);
  const cand = [revCAGR, profCAGR].filter(v => v != null);
  let g = cand.length ? cand.reduce((s, v) => s + v, 0) / cand.length : 0.05;
  g = Math.max(0.03, Math.min(0.20, g));
  const lastNum = +fys[fys.length - 1].slice(2);
  const eFY = k => 'FY' + String(lastNum + k).padStart(2, '0') + '(E)';
  const lr = revA[revA.length - 1], ln = niA[niA.length - 1], le = epsA[epsA.length - 1];
  const projRev = [lr * (1 + g), lr * (1 + g) ** 2], projNi = [ln * (1 + g), ln * (1 + g) ** 2];
  const projEps = [le == null ? null : le * (1 + g), le == null ? null : le * (1 + g) ** 2];
  const price = d['Current Price'];
  const crF = v => v == null || isNaN(v) ? '—' : Math.round(v).toLocaleString('en-IN');
  const n1 = (v, dp = 1) => v == null || isNaN(v) ? '—' : (+v).toFixed(dp);
  const pe = e => (price && e) ? n1(price / e) + 'x' : '—';
  const pct = v => v == null || isNaN(v) ? '—' : (v * 100).toFixed(1) + '%';

  const traj = finTable([...fys, eFY(1), eFY(2)], [
    ['Revenue (Cr)', [...revA.map(crF), ...projRev.map(crF)]],
    ['Net Profit (Cr)', [...niA.map(crF), ...projNi.map(crF)]],
    ['EPS', [...epsA.map(v => n1(v)), ...projEps.map(v => n1(v))]],
    ['P/E · Fwd', [...epsA.map((v, i) => i === epsA.length - 1 ? pe(v) : '—'), ...projEps.map(pe)]],
  ], 2);
  const mg = (num, den) => dates.map(dt => (num[dt] != null && den[dt]) ? num[dt] / den[dt] : null);
  const kr = finTable(fys, [
    ['EBITDA Margin', mg(EBITDA, R).map(pct)], ['Net Margin', mg(NI, R).map(pct)], ['ROE', mg(NI, EQ).map(pct)],
  ], 0);
  const fh = finTable(fys, [
    ['Debt/Equity', dates.map(dt => (DEBT[dt] != null && EQ[dt]) ? n1(DEBT[dt] / EQ[dt], 2) : '—')],
    ['Net Debt/EBITDA', dates.map(dt => (DEBT[dt] != null && EBITDA[dt]) ? n1((DEBT[dt] - (CASH[dt] || 0)) / EBITDA[dt], 2) + 'x' : '—')],
    ['Int Coverage', dates.map(dt => (EBIT[dt] != null && INT[dt]) ? n1(EBIT[dt] / INT[dt]) + 'x' : '—')],
    ['FCF (Cr)', dates.map(dt => crF(cr(FCF[dt])))],
    ['FCF/Profit', dates.map(dt => (FCF[dt] != null && NI[dt]) ? (FCF[dt] / NI[dt] * 100).toFixed(1) + '%' : '—')],
  ], 0);

  return `<div class="pc-fin-h">Earnings Trajectory</div>${traj}
    <div class="pc-fin-note">Revenue CAGR ${pct(revCAGR)} · Profit CAGR ${pct(profCAGR)} · Projection uses ${(g * 100).toFixed(1)}%</div>
    <div class="pc-fin-h">Key Ratios</div>${kr}
    <div class="pc-fin-h">Financial Health</div>${fh}
    <div class="pc-note">Projections are a simple extrapolation of historical growth. Actual results will vary. Not investment advice.</div>`;
}
async function loadFinancials(d) {
  const el = document.getElementById('pcFin'); if (!el) return;
  try {
    const j = await fetch(`/api/financials?symbol=${encodeURIComponent(tk(d.Symbol))}`).then(r => r.json());
    el.innerHTML = (j && j.series && renderFinancials(d, j.series)) || ratiosSection(d);
  } catch (e) {
    el.innerHTML = ratiosSection(d);
  }
}
async function loadNews(d) {
  const el = document.getElementById('pcNews'); if (!el) return;
  try {
    const j = await fetch(`/api/news?q=${encodeURIComponent(d.Name || tk(d.Symbol))}`).then(r => r.json());
    const items = (j && j.items) || [];
    el.innerHTML = items.length ? items.map(n =>
      `<a class="news-item" href="${n.link}" target="_blank" rel="noopener noreferrer"><div class="news-t">${n.title}</div><div class="news-m">${n.source || ''}${n.pub ? ' · ' + new Date(n.pub).toLocaleDateString('en-GB') : ''}</div></a>`).join('')
      : '<div class="pc-note">No recent news found.</div>';
  } catch (e) {
    el.innerHTML = '<div class="pc-note">News unavailable right now.</div>';
  }
}
// the always-on, static sections of the card (2-column grid)
function cardSections(d) {
  const N = v => (v == null || v === '') ? '—' : Number(v).toFixed(2);
  const P = v => (v == null || v === '') ? '—' : Number(v).toFixed(2) + '%';
  const M = v => (v == null || v === '') ? '—' : '₹' + Number(v).toFixed(2);
  const C = (v, suf = '') => { if (v == null || v === '') return '—'; const n = +v; if (isNaN(n)) return String(v); return `<span class="${n > 0 ? 'pos' : n < 0 ? 'neg' : ''}">${n.toFixed(2)}${suf}</span>`; };
  const pair = (a, b, fmt = N) => `${fmt(a)} / ${fmt(b)}`;
  const card = (title, rows) => `<div class="pc-card"><h4>${title}</h4>${rows.map(([l, v]) => `<div class="pc-row"><span class="k">${l}</span><span class="v">${v}</span></div>`).join('')}</div>`;

  const scores = `<div class="pc-card"><h4>Scores &amp; Regime</h4>
    ${bar('Technical', d['Technical Score'])}${bar('Momentum', d['Momentum Score'])}${bar('Fundamental', d['Fundamental Score'])}${bar('Composite', d['Composite Score'])}
    <div class="pc-row"><span class="k">Universe Rank</span><span class="v">${d['Universe Rank'] ?? '—'}</span></div>
    <div class="pc-row"><span class="k">Market Regime</span><span class="v">${d['Market Regime'] || '—'}</span></div>
    <div class="pc-row"><span class="k">Drawdown Status</span><span class="v">${d['Drawdown Status'] || '—'}</span></div></div>`;
  const tech = card('Technical Signals', [
    ['EMA 50 / 200', pair(d['EMA 50'], d['EMA 200'])], ['EMA Cross', d['EMA Cross'] || '—'],
    ['RSI 14', N(d['RSI 14'])], ['MACD', d['MACD Signal'] || '—'], ['Supertrend', d['Supertrend'] || '—'],
    ['Trend Consistency', d['Trend Consistency (12M)'] != null ? d['Trend Consistency (12M)'] + '/12' : '—'],
    ['Vol Trend', d['Vol Trend'] || '—'],
  ]);
  const ret = card('Returns & Momentum', [
    ['ROC 1M', C(d['ROC 1M %'], '%')], ['ROC 3M', C(d['ROC 3M %'], '%')], ['ROC 6M', C(d['ROC 6M %'], '%')],
    ['1Y CAGR', C(d['1Y CAGR %'], '%')], ['3Y CAGR', C(d['3Y CAGR %'], '%')],
    ['RS vs Nifty 1M/3M/6M', `${C(d['RS vs Nifty 1M %'])} / ${C(d['RS vs Nifty 3M %'])} / ${C(d['RS vs Nifty 6M %'])}`],
    ['Momentum Quality', N(d['Momentum Quality'])],
  ]);
  const risk = card('Risk', [
    ['Beta 1Y', N(d['Beta 1Y (Daily)'])], ['SD 1Y', P(d['SD 1Y %'])], ['ATR %', P(d['ATR % (14D)'])],
    ['Max Drawdown 1Y', C(d['1Y Max Drawdown %'], '%')], ['52W High / Low', pair(d['52W High'], d['52W Low'], M)],
    ['From 52W High', C(d['% from 52W High'], '%')], ['Capture Ratio', N(d['Capture Ratio'])],
  ]);
  const val = card('Valuation & Profitability', [
    ['PE / Sector PE', pair(d['PE Ratio'], d['Sector PE'])], ['PB / Sector PB', pair(d['PB Ratio'], d['Sector PB'])],
    ['EV/EBITDA', N(d['EV/EBITDA'])], ['PEG Ratio', N(d['PEG Ratio'])],
    ['ROE / ROCE', `${P(d['ROE %'])} / ${P(d['ROCE %'])}`], ['Net Profit Margin', P(d['Net Profit Margin %'])],
    ['D/E Ratio', N(d['Debt/Equity'])],
  ]);
  const grow = card('Growth &amp; Ownership', [
    ['Sales Growth 1Y / 3Y', `${C(d['Sales Growth 1Y %'], '%')} / ${C(d['Sales Growth 3Y %'], '%')}`],
    ['Profit Growth 1Y / 3Y', `${C(d['Profit Growth 1Y %'], '%')} / ${C(d['Profit Growth 3Y %'], '%')}`],
    ['EPS Growth 1Y', C(d['EPS Growth 1Y %'], '%')], ['FCF Yield', P(d['FCF Yield %'])],
    ['Div Yield / Payout', `${P(d['Dividend Yield %'])} / ${P(d['Dividend Payout %'])}`],
    ['Promoter Holding', P(d['Promoter Holding %'])], ['Pledge %', P(d['Pledge %'])],
    ['FII / DII Change', `${C(d['FII Change %'], '%')} / ${C(d['DII Change %'], '%')}`],
  ]);
  return `<div class="pc-cards">${scores}${tech}${ret}${risk}${val}${grow}</div>`;
}
// map a card section header's text → icon name, then prepend the inline icon
function cardHeaderIcon(txt) {
  const t = (txt || '').toLowerCase();
  if (t.includes('scores') || t.includes('regime')) return 'gauge';
  if (t.includes('technical')) return 'activity';
  if (t.includes('returns') || t.includes('momentum')) return 'trending';
  if (t.includes('risk')) return 'shield';
  if (t.includes('valuation') || t.includes('profitab')) return 'scale';
  if (t.includes('growth') || t.includes('ownership')) return 'sprout';
  if (t.includes('analyst')) return 'target';
  if (t.includes('financ')) return 'bars';
  if (t.includes('screen')) return 'grid';
  if (t.includes('peers')) return 'users';
  if (t.includes('news')) return 'newspaper';
  return null;
}
function decorateCardHeaders() {
  if (!window.icon) return;
  document.querySelectorAll('#panelBody .pc-card h4, #panelBody .pc-sec').forEach(h => {
    const n = cardHeaderIcon(h.textContent); if (n) h.insertAdjacentHTML('afterbegin', window.icon(n));
  });
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
    ${cardSections(d)}
    <div class="pc-sec">Financials &amp; Projections</div>
    <div id="pcFin" class="pc-fin"><div class="pc-note">Loading multi-year financials…</div></div>
    ${analystSection(d)}
    ${screensSection(d)}
    ${peersSection(d)}
    <div class="pc-sec">Recent News</div>
    <div id="pcNews" class="pc-news"><div class="pc-note">Loading news…</div></div>`;
  panel.classList.add('open'); scrim.classList.add('open');
  decorateCardHeaders();
  document.querySelectorAll('#panelBody .pc-table tr[data-sym]').forEach(tr => tr.onclick = () => { const r = (window.ALL || []).find(x => x.Symbol === tr.dataset.sym); if (r) openPanel(r); });
  const pgb = document.getElementById('peerGridBtn');
  if (pgb) pgb.onclick = () => { closePanel(); window.openInStocks(pgb.dataset.syms.split(',').map(s => (window.ALL || []).find(x => x.Symbol === s)).filter(Boolean), pgb.dataset.label); };
  loadFinancials(d);   // fetch + render the multi-year trajectory (falls back to static ratios on failure)
  loadNews(d);         // fetch recent headlines
}
window.openPanel = openPanel;

// data freshness stamp — prefer the real EOD trading date from changes.json ("today"), fall back to file mtime
(function stampFreshness() {
  const el = document.getElementById('freshness'); if (!el) return;
  const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const fmtISO = iso => { const [y, m, d] = iso.split('-').map(Number); return `${d} ${MON[m - 1]} ${y}`; };
  const show = txt => { el.innerHTML = `<span class="fresh-badge" title="End-of-day data — refreshed after NSE market close on trading days">EOD</span><span class="fresh-txt">Updated ${txt}</span>`; };
  fetch('data/changes.json').then(r => r.json()).then(j => {
    if (j && j.today) show(fmtISO(j.today)); else throw 0;
  }).catch(() => {
    fetch('data/stocks.json', { method: 'HEAD' }).then(r => {
      const lm = r.headers.get('last-modified');
      show(lm ? new Date(lm).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) : '—');
    }).catch(() => show('—'));
  });
})();
