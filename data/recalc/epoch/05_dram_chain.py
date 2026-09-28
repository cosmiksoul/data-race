"""Задача 5. Цепной индекс контрактных цен конвенциональной DRAM (TrendForce, кв/кв).

Вход: data/trendforce_dram_contract_qoq.csv (вручную из пресс-релизов TrendForce, ссылки в файле).
Индекс: I(2К25) = 1; I(q) = I(q-1) × (1 + Δq), по нижней, средней и верхней границе диапазона.
Средняя граница — середина диапазона. Вторая база: I(3К25) = 1 (цепочка 4К25→3К26).
4К26 — публичной цифры нет (отчёт TrendForce за пейволом), в цепочку не входит.
Раздельные цепочки PC и серверной DRAM не строятся: для 4К25 и 2К26 в пресс-релизах нет цифр по категориям.

Выход: derived/dram_chain_index.csv
"""
import pandas as pd
from common import ROOT, DERIVED

inp = pd.read_csv(ROOT / "data" / "trendforce_dram_contract_qoq.csv")
conv = inp[(inp.category == "conventional") & inp.low_pct.notna()].set_index("quarter")
order = ["3Q25", "4Q25", "1Q26", "2Q26", "3Q26"]

rows = [{"quarter": "2Q25", "status": "база", "idx_low": 1.0, "idx_mid": 1.0, "idx_high": 1.0,
         "idx3q25_low": None, "idx3q25_mid": None, "idx3q25_high": None}]
lo = mi = hi = 1.0
lo3 = mi3 = hi3 = None
for q in order:
    a, b = conv.loc[q, "low_pct"] / 100, conv.loc[q, "high_pct"] / 100
    lo, mi, hi = lo * (1 + a), mi * (1 + (a + b) / 2), hi * (1 + b)
    if q == "3Q25":
        lo3 = mi3 = hi3 = 1.0
    else:
        lo3, mi3, hi3 = lo3 * (1 + a), mi3 * (1 + (a + b) / 2), hi3 * (1 + b)
    rows.append({"quarter": q, "status": conv.loc[q, "status"], "qoq_low_pct": a * 100, "qoq_high_pct": b * 100,
                 "idx_low": lo, "idx_mid": mi, "idx_high": hi,
                 "idx3q25_low": lo3, "idx3q25_mid": mi3, "idx3q25_high": hi3})
out = pd.DataFrame(rows)
out.to_csv(DERIVED / "dram_chain_index.csv", index=False)
print(out.round(3).to_string(index=False))

# Варианты «откуда отсчитывать»
def chain(qs, which):
    v = 1.0
    for q in qs:
        a, b = conv.loc[q, "low_pct"] / 100, conv.loc[q, "high_pct"] / 100
        v *= 1 + {"low": a, "mid": (a + b) / 2, "high": b}[which]
    return v

variants = {
    "только итоги TrendForce: 4К25+1К26 (уровень 3К25 → 1К26)": ["4Q25", "1Q26"],
    "уровень 3К25 → 2К26 (2К26 — прогноз)": ["4Q25", "1Q26", "2Q26"],
    "уровень 3К25 → 3К26 (2К26, 3К26 — прогнозы)": ["4Q25", "1Q26", "2Q26", "3Q26"],
    "уровень 2К25 → 3К26 (все пять изменений)": order,
}
print()
for k, qs in variants.items():
    print(f"{k}: ×{chain(qs,'low'):.2f} / ×{chain(qs,'mid'):.2f} / ×{chain(qs,'high'):.2f} (низ/середина/верх)")
