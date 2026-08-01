// funds.js — Mutual Fund screener. Data is data/funds.json, built by scripts/fetch_funds.py
// from AMFI NAV files (latest NAV + 5 years of month-end NAVs → returns, SD, Sharpe, drawdown).
(function () {
  let FUNDS = null, api = null;
  let curSortCol = '3Y CAGR %', curSortDir = 'desc', curSub = 'all', curScreen = null;
  const $ = id => document.getElementById(id);
  const C = (field, o = {}) => ({ field, headerName: o.h || field, ...o });

  // shared numeric/colour helpers from app.js so Funds looks identical to Stocks
  const num = (f, d = 2, w) => window.numCol(f, d, w);

  const nameCol = C('Scheme Name', {
    pinned: 'left', width: 300, cellClass: 'cell-name', filter: 'agTextColumnFilter',
    // the plan/option suffix is noise in a list — the Plan column carries it
    valueFormatter: p => (p.value || '').replace(/\s*-\s*(direct|regular)\s*(plan)?\s*-?\s*(growth)?\s*(option)?\s*$/i, ''),
    tooltipValueGetter: p => p.value,
  });

  const COLS = [
    nameCol, C('Fund House', { width: 190 }), C('Category', { width: 210 }), C('Plan', { width: 90 }),
    num('NAV', 2, 95), num('1Y Return %', 2, 110), num('3Y CAGR %', 2, 105), num('5Y CAGR %', 2, 105),
    num('SD (Annualised) %', 2, 130), num('Sharpe (3Y)', 2, 105), num('Max Drawdown %', 2, 130),
    num('Positive Months %', 1, 130), num('3Y Rank in Category', 0, 140), num('1Y Rank in Category', 0, 140),
    num('History (Months)', 0, 120),
  ];
  const MOBILE = ['NAV', '1Y Return %', '3Y CAGR %'];
  const cols = () => window.compactCols(COLS, MOBILE, curSortCol);

  // pre-built screens — same idea as the stock screens, expressed as row predicates
  const SCREENS = [
    { name: 'Top 3Y performers', desc: 'Rank 1–5 in their category on 3-year CAGR', tag: 'returns',
      fn: r => r['3Y Rank in Category'] != null && r['3Y Rank in Category'] <= 5 },
    { name: 'Consistent compounders', desc: '3Y and 5Y CAGR both above 12%, drawdown better than −25%', tag: 'quality',
      fn: r => r['3Y CAGR %'] > 12 && r['5Y CAGR %'] > 12 && r['Max Drawdown %'] > -25 },
    { name: 'Best risk-adjusted', desc: 'Sharpe (3Y) above 1 — return well ahead of volatility', tag: 'risk',
      fn: r => r['Sharpe (3Y)'] > 1 },
    { name: 'Low volatility', desc: 'Annualised SD under 10% with a positive 3Y CAGR', tag: 'risk',
      fn: r => r['SD (Annualised) %'] != null && r['SD (Annualised) %'] < 10 && r['3Y CAGR %'] > 0 },
    { name: 'Steady month to month', desc: 'Positive in 65%+ of months over the period', tag: 'quality',
      fn: r => r['Positive Months %'] >= 65 },
    { name: 'Index funds', desc: 'Passive funds tracking an index', tag: 'type',
      fn: r => r.Category === 'Other Scheme - Index Funds' },
  ];

  const sortBy = (rows, col, dir) => {
    if (!col) return rows;
    const sign = dir === 'asc' ? 1 : -1;
    return rows.slice().sort((a, b) => {
      const x = a[col], y = b[col];
      const xn = x == null || x === '', yn = y == null || y === '';
      if (xn && yn) return 0; if (xn) return 1; if (yn) return -1;   // blanks last, both directions
      if (typeof x === 'number' && typeof y === 'number') return sign * (x - y);
      return sign * String(x).localeCompare(String(y));
    });
  };

  // ── dynamic filter builder (mirrors the Stocks / index-drill builders) ──
  const FILT_COLS = () => COLS.map(c => c.field);
  const isNumCol = col => {
    let n = 0, t = 0;
    for (const r of FUNDS) { const v = r[col]; if (v == null || v === '') continue; t++; if (typeof v === 'number') n++; }
    return t > 0 && n / t > 0.9;
  };
  const colVals = col => [...new Set(FUNDS.map(r => r[col]).filter(v => v != null && v !== ''))]
    .sort((a, b) => String(a).localeCompare(String(b)));

  function buildVal(wrap, col) {
    wrap.innerHTML = '';
    if (!col) return;
    if (isNumCol(col)) {
      wrap.innerHTML = `<input class="ctl fp-num f-min" type="number" placeholder="min"><span class="f-dash">–</span><input class="ctl fp-num f-max" type="number" placeholder="max">`;
      wrap.querySelectorAll('input').forEach(i => i.addEventListener('input', compute));
    } else {
      wrap.innerHTML = `<select class="ctl f-sel"><option value="">Any value</option>${colVals(col).map(v => `<option>${v}</option>`).join('')}</select>`;
      wrap.querySelector('select').addEventListener('change', compute);
    }
  }
  function addFilterRow() {
    const bar = $('fundFilterbar');
    const waiting = [...bar.querySelectorAll('.filtrow')].find(d => !d.querySelector('.f-col').value);
    if (waiting) return waiting.querySelector('.f-col').focus();   // don't stack empty rows
    const div = document.createElement('div'); div.className = 'filtrow';
    const colSel = document.createElement('select'); colSel.className = 'ctl f-col';
    colSel.innerHTML = `<option value="">Choose column…</option>` + FILT_COLS().map(c => `<option value="${c}">${c}</option>`).join('');
    const valWrap = document.createElement('span'); valWrap.className = 'f-val';
    const rm = document.createElement('button'); rm.className = 'rm'; rm.title = 'remove'; rm.textContent = '✕';
    rm.onclick = () => { div.remove(); if (!bar.children.length) bar.hidden = true; compute(); };
    colSel.onchange = () => { buildVal(valWrap, colSel.value); compute(); };
    div.append(colSel, valWrap, rm);
    bar.appendChild(div); bar.hidden = false;
  }
  const readFilters = () => [...document.querySelectorAll('#fundFilterbar .filtrow')].map(d => {
    const col = d.querySelector('.f-col').value; if (!col) return null;
    const sel = d.querySelector('.f-sel');
    if (sel) return { col, type: 'cat', v: sel.value };
    return { col, type: 'num', min: (d.querySelector('.f-min') || {}).value || '', max: (d.querySelector('.f-max') || {}).value || '' };
  }).filter(Boolean);
  function matchF(r, f) {
    if (f.type === 'cat') return !f.v || String(r[f.col]) === f.v;
    const v = parseFloat(r[f.col]), mn = parseFloat(f.min), mx = parseFloat(f.max);
    if (!isNaN(mn) && !(v >= mn)) return false;
    if (!isNaN(mx) && !(v <= mx)) return false;
    return true;
  }

  function compute() {
    if (!api) return;
    const q = $('fundSearch').value.trim().toLowerCase();
    const cat = $('fundCat').value, plan = $('fundPlan').value;
    const filters = readFilters();
    let rows = FUNDS.filter(r =>
      (!q || (r['Scheme Name'] || '').toLowerCase().includes(q) || (r['Fund House'] || '').toLowerCase().includes(q)) &&
      (!cat || r.Category === cat) && (!plan || r.Plan === plan) &&
      filters.every(f => matchF(r, f)));
    if (curSub === 'screens' && curScreen) rows = rows.filter(curScreen.fn);
    api.setGridOption('rowData', sortBy(rows, curSortCol, curSortDir));
    $('fundCount').textContent = `${rows.length} funds`;
    setTimeout(() => window.refitGrid(api), 30);
  }

  function renderScreens() {
    $('fundScreencards').innerHTML = SCREENS.map((s, i) =>
      `<div class="scard${curScreen === s ? ' active' : ''}" data-si="${i}"><h4>${s.name}</h4><p>${s.desc}</p></div>`).join('');
  }

  window.initFunds = async function () {
    if (api) return;
    try { FUNDS = await fetch('data/funds.json').then(r => r.json()); }
    catch (e) { $('fundCount').textContent = 'Failed to load data/funds.json'; return; }

    api = agGrid.createGrid($('fundGrid'), {
      columnDefs: cols(), defaultColDef: { sortable: false, resizable: true, filter: true },
      rowSelection: 'single', animateRows: true,
      autoSizeStrategy: window.autoSizeStrategy(),
      onFirstDataRendered: p => window.refitGrid(p.api),
    });

    const cats = [...new Set(FUNDS.map(r => r.Category).filter(Boolean))].sort();
    $('fundCat').innerHTML = '<option value="">All categories</option>' + cats.map(c => `<option>${c}</option>`).join('');
    $('fundSortCol').innerHTML = COLS.map(c => `<option value="${c.field}"${c.field === curSortCol ? ' selected' : ''}>${c.field}</option>`).join('');
    $('fundSortDir').value = curSortDir;
    const asOf = FUNDS.find(r => r['NAV Date']);
    $('fundAsOf').textContent = asOf ? `· NAV as of ${asOf['NAV Date']} · monthly NAV history from AMFI` : '';
    renderScreens();
    compute();
  };

  $('fundsub').addEventListener('click', e => {
    const b = e.target.closest('.sub'); if (!b) return;
    curSub = b.dataset.fsub;
    document.querySelectorAll('#fundsub .sub').forEach(x => x.classList.toggle('active', x === b));
    $('fundScreenwrap').hidden = curSub !== 'screens';
    if (curSub !== 'screens') curScreen = null;
    renderScreens(); compute();
  });
  $('fundScreencards').addEventListener('click', e => {
    const card = e.target.closest('.scard'); if (!card) return;
    const s = SCREENS[+card.dataset.si];
    curScreen = curScreen === s ? null : s;          // click again to clear
    renderScreens(); compute();
  });
  $('fundSearch').addEventListener('input', compute);
  $('fundCat').addEventListener('change', compute);
  $('fundPlan').addEventListener('change', compute);
  $('fundSortCol').addEventListener('change', () => {
    curSortCol = $('fundSortCol').value;
    api.setGridOption('columnDefs', cols());          // compact mode keeps the sorted column visible
    compute();
  });
  $('fundSortDir').addEventListener('change', () => { curSortDir = $('fundSortDir').value; compute(); });
  $('fundAddFilterBtn').addEventListener('click', addFilterRow);
  $('fundExportBtn').addEventListener('click', () => api && api.exportDataAsCsv({ fileName: 'screenedge_funds.csv' }));
  window.addEventListener('colsmode', () => { if (api) { api.setGridOption('columnDefs', cols()); compute(); } });
})();
