"""Задача 3. Доли владельцев AI-чипов (Epoch AI, 'Data on AI chip owners').

Источник: https://epoch.ai/data/ai_chip_owners_cumulative_by_designer.csv
(страница https://epoch.ai/data/ai-chip-owners, обновлено 12.05.2026, CC BY 4.0; скачано 28.09.2026).
Файл — накопленные H100e (медиана, 5-й и 95-й перцентили) по владельцу × производителю чипов на конец квартала.
1К2026 помечен Incomplete (по фискальным кварталам Nvidia/Broadcom, часть владельцев отсутствует) —
последний полный квартал 4К2025.
Владелец 'China (smuggled)' — спекулятивная оценка контрабанды; на сайте Epoch она по умолчанию выключена
(«Show speculative estimate of smuggled chips»). Считаем оба варианта знаменателя.
Пять гиперскейлеров (как в data insight Epoch от 14.04.2026): Amazon, Google, Meta, Microsoft, Oracle.

Выход:
  derived/chip_owners_h100e_by_owner_quarter.csv
  derived/chip_owners_shares_by_quarter.csv
"""
import pandas as pd
from common import OWN_DIR, DERIVED

d = pd.read_csv(OWN_DIR / "ai_chip_owners_cumulative_by_designer.csv")
TOP5 = ["Amazon", "Google", "Meta", "Microsoft", "Oracle"]
MED, P5, P95 = "Compute estimate in H100e (median)", "H100e (5th percentile)", "H100e (95th percentile)"

piv = d.pivot_table(index="End date", columns="Owner", values=MED, aggfunc="sum").fillna(0)
incomplete = d.groupby("End date")["Incomplete"].apply(lambda s: s.notna().any())
piv["incomplete"] = incomplete
piv.to_csv(DERIVED / "chip_owners_h100e_by_owner_quarter.csv")

owners = [c for c in piv.columns if c != "incomplete"]
tot_all = piv[owners].sum(axis=1)
tot_ex = tot_all - piv["China (smuggled)"]
sh = pd.DataFrame({
    "total_mln_incl_smuggled": tot_all / 1e6,
    "total_mln_excl_smuggled": tot_ex / 1e6,
    "top5_mln": piv[TOP5].sum(axis=1) / 1e6,
    "top5_share_excl_smuggled_pct": piv[TOP5].sum(axis=1) / tot_ex * 100,
    "top5_share_incl_smuggled_pct": piv[TOP5].sum(axis=1) / tot_all * 100,
    "china_legal_share_incl_pct": piv["China"] / tot_all * 100,
    "china_smuggled_share_incl_pct": piv["China (smuggled)"] / tot_all * 100,
    "china_legal_share_excl_pct": piv["China"] / tot_ex * 100,
    "incomplete": piv["incomplete"],
})
for o in TOP5 + ["CoreWeave", "xAI", "Other"]:
    sh[f"{o}_share_incl_pct"] = piv[o] / tot_all * 100
    sh[f"{o}_share_excl_pct"] = piv[o] / tot_ex * 100
sh.to_csv(DERIVED / "chip_owners_shares_by_quarter.csv")
print(sh[["total_mln_incl_smuggled", "total_mln_excl_smuggled", "top5_share_excl_smuggled_pct",
          "top5_share_incl_smuggled_pct", "china_legal_share_incl_pct", "china_smuggled_share_incl_pct",
          "incomplete"]].round(2).to_string())

q4, q1 = "2025-12-31", "2024-03-31"
print(f"\n4К2025: всего {sh.loc[q4,'total_mln_incl_smuggled']:.3f} млн H100e с контрабандой, "
      f"{sh.loc[q4,'total_mln_excl_smuggled']:.3f} без; топ-5 {sh.loc[q4,'top5_mln']:.3f} млн")
print(f"Топ-5: 4К2025 {sh.loc[q4,'top5_share_excl_smuggled_pct']:.1f}% (без контрабанды) / "
      f"{sh.loc[q4,'top5_share_incl_smuggled_pct']:.1f}% (с ней); 1К2024 {sh.loc[q1,'top5_share_excl_smuggled_pct']:.1f}% / "
      f"{sh.loc[q1,'top5_share_incl_smuggled_pct']:.1f}%")
print("\nДоли 4К2025 (знаменатель с контрабандой / без):")
for o in TOP5 + ["CoreWeave", "xAI", "Other"]:
    print(f"  {o}: {sh.loc[q4, o+'_share_incl_pct']:.1f}% / {sh.loc[q4, o+'_share_excl_pct']:.1f}%")

# Китай на 4К2025 по производителям с интервалами
cn = d[(d["End date"] == q4) & d.Owner.str.startswith("China")][["Owner", "Chip manufacturer", MED, P5, P95, "Power in MW (median)"]]
print("\nКитай 4К2025 (H100e):")
print(cn.to_string(index=False))
print(f"Китай всего: {cn[MED].sum()/1e6:.3f} млн H100e; легально {cn[cn.Owner=='China'][MED].sum()/1e6:.3f}")

# Суммарная TDP чипов (ГВт) — только сами ускорители, без серверов и охлаждения
pw = d[d["End date"] == q4]["Power in MW (median)"].sum()
print(f"\nСуммарная TDP ускорителей на 4К2025: {pw/1000:.2f} ГВт (медианы, с контрабандой); "
      f"Вт на H100e: {pw*1e6/ tot_all[q4]:.0f}")
