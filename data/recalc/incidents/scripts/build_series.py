"""Build monthly and yearly series for block 13 (incidents vs model releases).

Inputs (downloaded 2026-09-28, all open data files):
  AIID snapshot 2026-09-21: https://pub-72b2b2fc36ec423189843747af98f80e.r2.dev/backup-20260921101119.tar.bz2
      -> mongodump_full_snapshot/incidents.csv, classifications_MIT.csv  (CC BY-SA 4.0)
  Epoch AI 'Data on AI models' (CC BY 4.0):
      https://epoch.ai/data/notable_ai_models.csv, frontier_ai_models.csv,
      large_scale_ai_models.csv, all_ai_models.csv
  MIT AI Incident Tracker yearly aggregates (see fetch_mit.py) -> mit/*.json (CC BY 4.0)

Outputs: ../13-monthly.csv, ../13-yearly.csv, aiid_incidents_enriched.csv
"""
import os, re, json
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
SNAP = os.path.join(HERE, "mongodump_full_snapshot")
SNAPSHOT_DATE = pd.Timestamp("2026-09-21")
START, END = "2022-11", "2026-08"

# ---------------- AIID ----------------
inc = pd.read_csv(os.path.join(SNAP, "incidents.csv"))
inc["date"] = pd.to_datetime(inc["date"])  # 'Date harm occurred (editor-resolved)'
# Date the incident record was created in the DB = timestamp embedded in Mongo ObjectId.
# Monotonic in incident_id for id > 200 (checked); ids <= ~180 were bulk-migrated in Apr 2022.
inc["added"] = pd.to_datetime(
    inc["_id"].str.extract(r"ObjectId\((\w{8})")[0].apply(lambda h: int(h, 16)), unit="s")
inc["lag_days"] = (inc["added"] - inc["date"]).dt.days

txt = (inc["title"].fillna("") + " " + inc["description"].fillna("")).str.lower()
DEEPFAKE_RE = (r"deepfake|deep-fake|deep fake|face[- ]?swap|voice[- ]clon|clon(ed|ing)? (the )?voice|"
               r"cloned .{0,20}voice|nudif|undress|synthetic (video|voice|audio|image|media)|"
               r"ai[- ]generated (video|image|audio|voice|photo|nude|explicit|sexual|likeness|clip|robocall|content)|"
               r"ai[- ]generated .{0,30}(video|image|audio|voice|photo|nude|explicit)|"
               r"fake (video|audio|image|photo)s? .{0,40}\bai\b|impersonat.{0,60}(video|voice|audio|avatar|likeness)")
FRAUD_RE = r"scam|fraud|swindl|phish|extort|con artist|impersonat|fake investment|crypto scheme|sextort"
inc["kw_deepfake"] = txt.str.contains(DEEPFAKE_RE, regex=True)
inc["kw_fraud"] = txt.str.contains(FRAUD_RE, regex=True)

mit = pd.read_csv(os.path.join(SNAP, "classifications_MIT.csv"))
mit = mit.rename(columns={"Incident ID": "incident_id"})[["incident_id", "Risk Domain", "Risk Subdomain", "Entity", "Intent", "Timing"]]
inc = inc.merge(mit, on="incident_id", how="left")
inc["mit_classified"] = inc["Risk Subdomain"].notna()
inc["mit_fraud_4_3"] = inc["Risk Subdomain"].fillna("").str.startswith("4.3")
inc.drop(columns=["reports"]).to_csv(os.path.join(HERE, "aiid_incidents_enriched.csv"), index=False)

months = pd.period_range(START, END, freq="M")
def monthly(mask=None, col="date"):
    d = inc if mask is None else inc[mask]
    return d.groupby(d[col].dt.to_period("M")).size().reindex(months, fill_value=0)

m = pd.DataFrame(index=months)
m["incidents_aiid_by_event_date"] = monthly()
m["incidents_aiid_by_added_date"] = monthly(col="added")
m["incidents_aiid_by_event_date_deepfake_kw"] = monthly(inc.kw_deepfake)
m["incidents_aiid_by_event_date_fraud_kw"] = monthly(inc.kw_fraud)
m["incidents_aiid_by_event_date_mit_fraud_4_3"] = monthly(inc.mit_fraud_4_3)
m["incidents_aiid_by_event_date_mit_classified"] = monthly(inc.mit_classified)

# Completeness estimate for the event-date series: share of incidents (event date >= 2023)
# whose lag event->added is <= the time available until the snapshot. Empirical lag CDF.
lag_ref = inc[(inc["date"] >= "2023-01-01") & (inc["date"] < "2025-01-01")]["lag_days"].clip(lower=0)
def completeness(p):
    mid = p.to_timestamp(how="start") + pd.Timedelta(days=15)
    avail = (SNAPSHOT_DATE - mid).days
    return float((lag_ref <= avail).mean())
m["aiid_event_date_completeness_est"] = [round(completeness(p), 3) for p in months]

# ---------------- Epoch ----------------
def epoch(name):
    d = pd.read_csv(os.path.join(HERE, f"epoch_{name}.csv"), low_memory=False)
    d["pub"] = pd.to_datetime(d["Publication date"], errors="coerce")
    d["flop"] = pd.to_numeric(d["Training compute (FLOP)"], errors="coerce")
    return d
notable = epoch("notable_ai_models")
frontier = epoch("frontier_ai_models")
large = epoch("large_scale_ai_models")
allm = epoch("all_ai_models")

def mcount(d):
    return d.groupby(d["pub"].dt.to_period("M")).size().reindex(months, fill_value=0)

m["releases_notable"] = mcount(notable)
lang = notable["Domain"].fillna("").str.contains("Language|Multimodal", regex=True)
m["releases_notable_language_multimodal"] = mcount(notable[lang])
m["releases_frontier"] = mcount(frontier)  # Epoch: top-5 by training compute at release
m["releases_large_scale_gt1e23"] = mcount(large)  # Epoch: > 1e23 FLOP
m["releases_ge1e25_known_compute"] = mcount(allm[allm["flop"] >= 1e25])

def flag(p):
    notes = []
    if completeness(p) < 0.9:
        notes.append(f"AIID event-date series incomplete (~{completeness(p):.0%} expected in base)")
    if p >= pd.Period("2025-07", "M"):
        notes.append("Epoch large-scale/1e25 series incomplete (compute estimates lag)")
    if p >= pd.Period("2026-01", "M"):
        notes.append("Epoch notable may be incomplete")
    if p >= pd.Period("2025-10", "M"):
        notes.append("mit_* monthly columns: snapshot MIT classification covers incident ids <=1509 only")
    return "; ".join(notes)
m["incomplete_note"] = [flag(p) for p in months]
m.index = m.index.astype(str)
m.index.name = "month"
m.to_csv(os.path.join(OUT, "13-monthly.csv"), encoding="utf-8")

# ---------------- Yearly ----------------
years = list(range(2018, 2027))
Y = pd.DataFrame(index=years)
Y.index.name = "year"
g = inc.groupby(inc["date"].dt.year)
Y["aiid_incidents_by_event_year"] = g.size().reindex(years, fill_value=0)
Y["aiid_incidents_added_in_year"] = inc.groupby(inc["added"].dt.year).size().reindex(years)
Y.loc[Y.index < 2023, "aiid_incidents_added_in_year"] = np.nan  # 2022 includes bulk migration
Y["aiid_deepfake_kw"] = g["kw_deepfake"].sum().reindex(years, fill_value=0)
Y["aiid_fraud_kw"] = g["kw_fraud"].sum().reindex(years, fill_value=0)
Y["aiid_mit_classified_snapshot"] = g["mit_classified"].sum().reindex(years, fill_value=0)
Y["aiid_mit_fraud_4_3_snapshot"] = g["mit_fraud_4_3"].sum().reindex(years, fill_value=0)
# as-of reconstruction: incidents with event year Y already in DB by 5 Jan of Y+1
Y["aiid_event_year_asof_jan5_next_year"] = [
    int(((inc["date"].dt.year == y) & (inc["added"] < pd.Timestamp(f"{y+1}-01-05"))).sum()) if y >= 2023 else np.nan
    for y in years]

def mitdf(stack):
    d = json.load(open(os.path.join(HERE, "mit", f"mit_by_year_{stack}.json")))
    df = pd.DataFrame({s["name"]: s["data"] for s in d["series"]}, index=[int(y) for y in d["years"]])
    return df.reindex(years).fillna(0), d.get("lastUpdated")
ns, upd = mitdf("natSecImpact")
Y["mit_total"] = ns.sum(axis=1).astype(int)
Y["mit_natsec_ge4"] = (ns["4 Severe"] + ns["5 Critical"]).astype(int)
hs, _ = mitdf("highestSeverity")
Y["mit_harm_severity_ge4"] = (hs["4 Severe"] + hs["5 Catastrophic"]).astype(int)
eu, _ = mitdf("euRisk")
Y["mit_eu_unacceptable_share_pct"] = (eu["1 Unacceptable"] / eu.sum(axis=1) * 100).round(1)
en, _ = mitdf("entity")
Y["mit_entity_human_share_pct"] = (en["Human"] / en.sum(axis=1) * 100).round(1)
it, _ = mitdf("intent")
Y["mit_intentional_share_pct"] = (it["Intentional"] / it.sum(axis=1) * 100).round(1)
sd, _ = mitdf("subdomain")
Y["mit_fraud_4_3"] = sd[[c for c in sd.columns if c.startswith("4.3")]].sum(axis=1).astype(int)
au = json.load(open(os.path.join(HERE, "mit", "mit_by_year_natSecAutonomy.json")))
aud = pd.DataFrame({k: pd.Series(v["by_year"], index=[int(y) for y in v["years"]]) for k, v in au.items()}).reindex(years).fillna(0)
Y["mit_full_autonomy"] = aud["Full autonomy"].astype(int)
Y["mit_full_autonomy_share_pct"] = (aud["Full autonomy"] / aud.sum(axis=1) * 100).round(1)
# OECD AIM: monthly averages given in OECD (2026) 'Trends in AI incidents and hazards reported by the media'
Y["oecd_aim_monthly_avg"] = np.nan
Y.loc[2022, "oecd_aim_monthly_avg"] = 92
Y.loc[2025, "oecd_aim_monthly_avg"] = 324
Y["oecd_aim_share_of_ai_news_pct"] = np.nan
Y.loc[2022, "oecd_aim_share_of_ai_news_pct"] = 3.2
Y.loc[2025, "oecd_aim_share_of_ai_news_pct"] = 2.5
Y["epoch_notable"] = notable.groupby(notable["pub"].dt.year).size().reindex(years, fill_value=0)
Y["epoch_frontier_top5"] = frontier.groupby(frontier["pub"].dt.year).size().reindex(years, fill_value=0)
Y["epoch_large_scale_gt1e23"] = large.groupby(large["pub"].dt.year).size().reindex(years, fill_value=0)
Y["partial_year"] = ["2026 = Jan-Sep 21 (AIID) / to 28 Sep (MIT, Epoch)" if y == 2026 else "" for y in years]
Y["source"] = ("AIID snapshot 2026-09-21 (field 'date' = event date; 'added' = Mongo ObjectId time; kw_* = keyword proxies on title+description; "
               "mit_*_snapshot = classifications_MIT.csv in snapshot, covers ids<=1509); "
               f"MIT AI Incident Tracker (Arcola LLM pipeline over AIID), public chart API, lastUpdated {upd}; "
               "OECD (2026) Trends in AI incidents and hazards reported by the media; Epoch AI Data on AI models (2026-09-28)")
Y.to_csv(os.path.join(OUT, "13-yearly.csv"), encoding="utf-8")

# ---------------- checks printed for the claims registry ----------------
asof = inc[(inc["date"].dt.year == 2025) & (inc["added"] < "2026-01-05")]
print("2025 incidents as of 2026-01-05:", len(asof), "| deepfake_kw:", int(asof.kw_deepfake.sum()),
      "| fraud_kw:", int(asof.kw_fraud.sum()), "| fraud&deepfake kw:", int((asof.kw_fraud & asof.kw_deepfake).sum()),
      "| mit 4.3:", int(asof.mit_fraud_4_3.sum()), "| mit 4.3 & deepfake kw:", int((asof.mit_fraud_4_3 & asof.kw_deepfake).sum()))
now = inc[inc["date"].dt.year == 2025]
print("2025 incidents now:", len(now), "| deepfake_kw:", int(now.kw_deepfake.sum()), "| fraud_kw:", int(now.kw_fraud.sum()),
      "| mit 4.3 (snapshot, classified only):", int(now.mit_fraud_4_3.sum()), "of", int(now.mit_classified.sum()))
r = inc[(inc.incident_id >= 1254) & (inc.incident_id <= 1361)]
print("IDs 1254-1361:", len(r), r.added.min(), r.added.max(), r.date.dt.year.value_counts().to_dict())
ev = inc[inc["date"] >= "2023-01-01"]["lag_days"]
print("lag event->added (event>=2023): median", ev.median(), "p75", ev.quantile(.75), "p90", ev.quantile(.9),
      "share<=180d", round((ev <= 180).mean(), 3), "share<=365d", round((ev <= 365).mean(), 3))
print(Y.T.to_string())
