"""Hypothesis test for block 13: 'the more often models are released, the more incidents'.
Monthly AIID incidents vs Epoch model releases. Reads ../13-monthly.csv (built by build_series.py).
Writes corr_results.csv (all coefficients) and prints a summary used in ../13-correlation.md."""
import os
import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
m = pd.read_csv(os.path.join(HERE, "..", "13-monthly.csv")).set_index("month")

INC = {"inc_event": "incidents_aiid_by_event_date", "inc_added": "incidents_aiid_by_added_date"}
REL = {"notable": "releases_notable", "notable_lang": "releases_notable_language_multimodal",
       "frontier": "releases_frontier", "large_1e23": "releases_large_scale_gt1e23"}
WIN = {"full_2022-11_2026-08": ("2022-11", "2026-08"), "complete_2022-11_2025-06": ("2022-11", "2025-06")}

def detrend_log(x):
    y = np.log1p(np.asarray(x, float)); t = np.arange(len(y))
    b = np.polyfit(t, y, 1); return y - np.polyval(b, t)

def detrend_lin(x):
    y = np.asarray(x, float); t = np.arange(len(y))
    b = np.polyfit(t, y, 1); return y - np.polyval(b, t)

TRANSFORMS = {"levels": lambda x: np.asarray(x, float),
              "diff1": lambda x: np.diff(np.asarray(x, float), prepend=np.nan),
              "detrend_log": detrend_log,
              "detrend_lin": detrend_lin}

rows = []
rng = np.random.default_rng(13)
for wname, (a, b) in WIN.items():
    w = m.loc[a:b]
    for iname, icol in INC.items():
        for rname, rcol in REL.items():
            for tname, f in TRANSFORMS.items():
                xi = pd.Series(f(w[icol].values), index=w.index)
                xr = pd.Series(f(w[rcol].values), index=w.index)
                for lag in range(0, 4):  # releases lead incidents by `lag` months
                    d = pd.concat([xi, xr.shift(lag)], axis=1).dropna()
                    n = len(d)
                    r, p = stats.pearsonr(d.iloc[:, 0], d.iloc[:, 1])
                    rho, _ = stats.spearmanr(d.iloc[:, 0], d.iloc[:, 1])
                    z = np.arctanh(r); se = 1 / np.sqrt(n - 3)
                    rows.append(dict(window=wname, incidents=iname, releases=rname, transform=tname, lag=lag,
                                     n=n, pearson_r=round(r, 3), p_naive=round(p, 4), spearman_rho=round(rho, 3),
                                     ci95_lo=round(np.tanh(z - 1.96 * se), 3), ci95_hi=round(np.tanh(z + 1.96 * se), 3)))
res = pd.DataFrame(rows)
res.to_csv(os.path.join(HERE, "corr_results.csv"), index=False)

pd.set_option("display.width", 250)
key = res[(res.incidents == "inc_event")]
print("=== primary: incidents by event date ===")
for wname in WIN:
    k = key[key.window == wname]
    piv = k.pivot_table(index=["releases", "transform"], columns="lag", values="pearson_r")
    print("\n", wname); print(piv.to_string())
# multiple-testing tally for non-level transforms
nl = res[res["transform"] != "levels"]
print("\nnon-level tests:", len(nl), "| p<0.05:", int((nl.p_naive < 0.05).sum()),
      "| expected by chance ~", round(0.05 * len(nl), 1))
print(nl[nl.p_naive < 0.05].to_string())
lv = res[(res["transform"] == "levels") & (res["lag"] == 0)]
print("\nlevels lag0:\n", lv[["window", "incidents", "releases", "n", "pearson_r", "p_naive", "spearman_rho"]].to_string())

# Spike overlap test: months in top quartile of detrended (log) incidents vs releases, complete window
w = m.loc["2022-11":"2025-06"]
di = detrend_log(w[INC["inc_event"]]); dr = detrend_log(w[REL["notable"]])
ti = set(w.index[di >= np.quantile(di, .75)]); tr = set(w.index[dr >= np.quantile(dr, .75)])
ov = len(ti & tr)
# permutation expectation
sims = [len(set(rng.choice(w.index, len(ti), replace=False)) & tr) for _ in range(20000)]
print("\nspike overlap (top-quartile months, detrended log, notable):", ov, "of", len(ti),
      "| expected by chance", round(np.mean(sims), 2), "| P(overlap>=obs)", round(np.mean(np.array(sims) >= ov), 3))
print("incident spike months:", sorted(ti)); print("release spike months:", sorted(tr))

# yearly illustration of spurious level correlation (2018-2025, complete years)
y = pd.read_csv(os.path.join(HERE, "..", "13-yearly.csv")).set_index("year").loc[2018:2025]
r, p = stats.pearsonr(y["aiid_incidents_by_event_year"], y["epoch_notable"])
r2, p2 = stats.pearsonr(y["aiid_incidents_by_event_year"], y["epoch_large_scale_gt1e23"])
print(f"\nyearly 2018-2025: incidents vs notable r={r:.2f} p={p:.3f}; vs large-scale r={r2:.2f} p={p2:.3f}")
# growth comparison
for c in ["aiid_incidents_by_event_year", "epoch_notable", "epoch_large_scale_gt1e23"]:
    print(c, "2023->2025 growth x", round(y.loc[2025, c] / y.loc[2023, c], 2))
# trend shares: how much variance the time trend explains
t = np.arange(len(w))
for col in [INC["inc_event"], REL["notable"], REL["large_1e23"]]:
    r_t, _ = stats.pearsonr(t, w[col]); print(col, "corr with time (complete window)", round(r_t, 2))
