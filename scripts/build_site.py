"""
Сборка страницы «Гонка за искусственным интеллектом»: content/*.md + site/src → index.html в корне (главная GitHub Pages).

Один самодостаточный файл: шрифты (woff2 в base64), D3, topojson, картооснова,
данные площадок и графиков встраиваются внутрь, сеть в рантайме не нужна.

Запуск из корня проекта:  python scripts/build_site.py
Зависимости: PyYAML (pip install pyyaml).

Верстаются только пакеты со статусом «готов к вёрстке»; для остальных строк
манифеста MANIFEST выводится заглушка. Текст пакетов не переписывается:
сборка лишь переводит их разметку (content/README.md) в HTML.
"""
import base64, csv, html, json, re, sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTENT, LIB, FONTS = ROOT / "content", ROOT / "data" / "lib", ROOT / "prototype" / "fonts"
SRC, OUT = ROOT / "site" / "src", ROOT / "index.html"

EDITION = "2026-09-28"   # дата выпуска: шапка счёта, «сегодня» на графиках — обнови при пересборке
READY = "готов к вёрстке"
MAP_LINK = "mockup/"  # экран-штаб целиком (макет v0.1, mockup/index.html)

# Каркас страницы (docs/content-plan.md, раздел 3, план v1.3). Названия — для заглушек,
# у готовых пакетов заголовок берётся из пакета. Номер блока — рабочий (пакеты, реестр,
# якоря #bNN); на странице строки нумеруются по порядку манифеста (см. DISPLAY_NO).
MANIFEST = [
    ("block", "01", None, "Вопрос и как читать", "вопрос страницы и как читать теги"),
    ("block", "11", None, "Двигатель гонки", "частота релизов → спрос на обучение и на работу моделей"),
    ("divider", "Счёт · дебет", "debit", "кто платит"),
    ("block", "02", "debit", "Техника и малый бизнес", "память, SSD, GPU, консоли · VPS, облака, аренда GPU, SaaS"),
    ("block", "03", "debit", "Счёт за свет", "PJM, тарифы, кто платит за подключение"),
    ("block", "04", "debit", "Энергосистема и климат", "доля дата-центров в электричестве, газ, уголь, АЭС, выбросы, вода · врезка «Сосед за забором»"),
    ("block", "05", "debit", "Деньги и рабочие места", "капзатраты, ВВП, долги, концентрация, вакансии · врезка «Что останется, если это пузырь»"),
    ("block", "12", "debit", "Деньги по кругу", "сеть сделок вендоров и лабораторий · оценка против прибыли"),
    ("divider", "Счёт · кредит", "credit", "что получаем"),
    ("block", "06", "credit", "Почему интеллект дешевеет, а счёт — нет", "три цены · токены на задачу · эффект отдачи"),
    ("divider", "Мир и риски", None, "страны, риски и сценарии"),
    ("block", "07", None, "Гонка стран", "пять способов измерить страны, где данных мало"),
    ("block", "13", None, "Инциденты и риски", "динамика инцидентов, типология, оценки вероятности катастрофы"),
    ("block", "08", None, "Туман", "веер сценариев до 2030 года, ограничители"),
    ("block", "09", None, "Сальдо", "итоговый счёт и индикаторы"),
    ("block", "10", None, "Методика", "как считали, какие допущения, где синтез"),
]
# рабочий номер → номер строки на странице: 00 — вступление, дальше по порядку манифеста
DISPLAY_NO = {"00": "00", **{it[1]: f"{n:02d}" for n, it in
                            enumerate((it for it in MANIFEST if it[0] == "block"), 1)}}
SIDE = {"debit": "Дебет", "credit": "Кредит"}

RANGES = {
    "cyrillic": "U+0301,U+0400-045F,U+0490-0491,U+04B0-04B1,U+2116",
    "latin": "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,"
             "U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD",
}
FAMILIES = {"source-serif-4": "Source Serif 4", "ibm-plex-sans": "IBM Plex Sans", "ibm-plex-mono": "IBM Plex Mono"}
TAGS = {"факт": "tag", "оценка": "tag est", "прогноз": "tag proj"}
ICONS = {
    "круг": '<svg width="10" height="10" aria-hidden="true"><circle cx="5" cy="5" r="4" fill="currentColor"/></svg>',
    "квадрат": '<svg width="10" height="10" aria-hidden="true"><rect x="1" y="1" width="8" height="8" fill="currentColor"/></svg>',
    "ромб": '<svg width="10" height="10" aria-hidden="true"><path d="M5 .5 9.5 5 5 9.5 .5 5z" fill="currentColor"/></svg>',
}


class BuildError(Exception):
    pass


def fail(msg):
    raise BuildError(msg)


def rd(p):
    return Path(p).read_text(encoding="utf-8")


def ru_date(iso):
    y, m, d = iso.split("-")
    return f"{d}.{m}.{y}"


# ── пакеты ───────────────────────────────────────────────────────────────────

def load_packages():
    pk = {}
    for f in sorted(CONTENT.glob("[0-9][0-9]-*.md")):
        t = rd(f).replace("\r\n", "\n")
        m = re.match(r"---\n(.*?)\n---\n(.*)", t, re.S)
        if not m:
            fail(f"{f.name}: нет YAML-шапки")
        head = yaml.safe_load(m.group(1))
        head["_body"], head["_file"] = m.group(2), f.name
        pk[str(head["block"])] = head
    return pk


class Page:
    """Состояние сборки: глоссарий, сквозная нумерация источников."""

    def __init__(self, gloss, packages):
        self.gloss, self.pk = gloss, packages
        self.src_num, self.src_order = {}, []   # "06:s3" → 3
        self.terms_used = set()

    # ── инлайн-разметка ──
    def inline(self, text, block):
        s = html.escape(str(text).strip(), quote=False)
        s = re.sub(r"\[([^\]\[]+)\]\((https?://[^)\s]+)\)",
                   lambda m: f'<a href="{html.escape(m.group(2))}" target="_blank" rel="noopener">{m.group(1)}</a>', s)
        s = re.sub(r"\[\[([\w-]+)(?:\|([^\]]+))?\]\]", lambda m: self.term(m, block), s)
        s = re.sub(r"\[\^(\w+)\]", lambda m: self.ref(m.group(1), block), s)
        s = re.sub(r"\{(факт|оценка|прогноз)\}", lambda m: f'<span class="{TAGS[m.group(1)]}">{m.group(1)}</span>', s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
        return s

    def term(self, m, block):
        key, txt = m.group(1), m.group(2)
        if key not in self.gloss:
            fail(f"блок {block}: термина «{key}» нет в content/glossary.yml")
        self.terms_used.add(key)
        return f'<span class="term" data-term="{key}">{txt or self.gloss[key]["title"]}</span>'

    def ref(self, sid, block):
        key = f"{block}:{sid}"
        if sid not in (self.pk[block].get("sources") or {}):
            fail(f"блок {block}: ссылка [^{sid}] на источник, которого нет в шапке пакета")
        if key not in self.src_num:
            self.src_order.append(key)
            self.src_num[key] = len(self.src_order)
        n = self.src_num[key]
        return f'<sup class="ref"><a href="#src-{n}" aria-label="Источник {n}">{n}</a></sup>'

    def paras(self, text, block):
        return "\n".join(f"<p>{self.inline(p, block)}</p>" for p in re.split(r"\n\s*\n", text.strip()) if p.strip())

    # ── тело пакета ──
    def body(self, p):
        """Разбирает тело пакета на элементы. Возвращает (html, директивы 00)."""
        block, out, special = str(p["block"]), [], {}
        lines = p["_body"].split("\n")
        i, marks = 0, []
        para = []

        def flush():
            if not para:
                return
            txt = " ".join(x.strip() for x in para)
            para.clear()
            if txt.startswith("> "):
                out.append(f"<blockquote>{self.inline(txt[2:], block)}</blockquote>")
            elif txt.startswith("### "):
                out.append(f"<h3>{self.inline(txt[4:], block)}</h3>")
            else:
                attrs = ""
                for k in marks:
                    if k == "lead":
                        attrs += ' class="lead"'
                    elif k.startswith("bill:"):
                        bid = k[5:]
                        if bid not in {str(r["id"]) for r in p.get("receipt") or []}:
                            fail(f"блок {block}: якорь bill:{bid} без строки в receipt")
                        attrs += f' data-bill="{bid}"'
                out.append(f"<p{attrs}>{self.inline(txt, block)}</p>")
            marks.clear()

        while i < len(lines):
            ln = lines[i]
            mm = re.match(r"<!--\s*(lead|bill:[\w-]+)\s*-->\s*$", ln.strip())
            if mm:
                flush(); marks.append(mm.group(1)); i += 1; continue
            md = re.match(r":::\s*([\w-]+)(?:\s+([\w-]+))?\s*$", ln.strip())
            if md:
                flush()
                j = i + 1
                while j < len(lines) and lines[j].strip() != ":::":
                    j += 1
                if j == len(lines):
                    fail(f"блок {block}: директива ::: {md.group(1)} не закрыта")
                raw = "\n".join(lines[i + 1:j])
                kind, arg = md.group(1), md.group(2)
                if kind in ("grid-caption", "howto"):
                    special[kind] = raw
                else:
                    out.append(self.directive(kind, arg, raw, p))
                i = j + 1; continue
            if not ln.strip():
                flush()
            elif ln.startswith("### ") or ln.startswith("> "):
                flush(); para.append(ln); flush()
            else:
                para.append(ln)
            i += 1
        flush()
        return "\n".join(out), special

    def directive(self, kind, arg, raw, p):
        block = str(p["block"])
        if kind == "bigfig":
            d = yaml.safe_load(raw)
            return (f'<div class="bigfig {p.get("side", "")}"><div class="n">{html.escape(str(d["n"]))}'
                    f'<small>{html.escape(d["unit"])}</small></div><div class="c">{self.inline(d["caption"], block)}</div></div>')
        if kind == "rowsum":
            return f'<div class="rowsum">{self.inline(raw, block)}</div>'
        if kind == "chart":
            return self.chart(arg, yaml.safe_load(raw), block)
        fail(f"блок {block}: неизвестная директива ::: {kind}")

    def chart(self, cid, d, block):
        for k in ("title", "subtitle", "source", "aria"):
            if not d.get(k):
                fail(f"блок {block}, график {cid}: нет поля {k}")
        data = {}
        for f in d.get("data") or []:
            path = ROOT / f
            if not path.exists():
                fail(f"блок {block}, график {cid}: нет файла данных {f}")
            data[path.stem] = read_csv(path)
        self.charts[cid] = {"block": block, "data": data,
                            **{k: d.get(k) for k in ("labels", "annotations", "tooltip", "form")}}
        sub = legend_icons(self.inline(d["subtitle"], block))
        wide = " wide-fig" if d.get("wide") else ""
        return (f'<figure class="card{wide}" id="{cid}" data-chart="{cid}">\n'
                f'<div class="ct">{self.inline(d["title"], block)}</div>\n'
                f'<div class="cs">{sub}</div>\n'
                f'<svg id="chart-{cid}" role="img" aria-label="{html.escape(d["aria"])}"></svg>\n'
                f'<figcaption class="csrc">{self.inline(d["source"], block)}</figcaption>\n</figure>')


def legend_icons(s):
    """Значки легенды перед «OpenAI (круг)» и т. п. Текст подзаголовка не меняется."""
    s = re.sub(r"([\wА-яЁё.\-]+) \((круг|квадрат|ромб)\)",
               lambda m: f'<span class="lg"><i>{ICONS[m.group(2)]}</i>{m.group(0)}</span>', s)
    return s.replace("синяя ступенчатая линия", '<span class="lg"><i class="stepkey"></i>синяя ступенчатая линия</span>')


NUM = re.compile(r"^-?(\d+\.?\d*|\.\d+)$")


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for k, v in r.items():
            if isinstance(v, str) and NUM.match(v.strip()) and not re.match(r"^0\d", v.strip()):
                r[k] = float(v) if "." in v else int(v)
    return rows


# ── площадки штаба: сетка «1 точка = 100 МВт», метод наибольшего остатка ────

def largest_remainder(vals, unit=100):
    exact = [v / unit for v in vals]
    total = round(sum(vals) / unit)
    base = [int(x) for x in exact]
    rest = total - sum(base)
    order = sorted(range(len(vals)), key=lambda k: (-(exact[k] - base[k]), -vals[k]))
    for k in order[:rest]:
        base[k] += 1
    return base


def build_sites():
    d = json.loads(rd(ROOT / "data" / "data.json"))
    today, end = d["meta"]["today"], d["meta"]["planEnd"]
    at = lambda s, D: next((r[1] for r in reversed(s["p"]) if r[0] <= D), 0.0)
    sites = []
    for s in d["sites"]:
        t, e = at(s, today), at(s, end)
        sites.append({"n": s["n"], "c": s["c"], "ll": s["ll"], "o": s["o"], "t": t, "e": e,
                      "tl": [[r[0], r[1]] for r in s["p"] if r[0] <= today]})
    for s, n in zip(sites, largest_remainder([s["t"] for s in sites])):
        s["dt"] = n
    for s, n in zip(sites, largest_remainder([max(0.0, s["e"] - s["t"]) for s in sites])):
        s["dp"] = n
    tot, add = sum(s["t"] for s in sites), sum(max(0.0, s["e"] - s["t"]) for s in sites)
    return {"today": today, "end": end, "totalGW": round(tot / 1000, 1), "planAddGW": round(add / 1000, 1),
            "operating": sum(1 for s in sites if s["t"] > 0), "count": len(sites), "sites": sites}


# ── сборка ───────────────────────────────────────────────────────────────────

def fonts_css():
    faces = []
    for f in sorted(FONTS.glob("*.woff2")):
        for key, fam in FAMILIES.items():
            if f.stem.startswith(key + "-"):
                sub, weight, style = f.stem[len(key) + 1:].split("-")
                b64 = base64.b64encode(f.read_bytes()).decode()
                faces.append(f"@font-face{{font-family:'{fam}';font-style:{style};font-weight:{weight};font-display:swap;"
                             f"src:url(data:font/woff2;base64,{b64}) format('woff2');unicode-range:{RANGES[sub]}}}")
    return "\n".join(faces)


def rowline(side, no, text):
    s = f'<span class="side {side}">{SIDE[side]}</span>' if side in SIDE else ""
    return f'<div class="rowline">{s}<span>строка {no}</span><span>{html.escape(text)}</span></div>'


def main():
    pk = load_packages()
    gloss = yaml.safe_load(rd(CONTENT / "glossary.yml"))
    page = Page(gloss, pk)
    page.charts = {}
    ready = {k: v for k, v in pk.items() if v.get("status") == READY}
    for k, v in pk.items():
        if k not in ready:
            print(f"  пропущен пакет {v['_file']}: статус «{v.get('status')}»")

    # 00 — штаб и подпись к сетке единиц
    p0 = ready.get("00")
    if not p0:
        fail("пакет 00 не готов к вёрстке: без него нет вступления")
    _, sp0 = page.body(p0)
    hq, gc = p0["hq"], yaml.safe_load(sp0["grid-caption"])
    legend = "".join(f'<span><i class="{c}"></i>{html.escape(t)}</span>' for c, t in zip(("f", "h"), gc["legend"]))
    # преамбула над картой (план v1.3): короткий текст на тёмном поле штаба, под ним — сцена
    pre = (f'<section id="preamble" aria-label="Вступление"><div class="pre-in">'
           f'{page.paras(p0["preamble"], "00")}</div></section>\n') if p0.get("preamble") else ""
    hq_html = f"""<a class="skip" href="#paper">К тексту</a>
{pre}<section id="hq" aria-label="{html.escape(hq['brand'].capitalize())}: вступление">
  <div class="stage" id="stage">
    <svg id="stageSvg" aria-hidden="true"></svg>
    <div class="hq-ui" id="hqUi">
      <div class="hq-top">
        <div><div class="hq-brand">{html.escape(hq['brand'])}</div><div class="hq-sub">{html.escape(hq['sub'])}</div></div>
        <div class="hq-clock" aria-hidden="true">T <b id="hqT"></b></div>
      </div>
      <div class="hq-hero"><div class="lbl">{html.escape(hq['counter_label'])}</div><div class="num" id="hqNum">0<small>ГВт</small></div></div>
      <a class="hq-link" href="{MAP_LINK}">{html.escape(hq['link'])}</a>
      <div class="hq-cta">{html.escape(hq['cta'])} <span aria-hidden="true">↓</span></div>
    </div>
    <div class="opening" id="opening">
      <div class="intro">
        <div class="kicker">{html.escape(p0['kicker'])}</div>
        <h1>{html.escape(p0['title'])}</h1>
        <p class="dek">{html.escape(p0['dek'])}</p>
      </div>
      <div class="cap" data-bill="00">
        <div class="rl">{html.escape(gc['rowline'])}</div>
        {page.inline(gc['text'], '00')}
        <div class="key">{legend}</div>
        <div class="src">{page.inline(gc['source'], '00')}</div>
      </div>
    </div>
  </div>
</section>"""

    parts = []
    if "howto" in sp0:
        parts.append(f'<div class="howto">{page.paras(sp0["howto"], "00")}</div>')
    for item in MANIFEST:
        if item[0] == "divider":
            _, label, side, note = item
            parts.append(f'<div class="divider {side or ""}"><span>{html.escape(label)}</span><i></i><span class="dn">{html.escape(note)}</span></div>')
            continue
        _, no, side, name, topics = item
        p = ready.get(no)
        if p:
            body, _ = page.body(p)
            parts.append(f'<article class="block" id="b{no}">\n{rowline(p.get("side"), DISPLAY_NO[no], p.get("rowline", name))}\n'
                         f'<h2>{html.escape(p["title"])}</h2>\n{body}\n</article>')
        else:
            parts.append(f'<article class="block stub" id="b{no}">\n{rowline(side, DISPLAY_NO[no], name)}\n'
                         f'<h2>{html.escape(name)}</h2>\n'
                         f'<div class="pending"><b>Строка в работе.</b> {html.escape(topics)}.</div>\n</article>')

    # глоссарий: сначала термины в порядке употребления на странице, затем остальные
    keys = [k for k in gloss if k in page.terms_used] + [k for k in gloss if k not in page.terms_used]
    parts.append('<section id="glossary" aria-labelledby="gl-h"><h2 id="gl-h">Глоссарий</h2><dl>' +
                 "".join(f'<div><dt>{html.escape(gloss[k]["title"])}</dt><dd>{html.escape(gloss[k]["text"])}</dd></div>' for k in keys) +
                 "</dl></section>")

    # источники: упомянутые — по порядку первого упоминания, затем остальные по блокам
    for b, p in ready.items():
        for sid in p.get("sources") or {}:
            key = f"{b}:{sid}"
            if key not in page.src_num:
                page.src_order.append(key); page.src_num[key] = len(page.src_order)
                print(f"  источник {key} нигде не упомянут в тексте — добавлен в конец списка")
    lis = []
    for n, key in enumerate(page.src_order, 1):
        b, sid = key.split(":")
        lis.append(f'<li id="src-{n}">{page.inline(ready[b]["sources"][sid], b)}</li>')
    parts.append('<section id="sources" aria-labelledby="src-h"><h2 id="src-h">Источники</h2><ol>' + "\n".join(lis) + "</ol></section>")
    parts.append(f"""<footer class="colophon">«{html.escape(p0['title'])}» · выпуск {ru_date(EDITION)}. Данные о площадках — Epoch AI (CC BY 4.0).
Шрифты Source Serif 4 и IBM Plex (SIL Open Font License). Картографическая основа — us-atlas (US Census).
Визуальный язык графиков — по образцу <a href="https://github.com/larashero3-dotcom/lieflat-charts" target="_blank" rel="noopener">Lieflat Charts</a>; код написан заново.</footer>""")

    # строки счёта
    bill = {}
    for b, p in ready.items():
        for r in p.get("receipt") or []:
            rid = str(r["id"])
            if rid in bill:
                fail(f"строка счёта {rid} повторяется")
            bill[rid] = {"side": r["side"], "no": DISPLAY_NO[b], "ttl": r["title"], "val": r["value"], "who": r["who"], "tg": r["tags"]}

    sites = build_sites()
    total_f, total_h = sum(s["dt"] for s in sites["sites"]), sum(s["dp"] for s in sites["sites"])
    m = re.search(r"(\d+) закрашенные \+ (\d+) полых", gc.get("grid", ""))
    if m and (int(m.group(1)), int(m.group(2))) != (total_f, total_h):
        fail(f"сетка единиц: в пакете {m.group(1)} + {m.group(2)}, из data.json вышло {total_f} + {total_h}")

    js_data = {"edition": EDITION, "gloss": {k: [v["title"], v["text"]] for k, v in gloss.items()},
               "bill": bill, "charts": page.charts}
    jsn = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    app = rd(SRC / "app.js").replace("/*__CHARTS__*/", "\n".join(rd(f) for f in sorted((SRC / "charts").glob("*.js"))))
    libs = {n: rd(LIB / n) for n in ("d3.min.js", "topojson-client.min.js")}
    for n, js in list(libs.items()) + [("app.js", app)]:
        if "</script" in js.lower():
            fail(f"{n}: внутри встречается </script")

    t = rd(SRC / "page.html")
    rep = {
        "__TITLE__": html.escape(p0["title"]), "__DESC__": html.escape(p0["dek"]),
        "__EDITION__": ru_date(EDITION), "__HQ__": hq_html, "__BODY__": "\n\n".join(parts),
        "/*__FONTS__*/": fonts_css(), "/*__D3__*/": libs["d3.min.js"], "/*__TOPO__*/": libs["topojson-client.min.js"],
        "/*__DATA__*/": jsn(js_data), "/*__SITES__*/": jsn(sites), "/*__US__*/": rd(LIB / "states-10m.json"),
        "/*__APP__*/": app,
    }
    for k, v in rep.items():
        if k not in t:
            fail(f"в шаблоне нет метки {k}")
        t = t.replace(k, v)
    OUT.write_text(t, encoding="utf-8", newline="\n")
    kb = OUT.stat().st_size // 1024
    print(f"{OUT.relative_to(ROOT)}: {kb} КБ · пакетов свёрстано: {len(ready)} · строк счёта: {len(bill)} · "
          f"источников: {len(page.src_order)} · графиков: {len(page.charts)} · сетка: {total_f} + {total_h} точек")
    if kb > 3072:
        print("  внимание: файл больше 3 МБ")


if __name__ == "__main__":
    try:
        main()
    except BuildError as e:
        sys.exit(f"Ошибка сборки: {e}")
