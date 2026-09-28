"""Задача 1. Агрегаты хаба ДЦ Epoch: мощность объектов, IT-мощность, H100e на дату.

Выход:
  derived/hub_totals_by_date.csv       — итоги на ключевые даты
  derived/hub_timeseries_quarterly.csv — ряд по концам кварталов 2023–2030 (для блоков 00/08)
  derived/hub_sites_2026-09-27.csv     — площадки на 27.09.2026 (для сетки «1 точка = 100 МВт»)
  derived/hub_sites_2028-12-31.csv     — площадки на 31.12.2028
"""
import numpy as np
import pandas as pd
from common import load_hub, snapshot, DERIVED, EXPORT_DATE, TODAY, PLAN_DATE

dc, tl = load_hub()

# Проверка: 'Current power (MW)' в data_centers.csv = IT-мощность на дату выгрузки
s_exp = snapshot(tl, dc, EXPORT_DATE)
cur = dc.set_index("Name")
match_it = (abs(cur["Current power (MW)"] - s_exp["it_mw"]) < 0.5).sum()
match_fac = (abs(cur["Current power (MW)"] - s_exp["facility_mw"]) < 0.5).sum()
match_h = (abs(cur["Current H100 equivalents"] - s_exp["h100e"]) < 1).sum()
print(f"'Current power (MW)' совпадает с IT power: {match_it}/93; с Power (объект): {match_fac}/93; "
      f"H100e: {match_h}/93")


def totals(date):
    s = snapshot(tl, dc, date)
    return {
        "date": pd.Timestamp(date).date().isoformat(),
        "sites_total": len(s),
        "sites_operating": int(s["operating"].sum()),
        "facility_gw": s["facility_mw"].sum() / 1000,
        "it_gw": s["it_mw"].sum() / 1000,
        "h100e_mln": s["h100e"].sum() / 1e6,
        "implied_pue": s["facility_mw"].sum() / s["it_mw"].sum() if s["it_mw"].sum() else np.nan,
        "us_facility_gw": s.loc[s.Country == "United States", "facility_mw"].sum() / 1000,
        "dots_100mw_floor": int((s["facility_mw"] // 100).sum()),
        "dots_remainder_mw": float((s["facility_mw"] % 100).sum()),
    }


key_dates = ["2024-03-31", "2024-12-31", "2025-12-31", "2026-06-30", EXPORT_DATE, TODAY,
             "2026-12-31", "2027-12-31", PLAN_DATE, "2030-01-01"]
kt = pd.DataFrame([totals(d) for d in key_dates])
kt.to_csv(DERIVED / "hub_totals_by_date.csv", index=False)
print(kt.round(3).to_string(index=False))

q = pd.date_range("2023-03-31", "2029-12-31", freq="QE")
ts = pd.DataFrame([totals(d) for d in q])
ts["tag"] = np.where(pd.to_datetime(ts["date"]) <= pd.Timestamp(EXPORT_DATE), "оценка Epoch", "план/прогноз Epoch")
ts.to_csv(DERIVED / "hub_timeseries_quarterly.csv", index=False)

for d in [TODAY, PLAN_DATE]:
    s = snapshot(tl, dc, d).sort_values("facility_mw", ascending=False)
    s["dots_100mw"] = (s["facility_mw"] // 100).astype(int)
    s.to_csv(DERIVED / f"hub_sites_{d}.csv")

t, p = totals(TODAY), totals(PLAN_DATE)
print(f"\nНа {TODAY}: объекты {t['facility_gw']:.2f} ГВт, IT {t['it_gw']:.2f} ГВт, "
      f"{t['h100e_mln']:.2f} млн H100e, работают {t['sites_operating']} из {t['sites_total']}")
print(f"На {PLAN_DATE}: объекты {p['facility_gw']:.2f} ГВт, IT {p['it_gw']:.2f} ГВт, "
      f"{p['h100e_mln']:.2f} млн H100e, работают {p['sites_operating']} из {p['sites_total']}")
print(f"Рост объектов ×{p['facility_gw']/t['facility_gw']:.2f}, IT ×{p['it_gw']/t['it_gw']:.2f}")
print(f"Сетка 1 точка = 100 МВт (без округления вверх по площадкам): сегодня {t['dots_100mw_floor']} точек "
      f"+ остатки {t['dots_remainder_mw']:.0f} МВт; к концу 2028 — {p['dots_100mw_floor']} точек "
      f"+ {p['dots_remainder_mw']:.0f} МВт")
