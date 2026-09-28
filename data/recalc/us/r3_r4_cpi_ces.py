"""R3 · CPI США «компьютеры, периферия, умный дом» (CUSR0000SEEE01): г/г.
R4 · Занятость CES5051800001 (NAICS 518): пик, дата пика, последнее значение.
Вход: raw/*.csv (FRED). Выход: derived/cpi_computers_monthly.csv, derived/ces518_monthly.csv.
"""
from pathlib import Path
import pandas as pd

HERE = Path(__file__).parent
RAW, OUT = HERE / "raw", HERE / "derived"
OUT.mkdir(exist_ok=True)


def load(sid):
    s = pd.read_csv(RAW / f"{sid}.csv", parse_dates=["observation_date"], index_col="observation_date")[sid]
    return pd.to_numeric(s, errors="coerce").dropna()


# ---------- R3 ----------
cpi = pd.DataFrame({"computers_sa": load("CUSR0000SEEE01"), "computers_nsa": load("CUUR0000SEEE01"),
                    "cpi_all_sa": load("CPIAUCSL")})
# ВАЖНО: в ряду нет октября 2025 (BLS не публиковал CPI за октябрь 2025 из-за шатдауна).
# Поэтому г/г считаем по календарному сдвигу на 12 месяцев, а не на 12 строк.
cpi = cpi.asfreq("MS")
cpi = cpi[cpi.index >= cpi.computers_sa.first_valid_index()]
missing = cpi.index[cpi.computers_sa.isna()]
print("Пропуски в CUSR0000SEEE01:", [f"{m:%Y-%m}" for m in missing])
for src, dst in [("computers_sa", "computers_yoy_pct"), ("computers_nsa", "computers_nsa_yoy_pct"),
                 ("cpi_all_sa", "cpi_all_yoy_pct")]:
    cpi[dst] = 100 * (cpi[src] / cpi[src].shift(12) - 1)
cpi.round(3).to_csv(OUT / "cpi_computers_monthly.csv", index_label="month")
last = cpi.index[-1]
print(f"CPI computers, последний месяц {last:%Y-%m}: {cpi.computers_sa.iloc[-1]:.3f} (дек.2007=100)")
print(f"  г/г SA {cpi.computers_yoy_pct.iloc[-1]:.2f}% | г/г NSA {cpi.computers_nsa_yoy_pct.iloc[-1]:.2f}%"
      f" | CPI all г/г {cpi.cpi_all_yoy_pct.iloc[-1]:.2f}%")
print(f"  к дек. 2025: {100*(cpi.computers_sa.iloc[-1]/cpi.computers_sa.loc['2025-12-01']-1):.2f}%")
print("  последние 8 месяцев г/г:", {f"{k:%Y-%m}": v for k, v in cpi.computers_yoy_pct.tail(8).round(2).items()})
yoy = cpi.computers_yoy_pct.dropna()
print(f"  г/г >0 в {int((yoy > 0).sum())} из {len(yoy)} месяцев с {yoy.index[0]:%Y-%m}"
      f" (из них в 2026: {int((yoy['2026'] > 0).sum())}; 2021–2022: {int((yoy['2021':'2022'] > 0).sum())});"
      f" макс. г/г до 2026: {yoy[:'2025-12-01'].max():.2f}% в {yoy[:'2025-12-01'].idxmax():%Y-%m}")
ann = cpi.computers_sa.resample("YE").mean()
cagr = (ann.loc["2024"].iloc[0] / ann.loc["2008"].iloc[0]) ** (1 / 16) - 1
print(f"  среднегодовое изменение 2008→2024 (средние за год): {100*cagr:.2f}% в год")
print(f"  минимум индекса: {cpi.computers_sa.min():.3f} в {cpi.computers_sa.idxmin():%Y-%m}")

# ---------- R4 ----------
ces = load("CES5051800001").rename("emp_thousands").to_frame()
ces.to_csv(OUT / "ces518_monthly.csv", index_label="month")
s = ces.emp_thousands
print(f"\nCES5051800001: последнее {s.iloc[-1]:.1f} тыс. ({s.index[-1]:%Y-%m}), предыдущие:",
      {f"{k:%Y-%m}": v for k, v in s.tail(4).items()})
print(f"  пик за всю историю: {s.max():.1f} тыс. в {s.idxmax():%Y-%m}; данные с {s.index[0]:%Y-%m}")
s22 = s["2022-01-01":]
print(f"  пик с 2022: {s22.max():.1f} в {s22.idxmax():%Y-%m}; изменение пик→последнее {s.iloc[-1]-s22.max():.1f} тыс."
      f" ({100*(s.iloc[-1]/s22.max()-1):.1f}%)")
print(f"  2019 среднее {s['2019'].mean():.1f}; 2022 среднее {s['2022'].mean():.1f}; "
      f"2025 среднее {s['2025'].mean():.1f}; мин. с 2023: {s['2023':].min():.1f} в {s['2023':].idxmin():%Y-%m}")
print("  значения 2022-10..2023-02:", {f"{k:%Y-%m}": v for k, v in s["2022-10-01":"2023-02-01"].items()})
print(f"  дек. 2025 → авг. 2026: {s['2025-12-01']:.1f} → {s.iloc[-1]:.1f}; авг. 2025 → авг. 2026: {s['2025-08-01']:.1f} → {s.iloc[-1]:.1f}"
      f" ({100*(s.iloc[-1]/s['2025-08-01']-1):.1f}% г/г)")
