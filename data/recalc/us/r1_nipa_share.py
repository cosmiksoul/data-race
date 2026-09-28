"""R1 · Доля инвестиций в оборудование и ПО для обработки информации в ВВП США.
R2 · Капзатраты Big-4 2026 к номинальному ВВП США 2026.

Вход: raw/*.csv (FRED). Выход: derived/nipa_it_share_quarterly.csv + печать сводки.
"""
from pathlib import Path
import pandas as pd

HERE = Path(__file__).parent
RAW, OUT = HERE / "raw", HERE / "derived"
OUT.mkdir(exist_ok=True)

SERIES = {
    "A679RC1Q027SBEA": "ip_equip_and_software",   # оборудование + ПО для обработки информации
    "Y034RC1Q027SBEA": "ip_equipment",            # только оборудование для обработки информации
    "B935RC1Q027SBEA": "computers_periph",        # компьютеры и периферия
    "B985RC1Q027SBEA": "software",                # ПО (IPP)
    "Y033RC1Q027SBEA": "equipment_all",
    "Y001RC1Q027SBEA": "ipp_all",
    "GDP": "gdp",
}


def load(sid):
    s = pd.read_csv(RAW / f"{sid}.csv", parse_dates=["observation_date"], index_col="observation_date")[sid]
    return pd.to_numeric(s, errors="coerce")


df = pd.concat({v: load(k) for k, v in SERIES.items()}, axis=1).dropna()
# проверка тождества: A679RC = Y034RC + B985RC
df["check_sum"] = df.ip_equipment + df.software - df.ip_equip_and_software
assert df.check_sum.abs().max() < 1.0, df.check_sum.abs().max()

for c in ["ip_equip_and_software", "ip_equipment", "computers_periph", "software", "equipment_all", "ipp_all"]:
    df[f"{c}_pct_gdp"] = 100 * df[c] / df.gdp

d = df[df.index >= "1995-01-01"].copy()
d.index = d.index.to_period("Q")
d.round(4).to_csv(OUT / "nipa_it_share_quarterly.csv", index_label="quarter")

last = d.index[-1]
print(f"Последний квартал: {last}")
for c in ["ip_equip_and_software", "ip_equipment", "computers_periph", "software"]:
    col = f"{c}_pct_gdp"
    dot = d.loc["1999Q1":"2001Q4", col]
    pre = d.loc[:"2024Q4", col]
    print(f"{c:24s} {last}: {d[col].iloc[-1]:.3f}%  | пик 1999–2001: {dot.max():.3f}% в {dot.idxmax()}"
          f" | макс. до 2025: {pre.max():.3f}% в {pre.idxmax()} | 2024Q4: {d.loc['2024Q4', col]:.3f}%")
    # первый квартал после 2001, когда доля превысила пик доткомов
    after = d.loc["2002Q1":, col]
    over = after[after > dot.max()]
    print(f"{'':24s} впервые выше пика доткомов: {over.index[0] if len(over) else '—'}")

print("\nУровни, млрд $ SAAR:")
print(d.loc["2025Q1":, ["ip_equip_and_software", "ip_equipment", "computers_periph", "software", "gdp"]])
print("\nУровни в пике 2000:")
print(d.loc["2000Q1":"2001Q1", ["ip_equip_and_software", "ip_equipment", "software", "gdp",
                                 "ip_equip_and_software_pct_gdp", "ip_equipment_pct_gdp", "software_pct_gdp"]].round(3))

# ---------- R2: номинальный ВВП 2026 ----------
g = df.gdp
q1, q2 = g.loc["2026-01-01"], g.loc["2026-04-01"]
yoy = g.loc["2026-04-01"] / g.loc["2025-04-01"]          # рост за 4 квартала
q_rate = yoy ** 0.25                                       # средний квартальный темп
q3, q4 = q2 * q_rate, q2 * q_rate ** 2
gdp2026_trend = (q1 + q2 + q3 + q4) / 4
gdp2026_h1 = (q1 + q2) / 2
gdp2025 = g.loc["2025-01-01":"2025-10-01"].mean()
print(f"\nВВП 2025 (среднее 4 кв. SAAR): {gdp2025:,.1f} млрд $")
print(f"ВВП H1 2026 (среднее Q1,Q2 SAAR): {gdp2026_h1:,.1f}; г/г за 4 кв. {100*(yoy-1):.2f}%"
      f" → Q3 {q3:,.1f}, Q4 {q4:,.1f} → оценка 2026: {gdp2026_trend:,.1f} млрд $")
for capex in (720, 745):
    print(f"  Big-4 {capex} млрд $ = {100*capex/gdp2026_trend:.2f}% ВВП 2026 (тренд) / {100*capex/gdp2026_h1:.2f}% (H1)")
for capex in (410,):
    print(f"  Big-4 2025 {capex} млрд $ = {100*capex/gdp2025:.2f}% ВВП 2025")
pd.Series({"gdp2025": gdp2025, "gdp2026_h1": gdp2026_h1, "gdp_yoy_q2": yoy, "gdp2026_q3_est": q3,
           "gdp2026_q4_est": q4, "gdp2026_est": gdp2026_trend}).round(3).to_csv(OUT / "gdp2026_estimate.csv", header=["value"])
