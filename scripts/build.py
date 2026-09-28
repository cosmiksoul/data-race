"""
Сборка макета «Гонка за мощности».

1. Скачивает свежий архив Epoch AI (AI data centers) и страницу Satellite Explorer,
   из которой берутся координаты площадок (в CSV их нет).
2. Собирает компактный data/data.json.
3. Встраивает D3, topojson и картосновы в src/template.html → mockup/index.html
   (один самодостаточный файл, открывается без интернета).

Запуск из корня проекта:  python scripts/build.py [--offline]
--offline — не качать заново, собрать из того, что уже лежит в data/.
Зависимости: pandas (pip install pandas).
"""
import html, io, json, re, sys, zipfile, urllib.request
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA, RAW, LIB = ROOT / "data", ROOT / "data" / "raw", ROOT / "data" / "lib"
UA = {"User-Agent": "Mozilla/5.0 (data-race build script)"}
EPOCH_ZIP = "https://epoch.ai/data/data_centers/data_centers.zip"
EXPLORER = "https://epoch.ai/data/data-centers/satellite-explorer"
LIBS = {
    "d3.min.js": "https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js",
    "topojson-client.min.js": "https://cdn.jsdelivr.net/npm/topojson-client@3.1.0/dist/topojson-client.min.js",
    "states-10m.json": "https://cdn.jsdelivr.net/npm/us-atlas@3.0.1/states-10m.json",
    "countries-110m.json": "https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-110m.json",
}
TODAY = "2026-09-27"          # дата «сегодня» на экране — обнови при пересборке
PLAN_END = "2028-12-31"       # граница «ПЛАН» / «ТУМАН»
RETRIEVED = "2026-09-24"      # дата выгрузки Epoch (см. страницу Downloads)
# Фиксированный порядок владельцев = фиксированные цвета (--s1..--s8 в шаблоне).
# COLO — площадки колокейшн-операторов, у которых Epoch не указал арендатора.
OWNERS = ["Oracle", "Google", "Meta", "Microsoft", "Amazon", "SpaceXAI", "CoreWeave", "COLO"]


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def fetch(offline):
    RAW.mkdir(parents=True, exist_ok=True); LIB.mkdir(parents=True, exist_ok=True)
    zpath = RAW / "epoch_data_centers.zip"
    if not offline:
        zpath.write_bytes(get(EPOCH_ZIP))
        page = html.unescape(get(EXPLORER).decode("utf-8"))
        coords = {}
        for part in re.split(r'"id":\[0,"', page)[1:]:
            name = part.split('"', 1)[0]
            m = re.search(r'"lngLat":\[1,\[\[0,(-?[0-9.]+)\],\[0,(-?[0-9.]+)\]\]\]', part)
            if m and name not in coords:
                coords[name] = [float(m.group(1)), float(m.group(2))]
        (DATA / "coords.json").write_text(json.dumps(coords, ensure_ascii=False, indent=0), encoding="utf-8")
    for fn, url in LIBS.items():
        if not (LIB / fn).exists():
            (LIB / fn).write_bytes(get(url))
    return zpath


def md_clean(t):
    if pd.isna(t):
        return "", 0
    t = str(t)
    n = len(re.findall(r"\]\((https?://[^)]+)\)", t))
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1", t)
    t = re.sub(r"https?://\S+", "", t)
    return re.sub(r"\s+", " ", t).strip(), n


def conf_list(x):
    if pd.isna(x):
        return []
    out = []
    for p in str(x).split(","):
        p = p.strip(); m = re.match(r"(.*?)\s*#(\w+)$", p)
        out.append([m.group(1), m.group(2)] if m else [p, ""])
    return out


def build_data(zpath):
    z = zipfile.ZipFile(zpath)
    dc = pd.read_csv(io.BytesIO(z.read("data_centers.csv")))
    tl = pd.read_csv(io.BytesIO(z.read("data_center_timelines.csv")))
    tl["Date"] = pd.to_datetime(tl["Date"])
    coords = json.loads((DATA / "coords.json").read_text(encoding="utf-8"))
    missing = [n for n in dc["Name"] if n not in coords]
    if missing:
        print("! нет координат для:", missing)

    num = lambda v, k=1: round(float(v), k) if pd.notna(v) else 0
    sites, idx = [], {}
    for _, r in dc.iterrows():
        nm = r["Name"]
        if nm not in coords:
            continue
        idx[nm] = len(sites)
        owner = "COLO" if pd.isna(r["Owner"]) else re.sub(r"\s*#\w+", "", str(r["Owner"])).strip()
        oc = re.search(r"#(\w+)", str(r["Owner"])) if pd.notna(r["Owner"]) else None
        pts = [[x["Date"].strftime("%Y-%m-%d"), num(x["Power (MW)"]), num(x["IT power (MW)"]),
                int(x["H100 equivalents"]) if pd.notna(x["H100 equivalents"]) else 0,
                num(x["Total capital cost (2025 USD billions)"], 2), num(x["Buildings operational"])]
               for _, x in tl[tl["Data center"] == nm].sort_values("Date").iterrows()]
        sites.append({"n": nm, "o": owner, "oc": oc.group(1) if oc else "", "u": conf_list(r["Users"]),
                      "c": r["Country"], "ll": [round(v, 4) for v in coords[nm]], "p": pts})

    events = []
    for _, x in tl.iterrows():
        txt, n = md_clean(x["Construction status"])
        if txt and x["Data center"] in idx:
            events.append([x["Date"].strftime("%Y-%m-%d"), idx[x["Data center"]],
                           txt[:420] + ("…" if len(txt) > 420 else ""), n])
    events.sort(key=lambda e: e[0])

    agg = []
    for m in pd.date_range("2019-01-31", "2030-12-31", freq="ME"):
        cut = min(m, pd.Timestamp(TODAY)) if m.strftime("%Y-%m") == TODAY[:7] else m
        sub = tl[tl.Date <= cut].sort_values("Date").groupby("Data center").last()
        agg.append([m.strftime("%Y-%m"), round(float(sub["Power (MW)"].sum()) / 1000, 3),
                    round(float(sub["H100 equivalents"].sum()) / 1e6, 3),
                    round(float(sub["Total capital cost (2025 USD billions)"].sum()), 1)])

    data = {"meta": {"retrieved": RETRIEVED, "today": TODAY, "planEnd": PLAN_END,
                     "coverage": "44% (90% ДИ 23–81%) на 26.09.2026", "owners": OWNERS},
            "sites": sites, "events": events, "agg": agg}
    out = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    (DATA / "data.json").write_text(out, encoding="utf-8")
    print(f"data.json: {len(sites)} площадок, {len(events)} записей, {len(out)//1024} КБ")
    return out


def assemble(data_json):
    t = (ROOT / "src" / "template.html").read_text(encoding="utf-8")
    rd = lambda fn: (LIB / fn).read_text(encoding="utf-8")
    out = (t.replace("/*__D3__*/", rd("d3.min.js")).replace("/*__TOPO__*/", rd("topojson-client.min.js"))
            .replace("/*__DATA__*/", data_json.replace("</", "<\\/"))
            .replace("/*__US__*/", rd("states-10m.json")).replace("/*__WORLD__*/", rd("countries-110m.json")))
    (ROOT / "mockup" / "index.html").write_text(out, encoding="utf-8")
    print(f"mockup/index.html: {len(out)//1024} КБ")


if __name__ == "__main__":
    offline = "--offline" in sys.argv
    z = fetch(offline)
    assemble(build_data(z))
