# -*- coding: utf-8 -*-
"""
Блок 11 «Двигатель гонки»: тренд вычислений на обучение и ряд для графика.
Данные: Epoch AI (CC BY 4.0), наборы скачаны 28.09.2026 (in/).
Выход:
  out/11-training-compute.csv  — точки флагманов 6 лабораторий + рекорды на дату
  out/11-compute-trend.csv     — параметры лог-линейных трендов
  out/raw/trend_diag.txt       — диагностика (выборки, остатки)
Запуск: python3 out/raw/compute.py (из папки b11)
"""
import os
import numpy as np
import pandas as pd
from scipy import stats

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IN = os.path.join(BASE, "in")
OUT = os.path.join(BASE, "out")
RAW = os.path.join(OUT, "raw")

START = pd.Timestamp("2020-01-01")
END = pd.Timestamp("2026-09-29")
SPLIT = pd.Timestamp("2024-01-01")
RNG = np.random.default_rng(20260929)
EPOCH_SRC = "https://epoch.ai/data/ai-models (Epoch AI, CC BY 4.0; набор от 28.09.2026)"


def load(name):
    d = pd.read_csv(os.path.join(IN, name), low_memory=False)
    d["date"] = pd.to_datetime(d["Publication date"], errors="coerce")
    d["flop"] = pd.to_numeric(d["Training compute (FLOP)"], errors="coerce")
    return d


def decyear(s):
    s = pd.to_datetime(s)
    return s.dt.year + (s.dt.dayofyear - 1) / np.where(s.dt.is_leap_year, 366, 365)


def fit(df, label, sample, method="OLS log10(FLOP) ~ год", boot=True, note=""):
    """OLS по log10(FLOP); 90% ДИ наклона — t-распределение (и бутстрэп для контроля)."""
    df = df.dropna(subset=["flop", "date"])
    x = decyear(df["date"]).values
    y = np.log10(df["flop"].values)
    n = len(x)
    res = stats.linregress(x, y)
    b, se = res.slope, res.stderr
    t = stats.t.ppf(0.95, n - 2)
    lo, hi = b - t * se, b + t * se
    bl = bh = np.nan
    if boot and n >= 5:
        bs = []
        for _ in range(4000):
            i = RNG.integers(0, n, n)
            if np.ptp(x[i]) == 0:
                continue
            bs.append(stats.linregress(x[i], y[i]).slope)
        bl, bh = np.percentile(bs, [5, 95])
    g = lambda s: 10 ** s
    dbl = lambda s: 12 * np.log10(2) / s if s > 0 else np.nan
    return dict(
        period=f"{df['date'].min():%Y-%m}…{df['date'].max():%Y-%m}",
        sample=sample,
        n=n,
        growth_per_year=round(g(b), 2),
        ci90_low=round(g(lo), 2),
        ci90_high=round(g(hi), 2),
        ci90_boot_low=round(g(bl), 2) if not np.isnan(bl) else "",
        ci90_boot_high=round(g(bh), 2) if not np.isnan(bh) else "",
        oom_per_year=round(b, 3),
        doubling_months=round(dbl(b), 1),
        doubling_months_ci90=f"{dbl(hi):.1f}–{dbl(lo):.1f}" if lo > 0 else f"{dbl(hi):.1f}–∞",
        r2=round(res.rvalue ** 2, 3),
        method=method,
        source="расчёт по " + EPOCH_SRC,
        label=label,
        note=note,
    )


def main():
    fr = load("epoch_frontier_ai_models.csv")
    nt = load("epoch_notable_ai_models.csv")
    al = load("epoch_all_ai_models.csv")
    diag = []

    # ---------- 1. Выборки для тренда ----------
    win = lambda d: d[(d["date"] >= START) & (d["date"] <= END) & d["flop"].notna()]
    F = win(fr)
    F_pre = F[F["date"] < SPLIT]
    F_post = F[F["date"] >= SPLIT]
    F_noSpec = F[F["Confidence"] != "Speculative"]
    F_lang = F[F["Domain"].fillna("").str.contains("Language")]

    # Реконструкция «топ-5 / топ-10 на дату выхода» по notable (определение Epoch: топ-5)
    N = nt[nt["flop"].notna() & nt["date"].notna()].sort_values("date").reset_index(drop=True)

    def topk_flags(d, k):
        flags = []
        for i, r in d.iterrows():
            prev = d[d["date"] <= r["date"]]["flop"]
            flags.append((prev > r["flop"]).sum() < k)
        return np.array(flags)

    N["top5"] = topk_flags(N, 5)
    N["top10"] = topk_flags(N, 10)
    N5 = win(N[N["top5"]])
    N10 = win(N[N["top10"]])
    Nall = win(N)

    # Рекорд на дату — по всем моделям Epoch (all), новые максимумы
    A = al[al["flop"].notna() & al["date"].notna()].sort_values(["date", "flop"], ascending=[True, False])
    runmax, rec = -np.inf, []
    for _, r in A.iterrows():
        if r["flop"] > runmax:
            rec.append(r)
            runmax = r["flop"]
    R = pd.DataFrame(rec)
    R_win = win(R)
    diag.append("Рекорды (всё с 2019):\n" + R[R["date"] >= "2019-01-01"][
        ["Model", "Organization", "date", "flop", "Confidence"]].to_string())

    rows = []
    rows.append(fit(F, "frontier_2020_2026", "Epoch frontier (топ-5 на дату выхода), все с оценкой FLOP"))
    rows.append(fit(F_pre, "frontier_2020_2023", "Epoch frontier, выход 2020–2023"))
    rows.append(fit(F_post, "frontier_2024_2026", "Epoch frontier, выход 2024–09.2026",
                    note="мало точек; у флагманов Google/Anthropic/OpenAI 2025–2026 (кроме GPT-6 Astra) нет оценок Epoch"))
    rows.append(fit(F_noSpec, "frontier_2020_2026_noSpec", "Epoch frontier без оценок Speculative"))
    rows.append(fit(F_lang, "frontier_lang_2020_2026", "Epoch frontier, только языковые (Domain содержит Language)"))
    rows.append(fit(N5, "notable_top5_2020_2026", "notable, реконструкция топ-5 на дату выхода"))
    rows.append(fit(N10, "notable_top10_2020_2026", "notable, реконструкция топ-10 на дату выхода"))
    rows.append(fit(Nall, "notable_all_2020_2026", "все notable с оценкой FLOP (малые модели тянут вниз)"))
    rows.append(fit(R_win, "record_2020_2026", "рекорд на дату: только модели, побившие рекорд (all)",
                    note="ДИ занижает неопределённость: отбор по максимуму, сами оценки FLOP ±×2–3"))
    R_23 = R_win[R_win["date"] >= "2023-01-01"]
    rows.append(fit(R_23, "record_2023_2026", "рекорд на дату, рекордсмены 2023–2026 (GPT-4 … GPT-6 Astra)",
                    note="6 точек; нет оценок Epoch для Gemini 2.5–3.x, Claude 4–5, GPT-5.x — рекорд может быть занижен"))

    # Проверка излома в 2024 г.: y = a + b*x + c*(x-2024)*[x>=2024]
    x = decyear(F["date"]).values
    y = np.log10(F["flop"].values)
    hinge = np.clip(x - 2024.0, 0, None)
    X = np.column_stack([np.ones_like(x), x, hinge])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = len(y) - 3
    s2 = resid @ resid / dof
    cov = s2 * np.linalg.inv(X.T @ X)
    tval = beta[2] / np.sqrt(cov[2, 2])
    p = 2 * (1 - stats.t.cdf(abs(tval), dof))
    post = beta[1] + beta[2]
    se_post = np.sqrt(cov[1, 1] + cov[2, 2] + 2 * cov[1, 2])
    tq = stats.t.ppf(0.95, dof)
    rows.append(dict(
        period="2020-01…2026-09", sample="Epoch frontier, кусочно-линейная модель с изломом 01.2024",
        n=len(y), growth_per_year=round(10 ** post, 2),
        ci90_low=round(10 ** (post - tq * se_post), 2), ci90_high=round(10 ** (post + tq * se_post), 2),
        ci90_boot_low="", ci90_boot_high="", oom_per_year=round(post, 3),
        doubling_months=round(12 * np.log10(2) / post, 1) if post > 0 else "",
        doubling_months_ci90="", r2="",
        method="OLS с изломом (hinge) в 2024.0; рост после излома",
        source="расчёт по " + EPOCH_SRC, label="frontier_hinge_2024",
        note=f"до излома ×{10 ** beta[1]:.2f}/год; изменение наклона {beta[2]:+.3f} OOM/год, p={p:.2f}",
    ))

    # Рекорд-к-рекорду: GPT-4 (03.2023) → GPT-6 Astra (09.2026)
    def pt(name):
        r = al[al["Model"] == name].iloc[0]
        return r["date"], r["flop"]
    d0, f0 = pt("GPT-4 (Mar 2023)")
    d1, f1 = pt("GPT-6 Astra")
    yrs = (d1 - d0).days / 365.25
    gr = (f1 / f0) ** (1 / yrs)
    rows.append(dict(
        period=f"{d0:%Y-%m}…{d1:%Y-%m}", sample="две точки: GPT-4 (2.1e25) → GPT-6 Astra (1.0e27)",
        n=2, growth_per_year=round(gr, 2), ci90_low="", ci90_high="", ci90_boot_low="", ci90_boot_high="",
        oom_per_year=round(np.log10(gr), 3), doubling_months=round(12 * np.log(2) / np.log(gr), 1),
        doubling_months_ci90="", r2="", method="среднегодовой рост между двумя рекордами (CAGR)",
        source="расчёт по " + EPOCH_SRC, label="record_gpt4_to_astra",
        note=f"×{f1 / f0:.0f} за {yrs:.2f} года; ДИ не считается (2 точки, обе — оценки с неопределённостью ~×2)",
    ))
    d2, f2 = pt("Grok 4")
    yrs2 = (d1 - d2).days / 365.25
    gr2 = (f1 / f2) ** (1 / yrs2)
    rows.append(dict(
        period=f"{d2:%Y-%m}…{d1:%Y-%m}", sample="две точки: Grok 4 (5e26, Speculative) → GPT-6 Astra (1.0e27)",
        n=2, growth_per_year=round(gr2, 2), ci90_low="", ci90_high="", ci90_boot_low="", ci90_boot_high="",
        oom_per_year=round(np.log10(gr2), 3), doubling_months=round(12 * np.log(2) / np.log(gr2), 1),
        doubling_months_ci90="", r2="", method="среднегодовой рост между двумя рекордами (CAGR)",
        source="расчёт по " + EPOCH_SRC, label="record_grok4_to_astra",
        note=f"×{f1 / f2:.1f} за {yrs2:.2f} года",
    ))

    # Опубликованные оценки Epoch — для сравнения
    pub = [
        dict(period="2020…2026", sample="Epoch: frontier language models (страница Trends, обновл. 05.02.2026)",
             n="", growth_per_year=5.0, ci90_low=4.0, ci90_high=6.0, oom_per_year=0.7, doubling_months=5.2,
             doubling_months_ci90="4.6–6.0", method="опубликованная оценка Epoch",
             source="https://epoch.ai/trends", label="epoch_trends_2026", note="«5× per year since 2020»"),
        dict(period="2010…05.2024", sample="Epoch: notable models (Sevilla, Roldán, 28.05.2024)",
             n="", growth_per_year=4.1, ci90_low=3.7, ci90_high=4.6, method="опубликованная оценка Epoch",
             source="https://epoch.ai/publications/training-compute-of-frontier-ai-models-grows-by-4-5x-per-year",
             label="epoch_2024_notable", note=""),
        dict(period="2010…05.2024", sample="Epoch: frontier models (топ-10 на дату), вся выборка",
             n="", growth_per_year=5.3, ci90_low=4.9, ci90_high=5.7, method="опубликованная оценка Epoch",
             source="https://epoch.ai/publications/training-compute-of-frontier-ai-models-grows-by-4-5x-per-year",
             label="epoch_2024_frontier", note="после 2018 г. — ×4.2 (3.6–4.9)"),
        dict(period="2020…2026", sample="Epoch: стоимость обучения передовых моделей",
             n="", growth_per_year=3.5, ci90_low=2.8, ci90_high=4.4, doubling_months=7,
             method="опубликованная оценка Epoch", source="https://epoch.ai/trends",
             label="epoch_trends_cost", note="стоимость, а не FLOP"),
    ]
    rows.extend(pub)
    T = pd.DataFrame(rows)
    cols = ["label", "period", "sample", "n", "growth_per_year", "ci90_low", "ci90_high", "ci90_boot_low",
            "ci90_boot_high", "oom_per_year", "doubling_months", "doubling_months_ci90", "r2", "method",
            "source", "note"]
    T = T.reindex(columns=cols)
    T.to_csv(os.path.join(OUT, "11-compute-trend.csv"), index=False, encoding="utf-8")

    diag.append("\nВыборка frontier 2020–2026:\n" + F.sort_values("date")[
        ["Model", "Organization", "date", "flop", "Confidence"]].to_string())
    diag.append("\nВыборка notable top-5 2020–2026:\n" + N5[
        ["Model", "Organization", "date", "flop", "Confidence"]].to_string())

    # ---------- 2. Ряд для графика ----------
    flag = [
        # OpenAI
        ("GPT-4 (Mar 2023)", "OpenAI"), ("GPT-4.5", "OpenAI"), ("GPT-5", "OpenAI"), ("GPT-6 Astra", "OpenAI"),
        # Anthropic
        ("Claude 2", "Anthropic"), ("Claude 3.5 Sonnet", "Anthropic"), ("Claude 3.7 Sonnet", "Anthropic"),
        # Google
        ("PaLM 2", "Google"), ("Gemini 1.0 Ultra", "Google"),
        # xAI
        ("Grok-1", "xAI"), ("Grok-1.5", "xAI"), ("Grok-2", "xAI"), ("Grok 3", "xAI"), ("Grok 4", "xAI"),
        # Meta
        ("LLaMA-65B", "Meta"), ("Llama 2-70B", "Meta"), ("Llama 3-70B", "Meta"), ("Llama 3.1-405B", "Meta"),
        ("Llama 4 Maverick", "Meta"), ("Llama 4 Behemoth (preview)", "Meta"),
        # DeepSeek
        ("DeepSeek LLM 67B", "DeepSeek"), ("DeepSeek-V2 (MoE-236B)", "DeepSeek"), ("DeepSeek-V3", "DeepSeek"),
        ("DeepSeek-R1", "DeepSeek"), ("DeepSeek-V3.2", "DeepSeek"), ("DeepSeek-V4-Pro", "DeepSeek"),
    ]
    claim_of = {
        "GPT-6 Astra": "11-45", "Grok 4": "11-48", "GPT-4.5": "11-48", "Grok 3": "11-48", "GPT-5": "11-48",
        "Llama 4 Behemoth (preview)": "11-48", "GPT-4 (Mar 2023)": "11-44", "Gemini 1.0 Ultra": "11-42",
        "DeepSeek-V4-Pro": "11-49", "Llama 3.1-405B": "11-51",
    }
    rec_models = set(R["Model"])
    # рекорд, действовавший на начало окна (01.11.2022)
    carry = R[R["date"] < "2022-11-01"].iloc[-1]
    recs_in = R[(R["date"] >= "2022-11-01") & (R["date"] <= END)]
    out = []
    names = [m for m, _ in flag] + [m for m in recs_in["Model"] if m not in [f for f, _ in flag]] + [carry["Model"]]
    labmap = dict(flag)
    for m in names:
        r = al[al["Model"] == m]
        if r.empty:
            diag.append(f"НЕТ В НАБОРЕ: {m}")
            continue
        r = r.iloc[0]
        cost = r.get("Training compute cost (2023 USD)")
        out.append(dict(
            model=m,
            lab=labmap.get(m, r["Organization"]),
            release_date=f"{r['date']:%Y-%m-%d}",
            training_flop=f"{r['flop']:.4g}",
            confidence=r["Confidence"],
            cost_usd=f"{cost:.0f}" if pd.notna(cost) else "",
            is_record_at_date=str(m in rec_models),
            source=EPOCH_SRC + ("; рекорд, действовавший на 01.11.2022 (якорь линии)" if m == carry["Model"] else ""),
            claim_id=claim_of.get(m, "11-42" if m in rec_models else ""),
        ))
    S = pd.DataFrame(out).sort_values("release_date")
    S.to_csv(os.path.join(OUT, "11-training-compute.csv"), index=False, encoding="utf-8")

    # ступенчатая линия рекорда по месяцам (для графика; служебно)
    months = pd.date_range("2022-11-30", "2026-09-30", freq="ME")
    step = []
    for mth in months:
        cur = R[R["date"] <= mth].iloc[-1]
        step.append(dict(month=f"{mth:%Y-%m}", record_flop=f"{cur['flop']:.4g}", record_model=cur["Model"]))
    pd.DataFrame(step).to_csv(os.path.join(RAW, "11-record-step-monthly.csv"), index=False, encoding="utf-8")

    # топ-моделей 2025–2026 по FLOP
    top = al[(al["date"] >= "2025-01-01") & al["flop"].notna()].sort_values("flop", ascending=False).head(12)
    diag.append("\nТоп-12 по FLOP, выход 2025–2026:\n" + top[
        ["Model", "Organization", "date", "flop", "Confidence", "Training compute cost (2023 USD)"]].to_string())
    topc = al[al["Training compute cost (2023 USD)"].notna()].sort_values(
        "Training compute cost (2023 USD)", ascending=False).head(8)
    diag.append("\nТоп-8 по стоимости обучения (2023 USD):\n" + topc[
        ["Model", "date", "flop", "Training compute cost (2023 USD)"]].to_string())
    diag.append("\nТренды:\n" + T.to_string())
    with open(os.path.join(RAW, "trend_diag.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(diag))
    print(T[["label", "n", "growth_per_year", "ci90_low", "ci90_high", "ci90_boot_low", "ci90_boot_high",
             "doubling_months", "note"]].to_string())
    print(S.to_string())


# ---------- 3. Обучение против инференса (ручная сводка источников) ----------
U = "млрд USD"
EP_SPEND = "https://epoch.ai/data/ai-companies (ai_companies_compute_spend.csv, 24.09.2026)"
TI_FEB26 = ("https://www.theinformation.com/articles/openai-boost-revenue-forecasts-predicts-112-billion-cash-burn-2030 "
            "(цитата по " + EP_SPEND + ")")
TI_JAN26 = ("https://www.theinformation.com/articles/anthropic-lowers-profit-margin-projection-revenue-skyrockets "
            "(по https://epoch.ai/data-insights/company-spending-breakdown)")
DECODER = "https://the-decoder.com/openai-adds-111-billion-to-its-cash-burn-forecast-as-ai-costs-spiral-beyond-projections/"
TVI = [
    # company_or_scope, year, metric, value, unit, tag, source, source_type, note
    ("OpenAI", "2022", "расходы на вычисления и данные", 0.416, U, "ОЦЕНКА",
     "https://fortune.com/longform/chatgpt-openai-sam-altman-microsoft/", "вторичный",
     "прогноз компании для инвесторов; без разбивки на обучение и инференс"),
    ("OpenAI", "2024", "все вычисления (аренда облака)", 6.8, U, "ОЦЕНКА",
     "https://epoch.ai/data-insights/openai-compute-spend", "первоисточник",
     "оценка Epoch (10.10.2025) на данных The Information и NYT"),
    ("OpenAI", "2024", "вычисления на R&D (исследования, эксперименты, обучение)", 5.0, U, "ОЦЕНКА",
     "https://epoch.ai/data-insights/openai-compute-spend", "первоисточник", "включает ~$1 млрд амортизации исследовательских вычислений"),
    ("OpenAI", "2024", "вычисления на инференс", 1.8, U, "ОЦЕНКА",
     "https://epoch.ai/data-insights/openai-compute-spend", "первоисточник", "исходно — прогноз OpenAI из утечки (The Information, 10.2024)"),
    ("OpenAI", "2024", "доля инференса в расходах на вычисления", 26.5, "%", "ОЦЕНКА",
     "https://epoch.ai/data-insights/openai-compute-spend", "первоисточник",
     "1,8 / 6,8; на странице https://epoch.ai/trends округлено до 30%"),
    ("OpenAI", "2024", "доля финальных прогонов выпущенных моделей в R&D-вычислениях", 9.6, "%", "ОЦЕНКА",
     "https://epoch.ai/gradient-updates/r-and-d-vs-training-compute", "первоисточник",
     "≈$0,5 млрд; остальное — исследования, эксперименты, невыпущенные модели (Epoch, 23.03.2026)"),
    ("OpenAI", "2025", "вычисления на инференс", 8.0, U, "ОЦЕНКА", TI_FEB26, "вторичный",
     "«more than $8 billion», из них ~$4,5 млрд — на платных пользователей; данные для инвесторов (утечка)"),
    ("OpenAI", "2025", "вычисления на R&D (обучение и исследования)", 8.3, U, "ОЦЕНКА", TI_FEB26, "вторичный",
     "на ~$1 млрд меньше летнего прогноза; утечка"),
    ("OpenAI", "2025", "доля инференса в расходах на вычисления", 49.1, "%", "ОЦЕНКА", EP_SPEND, "данные",
     "расчёт 8,0 / (8,0 + 8,3); в 2024 г. — ~26%"),
    ("OpenAI", "2025", "вычисления на инференс (оценка Sacra)", 8.4, U, "ОЦЕНКА", "https://sacra.com/c/openai/", "вторичный",
     "источник цифры реестра; собственная модель Sacra без ссылки на первоисточник"),
    ("OpenAI", "2025", "инференс в Azure за I–III кв.", 8.67, U, "ОЦЕНКА", "https://www.wheresyoured.at/oai_docs/", "вторичный",
     "утечка документов Microsoft (Э. Зитрон, 12.11.2025), учёт по начислению; OpenAI и Microsoft не комментировали; не подтверждено"),
    ("OpenAI", "2024", "инференс в Azure за год", 3.767, U, "ОЦЕНКА", "https://www.wheresyoured.at/oai_docs/", "вторичный",
     "та же утечка; вдвое выше $1,8 млрд из The Information — не подтверждено"),
    ("OpenAI", "2025", "скорректированная валовая маржа", 33, "%", "ОЦЕНКА",
     "https://finance.yahoo.com/news/openai-sees-compute-spend-around-223950561.html", "вторичный",
     "Reuters со ссылкой на The Information: инференс подорожал вчетверо, маржа 40% → 33%"),
    ("OpenAI", "2026", "вычисления на инференс, прогноз", 14.1, U, "ПРОГНОЗ", "https://sacra.com/c/openai/", "вторичный",
     "оценка Sacra"),
    ("OpenAI", "2026", "обучение моделей, прогноз", 32, U, "ПРОГНОЗ", DECODER, "вторичный",
     "The Information, 20.02.2026, данные для инвесторов"),
    ("OpenAI", "2027", "обучение моделей, прогноз", 65, U, "ПРОГНОЗ", DECODER, "вторичный", "«around $65 billion»"),
    ("OpenAI", "2030", "обучение моделей, накопленно до 2030 г., прогноз", 440, U, "ПРОГНОЗ", DECODER, "вторичный",
     "«nearly $440 billion through 2030»"),
    ("OpenAI", "2030", "обучение и работа моделей, накопленно до 2030 г., прогноз", 665, U, "ПРОГНОЗ", DECODER, "вторичный",
     "The Information, 02.2026"),
    ("OpenAI", "2030", "все вычисления, накопленно до 2030 г., цель", 600, U, "ПРОГНОЗ",
     "https://finance.yahoo.com/news/openai-sees-compute-spend-around-223950561.html", "вторичный", "Reuters, 20.02.2026"),
    ("OpenAI", "2030", "все вычисления, накопленно до 2030 г., цель (пересмотр)", 750, U, "ПРОГНОЗ",
     "https://finance.yahoo.com/technology/ai/articles/openai-lifts-planned-compute-spending-144917731.html", "вторичный",
     "WSJ, 22.07.2026"),
    ("OpenAI", "2028", "вычисления на исследования, прогноз", 121, U, "ПРОГНОЗ",
     "https://techstrong.ai/articles/the-high-cost-of-intelligence-openai-anthropic-face-unprecedented-financial-hurdles-on-paths-to-ipos/",
     "вторичный", "WSJ (≈06.04.2026), документы для инвесторов; часть пересказов называет это «обучением»"),
    ("Anthropic", "2023", "облачные вычисления", 0.285, U, "ОЦЕНКА", EP_SPEND, "вторичный", "план, сообщённый инвесторам (The Information)"),
    ("Anthropic", "2024", "серверы для обучения", 1.5, U, "ОЦЕНКА", EP_SPEND, "вторичный", "The Information, 02.2025"),
    ("Anthropic", "2024", "все вычисления", 2.5, U, "ОЦЕНКА", EP_SPEND, "вторичный", "The Information, 07.2024 (прогноз)"),
    ("Anthropic", "2025", "вычисления на R&D (обучение)", 4.1, U, "ОЦЕНКА", TI_JAN26, "вторичный", "The Information, 01.2026"),
    ("Anthropic", "2025", "вычисления на инференс", 2.7, U, "ОЦЕНКА", TI_JAN26, "вторичный",
     "из графика The Information: валовая маржа 40% при выручке $4,5 млрд"),
    ("Anthropic", "2025", "доля инференса в расходах на вычисления", 39.7, "%", "ОЦЕНКА",
     "https://epoch.ai/data-insights/company-spending-breakdown", "данные", "расчёт 2,7 / (2,7 + 4,1)"),
    ("Anthropic", "2025", "вычисления и инфраструктура (черновик проспекта IPO)", 7.33, U, "ФАКТ",
     "https://finance.yahoo.com/technology/ai/articles/exclusive-anthropics-ipo-prospectus-shows-231722972.html",
     "вторичный", "Reuters, 28.09.2026; втрое больше 2024 г.; 58% операционных расходов $12,65 млрд; без разбивки"),
    ("Anthropic", "2026", "вычисления за I кв.", 3.4, U, "ОЦЕНКА", EP_SPEND, "вторичный", "WSJ, 20.05.2026"),
    ("Anthropic", "2028", "обучение моделей, прогноз (пик)", 30, U, "ПРОГНОЗ",
     "https://techstrong.ai/articles/the-high-cost-of-intelligence-openai-anthropic-face-unprecedented-financial-hurdles-on-paths-to-ipos/",
     "вторичный", "WSJ (≈06.04.2026)"),
    ("Nvidia", "2024", "доля инференса в выручке сегмента дата-центров (FY2024)", 40, "%", "ОЦЕНКА",
     "https://www.marketbeat.com/earnings/reports/2024-2-21-nvidia-co-stock", "первоисточник",
     "К. Кресс, звонок 21.02.2024; финансовый год до 28.01.2024; позже Nvidia долю числом не раскрывала"),
    ("Nvidia", "2025", "заявление: инференс — подавляющая часть вычислений", "", "", "ОЦЕНКА",
     "https://www.nasdaq.com/articles/nvidia-nvda-q4-2025-earnings-call-transcript", "первоисточник",
     "Д. Хуанг, 26.02.2025: «the vast majority of our compute today is actually inference»; без числа"),
    ("Отрасль (Deloitte)", "2023", "доля инференса во всех ИИ-вычислениях", 33, "%", "ОЦЕНКА",
     "https://www.deloitte.com/us/en/insights/industry/technology/technology-media-and-telecom-predictions/2026/compute-power-ai.html",
     "первоисточник", "TMT Predictions 2026, 18.11.2025"),
    ("Отрасль (Deloitte)", "2025", "доля инференса во всех ИИ-вычислениях", 50, "%", "ОЦЕНКА",
     "https://www.deloitte.com/us/en/insights/industry/technology/technology-media-and-telecom-predictions/2026/compute-power-ai.html",
     "первоисточник", ""),
    ("Отрасль (Deloitte)", "2026", "доля инференса во всех ИИ-вычислениях", 67, "%", "ПРОГНОЗ",
     "https://www.deloitte.com/us/en/insights/industry/technology/technology-media-and-telecom-predictions/2026/compute-power-ai.html",
     "первоисточник", "«roughly two-thirds»"),
    ("Отрасль (Gartner)", "2026", "доля инференса в расходах на ИИ-облако (AI-optimized IaaS)", 55, "%", "ПРОГНОЗ",
     "https://www.gartner.com/en/newsroom/press-releases/2026-08-10-gartner-forecasts-worldwide-artificial-intelligence-optimized-iaas-spending-to-grow-96-percent-in-2026",
     "первоисточник", "$23,3 млрд инференс против $19 млрд обучение; пресс-релиз 10.08.2026"),
    ("Отрасль (Gartner)", "2027", "доля инференса в расходах на ИИ-облако (AI-optimized IaaS)", 59, "%", "ПРОГНОЗ",
     "https://www.gartner.com/en/newsroom/press-releases/2026-08-10-gartner-forecasts-worldwide-artificial-intelligence-optimized-iaas-spending-to-grow-96-percent-in-2026",
     "первоисточник", ""),
    ("Отрасль (McKinsey)", "2025", "мощность дата-центров под инференс", 20.9, "ГВт", "ОЦЕНКА",
     "https://www.mckinsey.com/featured-insights/week-in-charts/the-future-of-ai-workloads", "первоисточник",
     "обучение — 23,1 ГВт; доля инференса ~47%; 24.02.2026"),
    ("Отрасль (McKinsey)", "2030", "мощность дата-центров под инференс", 93.3, "ГВт", "ПРОГНОЗ",
     "https://www.mckinsey.com/featured-insights/week-in-charts/the-future-of-ai-workloads", "первоисточник",
     "обучение — 62,2 ГВт; доля инференса ~60%"),
    ("Теория (Epoch)", "2024", "оптимальное соотношение затрат на обучение и инференс", "", "", "ОЦЕНКА",
     "https://epoch.ai/blog/optimally-allocating-compute-between-inference-and-training", "первоисточник",
     "Э. Эрдил, 29.03.2024: «AI labs should spend comparable resources on training and running inference»"),
    ("Anthropic, MiniMax, Z.ai", "2025", "доля вычислений (R&D + инференс) в расходах", "54-62", "%", "ОЦЕНКА",
     "https://epoch.ai/data-insights/company-spending-breakdown", "первоисточник", "Epoch, 04.02.2026"),
]


def write_tvi():
    import csv
    cols = ["company_or_scope", "year", "metric", "value", "unit", "tag", "source", "source_type", "note"]
    with open(os.path.join(OUT, "11-train-vs-infer.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in TVI:
            w.writerow(r)


# ---------- 4. Утверждения для реестра (11-40 … 11-69) ----------
DATA_CALC = "расчёт out/raw/compute.py по https://epoch.ai/data/ai-models (набор 28.09.2026)"
EP_DS = "https://epoch.ai/data/ai-models (epoch_all_ai_models.csv, 28.09.2026)"
CLAIMS = [
    # id, claim, plan_value, value, unit, date, tag, status, source, source_type, quote, note
    ("11-40", "Вычисления на обучение передовых моделей растут примерно в 4–5 раз в год (Epoch)", "4–5", "5", "раз в год",
     "2026-02-05", "ОЦЕНКА", "проверено", "https://epoch.ai/trends", "первоисточник",
     "Training compute for frontier language models has been growing at 5× per year since 2020",
     "Страница трендов Epoch: ×5 в год с 2020 г., 90% ДИ ×4–6, удвоение за 5,2 мес. (4,6–6,0). Работа Epoch 28.05.2024: notable ×4,1, frontier ×5,3 (после 2018 г. ×4,2). Формулировка «в 4–5 раз» корректна"),
    ("11-41", "Наш расчёт: у передовых моделей (набор Epoch frontier — топ-5 по вычислениям на дату выхода) рост ×4,4 в год за 2020–09.2026",
     "4–5", "4.44", "раз в год", "2026-09-28", "ОЦЕНКА", "проверено", DATA_CALC, "данные", "",
     "Лог-линейная регрессия, n=39, 90% ДИ ×3,9–5,1 (бутстрэп ×3,8–5,1), удвоение 5,6 мес. Без оценок Speculative ×4,4; реконструкция топ-10 по notable ×4,8 (4,2–5,4); только языковые ×4,3"),
    ("11-42", "Рекорд вычислений на обучение на дату рос в 2020–2026 гг. примерно в 4,2 раза в год", "", "4.22", "раз в год",
     "2026-09-28", "ОЦЕНКА", "проверено", DATA_CALC, "данные", "",
     "12 рекордсменов от Meena (01.2020) до GPT-6 Astra (09.2026); 90% ДИ ×3,8–4,7 занижает неопределённость (отбор по максимуму, сами оценки FLOP ±×2–3). Ступенчатая линия по месяцам — out/raw/11-record-step-monthly.csv"),
    ("11-43", "Темп роста в 2024–2026 гг. отличается от прежнего", "", "6.04", "раз в год", "2026-09-28", "ОЦЕНКА", "спорно",
     DATA_CALC, "данные", "",
     "Frontier 2024–09.2026: ×6,0 (90% ДИ ×2,6–14,0; n=10) против ×4,3 (3,4–5,5) в 2020–2023; излом в 2024 г. незначим (p=0,59). Но рекорд растёт медленнее: регрессия по 6 рекордсменам 2023–2026 — ×3,3 (2,4–4,4), GPT-4 → Astra ×3,0 в год, Grok 3 → Astra ~×2 в год. У большинства флагманов 2025–2026 нет оценок Epoch — вывод о смене темпа делать нельзя"),
    ("11-44", "Рекорд за 2023–2026 гг.: от GPT-4 (2,1e25 FLOP) до GPT-6 Astra (1e27) — в 48 раз за 3,5 года, около ×3 в год", "",
     "3.04", "раз в год", "2026-09-03", "ОЦЕНКА", "проверено", DATA_CALC, "данные", "",
     "Среднегодовой рост между двумя рекордами; медленнее тренда ×4–5. Регрессия по 6 рекордсменам 2023–2026 — см. 11-compute-trend.csv. Epoch (26.09.2025): GPT-5 обучали на меньших вычислениях, чем GPT-4.5, — упор на дообучение"),
    ("11-45", "Крупнейшее обучение — GPT-6 Astra (OpenAI, 03.09.2026): около 1e27 FLOP (реестр 08-41)", "1e27", "1.0001e27", "FLOP",
     "2026-09-03", "ОЦЕНКА", "проверено", EP_DS, "данные",
     "This suggests around 1e27 FLOP (corresponding to ~100k GB200s over 90 days at 25% FP8 MFU).",
     "Confidence: Likely; метод — по оборудованию; 90% ДИ примерно 5e26–2e27 FLOP (ноутбук Epoch). 100 тыс. GB200 — нижняя граница. Стоимость обучения Epoch не оценил"),
    ("11-46", "GPT-6 Astra обучали как минимум на 100 тыс. Nvidia GB200 (Абилин, Техас)", "", "100000", "ускорителей",
     "2026-09-06", "ФАКТ", "вторичный",
     "https://wccftech.com/openais-1-billion-gpt-6-astra-heralds-the-age-of-agi-according-to-nvidias-jensen-huang-yet-anthropics-fable-5-1-still-beats-it-on-swe-bench-pro-and-coding-benchmarks/amp/",
     "вторичный", "GPT-6 Astra, trained on ~100K+ NVIDIA Grace Blackwell NVLink72.",
     "Пост Д. Хуанга в X (06.09.2026) видели только в пересказах; в карточке модели OpenAI оборудование не раскрыто. Epoch ссылается на OpenAI и партнёров. Там же: «400K GPUs coming online next»"),
    ("11-47", "GPT-6 Astra вдвое превзошла прежний рекорд Grok 4 (5e26 FLOP)", "", "2.0", "раз", "2026-09-03", "ОЦЕНКА", "проверено",
     EP_DS, "данные", "",
     "Оценка Grok 4 — Speculative (сравнение с Grok 3 и доля RL). Относительно GPT-4 (2,1e25) Astra больше в ~48 раз"),
    ("11-48", "Следующие по величине обучения 2025–2026 гг.: Grok 4, GPT-4.5, Grok 3, GPT-5, Llama 4 Behemoth", "", "5e26", "FLOP",
     "2025-07-09", "ОЦЕНКА", "проверено", EP_DS, "данные", "",
     "Grok 4 — 5e26 (Speculative); GPT-4.5 — 3,8e26 (Likely); Grok 3 — 3,5e26 (Likely); GPT-5 — 6,6e25 (Speculative, ДИ 2e25–2e26); Llama 4 Behemoth (preview, не выпущена) — 5,2e25 (Likely)"),
    ("11-49", "Вычисления на обучение флагманов 2025–2026 гг. Google, Anthropic, OpenAI (GPT-5.x), xAI (Grok 4.x) и Meta (Muse)", "", "", "FLOP",
     "2026-09-28", "ОЦЕНКА", "не подтверждено", EP_DS, "данные", "",
     "В наборе Epoch нет оценок для Gemini 2.5–3.x, Claude Opus 4–5, Mythos, Fable, GPT-5.1–5.6, Grok 4.1–4.7, Muse. В 2026 г. помимо Astra крупнейшие оценённые — Composer 2.5 (3,9e25) и DeepSeek-V4-Pro (9,7e24). Точки этих моделей на график не ставить"),
    ("11-50", "Самые дорогие обучения по оценке Epoch: Grok 4 — около $388 млн, GPT-4.5 — $366 млн, Grok 3 — $218 млн", "", "388", "млн USD (2023)",
     "2025-07-09", "ОЦЕНКА", "проверено", EP_DS, "данные", "",
     "Поле Training compute cost (2023 USD): стоимость вычислений финального прогона. Для Grok 3 Epoch даёт и облачную цену ($850 млн), и стоимость покупки кластера ($4,4 млрд)"),
    ("11-51", "Обучение GPT-4 стоило около $37 млн, Llama 3.1-405B — $53 млн, Gemini 1.0 Ultra — $31 млн", "", "37.3", "млн USD (2023)",
     "2023-03-15", "ОЦЕНКА", "проверено", EP_DS, "данные", "",
     "Облачная цена GPT-4 — $81 млн, стоимость кластера — $806 млн (Epoch)"),
    ("11-52", "Обучение GPT-6 Astra стоило $0,5–1 млрд", "", "500-1000", "млн USD", "2026-09-06", "ОЦЕНКА", "вторичный",
     "https://www.hardwarepremium.com/noticias/58302/openai-s-gpt-6-astra-coste-entrenamiento-400000-gpu/", "вторичный", "",
     "Расчёт аналитиков: 100 тыс. GPU × 90–120 дней × $2,5–3,5 за час. Epoch стоимость не оценил. Порядок согласуется с трендом (Grok 4 — $388 млн)"),
    ("11-53", "Стоимость обучения передовых моделей растёт в 3,5 раза в год, удваиваясь примерно за 7 месяцев", "", "3.5", "раз в год",
     "2026-02-05", "ОЦЕНКА", "проверено", "https://epoch.ai/trends", "первоисточник", "", "90% ДИ ×2,8–4,4 (с 2020 г.)"),
    ("11-54", "В 2024 г. OpenAI потратила на вычисления около $6,8 млрд, из них на инференс — $1,8 млрд (около 26–30%)", "", "1.8",
     "млрд USD", "2025-10-10", "ОЦЕНКА", "проверено", "https://epoch.ai/data-insights/openai-compute-spend", "первоисточник",
     "Only 30% of OpenAI's compute spending in 2024 was used on inference.",
     "Цитата — со страницы https://epoch.ai/trends. R&D — $5 млрд. Исходные цифры — утечка в The Information"),
    ("11-55", "Финальные прогоны выпущенных моделей заняли лишь около 10% R&D-вычислений OpenAI в 2024 г.", "", "9.6", "%",
     "2026-03-23", "ОЦЕНКА", "проверено", "https://epoch.ai/gradient-updates/r-and-d-vs-training-compute", "первоисточник", "",
     "≈$0,5 млрд из $5 млрд; остальное — исследования, эксперименты, невыпущенные модели. У MiniMax — 22,6%, у Z.ai — 12,3%"),
    ("11-56", "Расходы OpenAI на инференс в 2025 г. — $8,4 млрд", "8.4", "8", "млрд USD", "2026-02-20", "ОЦЕНКА", "исправлено",
     TI_FEB26, "вторичный",
     "Last year, OpenAI spent more than $8 billion on the costs of running its AI models for its users",
     "Первичнее всего The Information (данные для инвесторов): «более $8 млрд», из них ~$4,5 млрд — на платных пользователей. $8,4 млрд — оценка Sacra без ссылки на источник. Писать «более $8 млрд»"),
    ("11-57", "Расходы OpenAI на обучение и исследовательские вычисления в 2025 г. — $8,3 млрд", "", "8.3", "млрд USD", "2026-02-20",
     "ОЦЕНКА", "вторичный", TI_FEB26, "вторичный",
     "Last year, OpenAI spent $8.3 billion [to train its models], about a billion less than it expected",
     "Epoch трактует как все R&D-вычисления, а не только финальные прогоны"),
    ("11-58", "Доля инференса в вычислительных расходах OpenAI выросла примерно с 26% в 2024 г. до 49% в 2025 г.", "", "49.1", "%",
     "2026-02-20", "ОЦЕНКА", "вторичный", EP_SPEND, "данные", "",
     "Расчёт: 8,0 / (8,0 + 8,3). Обе цифры — утечки. Epoch (2024): лабораториям выгодно тратить на обучение и инференс сопоставимо"),
    ("11-59", "Расходы OpenAI на инференс в 2025 г. выросли вчетверо, скорректированная валовая маржа упала с 40% до 33%", "", "4",
     "раза", "2026-02-20", "ОЦЕНКА", "вторичный",
     "https://finance.yahoo.com/news/openai-sees-compute-spend-around-223950561.html", "вторичный",
     "the expenses associated with running its AI models, referred to as inference, increased fourfold in 2025",
     "Reuters со ссылкой на The Information"),
    ("11-60", "Инференс OpenAI в Azure: $3,77 млрд в 2024 г. и $8,67 млрд за I–III кв. 2025 г.", "", "8.67", "млрд USD",
     "2025-11-12", "ОЦЕНКА", "не подтверждено", "https://www.wheresyoured.at/oai_docs/", "вторичный",
     "Based on documents viewed by this publication, I am able to report OpenAI's inference spend on Microsoft Azure",
     "Утечка документов Microsoft (Э. Зитрон); компании не комментировали. Противоречит $1,8 млрд за 2024 г. (The Information/Epoch). Для текста не использовать"),
    ("11-61", "Прогноз OpenAI: на обучение $32 млрд в 2026 г. и около $65 млрд в 2027 г., почти $440 млрд до 2030 г.", "", "32",
     "млрд USD", "2026-02-21", "ПРОГНОЗ", "вторичный", DECODER, "вторичный", "",
     "The Information, данные для инвесторов (02.2026); всего на обучение и работу моделей до 2030 г. — $665 млрд"),
    ("11-62", "Плановые вычислительные расходы OpenAI до 2030 г. подняты с ~$600 млрд до $750 млрд", "", "750", "млрд USD",
     "2026-07-22", "ПРОГНОЗ", "вторичный",
     "https://finance.yahoo.com/technology/ai/articles/openai-lifts-planned-compute-spending-144917731.html", "вторичный", "",
     "$600 млрд — Reuters, 20.02.2026; $750 млрд — WSJ, 22.07.2026"),
    ("11-63", "В 2028 г. OpenAI планирует потратить $121 млрд на вычисления для исследований, у Anthropic пик затрат на обучение — около $30 млрд",
     "", "121", "млрд USD", "2026-04-06", "ПРОГНОЗ", "вторичный",
     "https://techstrong.ai/articles/the-high-cost-of-intelligence-openai-anthropic-face-unprecedented-financial-hurdles-on-paths-to-ipos/",
     "вторичный", "", "WSJ, документы для инвесторов; в пересказах $121 млрд называют то «вычислениями», то «обучением»"),
    ("11-64", "Anthropic в 2025 г.: около $4,1 млрд на обучение (R&D) и $2,7 млрд на инференс", "", "4.1", "млрд USD", "2026-02-04",
     "ОЦЕНКА", "вторичный", "https://epoch.ai/data-insights/company-spending-breakdown", "вторичный", "",
     "Epoch по The Information (01.2026); доля инференса ~40%; вычисления — 54–62% расходов у Anthropic, MiniMax и Z.ai"),
    ("11-65", "Anthropic в 2025 г. потратила $7,33 млрд на вычисления и инфраструктуру — втрое больше, чем в 2024 г.", "", "7.33",
     "млрд USD", "2026-09-28", "ФАКТ", "вторичный",
     "https://finance.yahoo.com/technology/ai/articles/exclusive-anthropics-ipo-prospectus-shows-231722972.html", "вторичный",
     "The AI lab spent $7.33 billion on compute and infrastructure last year, a threefold surge from 2024",
     "Reuters по черновику проспекта IPO (не опубликован в EDGAR); 58% операционных расходов $12,65 млрд; разбивки на обучение и инференс нет"),
    ("11-66", "Anthropic в 2024 г.: $1,5 млрд на серверы для обучения, всего около $2,5 млрд на вычисления", "", "1.5", "млрд USD",
     "2025-02-12", "ОЦЕНКА", "вторичный", EP_SPEND, "вторичный",
     "The company spent $1.5 billion on servers for training AI models.", "The Information"),
    ("11-67", "Nvidia: около 40% выручки сегмента дата-центров за 2024 финансовый год пришлось на инференс", "", "40", "%",
     "2024-02-21", "ОЦЕНКА", "проверено", "https://www.marketbeat.com/earnings/reports/2024-2-21-nvidia-co-stock", "первоисточник",
     "We estimate in the past year approximately 40% of data center revenue was for AI inference.",
     "К. Кресс, звонок по итогам IV кв. FY2024. Позже Nvidia долю числом не раскрывала (в т. ч. звонок 26.08.2026)"),
    ("11-68", "Глава Nvidia: подавляющая часть вычислений на её ускорителях — инференс", "", "", "", "2025-02-26", "ОЦЕНКА",
     "проверено", "https://www.nasdaq.com/articles/nvidia-nvda-q4-2025-earnings-call-transcript", "первоисточник",
     "the vast majority of our compute today is actually inference",
     "Д. Хуанг, звонок по итогам IV кв. FY2025; без числа. Количественных заявлений Microsoft и Google о доле инференса не найдено"),
    ("11-69", "Инференс — больше половины нагрузки на ИИ-ускорители", "больше половины", "55", "%", "2026-08-10", "ПРОГНОЗ", "спорно",
     "https://www.gartner.com/en/newsroom/press-releases/2026-08-10-gartner-forecasts-worldwide-artificial-intelligence-optimized-iaas-spending-to-grow-96-percent-in-2026",
     "первоисточник",
     "In 2026, global spending on inference ($23.3 billion) will surpass that of training ($19 billion).",
     "Gartner: 55% расходов на ИИ-облако в 2026 г., 59% в 2027 г. Deloitte: половина вычислений в 2025 г., ~2/3 в 2026 г. McKinsey: в 2025 г. 20,9 ГВт инференса против 23,1 ГВт обучения, перевес — к 2030 г. Писать с атрибуцией, не как факт"),
]


def write_claims():
    import csv
    cols = ["id", "block", "claim", "plan_value", "value", "unit", "date", "tag", "status", "source", "source_type",
            "quote", "note"]
    ok_status = {"проверено", "исправлено", "устарело", "спорно", "вторичный", "не подтверждено"}
    ok_tag = {"ФАКТ", "ОЦЕНКА", "ПРОГНОЗ"}
    ok_st = {"первоисточник", "вторичный", "данные"}
    with open(os.path.join(OUT, "claims-11b.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for c in CLAIMS:
            cid, claim, pv, v, unit, date, tag, status, src, st, quote, note = c
            assert status in ok_status and tag in ok_tag and st in ok_st, cid
            assert len(quote.split()) <= 25, (cid, len(quote.split()))
            assert "," not in str(v) and " " not in str(v), cid
            w.writerow([cid, "11", claim, pv, v, unit, date, tag, status, src, st, quote, note])
    ids = [c[0] for c in CLAIMS]
    assert ids == [f"11-{i}" for i in range(40, 40 + len(ids))], ids


if __name__ == "__main__":
    main()
    write_tvi()
    write_claims()
