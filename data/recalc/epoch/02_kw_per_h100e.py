"""Задача 2. кВт на H100e по странам (хаб Epoch) и «сколько H100e даёт 1 ГВт».

Формула (одна дата, одни и те же площадки в числителе и знаменателе):
  kW/H100e(страна) = sum(мощность площадок страны, МВт) * 1000 / sum(H100e тех же площадок)
Берутся только работающие площадки (мощность объекта > 0) на дату; обе величины — из одной
и той же строки таймлайна каждой площадки (правило «на дату», см. common.py).
Считаем в двух вариантах знаменателя мощности: IT-мощность и мощность объекта.

Выход:
  derived/kw_per_h100e_by_country.csv   — страны × даты × (IT / объект)
  derived/kw_per_h100e_sites_2026-09-27.csv — по площадкам (тип чипов)
  derived/kw_per_h100e_china_sensitivity.csv — Китай: исключение по одной площадке
"""
import pandas as pd
from common import load_hub, snapshot, DERIVED, TODAY

dc, tl = load_hub()


def by_country(date):
    s = snapshot(tl, dc, date)
    s = s[s["operating"]]
    g = s.groupby("Country").agg(sites=("h100e", "size"), it_mw=("it_mw", "sum"),
                                 facility_mw=("facility_mw", "sum"), h100e=("h100e", "sum"))
    g.loc["ВСЕГО (хаб)"] = [len(s), s.it_mw.sum(), s.facility_mw.sum(), s.h100e.sum()]
    g["kw_it_per_h100e"] = g.it_mw * 1000 / g.h100e
    g["kw_facility_per_h100e"] = g.facility_mw * 1000 / g.h100e
    g["mln_h100e_per_gw_it"] = g.h100e / g.it_mw / 1000
    g["mln_h100e_per_gw_facility"] = g.h100e / g.facility_mw / 1000
    g["share_of_hub_h100e_pct"] = g.h100e / s.h100e.sum() * 100
    g.insert(0, "date", date)
    return g.sort_values("h100e", ascending=False)


rows = [by_country(d) for d in ["2025-12-31", TODAY, "2027-12-31", "2028-12-31"]]
out = pd.concat(rows)
out.to_csv(DERIVED / "kw_per_h100e_by_country.csv")
now = rows[1]
print(now.round(3).to_string())

us, cn = now.loc["United States"], now.loc["China"]
print(f"\nСША/Китай на {TODAY}: IT {us.kw_it_per_h100e:.3f} / {cn.kw_it_per_h100e:.3f} кВт на H100e "
      f"→ Китай ×{cn.kw_it_per_h100e/us.kw_it_per_h100e:.2f}; "
      f"объект {us.kw_facility_per_h100e:.3f} / {cn.kw_facility_per_h100e:.3f} → ×{cn.kw_facility_per_h100e/us.kw_facility_per_h100e:.2f}")
print(f"1 ГВт IT: США {us.mln_h100e_per_gw_it:.3f} млн H100e, Китай {cn.mln_h100e_per_gw_it:.3f}; "
      f"1 ГВт объекта: США {us.mln_h100e_per_gw_facility:.3f}, Китай {cn.mln_h100e_per_gw_facility:.3f}")
for r in rows:
    if "China" in r.index:
        print(f"{r.date.iloc[0]}: US IT {r.loc['United States','kw_it_per_h100e']:.3f}, "
              f"CN IT {r.loc['China','kw_it_per_h100e']:.3f} (ратио {r.loc['China','kw_it_per_h100e']/r.loc['United States','kw_it_per_h100e']:.2f}), "
              f"площадок CN {int(r.loc['China','sites'])}")

# По площадкам: kW/H100e почти целиком задаётся типом чипа (H100e выводится из типа и числа чипов)
s = snapshot(tl, dc, TODAY)
s = s[s["operating"]].copy()
s["kw_it_per_h100e"] = s.it_mw * 1000 / s.h100e
s["kw_facility_per_h100e"] = s.facility_mw * 1000 / s.h100e
s.sort_values("kw_it_per_h100e").to_csv(DERIVED / "kw_per_h100e_sites_2026-09-27.csv")
print("\nМедиана кВт IT на H100e по типу чипов (площадки с одним типом):")
single = s[s["Current chip types"].notna() & ~s["Current chip types"].str.contains(",", na=False)]
print(single.groupby("Current chip types")["kw_it_per_h100e"].agg(["count", "median", "min", "max"]).round(3).to_string())

# Чувствительность Китая: исключение по одной площадке
cn_sites = s[s.Country == "China"]
sens = []
for name in [None] + list(cn_sites.index):
    sub = cn_sites if name is None else cn_sites.drop(name)
    k = sub.it_mw.sum() * 1000 / sub.h100e.sum()
    kf = sub.facility_mw.sum() * 1000 / sub.h100e.sum()
    sens.append({"excluded": name or "(все 4)", "chips_excluded": None if name is None else cn_sites.loc[name, "Current chip types"],
                 "kw_it_per_h100e": k, "ratio_vs_us_it": k / us.kw_it_per_h100e,
                 "kw_facility_per_h100e": kf, "ratio_vs_us_facility": kf / us.kw_facility_per_h100e})
sens = pd.DataFrame(sens)
sens.to_csv(DERIVED / "kw_per_h100e_china_sensitivity.csv", index=False)
print("\nКитай, исключение по одной площадке:")
print(sens.round(3).to_string(index=False))

# Сравнение «как с как»: площадки США на H100/H200 (Hopper) против Китая на Ascend 910C
hop = s[(s.Country == "United States") & (s["Current chip types"].isin(["H100", "H100,A100"]))]
asc = s[s["Current chip types"] == "Ascend 910C"]
print(f"\nСША, только площадки на H100: {hop.it_mw.sum()*1000/hop.h100e.sum():.3f} кВт IT/H100e ({len(hop)} пл.); "
      f"Китай Ascend 910C: {asc.it_mw.sum()*1000/asc.h100e.sum():.3f} ({len(asc)} пл.)")
