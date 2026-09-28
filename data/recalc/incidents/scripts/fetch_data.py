"""Download the open data files used in block 13 (run once, then build_series.py -> correlation.py -> write_claims.py).
AIID snapshot list: https://incidentdatabase.ai/research/snapshots/ (CC BY-SA 4.0)
Epoch AI 'Data on AI models': https://epoch.ai/data/ai-models (CC BY 4.0)
MIT tracker aggregates: fetch_mit.py (CC BY 4.0)"""
import os, tarfile, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "data-race-research (research@example.org)"}

def get(url, path):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=600) as r, open(path, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    print("ok", url)

for name in ["notable_ai_models", "frontier_ai_models", "large_scale_ai_models", "all_ai_models"]:
    get(f"https://epoch.ai/data/{name}.csv", os.path.join(HERE, f"epoch_{name}.csv"))

snap = os.path.join(HERE, "aiid_backup-20260921.tar.bz2")
get("https://pub-72b2b2fc36ec423189843747af98f80e.r2.dev/backup-20260921101119.tar.bz2", snap)
with tarfile.open(snap, "r:bz2") as t:
    for m in ["incidents.csv", "classifications_MIT.csv", "classifications_CSETv1.csv", "license.txt"]:
        t.extract(f"mongodump_full_snapshot/{m}", HERE)
os.remove(snap)  # ~105 MB; only the CSVs above are needed
