// Режим правки — только в edit.html (python scripts/build_site.py собирает её рядом с index.html).
// Щелчок по тексту → правка на месте (или в окне, если в тексте есть термины, ссылки, теги) →
// запись в журнал «было → стало» с пометкой. Журнал живёт в этом браузере, пока его не выгрузят
// кнопкой «Скачать правки»; выгруженный файл применяет scripts/apply_edits.py к content/*.md.
// Чтобы убрать режим: удалить этот файл, edit.html, scripts/apply_edits.py и ветку edit в build_site.py.
(() => {
  const ED = JSON.parse(document.getElementById('d-edits').textContent);
  const U = ED.units;
  const KEY = 'data-race-edits:' + ED.edition;
  const keyOf = u => u.file + '\u0001' + u.find;
  let log = {};
  try { log = JSON.parse(localStorage.getItem(KEY) || '{}') || {}; } catch (e) { log = {}; }
  const store = () => { try { localStorage.setItem(KEY, JSON.stringify(log)); } catch (e) { /* журнал живёт до перезагрузки */ } };
  let on = true;

  // ── оформление ──
  const css = document.createElement('style');
  css.textContent = `
  .ed-on [data-ed]{cursor:text;border-radius:3px;transition:box-shadow .15s}
  .ed-on [data-ed]:hover{box-shadow:0 0 0 2px color-mix(in srgb,var(--credit) 45%,transparent)}
  .ed-on .hq-ui [data-ed]{pointer-events:auto}
  [data-ed].ed-changed{background:color-mix(in srgb,var(--credit) 14%,transparent);box-shadow:inset 0 -2px 0 var(--credit)}
  [data-ed][contenteditable]{outline:2px solid var(--credit);outline-offset:3px;background:color-mix(in srgb,var(--credit) 8%,transparent);cursor:text}
  .hq-ui [data-ed].ed-changed,.hq-ui [data-ed][contenteditable]{background:rgba(92,139,214,.18)}
  .ed-raw{white-space:pre-wrap;font-family:var(--mono);font-size:.82em}
  #edBtn{position:fixed;left:16px;bottom:16px;z-index:90;min-height:36px;padding:8px 14px;border-radius:999px;border:1px solid var(--credit);
    background:var(--paper);color:var(--ink);font:500 13px var(--sans);cursor:pointer;box-shadow:0 2px 10px rgba(0,0,0,.18)}
  #edBtn b{color:var(--credit)}
  #edPanel{position:fixed;left:16px;bottom:62px;z-index:90;width:min(420px,calc(100vw - 32px));max-height:min(72vh,640px);display:none;flex-direction:column;
    background:var(--paper);color:var(--ink);border:1px solid var(--faint);border-radius:8px;box-shadow:0 8px 30px rgba(0,0,0,.25);font:13px/1.45 var(--sans)}
  #edPanel.open{display:flex}
  #edPanel header{padding:12px 14px 8px;border-bottom:1px solid var(--faint)}
  #edPanel header b{font:600 12px var(--mono);letter-spacing:.12em;text-transform:uppercase}
  #edPanel header p{margin:6px 0 0;color:var(--ink-3);font-size:12.5px}
  #edPanel label.sw{display:flex;gap:8px;align-items:center;margin-top:8px;min-height:24px;cursor:pointer}
  #edList{overflow:auto;padding:4px 14px;flex:1}
  #edList .it{padding:10px 0;border-bottom:1px solid var(--faint)}
  #edList .w{font:500 11px var(--mono);letter-spacing:.06em;color:var(--ink-3);text-transform:uppercase}
  #edList .df{margin-top:4px;font-size:13.5px}
  #edList del,#edList .was{color:var(--debit);text-decoration:line-through}
  #edList ins{color:var(--credit);text-decoration:none;font-weight:600;background:color-mix(in srgb,var(--credit) 12%,transparent)}
  #edList details{margin-top:4px;color:var(--ink-3);font-size:12.5px}
  #edList summary{cursor:pointer;min-height:24px;display:flex;align-items:center}
  #edList .now{color:var(--credit);margin-top:2px}
  #edList .st{font-size:12px;color:var(--ink-3);margin-top:4px}
  #edList input{width:100%;margin-top:6px;min-height:30px;padding:4px 8px;border:1px solid var(--faint);border-radius:4px;background:transparent;color:var(--ink);font:13px var(--sans)}
  #edList .row,#edPanel footer{display:flex;gap:8px;flex-wrap:wrap;margin-top:6px}
  #edPanel footer{padding:10px 14px 12px;border-top:1px solid var(--faint);margin:0}
  #edPanel button,#edDlg button{min-height:30px;padding:4px 12px;border:1px solid var(--faint);border-radius:999px;background:transparent;color:var(--ink);font:12.5px var(--sans);cursor:pointer}
  #edPanel button.pri,#edDlg button.pri{border-color:var(--credit);color:var(--credit);font-weight:600}
  #edDlg{width:min(640px,calc(100vw - 32px));border:1px solid var(--faint);border-radius:8px;background:var(--paper);color:var(--ink);padding:16px;font:13px/1.45 var(--sans)}
  #edDlg::backdrop{background:rgba(0,0,0,.35)}
  #edDlg textarea{width:100%;min-height:180px;margin:8px 0;padding:8px;border:1px solid var(--faint);border-radius:4px;background:transparent;color:var(--ink);font:14px/1.5 var(--mono);resize:vertical}
  #edDlg input{width:100%;min-height:30px;padding:4px 8px;border:1px solid var(--faint);border-radius:4px;background:transparent;color:var(--ink);font:13px var(--sans)}
  #edDlg .hint{color:var(--ink-3);font-size:12px}
  #edDlg .row{display:flex;gap:8px;justify-content:flex-end;margin-top:12px;flex-wrap:wrap}
  @media (max-width:1180px){#edBtn{bottom:56px}#edPanel{bottom:102px}}`;
  document.head.append(css);
  document.documentElement.classList.add('ed-on');

  // ── состояние кусков текста ──
  const els = [...document.querySelectorAll('[data-ed]')];
  const original = new Map(els.map(el => [el, el.innerHTML]));
  const unitOf = el => U[+el.dataset.ed];
  const entryOf = u => log[keyOf(u)];
  function show(el) {
    const u = unitOf(el), e = entryOf(u);
    el.classList.toggle('ed-changed', !!e);
    el.classList.toggle('ed-raw', !!e && u.markup);
    if (!e) el.innerHTML = original.get(el);
    else el.textContent = e.new; // текст с разметкой показываем как есть — так видно, что уйдёт в пакет
  }
  function commit(u, text, note) {
    const k = keyOf(u), prev = log[k];
    if (text === u.orig) delete log[k];
    else log[k] = { file: u.file, kind: u.kind, find: u.find, pre: u.pre, suf: u.suf, where: u.where, orig: u.orig,
                    new: text, note: note != null ? note : (prev ? prev.note : ''), t: new Date().toISOString() };
    store();
    els.filter(el => unitOf(el) === u).forEach(show);
    render();
  }
  els.forEach(el => { el.tabIndex = 0; if (entryOf(unitOf(el))) show(el); });

  // ── правка на месте ──
  let editing = null;
  function inline(el, x, y) {
    const u = unitOf(el), e = entryOf(u);
    editing = el;
    el.textContent = e ? e.new : u.orig;
    try { el.contentEditable = 'plaintext-only'; } catch (_) { el.contentEditable = 'true'; }
    if (el.contentEditable !== 'plaintext-only') el.contentEditable = 'true';
    el.focus();
    const r = x != null && document.caretRangeFromPoint ? document.caretRangeFromPoint(x, y) : null;
    const sel = getSelection(); sel.removeAllRanges();
    if (r && el.contains(r.startContainer)) sel.addRange(r);
    else { const rr = document.createRange(); rr.selectNodeContents(el); rr.collapse(false); sel.addRange(rr); }
  }
  function finish(el, keep) {
    if (editing !== el) return;
    editing = null;
    const u = unitOf(el), text = el.textContent.replace(/[ \t\r\n]+/g, ' ').trim();
    el.removeAttribute('contenteditable');
    if (keep && text) commit(u, text); else show(el);
  }
  document.addEventListener('keydown', e => {
    const el = editing;
    if (el && e.target === el) {
      if (e.key === 'Escape') { e.preventDefault(); finish(el, false); el.focus(); }
      else if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); finish(el, true); el.focus(); }
      return;
    }
    const t = e.target.closest && e.target.closest('[data-ed]');
    if (on && t && e.key === 'Enter' && !editing) { e.preventDefault(); open(t); }
  }, true);
  document.addEventListener('focusout', e => { if (editing && e.target === editing) finish(editing, true); }, true);

  // ── правка в окне: текст с терминами, ссылками, тегами — в исходной разметке ──
  const dlg = document.createElement('dialog'); dlg.id = 'edDlg';
  dlg.innerHTML = `<div class="w" id="edDlgW" style="font:500 11px var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--ink-3)"></div>
    <textarea id="edDlgT" spellcheck="true" aria-label="Текст в разметке пакета"></textarea>
    <div class="hint">Разметка пакета: [[термин|текст]] — подсказка, [^s1] — ссылка на источник, {оценка} — тег, **жирный**, [текст](адрес) — ссылка.</div>
    <input id="edDlgN" placeholder="Пометка к правке (необязательно)" aria-label="Пометка к правке" style="margin-top:8px">
    <div class="row"><button type="button" id="edDlgR">Вернуть исходный</button><button type="button" id="edDlgC">Отмена</button><button type="button" class="pri" id="edDlgS">Сохранить</button></div>`;
  document.body.append(dlg);
  let dlgUnit = null;
  const $ = id => document.getElementById(id);
  function dialog(u) {
    const e = entryOf(u); dlgUnit = u;
    $('edDlgW').textContent = u.where + ' · ' + u.file;
    $('edDlgT').value = e ? e.new : u.orig; $('edDlgN').value = e ? e.note : '';
    dlg.showModal(); $('edDlgT').focus();
  }
  $('edDlgC').onclick = () => dlg.close();
  $('edDlgR').onclick = () => { commit(dlgUnit, dlgUnit.orig); dlg.close(); };
  $('edDlgS').onclick = () => {
    let v = $('edDlgT').value.replace(/\r/g, '').trim();
    if (dlgUnit.kind === 'yaml') v = v.replace(/[ \t\n]+/g, ' ');
    if (v) commit(dlgUnit, v, $('edDlgN').value.trim());
    dlg.close();
  };

  function open(el, x, y) { const u = unitOf(el); if (u.markup) dialog(u); else inline(el, x, y); }
  document.addEventListener('click', e => {
    if (!on || dlg.open) return;
    const el = e.target.closest('[data-ed]');
    if (!el || el === editing || e.target.closest('#edPanel')) return;
    e.preventDefault(); e.stopPropagation();
    if (editing) finish(editing, true);
    open(el, e.clientX, e.clientY);
  }, true);

  // ── журнал ──
  const btn = document.createElement('button'); btn.id = 'edBtn'; btn.type = 'button';
  btn.setAttribute('aria-controls', 'edPanel'); btn.setAttribute('aria-expanded', 'false');
  const panel = document.createElement('section'); panel.id = 'edPanel'; panel.setAttribute('aria-label', 'Журнал правок');
  panel.innerHTML = `<header><b>Журнал правок</b><p>Щёлкните по тексту страницы, чтобы исправить его. Enter — сохранить, Esc — отменить. Правки хранятся в этом браузере, пока вы их не скачаете.</p>
    <label class="sw"><input type="checkbox" id="edOn" checked> Режим правки: щелчок по тексту открывает правку</label></header>
    <div id="edList"></div>
    <footer><button type="button" class="pri" id="edDl">Скачать правки</button><button type="button" id="edCp">Скопировать</button><button type="button" id="edClr">Очистить журнал</button></footer>`;
  document.body.append(btn, panel);
  btn.onclick = () => { const o = panel.classList.toggle('open'); btn.setAttribute('aria-expanded', o); };
  $('edOn').onchange = e => { on = e.target.checked; document.documentElement.classList.toggle('ed-on', on); };

  // что изменилось: общее начало и конец отрезаем до границы слова, остаётся одна изменённая вставка
  function diff(a, b) {
    let i = 0; while (i < a.length && i < b.length && a[i] === b[i]) i++;
    let j = 0; while (j < a.length - i && j < b.length - i && a[a.length - 1 - j] === b[b.length - 1 - j]) j++;
    while (i > 0 && /\S/.test(a[i - 1])) i--;
    while (j > 0 && /\S/.test(a[a.length - j])) j--;
    const pre = a.slice(0, i), post = a.slice(a.length - j);
    return { pre: pre.length > 40 ? '…' + pre.slice(-40).replace(/^\S*\s/, '') : pre, del: a.slice(i, a.length - j),
             ins: b.slice(i, b.length - j), post: post.length > 40 ? post.slice(0, 40).replace(/\s\S*$/, '') + '…' : post };
  }
  const plural = (n, a, b, c) => { const m = n % 10, h = n % 100; return m === 1 && h !== 11 ? a : m >= 2 && m <= 4 && (h < 12 || h > 14) ? b : c; };
  const entries = () => Object.entries(log).sort((a, b) => a[1].t < b[1].t ? -1 : 1);
  function status(k) { // правка к куску текста, которого в этой сборке уже нет
    if (U.some(u => keyOf(u) === k)) return '';
    const e = log[k];
    return U.some(u => u.file === e.file && u.orig === e.new)
      ? 'Уже в пакете: страница пересобрана с этой правкой — строку можно удалить.'
      : 'Текста «было» в этой сборке нет: пакет изменили после правки. Проверьте вручную.';
  }
  function render() {
    const es = entries(), n = es.length;
    btn.innerHTML = `✎ Правки · <b>${n}</b>`;
    btn.setAttribute('aria-label', `Журнал правок: ${n} ${plural(n, 'правка', 'правки', 'правок')}`);
    const list = $('edList'); list.textContent = '';
    if (!n) { list.innerHTML = '<p style="color:var(--ink-3)">Пока правок нет.</p>'; return; }
    es.forEach(([k, e]) => {
      const it = document.createElement('div'); it.className = 'it';
      const mk = (cls, txt) => { const d = document.createElement('div'); d.className = cls; d.textContent = txt; return d; };
      const d = diff(e.orig, e.new), df = mk('df', '');
      df.append(d.pre); if (d.del) { const x = document.createElement('del'); x.textContent = d.del; df.append(x); }
      if (d.del && d.ins) df.append(' '); if (d.ins) { const x = document.createElement('ins'); x.textContent = d.ins; df.append(x); }
      df.append(d.post);
      const full = document.createElement('details'); full.innerHTML = '<summary>Весь текст: было и стало</summary>';
      full.append(mk('was', e.orig), mk('now', e.new));
      it.append(mk('w', e.where), df, full);
      const st = status(k); if (st) it.append(mk('st', st));
      const note = document.createElement('input'); note.placeholder = 'Пометка (необязательно)'; note.value = e.note || '';
      note.setAttribute('aria-label', 'Пометка к правке: ' + e.where);
      note.onchange = () => { e.note = note.value.trim(); store(); };
      const row = document.createElement('div'); row.className = 'row';
      const go = document.createElement('button'); go.type = 'button'; go.textContent = 'Показать';
      const el = els.find(x => keyOf(unitOf(x)) === k);
      go.disabled = !el; go.onclick = () => { el.scrollIntoView({ block: 'center', behavior: 'smooth' }); el.focus({ preventScroll: true }); };
      const undo = document.createElement('button'); undo.type = 'button'; undo.textContent = 'Отменить правку';
      undo.onclick = () => { delete log[k]; store(); if (el) show(el); render(); };
      row.append(go, undo); it.append(note, row); list.append(it);
    });
  }

  // выгрузка: читаемый список + данные для scripts/apply_edits.py в HTML-комментарии
  function exportMd() {
    const es = entries().map(([, e]) => e), now = new Date();
    const d2 = n => String(n).padStart(2, '0');
    const stamp = `${d2(now.getDate())}.${d2(now.getMonth() + 1)}.${now.getFullYear()}, ${d2(now.getHours())}:${d2(now.getMinutes())}`;
    const title = document.querySelector('h1') ? document.querySelector('h1').textContent : '';
    let md = `# Правки к странице «${title}»\n\nВыпуск ${ED.edition.split('-').reverse().join('.')} · выгружено ${stamp} · ${es.length} ${plural(es.length, 'правка', 'правки', 'правок')}\n`;
    es.forEach((e, i) => {
      const d = diff(e.orig, e.new);
      md += `\n## ${i + 1}. ${e.where}\n\nФайл: \`${e.file}\`\n\n` +
            `**Правка:** ${d.pre}${d.del ? `~~${d.del}~~` : ''}${d.del && d.ins ? ' → ' : ''}${d.ins ? `**${d.ins}**` : ''}${d.post}\n\n` +
            (e.note ? `**Пометка:** ${e.note}\n\n` : '') + `**Было:** ${e.orig}\n\n**Стало:** ${e.new}\n`;
    });
    const data = es.map(e => ({ file: e.file, kind: e.kind, find: e.find, pre: e.pre, suf: e.suf, orig: e.orig, new: e.new, note: e.note || '', where: e.where }));
    md += `\n---\n\nПрименить к пакетам: \`python scripts/apply_edits.py <этот файл>\` (проверка без записи — \`--dry-run\`).\n\n` +
          `<!-- edits-json\n${JSON.stringify(data, null, 1).replace(/>/g, '\\u003e')}\n-->\n`;
    return md;
  }
  const fname = () => { const d = new Date(), d2 = n => String(n).padStart(2, '0'); return `pravki-${d.getFullYear()}-${d2(d.getMonth() + 1)}-${d2(d.getDate())}-${d2(d.getHours())}${d2(d.getMinutes())}.md`; };
  $('edDl').onclick = () => {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([exportMd()], { type: 'text/markdown;charset=utf-8' }));
    a.download = fname(); document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  };
  $('edCp').onclick = async () => {
    try { await navigator.clipboard.writeText(exportMd()); $('edCp').textContent = 'Скопировано'; }
    catch (_) { $('edCp').textContent = 'Не удалось — скачайте файл'; }
    setTimeout(() => { $('edCp').textContent = 'Скопировать'; }, 1800);
  };
  $('edClr').onclick = () => {
    const n = Object.keys(log).length;
    if (!n || !confirm(`Удалить из журнала ${n} ${plural(n, 'правку', 'правки', 'правок')}? Скачанные файлы это не затронет.`)) return;
    log = {}; store(); els.forEach(show); render();
  };
  render();
  window.__edits = { exportMd, units: U, log: () => log };
})();
