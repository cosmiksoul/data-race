"""Fetch MIT AI Incident Tracker yearly aggregates from the public JSON endpoint that
powers the charts on airisk.mit.edu/ai-incident-tracker (dataset 'incidents-arcola').
No auth, no personal data in requests."""
import json, urllib.request, urllib.parse, os
B = "https://airi-echarts-visualizations.vercel.app/api/data/incidents"
OUT = os.path.join(os.path.dirname(__file__), "mit")
os.makedirs(OUT, exist_ok=True)
stacks = ["natSecImpact", "highestSeverity", "euRisk", "entity", "intent", "timing", "domain", "subdomain"]
for s in stacks:
    q = urllib.parse.urlencode({"src": "incidents-arcola", "chartType": "subdomain-by-year", "stackBy": s})
    req = urllib.request.Request(f"{B}?{q}", headers={"User-Agent": "data-race-research (research@example.org)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    json.dump(d, open(os.path.join(OUT, f"mit_by_year_{s}.json"), "w"), ensure_ascii=False)
    print(s, d.get("lastUpdated"), d.get("totalIncidents"), d.get("categories"))

# Autonomy (NatSec framework): counts per year for each autonomy level via filter
auto = {}
for lvl in ["Full autonomy", "Human-supervised", "Human-controlled"]:
    q = urllib.parse.urlencode({"src": "incidents-arcola", "chartType": "subdomain-by-year",
                                "stackBy": "natSecImpact", "natSecAutonomy": lvl})
    req = urllib.request.Request(f"{B}?{q}", headers={"User-Agent": "data-race-research (research@example.org)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    auto[lvl] = {"years": d["years"], "total": d.get("totalIncidents"),
                 "by_year": [sum(s["data"][i] for s in d["series"]) for i in range(len(d["years"]))]}
    print(lvl, d.get("totalIncidents"))
json.dump(auto, open(os.path.join(OUT, "mit_by_year_natSecAutonomy.json"), "w"), ensure_ascii=False)
