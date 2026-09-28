"""Общие функции пересчёта по хабу Epoch AI «AI data centers».

Данные: Epoch AI, 'AI data centers', https://epoch.ai/data/ai-data-centers,
выгрузка ZIP от 24.09.2026, лицензия CC BY 4.0.

Правило «на дату» (snapshot):
  для каждой площадки берём последнюю строку таймлайна с Date <= дата;
  если такой строки нет (первая запись позже даты), площадка даёт 0.
  Строки таймлайна после даты выгрузки (24.09.2026) — это прогнозы Epoch
  (плановые сроки ввода), поэтому значения «на 31.12.2028» — ПРОГНОЗ.
Поля таймлайна:
  'Power (MW)'      — мощность объекта (facility power, с охлаждением и потерями);
  'IT power (MW)'   — IT-мощность;
  'H100 equivalents'— вычислительная мощность в эквивалентах H100 (8-бит OP/s / 1,979e15).
В data_centers.csv 'Current power (MW)' совпадает с 'IT power (MW)' последней строки
не позже 24.09.2026 у всех 93 площадок (проверено в 01_hub_aggregates.py),
т. е. это IT-мощность, а не мощность объекта.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
DC_DIR = ROOT / "data" / "epoch_data_centers"
OWN_DIR = ROOT / "data" / "ai_chip_owners"
DERIVED = ROOT / "derived"
DERIVED.mkdir(exist_ok=True)

EXPORT_DATE = "2026-09-24"
TODAY = "2026-09-27"
PLAN_DATE = "2028-12-31"


def load_hub():
    dc = pd.read_csv(DC_DIR / "data_centers.csv")
    tl = pd.read_csv(DC_DIR / "data_center_timelines.csv")
    tl["Date"] = pd.to_datetime(tl["Date"])
    return dc, tl


def snapshot(tl, dc, date):
    """Состояние каждой из 93 площадок на дату (последняя запись <= date)."""
    date = pd.Timestamp(date)
    t = (tl[tl["Date"] <= date].sort_values("Date")
         .groupby("Data center").tail(1).set_index("Data center"))
    cols = ["Date", "Construction status", "IT power (MW)", "Power (MW)", "H100 equivalents"]
    s = dc.set_index("Name")[["Country", "Owner", "Current chip types"]].join(t[cols], how="left")
    for c in ["IT power (MW)", "Power (MW)", "H100 equivalents"]:
        s[c] = s[c].fillna(0.0)
    s = s.rename(columns={"Date": "row_date", "IT power (MW)": "it_mw",
                          "Power (MW)": "facility_mw", "H100 equivalents": "h100e"})
    s["operating"] = s["facility_mw"] > 0
    return s
