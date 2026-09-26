# -*- coding: utf-8 -*-
"""EIV simulation re-run — faithful to authors' eiv_simulation.py but with
PanelOLS replaced by exactly-equivalent two-way-dummy OLS (no linearmodels on 3.11).
Same DGP, same seed=1, same grid."""
import numpy as np, pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

def simulate(alpha_true, n_repos=300, n_q=10, median_vol=7,
             within_sd=0.35, between_sd=1.1, seed=0):
    rng = np.random.default_rng(seed)
    log_base = rng.normal(np.log(median_vol), between_sd, n_repos)
    q_eff = rng.normal(0, 0.10, n_q)
    repo, q, V, E = [], [], [], []
    for i in range(n_repos):
        for t in range(n_q):
            log_lv = log_base[i] + q_eff[t] + rng.normal(0, within_sd)
            lam_v = np.exp(log_lv)
            lam_e = lam_v ** alpha_true
            repo.append(f"r{i:04d}"); q.append(t)
            V.append(rng.poisson(lam_v)); E.append(rng.poisson(lam_e))
    return pd.DataFrame({"repo": repo, "q": q, "V": V, "E": E})

def est_within_logE1(df):
    d = df[df.V > 0].copy()
    d["ly"] = np.log(d.E + 1.0); d["lv"] = np.log(d.V)
    m = smf.ols("ly ~ lv + C(repo) + C(q)", d).fit()   # == PanelOLS entity+time FE
    return float(m.params["lv"])

def est_ppml(df):
    d = df[df.V > 0].copy()
    d["lv"] = np.log(d.V)
    try:
        m = smf.glm("E ~ lv + C(repo) + C(q)", d, family=sm.families.Poisson()).fit()
        return float(m.params["lv"])
    except Exception:
        return float("nan")

print(f"{'true a':>7} {'med_vol':>7} {'within_sd':>9} {'within+log(E+1)':>15} {'FE-PPML':>9}")
print("-"*54)
for alpha_true in (0.7, 1.0, 1.3):
    for median_vol, within_sd in [(7,0.35),(7,0.6),(1,0.35),(30,0.35)]:
        df = simulate(alpha_true, median_vol=median_vol, within_sd=within_sd, seed=1)
        print(f"{alpha_true:>7.2f} {median_vol:>7} {within_sd:>9.2f} "
              f"{est_within_logE1(df):>15.3f} {est_ppml(df):>9.3f}", flush=True)
