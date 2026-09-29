# -*- coding: utf-8 -*-
"""Блок 11 «Двигатель гонки»: сжимается ли интервал между флагманами.

Входы:  out/11-flagships.csv, out/raw/11-increments.csv,
        in/epoch_notable_ai_models.csv, in/epoch_frontier_ai_models.csv (Epoch AI, CC BY 4.0, 28.09.2026)
Выходы: out/11-cadence.csv — основное определение (is_flagship = да)
        out/raw/cadence_sensitivity.csv — три определения: основное, +превью, широкое (+промежуточные версии)
        out/raw/industry_gaps.csv — интервал между соседними флагманами любой из шести лабораторий
        out/raw/epoch_counts_language.csv — то же по Epoch, только языковые модели
Интервал относится к году более позднего релиза. 2026 = январь–сентябрь (до 29.09.2026).
Запуск из папки b11: python3 out/raw/cadence.py
"""
import os, re
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IN, OUT, RAW = (os.path.join(BASE, d) for d in ("in", "out", os.path.join("out", "raw")))
LABS = ["OpenAI", "Anthropic", "Google", "xAI", "Meta", "DeepSeek"]
YEARS = [2023, 2024, 2025, 2026]
ALL = "Все шесть"


def load_sets():
    fl = pd.read_csv(os.path.join(OUT, "11-flagships.csv"), dtype=str)
    inc = pd.read_csv(os.path.join(RAW, "11-increments.csv"), dtype=str)
    for d in (fl, inc):
        d["release_date"] = pd.to_datetime(d["release_date"])
    core = fl[fl.is_flagship == "да"][["lab", "model", "release_date"]]
    prev = fl[fl.is_flagship.isin(["да", "превью"])][["lab", "model", "release_date"]]
    broad = pd.concat([core, inc[inc.in_broad == "да"][["lab", "model", "release_date"]]])
    return {"основное (да)": core, "да + превью": prev, "широкое (да + промежуточные)": broad}


def per_lab_intervals(df):
    df = df.sort_values(["lab", "release_date"]).copy()
    df["interval_days"] = df.groupby("lab")["release_date"].diff().dt.days
    df["year"] = df["release_date"].dt.year
    return df


def cadence_table(df):
    d = per_lab_intervals(df)
    rows = []
    for lab in LABS + [ALL]:
        sub = d if lab == ALL else d[d.lab == lab]
        for y in YEARS:
            s = sub[sub.year == y]
            iv = s["interval_days"].dropna()
            rows.append({"lab": lab, "year": y, "n_flagships": len(s),
                         "median_interval_days": float(iv.median()) if len(iv) else None,
                         "n_intervals": len(iv)})
    return pd.DataFrame(rows)


def lab_of(org):
    o = str(org)
    for lab, pat in [("OpenAI", r"OpenAI"), ("Anthropic", r"Anthropic"), ("Google", r"Google|DeepMind"),
                     ("xAI", r"\bxAI\b"), ("Meta", r"Meta AI|Facebook"), ("DeepSeek", r"DeepSeek")]:
        if re.search(pat, o):
            return lab
    return None


def epoch_counts(fname, language_only=False):
    e = pd.read_csv(os.path.join(IN, fname), low_memory=False)
    e["date"] = pd.to_datetime(e["Publication date"], errors="coerce")
    e = e[(e.date >= "2023-01-01") & (e.date <= "2026-09-29")]
    if language_only:
        e = e[e["Domain"].fillna("").str.contains("Language")]
    e["lab"] = e["Organization"].map(lab_of)
    e = e[e.lab.notna()]
    e["year"] = e.date.dt.year
    c = e.groupby(["lab", "year"]).size()
    out = {(lab, y): int(c.get((lab, y), 0)) for lab in LABS for y in YEARS}
    for y in YEARS:
        out[(ALL, y)] = int(sum(out[(l, y)] for l in LABS))
    return out


def main():
    sets = load_sets()
    core = cadence_table(sets["основное (да)"])
    notable = epoch_counts("epoch_notable_ai_models.csv")
    frontier = epoch_counts("epoch_frontier_ai_models.csv")
    core["notable_epoch"] = [notable[(r.lab, r.year)] for r in core.itertuples()]
    core["frontier_epoch"] = [frontier[(r.lab, r.year)] for r in core.itertuples()]
    core[["lab", "year", "n_flagships", "median_interval_days", "notable_epoch", "frontier_epoch"]] \
        .to_csv(os.path.join(OUT, "11-cadence.csv"), index=False, float_format="%.1f")

    # Устойчивость к определению флагмана
    sens = []
    for name, df in sets.items():
        t = cadence_table(df)
        t.insert(0, "definition", name)
        sens.append(t)
    sens = pd.concat(sens)
    sens.to_csv(os.path.join(RAW, "cadence_sensitivity.csv"), index=False, float_format="%.1f")

    # Интервал в отрасли: между соседними флагманами любой из шести лабораторий
    gaps = []
    for name, df in sets.items():
        d = df.sort_values("release_date").copy()
        d["gap_days"] = d["release_date"].diff().dt.days
        d["year"] = d.release_date.dt.year
        for y in YEARS:
            g = d[d.year == y]["gap_days"].dropna()
            gaps.append({"definition": name, "year": y, "n": int((d.year == y).sum()),
                         "median_gap_days": float(g.median()), "mean_gap_days": round(float(g.mean()), 1)})
    pd.DataFrame(gaps).to_csv(os.path.join(RAW, "industry_gaps.csv"), index=False, float_format="%.1f")

    lang = epoch_counts("epoch_notable_ai_models.csv", language_only=True)
    pd.DataFrame([{"lab": k[0], "year": k[1], "notable_language": v} for k, v in lang.items()]) \
        .to_csv(os.path.join(RAW, "epoch_counts_language.csv"), index=False)

    # Лог-таблица интервалов по лабораториям (основное определение)
    per_lab_intervals(sets["основное (да)"]).to_csv(os.path.join(RAW, "intervals_core.csv"), index=False)

    pd.set_option("display.width", 200)
    print(core.to_string(index=False))
    print(sens[sens.lab == ALL].to_string(index=False))
    print(pd.DataFrame(gaps).to_string(index=False))


if __name__ == "__main__":
    main()
