/* ── строка 07 · графики ─────────────────────────────────────────────
   Данные — CSV из пакета content/07-strany.md; подписи, аннотации и строка
   «с учётом аренды за рубежом» берутся из полей form / annotations пакета. */

const quote07 = t => (/«([^»]+)»/.exec(t || '') || [])[1] || '';
const num07 = t => parseFloat(String(t).replace(',', '.'));
const r1_07 = v => v < 0.3 ? nf2.format(Math.round(v * 100 + 1e-9) / 100) : nf1.format(Math.round(v * 10 + 1e-9) / 10).replace(/,0$/, '');
// перенос подписи по словам: не длиннее n знаков в строке
const wrap07 = (t, n) => String(t).split(' ').reduce((a, w) => { const l = a[a.length - 1]; if (l && (l + ' ' + w).length <= n) a[a.length - 1] = l + ' ' + w; else a.push(w); return a; }, []);
const lines07 = (s, x, y, lines, cls, anchor = 'start', lh = 14) => {
  const t = s.append('text').attr('class', cls).attr('x', x).attr('y', y).attr('text-anchor', anchor);
  lines.forEach((ln, k) => t.append('tspan').attr('x', x).attr('dy', k ? lh : 0).text(ln));
  return t;
};
// отрезок-диапазон с подсказкой: зона нажатия — весь отрезок и не меньше 24 px в высоту
function range07(parent, x1, x2, y, label, build) {
  const g = parent.append('g').attr('class', 'mark').attr('tabindex', 0).attr('role', 'img').attr('aria-label', label);
  g.append('rect').attr('class', 'hit').attr('x', Math.min(x1, x2) - 8).attr('y', y - 13).attr('width', Math.abs(x2 - x1) + 16).attr('height', 26).attr('fill', 'transparent');
  bindTip(g.node(), build);
  return g;
}
const date07 = d => d.length === 7 ? ['январь', 'февраль', 'март', 'апрель', 'май', 'июнь', 'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь'][+d.slice(5) - 1] + ' ' + d.slice(0, 4) : fmtD(new Date(d));
const halo07 = t => t.attr('paint-order', 'stroke').attr('stroke', col('--paper')).attr('stroke-width', 4).attr('stroke-linejoin', 'round');

// fig07a · способы измерить Китай: отрезки-диапазоны на общей логарифмической оси
CHARTS.fig07a = (s, spec, opts) => {
  const M = spec.data['07-china-methods'], IND = spec.data['07-indirect'] || [];
  const form = spec.form || '', ann = spec.annotations || [];
  const w = s.node().clientWidth, mob = w < 560;
  const labW = mob ? 0 : Math.min(250, w * .28), m = { l: labW + 14, r: 12 }, labN = Math.floor(labW / 6.6);
  const x = d3.scaleLog().domain([0.1, 10]).range([m.l, w - m.r]);
  const rowH = mob ? 58 : 44, top = mob ? 36 : 26;
  const ink = col('--ink'), ink3 = col('--ink-3');
  const all = M.map(r => ({ name: r.method, lens: r.lens, lo: r.low_mln_h100e, mid: r.mid_mln_h100e, hi: r.high_mln_h100e, date: String(r.date), grp: r.independent_group, note: r.note, claims: r.claim_ids }));
  // основная панель — где стоят чипы; «другая мера» (использование с арендой за рубежом) — отдельной тонкой строкой
  const lens0 = all[0] ? all[0].lens : '', rows = all.filter(r => r.lens === lens0), ct = all.find(r => r.lens !== lens0);
  const ctNote = (/это другая мера:\s*([^.]+)/.exec(form) || [])[1];
  // подпись строки: слева от оси, на телефоне — над строкой; длинная переносится
  const label = (t, xx, y, b) => { const L = wrap07(t, mob ? Math.floor(w / 6.6) : labN);
    return lines07(s, xx, mob ? y - (L.length - 1) * 13 : y - (L.length - 1) * 6.5, L, 'dlbl' + (b ? ' b' : ''), mob ? 'start' : 'end', 13); };
  const band = /Затенённая полоса\s*([\d,]+)–([\d,]+)\s*—\s*([^.]+)/.exec(form);
  const a0 = quote07(ann[0]), a1 = quote07(ann[1]);
  const a0L = a0 && M[0] ? wrap07(a0, Math.floor((w - m.r - x(M[0].low_mln_h100e)) / 6.4)) : [];
  const yRow = k => top + k * rowH + (mob ? 22 : 0) + (k > 0 ? Math.max(0, a0L.length - 1) * 14 : 0) + (mob && k > 1 ? 18 : 0);
  const yCT = yRow(rows.length) + (mob ? 18 : 16);
  const yAxis = (ct ? yCT + (mob ? 30 : 14) : yRow(rows.length - 1)) + (mob ? 40 : 34);
  // панель «Если мерить не чипами»
  const pTitle = (/панель\s*«([^»]+)»/.exec(form) || [])[1];
  const pTop = yAxis + 44, pRowH = mob ? 68 : 40;
  const h = IND.length ? pTop + 24 + IND.length * pRowH + 34 : yAxis + 20;
  s.attr('viewBox', `0 0 ${w} ${h}`).attr('height', h);

  // бумага: общий диапазон и засечки оси
  if (band) {
    const b0 = num07(band[1]), b1 = num07(band[2]);
    s.append('rect').attr('x', x(b0)).attr('width', x(b1) - x(b0)).attr('y', top - (mob ? 4 : 18)).attr('height', yRow(rows.length - 1) - top + (mob ? 30 : 36))
      .attr('fill', col('--grid')).attr('opacity', .55);
    s.append('text').attr('class', 'lbl').attr('x', x(b0) + 4).attr('y', top - (mob ? 10 : 24)).text(`${band[3].trim()}: ${band[1]}–${band[2]}`);
  }
  [0.1, 0.3, 1, 3, 10].forEach(v => {
    s.append('line').attr('class', 'hair').attr('x1', x(v)).attr('x2', x(v)).attr('y1', top - 8).attr('y2', yAxis - 14).attr('stroke-dasharray', '1 3');
    s.append('text').attr('class', 'lbl').attr('x', x(v)).attr('y', yAxis).attr('text-anchor', v === 10 ? 'end' : v === 0.1 ? 'start' : 'middle').text(r1_07(v) + (v === 10 ? ' млн H100e' : ''));
  });

  const g = s.append('g');
  const cap = (gg, xx, y) => gg.append('line').attr('x1', xx).attr('x2', xx).attr('y1', y - 6).attr('y2', y + 6).attr('stroke', ink).attr('stroke-width', 1.4);
  rows.forEach((r, k) => {
    const y = yRow(k);
    label(r.name, mob ? 0 : labW, mob ? y - 16 : y + 4, true);
    const pairs = [['На дату', date07(r.date)], ['Основа', r.grp], ['Строки реестра', r.claims]];
    if (r.hi) {
      const gg = range07(g, x(r.lo), x(r.hi), y, `${r.name}: от ${r1_07(r.lo)} до ${r1_07(r.hi)} млн H100e` + (r.mid ? `, центр ${r1_07(r.mid)}` : ''),
        () => tipNode(r.name, [['Диапазон', `${nf2.format(r.lo)}–${nf2.format(r.hi)} млн H100e`]].concat(r.mid ? [['Центр', nf2.format(r.mid) + ' млн']] : [], pairs), r.note));
      const ln = gg.append('line').attr('x1', x(r.lo)).attr('x2', x(r.hi)).attr('y1', y).attr('y2', y).attr('stroke', ink).attr('stroke-width', 2.4);
      cap(gg, x(r.lo), y); cap(gg, x(r.hi), y);
      if (r.mid) gg.append('circle').attr('cx', x(r.mid)).attr('cy', y).attr('r', 5).attr('fill', ink).attr('stroke', col('--paper')).attr('stroke-width', 2);
      if (opts.animate && !RM) ln.attr('x2', x(r.lo)).transition().delay(k * 90).duration(420).attr('x2', x(r.hi));
      s.append('text').attr('class', 'dlbl').attr('x', x(r.lo) - 8).attr('y', y + 4).attr('text-anchor', 'end').text(r1_07(r.lo));
      s.append('text').attr('class', 'dlbl').attr('x', x(r.hi) + 8).attr('y', y + 4).text(r1_07(r.hi));
      if (r.mid) s.append('text').attr('class', 'dlbl b').attr('x', x(r.mid)).attr('y', y - 10).attr('text-anchor', 'middle').text(r1_07(r.mid));
    } else { // нижняя граница: засечка и стрелка «≥»
      const x0 = x(r.lo), x1 = x(r.lo * 1.7);
      const gg = range07(g, x0, x1, y, `${r.name}: не меньше ${r1_07(r.lo)} млн H100e — нижняя граница`,
        () => tipNode(r.name, [['Нижняя граница', `≥ ${nf2.format(r.lo)} млн H100e`]].concat(pairs), r.note));
      cap(gg, x0, y);
      gg.append('line').attr('x1', x0).attr('x2', x1).attr('y1', y).attr('y2', y).attr('stroke', ink).attr('stroke-width', 1.4);
      gg.append('path').attr('d', `M${x1 - 6},${y - 4} L${x1},${y} L${x1 - 6},${y + 4}`).attr('fill', 'none').attr('stroke', ink).attr('stroke-width', 1.4);
      s.append('text').attr('class', 'dlbl').attr('x', x0 - 8).attr('y', y + 4).attr('text-anchor', 'end').text('≥ ' + r1_07(r.lo));
    }
  });
  // аннотация у официальной статистики и скобка «обе опираются на поставки»
  if (a0L.length && rows[0]) lines07(s, x(rows[0].lo), yRow(0) + 19, a0L, 'ann', 'start', 14);
  // скобка в пустой левой части шкалы: две оценки, которые опираются на одни и те же поставки
  if (a1 && rows[1] && mob) { // на телефоне слева подписи строк: скобка у правого края, текст под ней
    const bx = w - 2, y1 = yRow(0), y2 = yRow(1);
    s.append('path').attr('d', `M${bx - 5},${y1} H${bx} V${y2} H${bx - 5}`).attr('fill', 'none').attr('stroke', ink3).attr('stroke-width', 1);
    s.append('text').attr('class', 'ann').attr('x', bx).attr('y', y2 + 22).attr('text-anchor', 'end').text('скобка: ' + a1);
  } else if (a1 && rows[1]) {
    const bx = x(0.4), y1 = yRow(0), y2 = yRow(1);
    s.append('path').attr('d', `M${bx + 5},${y1} H${bx} V${y2} H${bx + 5}`).attr('fill', 'none').attr('stroke', ink3).attr('stroke-width', 1);
    const L = wrap07(a1, Math.max(9, Math.floor((bx - x(0.1)) / 6.4)));
    lines07(s, bx - 7, (y1 + y2) / 2 + 4 - (L.length - 1) * 7, L, 'ann', 'end', 14);
  }
  // другая мера: использование с арендой за рубежом — тонкой линией, отдельно от общего диапазона
  if (ct) {
    const c = ct.mid, lo = ct.lo, hi = ct.hi, y = yCT, nm = ct.name;
    s.append('line').attr('x1', 0).attr('x2', w).attr('y1', y - (mob ? 34 : 22)).attr('y2', y - (mob ? 34 : 22)).attr('class', 'hair');
    label(nm, mob ? 0 : labW, mob ? y - 16 : y + 4, false);
    const gg = range07(g, x(lo), x(hi), y, `${nm}: центр ${r1_07(c)}, диапазон ${r1_07(lo)}–${r1_07(hi)} млн H100e`,
      () => tipNode(nm, [['Центр', nf2.format(c) + ' млн H100e'], ['Диапазон', `${nf2.format(lo)}–${nf2.format(hi)} млн`], ['На дату', date07(ct.date)], ['Строки реестра', ct.claims]], ct.note + (ctNote ? '. Другая мера: ' + ctNote + '.' : '')));
    gg.append('line').attr('x1', x(lo)).attr('x2', x(hi)).attr('y1', y).attr('y2', y).attr('stroke', ink3).attr('stroke-width', 1);
    gg.append('circle').attr('cx', x(c)).attr('cy', y).attr('r', 4).attr('fill', col('--paper')).attr('stroke', ink3).attr('stroke-width', 1.4);
    s.append('text').attr('class', 'dlbl').attr('x', x(lo) - 8).attr('y', y + 4).attr('text-anchor', 'end').text(r1_07(lo));
    s.append('text').attr('class', 'dlbl').attr('x', x(hi) + 8).attr('y', y + 4).text(r1_07(hi));
    if (ctNote) lines07(s, mob ? 0 : x(lo), y + 19, wrap07('другая мера: ' + ctNote, Math.floor((w - m.r - (mob ? 0 : x(lo))) / 6.4)), 'ann', 'start', 14);
  }

  // панель «Если мерить не чипами»: Китай к США, США = 100%
  if (IND.length) {
    const x2 = d3.scaleLinear().domain([0, 1]).range([m.l, w - m.r - (mob ? 0 : 60)]);
    s.append('text').attr('class', 'dlbl b').attr('x', 0).attr('y', pTop).text(pTitle || '');
    const yB = pTop + 24 + IND.length * pRowH;
    [0, .25, .5, .75, 1].forEach(v => {
      s.append('line').attr('class', v === 1 ? 'ledger' : 'hair').attr('x1', x2(v)).attr('x2', x2(v)).attr('y1', pTop + 12).attr('y2', yB - 12).attr('stroke-dasharray', v === 1 ? null : '1 3');
      s.append('text').attr('class', 'lbl').attr('x', x2(v)).attr('y', yB + 4).attr('text-anchor', v === 0 ? 'start' : v === 1 ? 'end' : 'middle').text(v === 1 ? 'США = 100%' : Math.round(v * 100) + '%');
    });
    IND.forEach((r, k) => {
      const y = pTop + 24 + k * pRowH + pRowH / 2 - (mob ? 0 : 4);
      label(r.metric, mob ? 0 : labW, mob ? y - 16 : y + 4, false);
      const v = String(r.china_to_us), ge = v.startsWith('≥'), [a, b] = v.replace('≥', '').split('-').map(Number);
      const tip = () => tipNode(r.metric, [['Китай', `${r.china} ${r.unit}`], ['США', `${r.us} ${r.unit}`], ['Китай к США', ge ? `≥ ${Math.round(a * 100)}%` : `${Math.round(a * 100)}–${Math.round(b * 100)}%`], ['Строки реестра', r.claim_ids]], r.note);
      if (ge) {
        const x0 = x2(a), x1 = x2(Math.min(1, a + .12));
        const gg = range07(g, x0, x1, y, `${r.metric}: Китай — не меньше ${Math.round(a * 100)}% от США`, tip);
        cap(gg, x0, y);
        gg.append('line').attr('x1', x0).attr('x2', x1).attr('y1', y).attr('y2', y).attr('stroke', ink).attr('stroke-width', 1.4);
        gg.append('path').attr('d', `M${x1 - 6},${y - 4} L${x1},${y} L${x1 - 6},${y + 4}`).attr('fill', 'none').attr('stroke', ink).attr('stroke-width', 1.4);
        s.append('text').attr('class', 'dlbl b').attr('x', x0 - 8).attr('y', y + 4).attr('text-anchor', 'end').text(`≥ ${Math.round(a * 100)}%`);
      } else {
        const gg = range07(g, x2(a), x2(b), y, `${r.metric}: Китай — ${Math.round(a * 100)}–${Math.round(b * 100)}% от США`, tip);
        gg.append('line').attr('x1', x2(a)).attr('x2', x2(b)).attr('y1', y).attr('y2', y).attr('stroke', ink).attr('stroke-width', 2.4);
        cap(gg, x2(a), y); cap(gg, x2(b), y);
        s.append('text').attr('class', 'dlbl b').attr('x', x2(b) + 8).attr('y', y + 4).text(`${Math.round(a * 100)}–${Math.round(b * 100)}%`);
      }
    });
  }
};

// fig07b · кВт на H100e по площадкам: точки по строкам-семействам чипов
CHARTS.fig07b = (s, spec, opts) => {
  const D = spec.data['07-sites-kw'];
  const form = spec.form || '';
  const FAM = ((/строки\s*—\s*семейства чипов\s*\(([^)]+)\)/.exec(form) || [])[1] || '').split(',').map(t => t.trim()).filter(Boolean);
  const dom = (/кВт на H100e\s*\(([\d,]+)–([\d,]+)\)/.exec(form) || [0, '0,5', '5,5']).slice(1).map(num07);
  const annTxt = quote07((spec.annotations || [])[0]);
  const RU = { 'United States': 'США', China: 'Китай', Malaysia: 'Малайзия', 'United Kingdom': 'Великобритания', Norway: 'Норвегия', Portugal: 'Португалия', Finland: 'Финляндия', Iceland: 'Исландия', Indonesia: 'Индонезия', Australia: 'Австралия' };
  const fams = FAM.length ? FAM : [...new Set(D.map(d => d.chip_family))];
  const w = s.node().clientWidth, mob = w < 560;
  const labW = mob ? 0 : 150, m = { l: labW + 14, r: 14, t: mob ? 48 : 34 };
  const x = d3.scaleLinear().domain(dom).range([m.l, w - m.r]);
  const ink = col('--ink'), grey = col('--l4'), deb = col('--debit');
  // средние по стране — взвешенные: вся IT-мощность на все H100e
  const avg = c => { const r = D.filter(d => d.country === c); return d3.sum(r, d => d.it_mw) * 1000 / d3.sum(r, d => d.h100e); };
  const aUS = avg('United States'), aCN = avg('China');
  // высота строки: точки, подписи площадок в Китае и аннотация
  const rows = fams.map(f => {
    const pts = D.filter(d => d.chip_family === f).sort((a, b) => a.kw_it_per_h100e - b.kw_it_per_h100e);
    const cn = pts.filter(d => d.country === 'China');
    const right = cn.length && x(d3.max(cn, d => d.kw_it_per_h100e)) + 10 + d3.max(cn, d => d.site.length) * 6.4 < w;
    const annL = cn.length && !right && annTxt ? wrap07(annTxt, mob ? 36 : 44).length : 0;
    const hh = Math.max(mob ? 42 : 30, cn.length > 1 ? cn.length * 14 + 10 : 0, annL ? 30 + annL * 14 : 0) + (mob ? 16 : 0);
    return { f, pts, cn, right, annL, hh };
  });
  let yy = m.t + 8; rows.forEach(r => { r.y = yy + (mob ? 16 : 0) + Math.min(r.hh - (mob ? 16 : 0), mob ? 42 : 30) / 2; yy += r.hh; });
  const yAxis = yy + 16, h = yAxis + 6;
  s.attr('viewBox', `0 0 ${w} ${h}`).attr('height', h);

  // бумага: засечки оси и строки
  d3.range(Math.ceil(dom[0]), Math.floor(dom[1]) + 1).forEach(v => {
    s.append('line').attr('class', 'hair').attr('x1', x(v)).attr('x2', x(v)).attr('y1', m.t).attr('y2', yy).attr('stroke-dasharray', '1 3');
    s.append('text').attr('class', 'lbl').attr('x', x(v)).attr('y', yAxis).attr('text-anchor', v === Math.floor(dom[1]) ? 'end' : 'middle').text(v + (v === Math.floor(dom[1]) ? ' кВт' : ''));
  });
  rows.forEach(r => s.append('line').attr('class', 'ledger').attr('x1', mob ? 0 : m.l).attr('x2', w - m.r).attr('y1', r.y).attr('y2', r.y).attr('opacity', .6));
  // средние: США — тушью, Китай — акцент «дебет» (платит лишним электричеством)
  // на телефоне подписи средних — в две строки над графиком, обе от своей линии вправо
  [[aUS, 'США', ink, mob ? 'start' : 'end', mob ? 30 : 12], [aCN, 'Китай', deb, 'start', 12]].forEach(([v, n, c, anc, dy]) => {
    s.append('line').attr('x1', x(v)).attr('x2', x(v)).attr('y1', m.t - dy + 6).attr('y2', yy).attr('stroke', c).attr('stroke-width', 1.2);
    s.append('text').attr('class', 'dlbl b').attr('x', x(v) + (anc === 'end' ? -6 : 6)).attr('y', m.t - dy).attr('text-anchor', anc).attr('fill', c).text(`${n} в среднем · ${nf2.format(Math.round(v * 100) / 100)}`);
  });

  const g = s.append('g');
  let k = 0;
  rows.forEach(r => {
    halo07(s.append('text').attr('class', 'dlbl' + (r.cn.length ? ' b' : '')).attr('x', mob ? 0 : labW).attr('y', mob ? r.y - 18 : r.y + 4).attr('text-anchor', mob ? 'start' : 'end').text(r.f));
    // медиана строки — короткая засечка
    const med = d3.median(r.pts, d => d.kw_it_per_h100e);
    if (r.pts.length > 1) s.append('line').attr('x1', x(med)).attr('x2', x(med)).attr('y1', r.y - 11).attr('y2', r.y + 11).attr('stroke', ink).attr('stroke-width', 1.6);
    // точки: совпадающие раздвигаем по вертикали, чтобы видна была каждая
    const placed = [];
    r.pts.forEach(d => {
      const px = x(d.kw_it_per_h100e), n = placed.filter(p => Math.abs(p - px) < 7).length; placed.push(px);
      const dy = [0, -6, 6, -12, 12][n % 5], cn = d.country === 'China';
      const gg = mark(g, px, r.y + dy, `${d.site}, ${RU[d.country] || d.country}: ${nf2.format(d.kw_it_per_h100e)} кВт на H100e`,
        () => tipNode(d.site, [['Страна', RU[d.country] || d.country], ['Владелец', d.owner], ['Чипы', d.chips || 'не указаны'], ['IT-мощность', nf0.format(d.it_mw) + ' МВт'], ['H100e', nf0.format(d.h100e)], ['кВт на H100e', nf2.format(d.kw_it_per_h100e)]]));
      gg.append('circle').attr('r', cn ? 4.6 : 3.6).attr('fill', cn ? ink : grey).attr('stroke', col('--paper')).attr('stroke-width', 1.2);
      if (opts.animate && !RM) gg.attr('opacity', 0).transition().delay(60 + k++ * 8).duration(200).attr('opacity', 1);
    });
    // подписи площадок в Китае: справа от точек, а если не помещаются — слева, с аннотацией под подписью
    if (!r.cn.length) return;
    const names = r.cn.slice().sort((a, b) => a.kw_it_per_h100e - b.kw_it_per_h100e).map(d => d.site + (r.cn.length === 1 ? ' · ' + nf1.format(d.kw_it_per_h100e) + ' кВт' : ''));
    if (r.right) {
      const lx = x(d3.max(r.cn, d => d.kw_it_per_h100e)) + 10;
      halo07(lines07(s, lx, r.y + 4 - (names.length - 1) * 7, names, 'dlbl', 'start', 14));
    } else {
      const lx = x(d3.min(r.cn, d => d.kw_it_per_h100e)) - 10;
      halo07(lines07(s, lx, r.y + 4, names, 'dlbl b', 'end', 14));
      if (r.annL) halo07(lines07(s, lx, r.y + 22, wrap07(annTxt, mob ? 36 : 44), 'ann', 'end', 14));
    }
  });
};
