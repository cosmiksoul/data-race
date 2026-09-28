/* ── строка 06 · графики ─────────────────────────────────────────────
   Данные — CSV из пакета content/06-intellekt.md; тексты подписей и аннотаций
   берутся из полей labels / annotations / tooltip / form пакета. */

// fig1 · три цены: флагманы при выходе + ступенчатая линия уровня GPT-4
CHARTS.fig1 = (s, spec, opts) => {
  const F = spec.data['06-flagships'].map(r => ({ lab: r.lab, m: r.model, d: new Date(r.release_date), i: r.input_usd_per_mtok, o: r.output_usd_per_mtok, b: r.blended_3to1, note: r.note }));
  const FIX = spec.data['06-gpt4-level'].map(r => ({ m: r.model, d: new Date(r.date), p: r.blended_usd_per_mtok }));
  const short = m => m.replace(/^Claude /, '');
  const byName = n => F.find(f => f.m === n || short(f.m) === n);
  // основная линейка и подписи — из описания графика в пакете
  const mm = /линейки OpenAI ([^;]+)/.exec(spec.form || '');
  const MAIN = mm ? mm[1].split('→').map(x => x.trim()) : ['GPT-4', 'GPT-4o', 'GPT-5', 'GPT-5.5', 'GPT-6 Astra'];
  const lm = /:\s*([^;]+)/.exec(spec.labels || '');
  const LABELS = lm ? lm[1].split(',').map(x => x.trim()) : [];
  const ann = spec.annotations || [];

  const w = s.node().clientWidth, mob = w < 560, h = mob ? 360 : 440;
  const m = { l: 44, r: mob ? 12 : 120, t: 16, b: 30 };
  s.attr('viewBox', `0 0 ${w} ${h}`).attr('height', h);
  const x = d3.scaleUtc().domain([new Date('2023-01-01'), new Date('2026-12-31')]).range([m.l, w - m.r]);
  const y = d3.scaleLog().domain([0.08, 160]).range([h - m.b, m.t]);
  // бумага: линии бухгалтерской книги
  [0.1, 1, 10, 100].forEach(v => { s.append('line').attr('class', 'ledger').attr('x1', m.l).attr('x2', w - m.r).attr('y1', y(v)).attr('y2', y(v)); s.append('text').attr('class', 'lbl').attr('x', m.l - 8).attr('y', y(v) + 3.5).attr('text-anchor', 'end').text('$' + nf2.format(v)); });
  d3.range(2023, 2027).forEach(yr => { const xx = x(new Date(yr + '-01-01')); s.append('line').attr('class', 'hair').attr('x1', xx).attr('x2', xx).attr('y1', m.t).attr('y2', h - m.b).attr('stroke-dasharray', '1 3'); s.append('text').attr('class', 'lbl').attr('x', xx + 3).attr('y', h - m.b + 16).text(yr); });
  // уровень GPT-4 — акцент «кредит»; данные Epoch — до декабря 2024 года
  const line = d3.line().x(d => x(d.d)).y(d => y(d.p)).curve(d3.curveStepAfter);
  const fx = FIX.concat([{ d: new Date('2024-12-31'), p: FIX[FIX.length - 1].p }]);
  const step = s.append('path').datum(fx).attr('d', line).attr('fill', 'none').attr('stroke', col('--credit')).attr('stroke-width', 2);
  if (opts.animate && !RM) { const L = step.node().getTotalLength(); step.attr('stroke-dasharray', `${L} ${L}`).attr('stroke-dashoffset', L).transition().duration(700).attr('stroke-dashoffset', 0); }
  const gFix = s.append('g');
  FIX.forEach(d => { const g = mark(gFix, x(d.d), y(d.p), `${d.m}, ${fmtD(d.d)}: ${money(d.p)} за 1 млн токенов, самая дешёвая модель уровня GPT-4`,
    () => tipNode(d.m, [['Дата', fmtD(d.d)], ['Смешанная цена', money(d.p)]], 'Самая дешёвая модель уровня GPT-4 на научных вопросах (Epoch AI)'));
    g.append('circle').attr('r', 3.2).attr('fill', col('--credit')).attr('stroke', col('--paper')).attr('stroke-width', 1.5); });
  const last = FIX[FIX.length - 1], prev = FIX[FIX.length - 2];
  s.append('text').attr('class', 'ann credit').attr('x', mob ? x(prev.d) + 4 : x(last.d) + 8).attr('y', mob ? y(prev.p) - 8 : y(last.p) - 8).text(before(ann[0]));
  // основная линейка GPT
  const ml = MAIN.map(byName).filter(Boolean).sort((a, b) => a.d - b.d);
  s.append('path').datum(ml).attr('d', d3.line().x(d => x(d.d)).y(d => y(d.b)).curve(d3.curveMonotoneX)).attr('fill', 'none').attr('stroke', col('--ink')).attr('stroke-width', 1.2);
  // точки флагманов: оттенок серого и форма значка — лаборатория
  const LC = { OpenAI: col('--l1'), Anthropic: col('--l3'), Google: col('--l4') };
  const g = s.append('g');
  F.forEach((d, k) => {
    const gg = mark(g, x(d.d), y(d.b), `${d.m}, ${d.lab}, ${fmtD(d.d)}: ${money(d.b)} за 1 млн токенов`,
      () => tipNode(d.m, [['Выход', fmtD(d.d)], ['Запрос / ответ', `$${nf2.format(d.i)} / $${nf2.format(d.o)}`], ['Смешанная цена', money(d.b)]], d.note));
    shape(gg, d.lab, 4.6).attr('fill', LC[d.lab]).attr('stroke', col('--paper')).attr('stroke-width', 1.8);
    if (opts.animate && !RM) gg.attr('opacity', 0).transition().delay(80 + k * 25).duration(220).attr('opacity', 1);
  });
  // подписи — выборочно, как в описании графика; на телефоне — только основная линейка
  const BOLD = new Set([MAIN[0], 'GPT-5', MAIN[MAIN.length - 1]]);
  const POS = { 'GPT-4': [8, -8], 'GPT-4o': [8, -8], 'GPT-5': [8, 17], 'GPT-5.5': [-8, -8, 'end'], 'GPT-6 Astra': [8, 4], 'GPT-4.5': [8, 4], 'Mythos Preview': [-8, -8, 'end'], '3 Opus': [8, -8], 'Fable 5': [-8, -8, 'end'] };
  const MOB = new Set(['GPT-4', 'GPT-5', 'GPT-5.5']);
  const lab = name => { const d = byName(name); if (!d) return; const [dx, dy, anchor] = POS[name] || [8, -8];
    s.append('text').attr('class', 'dlbl' + (BOLD.has(name) ? ' b' : '')).attr('x', x(d.d) + dx).attr('y', y(d.b) + dy).attr('text-anchor', anchor || 'start').text(short(d.m) + ' · ' + money(d.b)); };
  LABELS.forEach(n => { if (!mob || MOB.has(n)) { if (!(mob && n === MAIN[MAIN.length - 1])) lab(n); } });
  const ga = byName(MAIN[MAIN.length - 1]);
  if (mob && ga) { // на телефоне подпись последнего флагмана — на выноске над точкой
    const yT = y(80);
    s.append('line').attr('x1', x(ga.d)).attr('x2', x(ga.d)).attr('y1', y(ga.b) - 6).attr('y2', yT + 4).attr('stroke', col('--ink-4')).attr('stroke-width', .8);
    s.append('text').attr('class', 'dlbl b').attr('x', w - m.r).attr('y', yT).attr('text-anchor', 'end').text(short(ga.m) + ' · ' + money(ga.b));
  }
  // скобка подорожания с августа 2025 (на телефоне не показывается — нет места)
  const g5 = byName('GPT-5');
  if (!mob && g5 && ga && ann[1]) {
    const xx = x(ga.d) + 70, y1 = y(g5.b), y2 = y(ga.b);
    s.append('line').attr('x1', xx).attr('x2', xx).attr('y1', y1).attr('y2', y2).attr('stroke', col('--ink-3')).attr('stroke-width', .8);
    s.append('line').attr('x1', x(g5.d) + 6).attr('x2', xx).attr('y1', y1).attr('y2', y1).attr('stroke', col('--faint')).attr('stroke-dasharray', '2 3');
    const t6 = s.append('text').attr('class', 'ann').attr('x', xx + 6).attr('y', (y1 + y2) / 2 - 4);
    before(ann[1]).split(' / ').forEach((ln, k) => t6.append('tspan').attr('x', xx + 6).attr('dy', k ? 15 : 0).text(ln));
  }
};

// fig1b · подписки: ровные ступени тарифов
CHARTS.fig1b = (s, spec) => {
  const T = spec.data['06-subscriptions'].map(r => ({ n: r.plan, lab: r.lab, p: r.usd_per_month, dd: new Date(r.launch_date), pause: r.new_signups_paused || '' }));
  const lm = /справа:\s*(.+)$/.exec(spec.form || '');
  const LEVELS = lm ? lm[1].split(' / ').map(t => ({ t: t.trim(), v: +/\$(\d+)/.exec(t)[1] })) : [];
  const annTxt = (/«([^»]+)»\s*$/.exec((spec.annotations || [])[0] || '') || [])[1];
  const tipTxt = (/«([^»]+)»\s*$/.exec(spec.tooltip || '') || [])[1];
  const w = s.node().clientWidth, mob = w < 560, h = mob ? 280 : 210;
  const m = { l: 44, r: mob ? 12 : 150, t: 12, b: 28 };
  s.attr('viewBox', `0 0 ${w} ${h}`).attr('height', h);
  const x = d3.scaleUtc().domain([new Date('2023-01-01'), new Date('2026-12-31')]).range([m.l, w - m.r]);
  const y = d3.scaleLinear().domain([0, 220]).range([h - m.b, m.t]);
  [0, 100, 200].forEach(v => { s.append('line').attr('class', 'ledger').attr('x1', m.l).attr('x2', w - m.r).attr('y1', y(v)).attr('y2', y(v)); s.append('text').attr('class', 'lbl').attr('x', m.l - 8).attr('y', y(v) + 3.5).attr('text-anchor', 'end').text('$' + v); });
  d3.range(2023, 2027).forEach(yr => { const xx = x(new Date(yr + '-01-01')); s.append('text').attr('class', 'lbl').attr('x', xx + 3).attr('y', h - m.b + 16).text(yr); });
  const LC = { OpenAI: col('--l1'), Anthropic: col('--l3') };
  const end = new Date(PAGE.edition);
  const gl = s.append('g'), gm = s.append('g');
  T.forEach(t => { const off = t.lab === 'Anthropic' ? 3 : -3;
    gl.append('line').attr('x1', x(t.dd)).attr('x2', x(end)).attr('y1', y(t.p) + off).attr('y2', y(t.p) + off).attr('stroke', LC[t.lab]).attr('stroke-width', 1.6);
    const gg = mark(gm, x(t.dd), y(t.p) + off, `${t.n}, $${t.p} в месяц, с ${fmtD(t.dd)}`,
      () => tipNode(`${t.n} · $${t.p} в месяц`, [['Появился', fmtD(t.dd)]], t.pause ? tipTxt : ''));
    shape(gg, t.lab, 3.8).attr('fill', LC[t.lab]).attr('stroke', col('--paper')).attr('stroke-width', 1.5);
  });
  // подписи уровней: справа от ступеней; на телефоне — над ними
  LEVELS.forEach(L => {
    if (!mob) { s.append('text').attr('class', 'dlbl').attr('x', x(end) + 8).attr('y', y(L.v) + (L.v === 20 ? -2 : L.v < 20 ? 12 : 4)).text(L.t); return; }
    if (L.v < 20) { const st = T.filter(t => t.p === L.v).sort((a, b) => a.dd - b.dd)[0]; s.append('text').attr('class', 'dlbl').attr('x', x(st.dd) - 8).attr('y', y(L.v) + 1).attr('text-anchor', 'end').text(L.t); return; }
    s.append('text').attr('class', 'dlbl').attr('x', w - m.r).attr('y', y(L.v) - 13).attr('text-anchor', 'end').text(L.t);
  });
  // отметка: новых подписчиков не принимают — акцент «дебет»
  const pz = T.find(t => t.pause);
  if (pz) {
    const px = x(new Date(pz.pause)), yy = y(pz.p);
    s.append('line').attr('x1', px).attr('x2', px).attr('y1', yy - (mob ? 8 : 12)).attr('y2', yy + (mob ? 12 : 8)).attr('stroke', col('--debit')).attr('stroke-width', 1.4);
    s.append('text').attr('class', 'ann debit').attr('x', px - 6).attr('y', mob ? yy + 20 : yy - 16).attr('text-anchor', 'end').text(annTxt);
  }
};

// fig2 · единичная диаграмма: одна точка — 100 токенов
CHARTS.fig2 = (s, spec, opts) => {
  const rows = spec.data['06-output-length'];
  const labels = String(spec.labels || '').split(' / ');
  const w = s.node().clientWidth, mob = w < 560;
  const cols = mob ? 15 : 30, step = Math.min(18, w / cols), r = step * .32;
  const ink = col('--ink');
  let yy = 20; const pts = [];
  rows.forEach((row, k) => {
    const n = Math.round(row.median_output_tokens / 100), nr = Math.ceil(n / cols);
    s.append('text').attr('class', 'dlbl b').attr('x', 0).attr('y', yy - 6).text(labels[k] || row.model_type);
    for (let i = 0; i < n; i++) pts.push({ x: (i % cols) * step + step / 2, y: yy + Math.floor(i / cols) * step + step / 2 });
    yy += nr * step + 34;
  });
  const h = yy - 20; s.attr('viewBox', `0 0 ${w} ${h}`).attr('height', h);
  const c = s.append('g').selectAll('circle').data(pts).join('circle').attr('cx', d => d.x).attr('cy', d => d.y).attr('r', r).attr('fill', ink);
  if (opts.animate && !RM) c.attr('opacity', 0).transition().delay((d, i) => i * 12).duration(180).attr('opacity', 1);
};
