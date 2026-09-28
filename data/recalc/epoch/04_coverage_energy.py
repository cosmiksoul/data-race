"""Задачи 4 и 6. Охват хаба Epoch → мировой эквивалент; энергетические пересчёты.

Константы из первоисточников (открыты 28.09.2026):
  Epoch, https://epoch.ai/data/ai-data-centers (обновлено 24.09.2026):
    «we estimate this database's coverage of global deployed AI computing capacity to be 44%
     as of September 28, 2026 (90% CI: 23% to 81%)» — охват в единицах вычислений (H100e), на сегодня;
    «since Q1 2024 where coverage is 22% (90% CI: 11% to 49%)»;
    «the average power consumption of these data centers is typically 60–80% of capacity».
  Epoch, https://epoch.ai/data-insights/ai-datacenter-power (16.01.2026):
    мир ≈ 30 ГВт в 4К2025 = TDP проданных чипов × 2,5 (мощность объекта).
  IEA, Key Questions on Energy and AI (2026), базовый сценарий:
    AI-ориентированные ДЦ ≈ 465 ТВт·ч в 2030; все ДЦ 485 ТВт·ч (2025) → ~950 ТВт·ч (2030).
  EIA, Electric Sales, Revenue, and Average Price 2024, Table 5A (выпуск 07.10.2025):
    U.S. Total — 143 144 185 бытовых потребителей, 863,275 кВт·ч в месяц → 10 359 кВт·ч в год.
  EIA FAQ id=97: 10 791 кВт·ч в год (2022) — значение, на которое опирается план (~10,8 тыс.).

Выход: derived/coverage_energy.csv
"""
import pandas as pd
from common import load_hub, snapshot, DERIVED, OWN_DIR, TODAY, PLAN_DATE

HOURS = 8760
COV, COV_LO, COV_HI = 0.44, 0.23, 0.81
UTIL_LO, UTIL_HI = 0.60, 0.80
IEA_AI_TWH_2030 = 465
EIA_KWH_2024 = 863.27502 * 12
EIA_CUST_2024 = 143_144_185
EIA_KWH_2022 = 10_791

dc, tl = load_hub()
rows = []


def add(block, name, value, unit, formula):
    rows.append({"block": block, "metric": name, "value": value, "unit": unit, "formula": formula})


now, plan = snapshot(tl, dc, TODAY), snapshot(tl, dc, PLAN_DATE)
F0, I0, H0 = now.facility_mw.sum() / 1000, now.it_mw.sum() / 1000, now.h100e.sum() / 1e6
F1, I1, H1 = plan.facility_mw.sum() / 1000, plan.it_mw.sum() / 1000, plan.h100e.sum() / 1e6

# --- Задача 4: хаб / охват
for lab, v, u in [("мощность объектов сегодня", F0, "ГВт"), ("IT-мощность сегодня", I0, "ГВт"),
                  ("H100e сегодня", H0, "млн H100e"), ("мощность объектов план 31.12.2028", F1, "ГВт"),
                  ("IT-мощность план 31.12.2028", I1, "ГВт"), ("H100e план 31.12.2028", H1, "млн H100e")]:
    add("08/07", f"{lab} → мир (центр)", v / COV, u, f"{v:.3f}/0.44")
    add("08/07", f"{lab} → мир (90% ДИ)", f"{v/COV_HI:.1f}-{v/COV_LO:.1f}", u, f"{v:.3f}/0.81 … {v:.3f}/0.23")

# Проверка через продажи чипов: TDP ускорителей × 2,5 (метод Epoch data insight)
own = pd.read_csv(OWN_DIR / "ai_chip_owners_cumulative_by_designer.csv")
tdp_q4 = own[own["End date"] == "2025-12-31"]["Power in MW (median)"].sum() / 1000
end25 = snapshot(tl, dc, "2025-12-31").facility_mw.sum() / 1000
add("08", "мир 4К2025: TDP ускорителей (Chip Owners)", tdp_q4, "ГВт", "сумма Power in MW (median), 4К2025")
add("08", "мир 4К2025: мощность объектов = TDP × 2,5", tdp_q4 * 2.5, "ГВт", f"{tdp_q4:.2f}×2.5")
add("08", "хаб 31.12.2025, мощность объектов", end25, "ГВт", "правило «на дату»")
add("08", "охват хаба по мощности на конец 2025", end25 / (tdp_q4 * 2.5) * 100, "%", f"{end25:.2f}/{tdp_q4*2.5:.2f}")

# --- Задача 6: энергия
iea_avg = IEA_AI_TWH_2030 * 1e3 / HOURS
add("08", "IEA 465 ТВт·ч (2030) → средняя нагрузка", iea_avg, "ГВт", "465 000 ГВт·ч / 8760 ч")
add("08", "IEA 465 ТВт·ч → мощность при загрузке 60–80%", f"{iea_avg/UTIL_HI:.1f}-{iea_avg/UTIL_LO:.1f}", "ГВт",
    "53,1/0,8 … 53,1/0,6")
for lab, cap in [("план хаба 2028", F1), ("план хаба 2028 → мир (÷0,44)", F1 / COV)]:
    add("08", f"{lab}: годовое потребление при загрузке 60–80%",
        f"{cap*UTIL_LO*HOURS/1e3:.0f}-{cap*UTIL_HI*HOURS/1e3:.0f}", "ТВт·ч/год", f"{cap:.1f} ГВт × 0,6…0,8 × 8760 ч")

twh_full = F0 * HOURS / 1e3
add("00", "17,3 ГВт × 8760 ч (загрузка 100%)", twh_full, "ТВт·ч/год", f"{F0:.3f}×8760/1000")
add("00", "домохозяйств США, загрузка 100%, EIA 2024 (10 359 кВт·ч)", twh_full * 1e9 / EIA_KWH_2024 / 1e6, "млн",
    "ТВт·ч×1e9 / 10359")
add("00", "домохозяйств США, загрузка 100%, EIA 2022 (10 791 кВт·ч)", twh_full * 1e9 / EIA_KWH_2022 / 1e6, "млн",
    "ТВт·ч×1e9 / 10791")
add("00", "домохозяйств США, загрузка 60–80%, EIA 2024",
    f"{twh_full*UTIL_LO*1e9/EIA_KWH_2024/1e6:.1f}-{twh_full*UTIL_HI*1e9/EIA_KWH_2024/1e6:.1f}", "млн",
    "×0,6…0,8")
us_f = now.loc[now.Country == "United States", "facility_mw"].sum() / 1000
add("00", "только площадки в США (загрузка 100%), EIA 2024", us_f * HOURS * 1e6 / EIA_KWH_2024 / 1e6, "млн",
    f"{us_f:.2f} ГВт×8760")
add("00", "доля от всех бытовых потребителей США (загрузка 100%)",
    twh_full * 1e9 / EIA_KWH_2024 / EIA_CUST_2024 * 100, "%", "/143 144 185")

out = pd.DataFrame(rows)
out.to_csv(DERIVED / "coverage_energy.csv", index=False)
pd.set_option("display.width", 220)
pd.set_option("display.max_colwidth", 70)
print(out.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
