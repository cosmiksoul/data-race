"""R6 · SEC XBRL companyfacts: квартальные капзатраты, операционный денежный поток, FCF.

Компании: Alphabet (+ Google Inc. до 2015 для истории), Microsoft, Amazon, Meta, Oracle.
В 10-Q денежные потоки накопленные с начала финансового года (YTD) → квартал = YTD(t) − YTD(t−1).
Q4 = годовое значение из 10-K − YTD за 9 месяцев. У Microsoft ФГ заканчивается 30 июня,
у Oracle — 31 мая (кварталы кончаются в авг/ноя/фев/май → привязка к календарному кварталу
по месяцу окончания: авг→Q3, ноя→Q4, фев→Q1, май→Q2; это сдвиг на 1 месяц).

FCF = OCF − капзатраты (покупка основных средств, валовая). Дополнительно — FCF за вычетом
погашения финансового лизинга (FinanceLeasePrincipalPayments), как у Meta/Amazon в их «FCF less
principal repayments of finance leases».

Выход: derived/sec_capex_ocf_quarterly.csv (для графика «Точка пересечения»),
       derived/sec_capex_calendar_annual.csv.
"""
from pathlib import Path
from collections import defaultdict
import json
import pandas as pd

HERE = Path(__file__).parent
RAW, OUT = HERE / "raw", HERE / "derived"
OUT.mkdir(exist_ok=True)

COMPANIES = {
    "Alphabet": ["0001652044", "0001288776"],   # Alphabet Inc. + Google Inc. (история до 3К15)
    "Microsoft": ["0000789019"],
    "Amazon": ["0001018724"],
    "Meta": ["0001326801"],
    "Oracle": ["0001341439"],
}
CAPEX_TAGS = ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"]
OCF_TAGS = ["NetCashProvidedByUsedInOperatingActivities", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"]
LEASE_TAGS = ["FinanceLeasePrincipalPayments"]
ROU_FIN_TAGS = ["RightOfUseAssetObtainedInExchangeForFinanceLeaseLiability"]  # новые активы в финлизинг (неденежные)


def facts_for(ciks, tags):
    """Все длительностные факты (start, end) по тегам; при дублях берём последнюю поданную версию.
    Если для одного периода есть несколько тегов (смена тега у Amazon в 2017), приоритет — порядок в tags."""
    best = {}
    for cik in ciks:
        d = json.load(open(RAW / f"CIK{cik}.json"))
        g = d["facts"].get("us-gaap", {})
        for prio, tag in enumerate(tags):
            for f in g.get(tag, {}).get("units", {}).get("USD", []):
                if "start" not in f:
                    continue
                key = (f["start"], f["end"])
                rank = (-prio, f["filed"])  # сначала приоритет тега, затем более поздняя подача
                if key not in best or rank > best[key][0]:
                    best[key] = (rank, f["val"], tag, f["form"], f["filed"], f.get("accn"))
    return best


def to_quarters(best):
    """Из YTD-фактов получить квартальные значения. Возвращает {end: (value, method)}."""
    by_start = defaultdict(list)
    direct = {}
    for (s, e), (_, v, *_rest) in best.items():
        s_, e_ = pd.Timestamp(s), pd.Timestamp(e)
        days = (e_ - s_).days
        by_start[s_].append((e_, v, days))
        if 80 <= days <= 100:
            direct[e_] = v
    q = {}
    for s_, lst in by_start.items():
        lst.sort()
        prev = None
        for e_, v, days in lst:
            if days > 380:
                continue
            if 80 <= days <= 100:
                q.setdefault(e_, (v, "3M"))
            elif prev is not None and 80 <= (e_ - prev[0]).days <= 100:
                q.setdefault(e_, (v - prev[1], f"YTD{round(days/30.4)}M−YTD{round(prev[2]/30.4)}M"))
            prev = (e_, v, days)
    # прямые 3-месячные значения приоритетнее вычисленных
    for e_, v in direct.items():
        q[e_] = (v, "3M")
    return q


def cal_q(ts):
    return f"{ts.year}Q{(ts.month - 1) // 3 + 1}"


rows = []
for name, ciks in COMPANIES.items():
    capex = to_quarters(facts_for(ciks, CAPEX_TAGS))
    ocf = to_quarters(facts_for(ciks, OCF_TAGS))
    lease = to_quarters(facts_for(ciks, LEASE_TAGS))
    rou = to_quarters(facts_for(ciks, ROU_FIN_TAGS))
    for e in sorted(set(capex) & set(ocf)):
        rows.append({
            "company": name, "period_end": e.date(), "cal_quarter": cal_q(e),
            "capex_bn": capex[e][0] / 1e9, "ocf_bn": ocf[e][0] / 1e9,
            "fin_lease_principal_bn": lease[e][0] / 1e9 if e in lease else None,
            "fin_lease_rou_added_bn": rou[e][0] / 1e9 if e in rou else None,
            "capex_method": capex[e][1], "ocf_method": ocf[e][1],
        })

df = pd.DataFrame(rows)
df["fcf_bn"] = df.ocf_bn - df.capex_bn
df["fcf_less_fin_lease_bn"] = df.fcf_bn - df.fin_lease_principal_bn.fillna(0)
df["capex_to_ocf_pct"] = 100 * df.capex_bn / df.ocf_bn
df = df.sort_values(["company", "period_end"]).reset_index(drop=True)
# Скользящие 4 квартала (TTM)
g = df.groupby("company")
df["capex_ttm_bn"] = g.capex_bn.transform(lambda s: s.rolling(4).sum())
df["ocf_ttm_bn"] = g.ocf_bn.transform(lambda s: s.rolling(4).sum())
df["capex_to_ocf_ttm_pct"] = 100 * df.capex_ttm_bn / df.ocf_ttm_bn
df.round(3).to_csv(OUT / "sec_capex_ocf_quarterly.csv", index=False)

# Проверка непрерывности кварталов
for name, sub in df.groupby("company"):
    ends = pd.to_datetime(sub.period_end).sort_values()
    gaps = ends.diff().dt.days.dropna()
    bad = gaps[(gaps < 80) | (gaps > 100)]
    print(f"{name}: {len(sub)} кв., {ends.iloc[0].date()} … {ends.iloc[-1].date()}; разрывов: {len(bad)}")

pd.set_option("display.width", 220)
cols = ["cal_quarter", "period_end", "capex_bn", "ocf_bn", "fcf_bn", "capex_to_ocf_pct", "fin_lease_principal_bn", "fcf_less_fin_lease_bn"]

# ---- Контроль: сумма 4 кварталов = годовое значение (последние 3 ФГ) ----
print("Контроль Q1+Q2+Q3+Q4 = год (капзатраты):")
for name, ciks in COMPANIES.items():
    best = facts_for(ciks, CAPEX_TAGS)
    annual = {pd.Timestamp(e): v / 1e9 for (s, e), (_, v, *_r) in best.items()
              if 350 <= (pd.Timestamp(e) - pd.Timestamp(s)).days <= 380}
    sub = df[df.company == name].set_index(pd.to_datetime(df[df.company == name].period_end))
    for e in sorted(annual)[-3:]:
        s4 = sub.loc[(sub.index > e - pd.DateOffset(months=12)) & (sub.index <= e), "capex_bn"]
        print(f"  {name:9s} ФГ до {e.date()}: год {annual[e]:.3f} | сумма {len(s4)} кв. {s4.sum():.3f}")

print()
for name in COMPANIES:
    sub = df[(df.company == name) & (df.period_end >= pd.Timestamp("2023-01-01").date())]
    print(f"=== {name} ===")
    print(sub[cols].round(2).to_string(index=False))
    neg_all = df[(df.company == name) & (df.fcf_bn < 0)]
    first = df[df.company == name].iloc[0]
    print(f"  данные с {first.period_end}; кварталов с FCF<0: {len(neg_all)} →",
          ", ".join(f"{r.cal_quarter}({r.fcf_bn:.2f})" for r in neg_all.itertuples()) or "нет")
    w = df[(df.company == name) & (df.period_end >= pd.Timestamp("2023-01-01").date())]
    xq = w[w.capex_bn > w.ocf_bn]
    xt = w[w.capex_ttm_bn > w.ocf_ttm_bn]
    print(f"  с 2023: капзатраты > OCF (квартал): {', '.join(xq.cal_quarter) or 'нет'}; "
          f"по TTM: {', '.join(xt.cal_quarter) or 'нет'}; макс. квартальное отношение {w.capex_to_ocf_pct.max():.1f}%"
          f" ({w.loc[w.capex_to_ocf_pct.idxmax(), 'cal_quarter']}); TTM последнее {w.capex_to_ocf_ttm_pct.iloc[-1]:.1f}%")
    print()

# ---- Календарные годы: капзатраты Big-4 ----
df["cal_year"] = pd.to_datetime(df.period_end).dt.year
ann = df[df.cal_year.isin([2023, 2024, 2025])].groupby(["company", "cal_year"]).agg(
    capex_bn=("capex_bn", "sum"), ocf_bn=("ocf_bn", "sum"), n=("capex_bn", "size"),
    fin_lease_rou_added_bn=("fin_lease_rou_added_bn", "sum"), n_rou=("fin_lease_rou_added_bn", "count")).reset_index()
ann["capex_plus_fin_lease_bn"] = ann.capex_bn + ann.fin_lease_rou_added_bn
ann["fcf_bn"] = ann.ocf_bn - ann.capex_bn
ann["capex_to_ocf_pct"] = 100 * ann.capex_bn / ann.ocf_bn
ann.round(2).to_csv(OUT / "sec_capex_calendar_annual.csv", index=False)
print(ann.round(1).to_string(index=False))
big4 = ann[ann.company.isin(["Alphabet", "Microsoft", "Amazon", "Meta"])]
for y in (2024, 2025):
    b = big4[big4.cal_year == y]
    print(f"Big-4 календарный {y}: капзатраты {b.capex_bn.sum():.1f} млрд $ ({int(b.n.sum())} кв.); OCF {b.ocf_bn.sum():.1f};"
          f" + новые активы в финлизинг {b.fin_lease_rou_added_bn.sum():.1f} ({int(b.n_rou.sum())} кв.) = {b.capex_plus_fin_lease_bn.sum():.1f}")
# Как получается «≈410»: Microsoft за ФГ26 (июль 2025 – июнь 2026) вместо календарного 2025
msft_fy26 = df[(df.company == "Microsoft") & (pd.to_datetime(df.period_end) > "2025-06-30") & (pd.to_datetime(df.period_end) <= "2026-06-30")].capex_bn.sum()
b25 = big4[(big4.cal_year == 2025) & (big4.company != "Microsoft")].capex_bn.sum()
print(f"Смешанный счёт: Alphabet+Amazon+Meta кал. 2025 {b25:.1f} + Microsoft ФГ26 {msft_fy26:.1f} = {b25 + msft_fy26:.1f}")

# ---- Сумма пяти по календарным кварталам (Oracle — со сдвигом на месяц) ----
five = df[df.period_end >= pd.Timestamp("2023-01-01").date()].pivot_table(
    index="cal_quarter", columns="company", values=["capex_bn", "ocf_bn"], aggfunc="sum")
tot = pd.DataFrame({"capex5": five["capex_bn"].sum(axis=1, min_count=5), "ocf5": five["ocf_bn"].sum(axis=1, min_count=5),
                    "capex4": five["capex_bn"][["Alphabet", "Amazon", "Meta", "Microsoft"]].sum(axis=1, min_count=4),
                    "ocf4": five["ocf_bn"][["Alphabet", "Amazon", "Meta", "Microsoft"]].sum(axis=1, min_count=4)})
tot["capex5_to_ocf5_pct"] = 100 * tot.capex5 / tot.ocf5
tot["capex4_to_ocf4_pct"] = 100 * tot.capex4 / tot.ocf4
tot.round(2).to_csv(OUT / "sec_capex_ocf_sum_by_cal_quarter.csv")
print("\nСумма по календарным кварталам (5 компаний; Big-4):")
print(tot.round(1).to_string())
