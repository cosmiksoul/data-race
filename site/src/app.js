(() => {
'use strict';
const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
const PAGE = JSON.parse(document.getElementById('d-page').textContent);
const DATA = JSON.parse(document.getElementById('d-sites').textContent);
const US = JSON.parse(document.getElementById('d-us').textContent);
const css = () => getComputedStyle(document.documentElement);
const col = n => css().getPropertyValue(n).trim();
const nf1 = new Intl.NumberFormat('ru-RU', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const nf0 = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 });
const nf2 = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 });
const el = (t, c, x) => { const e = document.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; };
const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
const ease = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
const lerp = (a, b, t) => a + (b - a) * t;
const plural = (n, one, few, many) => { const a = n % 10, b = n % 100; return a === 1 && b !== 11 ? one : a >= 2 && a <= 4 && (b < 12 || b > 14) ? few : many; };
const fmtD = d => d.toISOString().slice(0, 10).split('-').reverse().join('.');
const money = v => '$' + (v >= 1 ? nf1.format(v).replace(/,0$/, '') : nf2.format(v));
const kv = pairs => { const k = el('div', 'kv'); pairs.forEach(([a, b]) => k.append(el('span', '', a), el('b', '', b))); return k; };

/* ── тема ── */
const root = document.documentElement, themeBtn = document.getElementById('themeBtn');
const THEMES = ['auto', 'light', 'dark'], TL = { auto: 'авто', light: 'светлая', dark: 'тёмная' };
const themeLabel = () => { themeBtn.textContent = 'Тема: ' + TL[root.dataset.theme]; };
function setTheme(t) { root.dataset.theme = t; themeLabel(); try { localStorage.setItem('sch-theme', t); } catch (e) {} redrawAll(); }
if (!THEMES.includes(root.dataset.theme)) root.dataset.theme = 'auto';
themeLabel();
themeBtn.addEventListener('click', () => setTheme(THEMES[(THEMES.indexOf(root.dataset.theme) + 1) % 3]));
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => redrawAll());

/* ── подсказки ── */
const tip = document.getElementById('tip');
function showTip(node, x, y) { tip.replaceChildren(node); tip.classList.add('on'); placeTip(x, y); }
function placeTip(x, y) { const r = tip.getBoundingClientRect(); let L = x + 14, T = y + 14; if (L + r.width > innerWidth - 8) L = x - r.width - 14; if (T + r.height > innerHeight - 8) T = y - r.height - 14; tip.style.left = Math.max(8, L) + 'px'; tip.style.top = Math.max(8, T) + 'px'; }
function hideTip() { tip.classList.remove('on'); }
addEventListener('keydown', e => { if (e.key === 'Escape') hideTip(); });
// подсказка для элемента: мышь, касание и фокус с клавиатуры
function bindTip(node, build) {
  const at = e => e && e.clientX != null ? [e.clientX, e.clientY] : (r => [r.right, r.bottom])(node.getBoundingClientRect());
  node.addEventListener('pointerenter', e => showTip(build(), ...at(e)));
  node.addEventListener('pointermove', e => placeTip(e.clientX, e.clientY));
  node.addEventListener('pointerleave', hideTip);
  node.addEventListener('focus', () => showTip(build(), ...at()));
  node.addEventListener('blur', hideTip);
}
document.querySelectorAll('.term').forEach(t => {
  const g = PAGE.gloss[t.dataset.term]; if (!g) return;
  t.tabIndex = 0; t.setAttribute('aria-description', g[0] + '. ' + g[1]);
  bindTip(t, () => { const f = document.createDocumentFragment(); f.append(el('div', 't', g[0]), el('div', '', g[1])); return f; });
});

/* ── счёт ── */
const BILL = PAGE.bill;
const billList = document.getElementById('billList'), billEmpty = document.getElementById('billEmpty');
const barList = document.getElementById('barList'), bar = document.getElementById('receiptBar'), billCount = document.getElementById('billCount');
const barBtn = document.getElementById('receiptBarBtn');
const printed = new Set(), ORDER = Object.keys(BILL);
function billItem(b) {
  const li = el('li', b.side);
  const top = el('div'); top.append(el('span', 'sgn', b.side === 'debit' ? '−' : '+'), el('span', 'no', b.no + ' · '), el('span', 'ttl', b.ttl));
  li.append(top, el('div', '', b.val), el('span', 'who', b.who), el('span', 'tg', b.tg));
  li.setAttribute('aria-label', `Строка ${b.no}, ${b.side === 'debit' ? 'дебет' : 'кредит'}: ${b.ttl} — ${b.val}; ${b.who}; ${b.tg}`);
  return li;
}
const receiptBox = document.getElementById('receipt');
let pinned = null, lastKey = null; // pinned — позиция, которую читатель развернул сам; lastKey — последняя напечатанная
function setCompact(li, on) { li.classList.toggle('compact', on); li.setAttribute('aria-expanded', String(!on)); }
function fitReceipt() {
  const items = [...billList.querySelectorAll('li[data-no]')]; if (!items.length || !receiptBox.offsetParent) return;
  const cur = items.filter(li => li.dataset.key === lastKey).map(li => li.dataset.no)[0] || items[items.length - 1].dataset.no;
  items.forEach(li => setCompact(li, li !== pinned && li.dataset.no !== cur));
  // если текущий блок не помещается, сворачиваем его старые позиции, последняя остаётся раскрытой
  for (let i = 0; i < items.length - 1 && receiptBox.scrollHeight > receiptBox.clientHeight; i++) if (items[i] !== pinned) setCompact(items[i], true);
}
billList.addEventListener('click', e => { const li = e.target.closest('li[data-no]'); if (!li) return; pinned = li.classList.contains('compact') ? li : null; fitReceipt(); });
billList.addEventListener('keydown', e => { if ((e.key === 'Enter' || e.key === ' ') && e.target.matches('li[data-no]')) { e.preventDefault(); e.target.click(); } });
function printBill(key) {
  if (printed.has(key) || !BILL[key]) return; printed.add(key); lastKey = key;
  if (billEmpty) billEmpty.remove();
  const li = billItem(BILL[key]); li.dataset.no = BILL[key].no; li.tabIndex = 0; li.setAttribute('role', 'button');
  // строки стоят в порядке документа, даже если читатель перескочил по ссылке
  const idx = ORDER.indexOf(key), after = l => [...l.children].find(c => ORDER.indexOf(c.dataset.key) > idx) || null;
  li.dataset.key = key; const li2 = billItem(BILL[key]); li2.dataset.key = key;
  billList.insertBefore(li, after(billList)); barList.insertBefore(li2, after(barList)); fitReceipt();
  billCount.textContent = printed.size; document.getElementById('billWord').textContent = plural(printed.size, 'строка', 'строки', 'строк'); bar.classList.add('on');
}
barBtn.addEventListener('click', () => { const o = bar.classList.toggle('open'); barBtn.setAttribute('aria-expanded', String(o)); });
// строка печатается, когда абзац-якорь поднялся выше 65% высоты экрана; пройденные при быстром переходе
// (ссылка, клавиша End) тоже печатаются — поэтому проверка при прокрутке, а не IntersectionObserver
const anchors = [...document.querySelectorAll('[data-bill]')].filter(n => n.dataset.bill !== '00');
function checkBills() { for (const n of anchors) if (!printed.has(n.dataset.bill) && n.getBoundingClientRect().top < innerHeight * .65) printBill(n.dataset.bill); }

/* ═══ ШТАБ И ПЕРЕХОД ═══ */
const hq = document.getElementById('hq'), stage = document.getElementById('stage');
const svg = d3.select('#stageSvg'), hqUi = document.getElementById('hqUi'), opening = document.getElementById('opening');
const hqNum = document.getElementById('hqNum');
const gMap = svg.append('g'), gGlow = svg.append('g'), gDots = svg.append('g');
const defs = svg.append('defs');
const grad = defs.append('radialGradient').attr('id', 'glow');
[['0%', '#ffffff', .95], ['22%', '#8fe3ff', .85], ['60%', '#8fe3ff', .18], ['100%', '#8fe3ff', 0]].forEach(([o, c, a]) => grad.append('stop').attr('offset', o).attr('stop-color', c).attr('stop-opacity', a));
const states = topojson.feature(US, US.objects.states), nation = topojson.feature(US, US.objects.nation);
const sites = DATA.sites;
const TODAY = DATA.today;
const [ty, tm] = TODAY.split('-').map(Number);
const months = d3.timeMonths(new Date(Date.UTC(2021, 0, 1)), new Date(Date.UTC(ty, tm, 1))).map(d => d.toISOString().slice(0, 7));
const monthEnd = ym => { const [y, m] = ym.split('-').map(Number); return new Date(Date.UTC(y, m, 0)).toISOString().slice(0, 10); };
const powAt = (s, D) => { let p = 0; for (const t of s.tl) { if (t[0] <= D) p = t[1]; else break; } return p; };
let W = 0, H = 0, proj;
const rScale = d3.scaleSqrt().domain([0, 2500]).range([0, 20]);
let dots = [], grid = null, laidOut = false;
let playT = 1; // 0..1 автопроигрывание
let lastP = -1;

function layoutStage() {
  W = stage.clientWidth; H = stage.clientHeight;
  laidOut = W > 0 && H > 0;
  if (!laidOut) return; // сцены не видно — разложим точки, когда у окна появится размер
  svg.attr('viewBox', `0 0 ${W} ${H}`);
  const mob = W < 720;
  // карта — справа от преамбулы (на телефоне — между преамбулой и счётчиком): меряем, а не угадываем
  const sr0 = stage.getBoundingClientRect(), pre = hqUi.querySelector('.hq-pre'), heroTop = hqUi.querySelector('.hq-hero').getBoundingClientRect().top - sr0.top;
  const pr = pre ? pre.getBoundingClientRect() : null;
  const box = mob ? [[W * .04, (pr ? pr.bottom - sr0.top : H * .2) + 14], [W * .96, Math.max((pr ? pr.bottom - sr0.top : H * .2) + 134, heroTop - 14)]]
                  : [[Math.max(W * .3, pr ? pr.right - sr0.left + 40 : W * .08), H * .1], [W * .97, H * .86]];
  proj = d3.geoAlbersUsa().fitExtent(box, nation);
  rScale.range([0, Math.max(9, Math.min(22, W / 60))]);
  const path = d3.geoPath(proj);
  gMap.selectAll('*').remove();
  gMap.append('g').selectAll('path').data(states.features).join('path').attr('d', path).attr('fill', '#0e141b').attr('stroke', '#1b2430').attr('stroke-width', .6);
  gMap.append('path').datum(nation).attr('d', path).attr('fill', 'none').attr('stroke', '#2a3746');
  // позиции площадок; площадки вне США прилетают справа
  let off = 0; const offN = sites.filter(s => !proj(s.ll)).length;
  sites.forEach(s => { const p = proj(s.ll); if (p) { s.xy = p; s.off = false; } else { s.xy = [W + 30, H * (.2 + .6 * (off++ / Math.max(1, offN - 1)))]; s.off = true; } });
  // сетка единиц: 1 точка = 100 МВт
  const nF = sites.reduce((a, s) => a + s.dt, 0), nH = sites.reduce((a, s) => a + s.dp, 0), N = nF + nH;
  let gx0, gy0, gw, gh;
  const cols = 22;
  if (mob) { // сетка между заголовком и подписью: меряем их, а не угадываем
    const sr = stage.getBoundingClientRect(), ib = opening.querySelector('.intro').getBoundingClientRect().bottom - sr.top, ct = opening.querySelector('.cap').getBoundingClientRect().top - sr.top;
    gx0 = 16; gw = W - 32; gy0 = ib + 18; gh = Math.max(120, ct - 18 - gy0); }
  else { gx0 = W * .47; gw = Math.min(W * .47, 640); gy0 = H * .14; gh = H * .74; }
  const rows = Math.ceil(N / cols); const step = Math.min(gw / cols, gh / rows);
  if (mob) gx0 = 16 + (gw - step * cols) / 2;
  const r = step * .28;
  const order = sites.slice().sort((a, b) => b.t - a.t);
  dots = []; let k = 0;
  const cell = i => [gx0 + (i % cols) * step + step / 2, gy0 + Math.floor(i / cols) * step + step / 2];
  order.forEach(s => { for (let j = 0; j < s.dt; j++) { const [x1, y1] = cell(k); const a = (j * 2.39996) % (2 * Math.PI), rr = Math.sqrt(j) * 3; dots.push({ x0: s.xy[0] + Math.cos(a) * rr, y0: s.xy[1] + Math.sin(a) * rr, x1, y1, fill: true, s, i: k }); k++; } });
  const orderP = sites.slice().sort((a, b) => b.dp - a.dp);
  orderP.forEach(s => { for (let j = 0; j < s.dp; j++) { const [x1, y1] = cell(k); dots.push({ x0: x1, y0: y1, x1, y1, fill: false, s, i: k }); k++; } });
  dots.forEach(d => { d.r = r; d.delay = d.fill ? (d.i / nF) * .28 : ((d.i - nF) / nH) * .2; });
  gDots.selectAll('circle').data(dots).join('circle').attr('r', r);
  gGlow.selectAll('g.site').data(sites.filter(s => !s.off)).join(enter => { const g = enter.append('g').attr('class', 'site'); g.append('circle').attr('class', 'halo').attr('fill', 'url(#glow)'); g.append('circle').attr('class', 'core').attr('fill', '#eefaff'); return g; }).attr('transform', s => `translate(${s.xy[0]},${s.xy[1]})`);
  grid = { gx0, gy0, step, cols, N };
  lastP = -1; render();
}

function renderGlow(D) {
  gGlow.selectAll('g.site').each(function (s) { const p = powAt(s, D); const R = rScale(p); d3.select(this).select('.halo').attr('r', p > 0 ? R * 2.3 : 0); d3.select(this).select('.core').attr('r', p > 0 ? Math.max(1.4, R * .28) : 0); });
  return sites.reduce((a, s) => a + powAt(s, D), 0);
}

// окно нулевой высоты (фоновая вкладка, превью, скрытый фрейм) даёт 0 / 0 — считаем, что переход не начат
function progress() { const r = hq.getBoundingClientRect(); const total = r.height - innerHeight; return total > 0 ? clamp(-r.top / total) : 0; }
const phase = () => clamp((progress() - .12) / .74);

function render() {
  const P = progress();
  if (P === lastP && playT >= 1) return; lastP = P;
  const t = clamp((P - .12) / .74); // фаза перехода
  const paper = col('--paper'), ink = col('--ink');
  const bgT = ease(clamp(t / .35));
  stage.style.background = d3.interpolateRgb('#07090d', paper)(bgT);
  gMap.attr('opacity', 1 - clamp(t / .12));
  // автопроигрывание и счётчик
  const mi = Math.round(lerp(0, months.length - 1, playT)); const ym = months[mi];
  const D = playT >= 1 ? TODAY : monthEnd(ym);
  const tot = renderGlow(D);
  hqNum.firstChild.nodeValue = nf1.format(tot / 1000);
  gGlow.attr('opacity', 1 - clamp(t / .14));
  hqUi.style.opacity = 1 - clamp(t / .15);
  hqUi.style.visibility = t > .15 ? 'hidden' : '';
  opening.style.opacity = ease(clamp((t - .72) / .2));
  opening.style.pointerEvents = t > .9 ? 'auto' : 'none';
  opening.inert = t <= .9; // пока подпись не видна, её термины не попадают в порядок Tab
  if (t > .95) printBill('00');
  // точки
  const glowC = d3.color('#8fe3ff'), inkC = d3.color(ink);
  gDots.selectAll('circle').each(function (d) {
    const c = d3.select(this);
    if (d.fill) {
      const u = RM ? (t > .5 ? 1 : 0) : ease(clamp((t - .08 - d.delay) / .42));
      const vis = t <= 0 ? 0 : clamp(t / .08);
      const powered = powAt(d.s, D) > 0 || t > 0;
      c.attr('cx', lerp(d.x0, d.x1, u)).attr('cy', lerp(d.y0, d.y1, u))
       .attr('fill', d3.interpolateRgb(glowC, inkC)(Math.max(bgT, clamp(u * 1.4)))).attr('stroke', 'none')
       .attr('opacity', powered ? vis : 0);
    } else {
      const u = RM ? (t > .6 ? 1 : 0) : ease(clamp((t - .62 - d.delay) / .16));
      c.attr('cx', d.x1).attr('cy', d.y1).attr('fill', 'none').attr('stroke', ink).attr('stroke-width', 1).attr('opacity', u);
    }
  });
}

// автопроигрывание 2021 → сегодня; над картой стоит преамбула, поэтому ролик ждёт,
// пока сцена не займёт почти весь экран, — иначе он отыграет, пока читают текст
function autoplay() {
  if (RM) { playT = 1; render(); return; }
  playT = 0; lastP = -1; render();
  const inView = () => innerHeight > 0 && hq.getBoundingClientRect().top <= innerHeight * .3;
  const start = () => {
    const t0 = performance.now(), dur = 6500;
    const step = now => { if (progress() > .02) { playT = 1; lastP = -1; render(); return; } playT = clamp((now - t0) / dur); lastP = -1; render(); if (playT < 1) requestAnimationFrame(step); };
    requestAnimationFrame(step);
  };
  if (inView()) { start(); return; }
  const wait = () => { if (inView()) { removeEventListener('scroll', wait); removeEventListener('resize', wait); start(); } };
  addEventListener('scroll', wait, { passive: true }); addEventListener('resize', wait);
}
let ticking = false;
addEventListener('scroll', () => { if (!ticking) { ticking = true; requestAnimationFrame(() => { ticking = false; render(); checkBills(); }); } }, { passive: true });

// подсказка по точкам сетки в финальном кадре
svg.on('pointermove', e => {
  if (phase() < .95 || !grid) { hideTip(); return; }
  const [x, y] = d3.pointer(e);
  const c = Math.floor((x - grid.gx0) / grid.step), r = Math.floor((y - grid.gy0) / grid.step);
  if (c < 0 || c >= grid.cols || r < 0) { hideTip(); return; }
  const d = dots[r * grid.cols + c]; if (!d) { hideTip(); return; }
  const f = document.createDocumentFragment(); f.append(el('div', 't', d.s.n));
  f.append(kv([['Работает сегодня', nf0.format(d.s.t) + ' МВт'], ['В планах к концу 2028 года', nf0.format(d.s.e) + ' МВт']]),
    el('div', 'note', d.fill ? 'Закрашенная точка — 100 МВт, которые уже работают' : 'Полая точка — 100 МВт в планах'));
  showTip(f, e.clientX, e.clientY);
}).on('pointerleave', hideTip);

/* ═══ ГРАФИКИ ═══ */
// Реестр: CHARTS[id] = (svg, spec, opts) → рисует в d3-выделение svg.
// spec — данные из пакета: data (CSV по имени файла), labels, annotations, tooltip.
const CHARTS = {};
// значок лаборатории: OpenAI — круг, Anthropic — квадрат, Google — ромб
function shape(sel, lab, r) {
  if (lab === 'OpenAI') return sel.append('circle').attr('r', r);
  if (lab === 'Anthropic') return sel.append('rect').attr('x', -r * .9).attr('y', -r * .9).attr('width', r * 1.8).attr('height', r * 1.8);
  return sel.append('path').attr('d', `M0 ${-r * 1.2} L${r * 1.2} 0 L0 ${r * 1.2} L${-r * 1.2} 0Z`);
}
// точка графика с подсказкой: зона нажатия 26 px, фокус с клавиатуры
function mark(parent, x, y, label, build) {
  const g = parent.append('g').attr('class', 'mark').attr('transform', `translate(${x},${y})`).attr('tabindex', 0).attr('role', 'img').attr('aria-label', label);
  g.append('circle').attr('class', 'hit').attr('r', 13).attr('fill', 'transparent');
  bindTip(g.node(), build);
  return g;
}
const tipNode = (title, pairs, note) => { const f = document.createDocumentFragment(); f.append(el('div', 't', title)); if (pairs && pairs.length) f.append(kv(pairs)); if (note) f.append(el('div', 'note', note)); return f; };
const before = (s, sep = ' — ') => String(s || '').split(sep)[0].trim();

/*__CHARTS__*/

const figs = [...document.querySelectorAll('figure[data-chart]')];
function draw(fig, opts = {}) {
  const id = fig.dataset.chart, s = d3.select(fig.querySelector(':scope > svg'));
  s.selectAll('*').remove();
  if (!CHARTS[id]) {
    if (!fig.querySelector('.nochart')) fig.querySelector(':scope > svg').replaceWith(Object.assign(el('div', 'nochart', 'График в работе'), { role: 'img' }));
    return;
  }
  CHARTS[id](s, PAGE.charts[id], opts);
}
const drawCharts = () => figs.forEach(f => draw(f));
const shown = new Set();
const figObs = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting && !shown.has(e.target)) { shown.add(e.target); draw(e.target, { animate: true }); } }), { threshold: .4 });
figs.forEach(f => figObs.observe(f));

function redrawAll() { lastP = -1; render(); drawCharts(); }
let rT, lastW = innerWidth;
addEventListener('resize', () => { clearTimeout(rT); rT = setTimeout(() => {
  // на телефоне адресная строка меняет высоту окна при прокрутке — сетку перестраиваем только при смене ширины
  if (!laidOut || innerWidth !== lastW || innerWidth >= 720) { lastW = innerWidth; layoutStage(); drawCharts(); }
  fitReceipt();
}, 150); });
layoutStage(); drawCharts(); autoplay(); checkBills();
if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { layoutStage(); drawCharts(); });
window.__sch = { printBill, phase, grid: () => grid };
})();
