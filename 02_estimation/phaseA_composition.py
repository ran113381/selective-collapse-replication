# -*- coding: utf-8 -*-
"""Phase A1 + A4 — composition-friendly estimation + robustness battery.

The fixed monthly total (100) per language means the estimand is
COMPOSITION, not absolute volume. Re-estimate the dose-response as:
  (i)  PPML fixed-total  : E[n_st] = exp(bin_FE + month_FE + gamma * score*post)
  (ii) log-ratio series  : log(s4/s1)_t ~ post, Newey-West (serial corr)
  (iii) OLS log-count     : the existing headline, for continuity
Report all three per language (python / javascript / java).

Robustness (same script):
  - placebo cutoffs: fake events across the pre-period; is 2022-12 extreme?
  - permutation null: shuffle bin scores, rebuild the gamma null distribution
  - BH-FDR across an early confirmatory family (three PPML estimates and the
    answer-margin snapshot). The correction reported in Section 7.1 of the
    manuscript uses a different family and is computed by bh_fdr_table1_family.py.
"""
import os
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
import pyfixest as pf

DATA = (r"C:\Users\<user>\AppData\Local\Temp\claude\E-------\77fae8c6-f490-4ed9-96cb-fd023fd3807e"
        r"\scratchpad\P9\P9_验证经济学_迁移包_20260629\P9_code\legB\data")
EVENT = 2022 * 12 + 11  # 2022-12 as year*12+month(0-idx: Dec=11)
PANELS = {"python": "within_so_llm_panel.csv",
          "javascript": "within_so_llm_panel_js.csv",
          "java": "within_so_llm_panel_java.csv"}


def ym_int(ym):
    y, m = ym.split("-")
    return int(y) * 12 + (int(m) - 1)


def long_panel(fn):
    w = pd.read_csv(os.path.join(DATA, fn))
    recs = []
    for _, r in w.iterrows():
        t = ym_int(r["ym"])
        for b in (1, 2, 3, 4):
            recs.append({"ym": r["ym"], "t": t, "score": b,
                         "count": int(r[f"s{b}"]), "post": int(t >= EVENT)})
    d = pd.DataFrame(recs)
    d["dose"] = d["score"] * d["post"]
    return w, d


def ppml_dose(d, event=EVENT):
    m = pf.fepois("count ~ dose | score + ym", data=d, vcov={"CRV1": "ym"})
    g = float(m.coef().iloc[0]); se = float(m.se().iloc[0])
    return g, se, m.pvalue().iloc[0]


def ols_dose(d):
    dd = d.copy(); dd["y"] = np.log(dd["count"].clip(lower=1))
    bins = pd.get_dummies(dd["score"], prefix="b", drop_first=True).astype(float)
    mo = pd.get_dummies(dd["ym"], prefix="m", drop_first=True).astype(float)
    X = sm.add_constant(pd.concat([dd[["dose"]].astype(float), bins, mo], axis=1))
    r = sm.OLS(dd["y"].to_numpy(), X.to_numpy()).fit(
        cov_type="cluster", cov_kwds={"groups": dd["ym"].to_numpy()})
    i = list(X.columns).index("dose")
    return r.params[i], r.bse[i], r.pvalues[i]


def logratio_nw(w):
    d = w.copy(); d["t"] = d["ym"].map(ym_int)
    d["post"] = (d["t"] >= EVENT).astype(int)
    d["lr"] = np.log((d["s4"] + 0.5) / (d["s1"] + 0.5))
    X = sm.add_constant(d[["post"]].astype(float))
    r = sm.OLS(d["lr"].to_numpy(), X.to_numpy()).fit(
        cov_type="HAC", cov_kwds={"maxlags": 6})
    return r.params[1], r.bse[1], r.pvalues[1]


def placebo_cutoffs(d):
    """Fake events every 6 months in the pre-period; report |gamma| rank of the true event."""
    ts = sorted(d["t"].unique())
    cands = [t for t in ts if ts[6] <= t <= EVENT]  # need pre & post on both sides
    gs = {}
    for ev in cands:
        dd = d.copy()
        dd["postX"] = (dd["t"] >= ev).astype(int)
        dd["doseX"] = dd["score"] * dd["postX"]
        dd["y"] = np.log(dd["count"].clip(lower=1))
        bins = pd.get_dummies(dd["score"], prefix="b", drop_first=True).astype(float)
        mo = pd.get_dummies(dd["ym"], prefix="m", drop_first=True).astype(float)
        X = sm.add_constant(pd.concat([dd[["doseX"]].astype(float), bins, mo], axis=1))
        r = sm.OLS(dd["y"].to_numpy(), X.to_numpy()).fit()
        gs[ev] = r.params[list(X.columns).index("doseX")]
    true_g = gs[EVENT]
    rank = sum(1 for v in gs.values() if v <= true_g)  # how many are as negative
    return true_g, rank, len(gs)


def permutation_null(d, obs_g, nperm=2000, seed=7):
    rng = np.random.default_rng(seed)
    scoremap = {}
    perms = []
    bins = pd.get_dummies(d["score"], prefix="b", drop_first=True).astype(float)
    mo = pd.get_dummies(d["ym"], prefix="m", drop_first=True).astype(float)
    Xbase = pd.concat([bins, mo], axis=1)
    for _ in range(nperm):
        sh = rng.permutation([1, 2, 3, 4])
        m = dict(zip([1, 2, 3, 4], sh))
        dd = d.copy()
        dd["sc"] = dd["score"].map(m)
        dd["doseP"] = dd["sc"] * dd["post"]
        dd["y"] = np.log(dd["count"].clip(lower=1))
        X = sm.add_constant(pd.concat([dd[["doseP"]].astype(float).reset_index(drop=True),
                                       Xbase.reset_index(drop=True)], axis=1))
        r = sm.OLS(dd["y"].to_numpy(), X.to_numpy()).fit()
        perms.append(r.params[list(X.columns).index("doseP")])
    perms = np.array(perms)
    p = (np.sum(perms <= obs_g) + 1) / (nperm + 1)  # one-sided (negative)
    return p, perms


def bh_fdr(pvals, names):
    m = len(pvals)
    order = np.argsort(pvals)
    out = {}
    prev = 1.0
    for rank, idx in enumerate(order[::-1]):
        k = m - rank
        adj = min(prev, pvals[idx] * m / k)
        out[names[idx]] = adj
        prev = adj
    return out


print("=" * 74)
print("PHASE A1 — composition-friendly dose-response (3 estimators x 3 languages)")
print("=" * 74)
results = {}
for lang, fn in PANELS.items():
    w, d = long_panel(fn)
    gp, sep, pp = ppml_dose(d)
    go, seo, po = ols_dose(d)
    glr, selr, plr = logratio_nw(w)
    results[lang] = dict(ppml=(gp, sep, pp), ols=(go, seo, po), lr=(glr, selr, plr), d=d, w=w)
    print(f"\n[{lang}]  n_months={w.shape[0]}")
    print(f"  PPML fixed-total dose  gamma={gp:+.4f} (se {sep:.4f}, p={pp:.4g})   "
          f"=> {(np.exp(gp)-1)*100:+.1f}%/point, s4-s1 {(np.exp(3*gp)-1)*100:+.0f}%")
    print(f"  OLS log-count dose     gamma={go:+.4f} (se {seo:.4f}, p={po:.4g})   [existing headline]")
    print(f"  log-ratio(s4/s1) post  beta ={glr:+.4f} (se {selr:.4f}, p={plr:.4g}, Newey-West L=6)")

print("\n" + "=" * 74)
print("PHASE A4 — placebo cutoffs + permutation null (python, headline)")
print("=" * 74)
dpy = results["python"]["d"]
tg, rank, ncut = placebo_cutoffs(dpy)
print(f"  placebo: true 2022-12 gamma={tg:+.4f}; rank {rank}/{ncut} most-negative "
      f"among {ncut} candidate cutoffs (1 = most extreme)")
pperm, perms = permutation_null(dpy, results["python"]["ols"][0])
print(f"  permutation null (2000 draws, shuffle bin scores): "
      f"obs gamma={results['python']['ols'][0]:+.4f}, "
      f"null mean={perms.mean():+.4f} sd={perms.std():.4f}, one-sided p={pperm:.4g}")

print("\n" + "=" * 74)
print("PHASE A4 — Benjamini-Hochberg FDR across confirmatory family")
print("=" * 74)
fam_p = [results["python"]["ppml"][2], results["javascript"]["ppml"][2],
         results["java"]["ppml"][2], 0.022]  # answer-margin p from A2
fam_n = ["python dose (PPML)", "javascript dose (PPML)", "java dose (PPML)",
         "answer-margin DiD"]
adj = bh_fdr(fam_p, fam_n)
for n in fam_n:
    print(f"  {n:26s} raw p={fam_p[fam_n.index(n)]:.4g}   BH-adj q={adj[n]:.4g}")

print("\nDONE")
