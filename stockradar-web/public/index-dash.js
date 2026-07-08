// index-dash.js — Phase 3. Index Dashboard: Indian indices + Global, with drill-down
// (A/D, gainers/losers with 5/10/15 toggle, RS-vs-selected-index computed on the fly).
(function () {
  let INDICES = null, GLOBAL = null, idxApi = null, drillApi = null;
  let curISub = 'indian', curDView = 'overview', curDrillRows = [], curIndexName = '';
  let curIdxSortCol = 'Day Change %', curIdxSortDir = 'desc';
  const $ = id => document.getElementById(id);
  const num = (v, d = 2) => (v == null || v === '' || isNaN(v)) ? '' : Number(v).toFixed(d);
  const C = (field, o = {}) => ({ field, headerName: o.h || field, ...o });
  const parts = s => (s || '').split(/[;,]/).map(x => x.trim());
  // dropdown-driven sort (mirrors the Stocks tab): blanks always last
  const sortBy = (rows, col, dir) => {
    if (!col) return rows;
    const sign = dir === 'asc' ? 1 : -1;
    return rows.slice().sort((a, b) => {
      let x = a[col], y = b[col];
      const xn = x == null || x === '', yn = y == null || y === '';
      if (xn && yn) return 0; if (xn) return 1; if (yn) return -1;
      if (typeof x === 'number' && typeof y === 'number') return sign * (x - y);
      return sign * String(x).localeCompare(String(y));
    });
  };

  const IDX_COLS = [
    C('Index', { pinned: 'left', width: 200, cellClass: 'cell-name', filter: 'agTextColumnFilter' }),
    C('Category', { width: 130 }), C('Available ETF', { width: 120 }),
    C('Market Regime', { cellRenderer: window.regimeRenderer, width: 112 }),
    window.numCol('Current Price', 2, 105), window.numCol('Day Change %', 2, 100),
    window.numCol('RSI 14', 1, 85), C('MACD Signal', { width: 110 }), C('Supertrend', { width: 105 }),
    window.numCol('ROC 1M %', 2), window.numCol('ROC 3M %', 2), window.numCol('ROC 6M %', 2),
    window.numCol('1Y CAGR %', 2), window.numCol('RS vs Nifty 3M %', 2, 140),
    window.numCol('PE Ratio', 1, 90), window.numCol('Dividend Yield %', 2, 125),
  ];
  const GLB_COLS = [
    C('Name', { pinned: 'left', width: 160, cellClass: 'cell-name', filter: 'agTextColumnFilter' }),
    C('Category', { width: 120 }), C('Market Regime', { cellRenderer: window.regimeRenderer, width: 112 }),
    window.numCol('Current Price', 2, 110), window.numCol('Day Change %', 2, 100),
    window.numCol('RSI 14', 1, 85), C('MACD Signal', { width: 110 }), C('Supertrend', { width: 105 }),
    window.numCol('ROC 1M %', 2), window.numCol('ROC 3M %', 2), window.numCol('ROC 6M %', 2),
    window.numCol('1Y CAGR %', 2), window.numCol('SD 1Y %', 2, 100), C('Drawdown Status', { cellRenderer: window.ddRenderer, width: 120 }),
  ];

  window.initIndex = async function () {
    if (idxApi) return;
    try { [INDICES, GLOBAL] = await Promise.all([fetch('data/indices.json').then(r => r.json()), fetch('data/global.json').then(r => r.json())]); }
    catch (e) { return; }
    try { await ensureData(); } catch (e) { }
    idxApi = agGrid.createGrid($('idxGrid'), {
      columnDefs: IDX_COLS, defaultColDef: { sortable: false, resizable: true, filter: true },
      rowSelection: 'single', animateRows: true,
      onRowClicked: e => { if (curISub === 'indian') openDrill(e.data); },
    });
    const cats = [...new Set(INDICES.map(r => r.Category).filter(Boolean))].sort();
    $('idxCat').innerHTML = '<option value="">All categories</option>' + cats.map(c => `<option>${c}</option>`).join('');
    fillIdxSort();
    applyIdx();
  };

  // populate the Sort-by dropdown from the current sub-tab's columns, keeping selection if still valid
  function fillIdxSort() {
    const cols = (curISub === 'indian' ? IDX_COLS : GLB_COLS).map(c => c.field);
    if (!cols.includes(curIdxSortCol)) curIdxSortCol = cols.includes('Day Change %') ? 'Day Change %' : cols[0];
    $('idxSortCol').innerHTML = cols.map(c => `<option value="${c}"${c === curIdxSortCol ? ' selected' : ''}>${c}</option>`).join('');
    $('idxSortDir').value = curIdxSortDir;
  }

  function applyIdx() {
    const q = $('idxSearch').value.trim().toLowerCase(), cat = $('idxCat').value;
    if (curISub === 'indian') {
      idxApi.setGridOption('columnDefs', IDX_COLS);
      const rows = INDICES.filter(r => (!q || (r.Index || '').toLowerCase().includes(q)) && (!cat || r.Category === cat));
      idxApi.setGridOption('rowData', sortBy(rows, curIdxSortCol, curIdxSortDir));
    } else {
      idxApi.setGridOption('columnDefs', GLB_COLS);
      const rows = GLOBAL.filter(r => !q || (r.Name || '').toLowerCase().includes(q));
      idxApi.setGridOption('rowData', sortBy(rows, curIdxSortCol, curIdxSortDir));
    }
  }

  $('idxsub').addEventListener('click', e => {
    const b = e.target.closest('.sub'); if (!b) return;
    curISub = b.dataset.isub;
    document.querySelectorAll('#idxsub .sub').forEach(x => x.classList.toggle('active', x === b));
    $('idxCat').style.display = curISub === 'indian' ? '' : 'none';
    fillIdxSort();
    applyIdx();
  });
  $('idxSearch').addEventListener('input', applyIdx);
  $('idxCat').addEventListener('change', applyIdx);
  $('idxSortCol').addEventListener('change', () => { curIdxSortCol = $('idxSortCol').value; applyIdx(); });
  $('idxSortDir').addEventListener('change', () => { curIdxSortDir = $('idxSortDir').value; applyIdx(); });

  // ── drill-down ──
  function drillViews() {
    const V = window.VIEWS;
    const rsCol = p => ({ field: `RS vs ${curIndexName} ${p} %`, headerName: `RS vs Idx ${p} %`, type: 'numericColumn', valueFormatter: window.numFmt(2), cellClass: window.grClass, width: 150, filter: 'agNumberColumnFilter' });
    return {
      overview: V.overview, technicals: V.technicals, risk: V.risk, fundamentals: V.fundamentals,
      returns: [...V.returns, rsCol('1M'), rsCol('3M'), rsCol('6M'), rsCol('12M')],
    };
  }

  function openDrill(idxRow) {
    curIndexName = idxRow.Index;
    const cons = window.ALL.filter(r => parts(r['Index Membership']).includes(curIndexName));
    const i1 = idxRow['ROC 1M %'], i3 = idxRow['ROC 3M %'], i6 = idxRow['ROC 6M %'], i12 = idxRow['1Y CAGR %'];
    const rs = (v, iv) => (v != null && iv != null) ? +(v - iv).toFixed(2) : null;
    curDrillRows = cons.map(r => ({
      ...r,
      [`RS vs ${curIndexName} 1M %`]: rs(r['ROC 1M %'], i1),
      [`RS vs ${curIndexName} 3M %`]: rs(r['ROC 3M %'], i3),
      [`RS vs ${curIndexName} 6M %`]: rs(r['ROC 6M %'], i6),
      [`RS vs ${curIndexName} 12M %`]: rs(r['ROC 12M %'], i12),
    }));

    const chg = idxRow['Day Change %'];
    $('drillHead').innerHTML = `${curIndexName}<span class="dh-sub">${idxRow.Category || ''} · ₹${num(idxRow['Current Price'])} <span class="${chg > 0 ? 'pos' : chg < 0 ? 'neg' : ''}">${chg > 0 ? '+' : ''}${num(chg)}%</span> · ${idxRow['Market Regime'] || ''}</span>${idxRow['Available ETF'] ? `<span class="dh-etf">ETF: ${idxRow['Available ETF']}</span>` : ''}`;

    const adv = cons.filter(r => r['Day Change %'] > 0).length, dec = cons.filter(r => r['Day Change %'] < 0).length, unch = cons.filter(r => r['Day Change %'] === 0).length;
    $('drillCards').innerHTML = [['Advances', adv], ['Declines', dec], ['Unchanged', unch], ['A/D Ratio', dec ? (adv / dec).toFixed(2) : adv], ['Constituents', cons.length]]
      .map(([l, v]) => `<div class="ad-card"><div class="ad-v">${v}</div><div class="ad-l">${l}</div></div>`).join('');
    renderGL(+$('glCount').value);

    if (!drillApi) drillApi = agGrid.createGrid($('drillGrid'), {
      columnDefs: drillViews().overview, defaultColDef: { sortable: true, resizable: true, filter: true },
      rowSelection: 'single', animateRows: true, onRowClicked: e => window.openPanel && window.openPanel(e.data),
    });
    curDView = 'overview';
    document.querySelectorAll('#drillViewtabs .vt').forEach(x => x.classList.toggle('active', x.dataset.dview === 'overview'));
    drillApi.setGridOption('columnDefs', drillViews().overview);
    drillApi.setGridOption('rowData', curDrillRows);
    $('idxList').hidden = true; $('idxDrill').hidden = false;
  }

  function renderGL(n) {
    const sorted = curDrillRows.filter(r => r['Day Change %'] != null).slice().sort((a, b) => b['Day Change %'] - a['Day Change %']);
    const gain = sorted.slice(0, n), lose = sorted.slice(-n).reverse();
    const rowHtml = r => `<div class="gl-row" data-sym="${r.Symbol}"><span class="g-name">${window.stockLabel(r)}</span><span>₹${num(r['Current Price'])}</span><span class="${r['Day Change %'] > 0 ? 'pos' : 'neg'}">${r['Day Change %'] > 0 ? '+' : ''}${num(r['Day Change %'])}%</span></div>`;
    $('glWrap').innerHTML = `<div class="gl-col"><h4 class="pos">Top Gainers</h4>${gain.map(rowHtml).join('') || '<p class="empty">—</p>'}</div><div class="gl-col"><h4 class="neg">Top Losers</h4>${lose.map(rowHtml).join('') || '<p class="empty">—</p>'}</div>`;
    $('glWrap').querySelectorAll('.gl-row').forEach(c => c.onclick = () => { const r = window.ALL.find(x => x.Symbol === c.dataset.sym); if (r && window.openPanel) window.openPanel(r); });
  }
  $('glCount').addEventListener('change', () => renderGL(+$('glCount').value));

  $('drillViewtabs').addEventListener('click', e => {
    const b = e.target.closest('.vt'); if (!b) return;
    document.querySelectorAll('#drillViewtabs .vt').forEach(x => x.classList.remove('active'));
    b.classList.add('active'); curDView = b.dataset.dview;
    const sort = drillApi.getColumnState().filter(c => c.sort).map(c => ({ colId: c.colId, sort: c.sort, sortIndex: c.sortIndex }));
    drillApi.setGridOption('columnDefs', drillViews()[curDView]);
    if (sort.length) drillApi.applyColumnState({ state: sort });
  });
  $('drillBack').addEventListener('click', () => { $('idxDrill').hidden = true; $('idxList').hidden = false; });
})();
