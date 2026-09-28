"""
Проверка собранной страницы index.html (чек-лист из CLAUDE.md).

Запуск из корня проекта:  python scripts/check_site.py [--quick]
Зависимости: pip install playwright && python -m playwright install chromium

Снимает кадры в screens/ (папка в .gitignore) на 1440×900 светлой и тёмной,
1024×768 и 390×844: холодный старт, середина и финал перехода, блоки, графики,
счёт. Проверяет: ошибки консоли, горизонтальную прокрутку, наезды подписей
графиков друг на друга и на точки, что счёт помещается в экран, что ссылки
на источники и подсказки не битые, что страница без ошибок открывается в окне
нулевой высоты (фоновая вкладка, превью) и потом раскладывается.
Код выхода 1, если есть замечания.
"""
import asyncio, subprocess, sys, tempfile
from collections import Counter
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "index.html").as_uri()
SHOTS = ROOT / "screens"
QUICK = "--quick" in sys.argv

VIEWS = [  # имя, размер, тема, reduced motion
    ("1440-light", (1440, 900), "light", False),
    ("1440-dark", (1440, 900), "dark", False),
    ("1024", (1024, 768), "light", False),
    ("390", (390, 844), "light", False),
    ("1440-rm", (1440, 900), "light", True),
]

# наезды: пересечение прямоугольников подписей между собой и с точками данных
OVERLAPS = r"""
() => {
  const out = [];
  const R = e => e.getBoundingClientRect();
  const hit = (a, b, pad = 0.5) => Math.min(a.right, b.right) - Math.max(a.left, b.left) > pad && Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > pad;
  document.querySelectorAll('figure.card > svg').forEach(svg => {
    const id = svg.closest('figure').id;
    const texts = [...svg.querySelectorAll('text')].filter(t => t.textContent.trim()).map(t => ({ t: t.textContent.trim(), r: R(t) }));
    const marks = [...svg.querySelectorAll('.mark > :not(.hit), :scope > g > circle')].map(m => ({ r: R(m), n: m.parentNode.getAttribute('aria-label') || 'точка' }));
    for (let i = 0; i < texts.length; i++) {
      for (let j = i + 1; j < texts.length; j++) if (hit(texts[i].r, texts[j].r)) out.push(`${id}: «${texts[i].t}» × «${texts[j].t}»`);
      for (const m of marks) if (hit(texts[i].r, m.r, 1)) { out.push(`${id}: «${texts[i].t}» на точке ${m.n}`); break; }
      if (texts[i].r.right > innerWidth || texts[i].r.left < 0) out.push(`${id}: «${texts[i].t}» за краем экрана`);
    }
  });
  return out;
}
"""

INTEGRITY = r"""
() => {
  const out = [];
  document.querySelectorAll('a[href^="#"]').forEach(a => { const id = a.getAttribute('href').slice(1); if (id && !document.getElementById(id)) out.push('битая ссылка ' + a.getAttribute('href')); });
  const g = JSON.parse(document.getElementById('d-page').textContent).gloss;
  document.querySelectorAll('.term').forEach(t => { if (!g[t.dataset.term]) out.push('нет подсказки ' + t.dataset.term); });
  document.querySelectorAll('figure[data-chart]').forEach(f => { const s = f.querySelector(':scope > svg'); if (!s || !s.childElementCount) out.push('пустой график ' + f.id); });
  return out;
}
"""


async def scroll_to(pg, js_y, wait=450):
    await pg.evaluate(f"window.scrollTo(0, Math.max(0, {js_y}))")
    await pg.wait_for_timeout(wait)


def watch(pg, name, issues):
    """Ошибки и предупреждения консоли (в том числе сообщения браузера о разборе SVG) и исключения JS."""
    pg.on("console", lambda m: issues.append(f"[{name}] консоль {m.type}: {m.text}") if m.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: issues.append(f"[{name}] ошибка JS: {e}"))


async def check_hidden_start(b, issues):
    """Страница открыта в окне нулевой высоты (фоновая вкладка, превью, скрытый фрейм),
    затем окно получает размер: ошибок быть не должно, сетка штаба раскладывается."""
    name = "фрейм 0→700"
    ctx = await b.new_context(viewport={"width": 1100, "height": 760})
    pg = await ctx.new_page()
    watch(pg, name, issues)
    site = (ROOT / "index.html").read_bytes()

    async def serve(route):
        if route.request.url.endswith("/site/"):
            await route.fulfill(body=site, content_type="text/html; charset=utf-8")
        else:
            await route.fulfill(body='<body style="margin:0"><iframe id="f" src="/site/" style="width:1024px;height:0;border:0"></iframe>',
                                content_type="text/html; charset=utf-8")
    await pg.route("http://check.test/**", serve)
    await pg.goto("http://check.test/")
    await pg.wait_for_timeout(2500)
    await pg.evaluate("document.getElementById('f').style.height = '700px'")
    await pg.wait_for_timeout(7500)
    st = await pg.frames[1].evaluate("""(() => { const cs = [...document.querySelectorAll('#stageSvg circle')];
        return { dots: cs.length, grid: !!window.__sch.grid(),
                 bad: cs.filter(c => ['cx', 'cy'].some(a => c.hasAttribute(a) && !isFinite(parseFloat(c.getAttribute(a))))).length }; })()""")
    if not st["grid"] or st["dots"] < 484 or st["bad"]:
        issues.append(f"[{name}] сетка штаба не разложилась после появления размера: {st}")
    await pg.screenshot(path=str(SHOTS / "hidden-start_00-cold.png"))
    await ctx.close()


async def check_view(b, name, size, scheme, rm, issues):
    ctx = await b.new_context(viewport={"width": size[0], "height": size[1]}, color_scheme=scheme,
                              reduced_motion="reduce" if rm else "no-preference",
                              is_mobile=size[0] < 720, has_touch=size[0] < 720, device_scale_factor=1)
    pg = await ctx.new_page()
    watch(pg, name, issues)
    shot = lambda lab: pg.screenshot(path=str(SHOTS / f"{name}_{lab}.png"))

    async def hscroll(where):
        if await pg.evaluate("document.documentElement.scrollWidth > innerWidth"):
            issues.append(f"[{name}] горизонтальная прокрутка ({where})")

    await pg.goto(PAGE)
    await pg.wait_for_timeout(2500)  # середина автопроигрывания штаба
    await shot("00-cold"); await hscroll("холодный старт")
    over = await pg.evaluate("""(() => { const p = document.querySelector('.hq-pre'); if (!p) return null;
        const a = p.getBoundingClientRect(), h = document.querySelector('.hq-hero').getBoundingClientRect(); return a.bottom > h.top - 4 ? 'счётчик' : null; })()""")
    if over:
        issues.append(f"[{name}] преамбула наезжает на {over}")
    base = await pg.evaluate('document.getElementById("hq").offsetTop')
    await scroll_to(pg, base, 7200)  # сцена на экране: автопроигрывание 2021 → сегодня
    await shot("00b-hq"); await hscroll("штаб")
    if rm and QUICK:
        await ctx.close(); return
    H = await pg.evaluate('document.getElementById("hq").offsetHeight - innerHeight')
    for frac, lab in [(.2, "01-trans-a"), (.35, "02-trans-mid"), (.6, "03-trans-late"), (1.0, "04-trans-final")]:
        await scroll_to(pg, base + int(H * frac), 600); await shot(lab)
    await hscroll("финал перехода")
    printed = await pg.evaluate("document.querySelectorAll('#billList li[data-no]').length")
    if printed < 1:
        issues.append(f"[{name}] строка 00 не напечаталась в финале перехода")
    if rm:
        await ctx.close(); return

    # подсказка термина с клавиатуры
    await scroll_to(pg, base + H + 10)
    await pg.focus(".opening .term") if await pg.locator(".opening .term").count() else None
    await pg.wait_for_timeout(200)
    if not await pg.evaluate("document.getElementById('tip').classList.contains('on')"):
        issues.append(f"[{name}] подсказка термина не открылась по фокусу")
    await pg.evaluate("document.activeElement.blur()")

    targets = [("05-howto", ".howto", 40), ("06-stubs", "#b01", 40), ("06b-b12", "#b12", 40), ("07-b06", "#b06", 40), ("08-fig1", "#fig1", 60),
               ("09-fig1b", "#fig1b", 60), ("10-fig2", "#fig2", 80), ("11-b06-end", ".rowsum", 300),
               ("12-world", "#b07", 40), ("13-glossary", "#glossary", 40), ("14-sources", "#sources", 40)]
    for lab, sel, pad in targets:
        await scroll_to(pg, f'document.querySelector("{sel}").getBoundingClientRect().top + scrollY - {pad}', 1400 if "fig" in lab else 500)
        await shot(lab); await hscroll(lab)

    # все якоря счёта: пройти по порядку, затем проверить, что счёт помещается в экран
    for i in range(await pg.locator("[data-bill]").count()):
        await scroll_to(pg, f'document.querySelectorAll("[data-bill]")[{i}].getBoundingClientRect().top + scrollY - innerHeight * .3', 250)
    n = await pg.evaluate("document.querySelectorAll('#billList li[data-no]').length")
    total = await pg.evaluate("Object.keys(JSON.parse(document.getElementById('d-page').textContent).bill).length")
    if n != total:
        issues.append(f"[{name}] напечатано строк счёта: {n} из {total}")
    await scroll_to(pg, 'document.querySelector(".rowsum").getBoundingClientRect().top + scrollY - 200', 700)
    if size[0] > 1180:
        fit = await pg.evaluate("""(() => { const r = document.getElementById('receipt'), b = r.getBoundingClientRect();
            return { bottom: b.bottom, over: r.scrollHeight - r.clientHeight }; })()""")
        if fit["bottom"] > size[1] or fit["over"] > 1:
            issues.append(f"[{name}] счёт не помещается в экран: {fit}")
        await shot("15-receipt")
        await pg.click("#billList li.compact")
        await pg.wait_for_timeout(300); await shot("16-receipt-expanded")
    else:
        await pg.click("#receiptBarBtn"); await pg.wait_for_timeout(400)
        fit = await pg.evaluate("(() => { const b = document.getElementById('receiptBar').getBoundingClientRect(); return { top: b.top, bottom: b.bottom }; })()")
        if fit["top"] < 0 or fit["bottom"] > size[1] + 1:
            issues.append(f"[{name}] плашка счёта не помещается в экран: {fit}")
        await shot("15-receipt-bar")
        await pg.click("#receiptBarBtn")

    # подписи графиков и целостность ссылок — после финальной отрисовки
    await scroll_to(pg, 'document.querySelector("#fig2").getBoundingClientRect().top + scrollY - 80', 1500)
    for o in await pg.evaluate(OVERLAPS):
        issues.append(f"[{name}] наезд подписей: {o}")
    for o in await pg.evaluate(INTEGRITY):
        issues.append(f"[{name}] {o}")

    # подсказка точки графика с клавиатуры
    await pg.focus("#fig1 .mark"); await pg.wait_for_timeout(150)
    if not await pg.evaluate("document.getElementById('tip').classList.contains('on')"):
        issues.append(f"[{name}] подсказка точки графика не открылась по фокусу")
    await shot("17-fig1-focus")

    # переключатель темы: авто → светлая → тёмная, выбор переживает перезагрузку
    if name == "1440-light":
        await pg.click("#themeBtn"); await pg.click("#themeBtn")
        await pg.reload(); await pg.wait_for_timeout(500)
        if await pg.evaluate("document.documentElement.dataset.theme") != "dark":
            issues.append(f"[{name}] выбор темы не сохранился после перезагрузки")
        await scroll_to(pg, 'document.querySelector("#fig1").getBoundingClientRect().top + scrollY - 60', 900)
        await shot("18-theme-dark-toggle")
        for o in await pg.evaluate(OVERLAPS):
            issues.append(f"[{name}/тёмная кнопкой] наезд подписей: {o}")
    await ctx.close()


async def check_edit(b, name, size, issues):
    """edit.html: правка на месте, правка в окне, журнал, сохранение после перезагрузки,
    выгрузка и проверка выгрузки скриптом apply_edits.py (без записи в пакеты)."""
    name = f"правка {name}"
    ctx = await b.new_context(viewport={"width": size[0], "height": size[1]}, is_mobile=size[0] < 720,
                              has_touch=size[0] < 720, device_scale_factor=1)
    pg = await ctx.new_page()
    watch(pg, name, issues)
    shot = lambda lab: pg.screenshot(path=str(SHOTS / f"edit-{size[0]}_{lab}.png"))
    await pg.goto((ROOT / "edit.html").as_uri())
    await pg.wait_for_timeout(1200)
    if "data-ed=" in (ROOT / "index.html").read_text(encoding="utf-8"):
        issues.append(f"[{name}] отметки режима правки попали в index.html")
    n_units = await pg.evaluate("window.__edits.units.length")
    n_els = await pg.evaluate("document.querySelectorAll('[data-ed]').length")
    if n_units < 50 or n_els < n_units - 10:
        issues.append(f"[{name}] мало редактируемого текста: кусков {n_units}, на странице {n_els}")
    log_n = "Object.keys(window.__edits.log()).length"

    async def click(sel):
        await scroll_to(pg, f'document.querySelector("{sel}").getBoundingClientRect().top + scrollY - innerHeight * .3', 300)
        await pg.click(sel)
        await pg.wait_for_timeout(150)

    # 1. абзац без разметки — правка на месте
    plain = await pg.evaluate("""(() => { const U = window.__edits.units;
        const el = [...document.querySelectorAll('#b06 p[data-ed]')].find(e => !U[+e.dataset.ed].markup); return el && el.dataset.ed; })()""")
    await click(f"[data-ed='{plain}']")
    if await pg.evaluate("id => !document.querySelector(`[data-ed='${id}']`).isContentEditable", plain):
        issues.append(f"[{name}] абзац не стал редактируемым по щелчку")
    await pg.keyboard.press("Control+End"); await pg.keyboard.type(" ПРОВЕРКА")
    await shot("01-inline")
    await pg.keyboard.press("Enter"); await pg.wait_for_timeout(150)
    if await pg.evaluate(log_n) != 1:
        issues.append(f"[{name}] правка на месте не попала в журнал")
    # 2. абзац с терминами и ссылками — правка в окне, в разметке пакета
    marked = await pg.evaluate("""(() => { const U = window.__edits.units;
        const el = [...document.querySelectorAll('#b06 p[data-ed]')].find(e => U[+e.dataset.ed].markup); return el && el.dataset.ed; })()""")
    await click(f"[data-ed='{marked}']")
    if not await pg.evaluate("document.getElementById('edDlg').open"):
        issues.append(f"[{name}] окно правки не открылось для текста с разметкой")
    else:
        await pg.fill("#edDlgT", (await pg.input_value("#edDlgT")) + " ПРОВЕРКА-2")
        await pg.fill("#edDlgN", "пометка из проверки")
        await shot("02-dialog")
        await pg.click("#edDlgS"); await pg.wait_for_timeout(150)
    # 3. заголовок блока — поле YAML
    await click("#b06 h2[data-ed]")
    await pg.keyboard.press("Control+End"); await pg.keyboard.type(" (проверка)"); await pg.keyboard.press("Enter")
    await pg.wait_for_timeout(150)
    if await pg.evaluate(log_n) != 3:
        issues.append(f"[{name}] в журнале {await pg.evaluate(log_n)} правок вместо 3")
    await pg.click("#edBtn"); await pg.wait_for_timeout(200)
    await shot("03-panel")
    if await pg.evaluate("document.documentElement.scrollWidth > innerWidth"):
        issues.append(f"[{name}] горизонтальная прокрутка")
    # журнал переживает перезагрузку, выгрузка читается скриптом применения
    await pg.reload(); await pg.wait_for_timeout(1000)
    if await pg.evaluate("document.querySelectorAll('.ed-changed').length") < 3:
        issues.append(f"[{name}] правки не восстановились после перезагрузки")
    md = await pg.evaluate("window.__edits.exportMd()")
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
        fh.write(md)
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "apply_edits.py"), fh.name, "--dry-run"],
                       capture_output=True, text=True)
    Path(fh.name).unlink()
    if r.returncode or "применимы: 3" not in r.stdout:
        issues.append(f"[{name}] выгрузка не применяется: {r.stdout.strip().splitlines()[-1:] or r.stderr.strip()}")
    await ctx.close()


async def main():
    SHOTS.mkdir(exist_ok=True)
    for f in SHOTS.glob("*.png"):
        f.unlink()
    issues = []
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for v in VIEWS:
            await check_view(b, *v, issues)
            print(f"  {v[0]}: готово")
        await check_hidden_start(b, issues)
        print("  фрейм 0→700: готово")
        for nm, size in (("1440", (1440, 900)), ("390", (390, 844))):
            await check_edit(b, nm, size, issues)
            print(f"  режим правки {nm}: готово")
        await b.close()
    kb = (ROOT / "index.html").stat().st_size // 1024
    print(f"Кадров: {len(list(SHOTS.glob('*.png')))} в {SHOTS.relative_to(ROOT)}/ · размер страницы {kb} КБ")
    if issues:
        uniq = Counter(issues)  # одна ошибка в каждом кадре анимации даёт тысячи одинаковых строк
        print(f"Замечаний: {len(issues)}, разных: {len(uniq)}")
        print("\n".join(f"  {i}" + (f"  (×{n})" if n > 1 else "") for i, n in uniq.most_common(40))); sys.exit(1)
    print("Замечаний нет: консоль чистая, горизонтальной прокрутки нет, подписи не наезжают, счёт помещается в экран")


asyncio.run(main())
