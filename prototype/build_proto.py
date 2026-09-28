"""Сборка прототипа «Счёт за интеллект»: встраивает шрифты, D3, topojson, картоснову и данные в один HTML."""
import base64, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIB = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / 'data' / 'lib'  # data-race/data/lib
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / 'index.html'

RANGES = {
    'cyrillic': 'U+0301,U+0400-045F,U+0490-0491,U+04B0-04B1,U+2116',
    'latin': 'U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD',
}
FAMILIES = {'source-serif-4': 'Source Serif 4', 'ibm-plex-sans': 'IBM Plex Sans', 'ibm-plex-mono': 'IBM Plex Mono'}

faces = []
for f in sorted((HERE / 'fonts').glob('*.woff2')):
    stem = f.stem  # e.g. source-serif-4-cyrillic-400-normal
    for key, fam in FAMILIES.items():
        if stem.startswith(key + '-'):
            sub, weight, style = stem[len(key) + 1:].split('-')
            b64 = base64.b64encode(f.read_bytes()).decode()
            faces.append(f"@font-face{{font-family:'{fam}';font-style:{style};font-weight:{weight};font-display:swap;"
                         f"src:url(data:font/woff2;base64,{b64}) format('woff2');unicode-range:{RANGES[sub]}}}")
fonts_css = '\n'.join(faces)

t = (HERE / 'src' / 'proto.html').read_text(encoding='utf-8')
rd = lambda p: Path(p).read_text(encoding='utf-8')
d3 = rd(LIB / 'd3.min.js'); topo = rd(LIB / 'topojson-client.min.js')
for name, js in (('d3', d3), ('topojson', topo)):
    assert '</script' not in js.lower(), name
sites = rd(HERE / 'data' / 'proto-data.json').replace('</', '<\\/')
us = rd(LIB / 'states-10m.json')
out = (t.replace('/*__FONTS__*/', fonts_css).replace('/*__D3__*/', d3).replace('/*__TOPO__*/', topo)
        .replace('/*__SITES__*/', sites).replace('/*__US__*/', us))
OUT.write_text(out, encoding='utf-8')
print(f'{OUT}: {len(out) // 1024} КБ, шрифтов: {len(faces)}')
