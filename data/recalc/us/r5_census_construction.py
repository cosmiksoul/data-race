"""R5 · Census C30: частное строительство «Data center» и «Manufacturing».
privsatime.xlsx — SAAR (млн $), privtime.xlsx — без сезонной корректировки (млн $ за месяц).
Выход: derived/census_dc_vs_mfg_monthly.csv (для графика «Датацентры против заводов»),
       derived/census_dc_vs_mfg_annual.csv (календарные суммы NSA).
"""
from pathlib import Path
import re
import pandas as pd

HERE = Path(__file__).parent
RAW, OUT = HERE / "raw", HERE / "derived"
OUT.mkdir(exist_ok=True)


def read_c30(fname):
    raw = pd.read_excel(RAW / fname, header=None)
    hdr = [re.sub(r"\s+", " ", str(h).replace("_x000D_", "")).strip() for h in raw.iloc[3]]
    body = raw.iloc[4:].copy()
    body.columns = hdr
    flags = body["Date"].astype(str).str.extract(r"^([A-Z][a-z]{2}-\d{2})([pr]?)$")
    body = body[flags[0].notna()].copy()
    body["flag"] = flags[1][flags[0].notna()]
    body["month"] = pd.to_datetime(flags[0][flags[0].notna()], format="%b-%y")
    body = body.set_index("month").sort_index()
    total_col = [c for c in hdr if c.startswith("Total")][0]
    out = pd.DataFrame({
        "total_private": pd.to_numeric(body[total_col], errors="coerce"),
        "nonresidential": pd.to_numeric(body["Nonresidential"], errors="coerce"),
        "office": pd.to_numeric(body["Office"], errors="coerce"),
        "data_center": pd.to_numeric(body["Data center"], errors="coerce"),
        "manufacturing": pd.to_numeric(body["Manufacturing"], errors="coerce"),
        "mfg_computer_electronic_electrical": pd.to_numeric(body["Computer/ electronic/ electrical"], errors="coerce"),
        "flag": body["flag"],
    })
    return out


sa = read_c30("privsatime.xlsx")
nsa = read_c30("privtime.xlsx")
foot = pd.read_excel(RAW / "privsatime.xlsx", header=None)[0].astype(str)
release = foot[foot.str.contains("Source: U.S. Census Bureau")].iloc[0]
print(release.strip())

m = sa.join(nsa.drop(columns="flag"), rsuffix="_nsa")
m.to_csv(OUT / "census_dc_vs_mfg_monthly.csv", index_label="month")

last = sa.index[-1]
bn = lambda x: x / 1000
dc, mf = sa.data_center, sa.manufacturing
print(f"Последний месяц: {last:%Y-%m} (флаг '{sa.flag.iloc[-1]}')")
print(f"Data center SAAR: {bn(dc.iloc[-1]):.1f} млрд $; год назад {bn(dc.loc[last - pd.DateOffset(years=1)]):.1f};"
      f" г/г {100*(dc.iloc[-1]/dc.loc[last - pd.DateOffset(years=1)]-1):.1f}%")
first_dc = dc.first_valid_index()
print(f"Data center первый месяц в ряду: {first_dc:%Y-%m} = {bn(dc.loc[first_dc]):.2f} млрд $ SAAR;"
      f" мин. {bn(dc.min()):.2f} в {dc.idxmin():%Y-%m}; 2014 ср. SAAR {bn(dc['2014'].mean()):.2f}")
print(f"Manufacturing SAAR: последнее {bn(mf.iloc[-1]):.1f}; пик {bn(mf.max()):.1f} в {mf.idxmax():%Y-%m};"
      f" изменение {100*(mf.iloc[-1]/mf.max()-1):.1f}%; год назад {bn(mf.loc[last - pd.DateOffset(years=1)]):.1f}")
mcee = sa.mfg_computer_electronic_electrical
print(f"  в т.ч. computer/electronic/electrical: последнее {bn(mcee.iloc[-1]):.1f}; пик {bn(mcee.max()):.1f} в {mcee.idxmax():%Y-%m}")
print(f"Office (вкл. Data center) SAAR: {bn(sa.office.iloc[-1]):.1f}; доля ДЦ в office {100*dc.iloc[-1]/sa.office.iloc[-1]:.0f}%")
cross = sa[(sa.data_center >= sa.manufacturing)]
print(f"Месяцы, когда ДЦ ≥ заводов: {len(cross)} (первый: {cross.index[0]:%Y-%m})" if len(cross) else "ДЦ ещё не догнали заводы;"
      f" разрыв {bn(mf.iloc[-1]-dc.iloc[-1]):.1f} млрд $ SAAR")

# Календарные суммы (NSA): фактические расходы за год
ann = nsa[["data_center", "manufacturing", "total_private"]].groupby(nsa.index.year).agg(["sum", "count"])
tab = pd.DataFrame({
    "data_center_bn": ann[("data_center", "sum")] / 1000,
    "manufacturing_bn": ann[("manufacturing", "sum")] / 1000,
    "months": ann[("data_center", "count")],
})
tab = tab[tab.index >= 2014]
tab.round(2).to_csv(OUT / "census_dc_vs_mfg_annual.csv", index_label="year")
print("\nКалендарные суммы NSA, млрд $ (2026 — неполный год):")
print(tab.round(1).to_string())
ytd = nsa.loc["2026-01-01":last, ["data_center", "manufacturing"]].sum() / 1000
ytd_prev = nsa.loc["2025-01-01":last - pd.DateOffset(years=1), ["data_center", "manufacturing"]].sum() / 1000
print(f"Янв–{last:%b} 2026 к тому же периоду 2025: ДЦ {ytd.data_center:.1f} vs {ytd_prev.data_center:.1f}"
      f" ({100*(ytd.data_center/ytd_prev.data_center-1):+.1f}%); заводы {ytd.manufacturing:.1f} vs {ytd_prev.manufacturing:.1f}"
      f" ({100*(ytd.manufacturing/ytd_prev.manufacturing-1):+.1f}%)")
