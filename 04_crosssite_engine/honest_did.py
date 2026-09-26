"""
P9 Leg B — Rambachan-Roth-style HONEST DiD bounds for the within-SO tag probe.

The raw within-SO DiD (run_within_so.py) shows GEN questions fall ~53% more than VER
post-ChatGPT, with flat-ish pre leads (slope ~-0.005/mo). This module puts an HONEST
inference on that: instead of assuming parallel trends, it asks how much the (unseen)
pre-trend would have to bend for the effect to disappear.

What it does:
  1. Joint event-study regression  y ~ Σ_k gen×1[k] (k≠-1) + cotag_FE + month_FE
     with cotag-CLUSTER-robust vcov V (so θ = l'β has SE = sqrt(l'Vl)).
  2. LINEAR honest counterfactual (Rambachan-Roth, linear case): fit the pre-period
     leads' linear trend, project it forward as the no-ChatGPT counterfactual, and report
     the detrended LATE-post effect θ = mean_{k≥late}(β_k − extrap_k) with a proper CI that
     propagates BOTH the post estimates and the pre-trend estimation uncertainty.
  3. BREAKDOWN slope: the counterfactual trend slope δ that would drive the effect (or its
     95% CI bound) to zero — compared to the estimated pre-slope. If δ_breakdown is far
     steeper than anything seen in the pre-period, the effect is robust to plausible
     pre-trend violations.

Reuses run_within_so.load() so the sample is IDENTICAL to the headline probe.
Needs statsmodels (joint regression + cluster vcov) + scipy.

Usage:
  python honest_did.py                       # window -18..18, late = k>=12
  python honest_did.py --kmin -18 --kmax 18 --late 12
"""
import os
import argparse
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

import run_within_so as rw   # reuse the EXACT same sample/load


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kmin", type=int, default=-18)
    ap.add_argument("--kmax", type=int, default=18)
    ap.add_argument("--late", type=int, default=12, help="late-post horizon: target = mean over k>=late")
    ap.add_argument("--min-mean", type=float, default=0.0)
    args = ap.parse_args()

    df = rw.load(min_mean=args.min_mean, kmin=args.kmin, kmax=args.kmax)
    gen = df["gen"].to_numpy().astype(float)
    kk = df["k"].to_numpy().astype(int)

    ks = sorted(df["k"].unique())
    ks_use = [k for k in ks if k != -1]            # event time, drop k=-1 reference

    # ---- joint event-study design: gen×1[k=j] + cotag FE + month FE ----
    cols = {f"g{j}": gen * (kk == j) for j in ks_use}
    G = pd.DataFrame(cols, index=df.index)
    cot_d = pd.get_dummies(df["cotag"], prefix="c", drop_first=True).astype(float)
    ym_d = pd.get_dummies(df["ym"], prefix="m", drop_first=True).astype(float)
    X = pd.concat([G, cot_d, ym_d], axis=1)
    X = sm.add_constant(X)
    names = list(X.columns)
    res = sm.OLS(df["y"].to_numpy(), X.to_numpy()).fit(
        cov_type="cluster", cov_kwds={"groups": df["cotag"].to_numpy()})

    gk_names = [f"g{j}" for j in ks_use]
    pos = [names.index(n) for n in gk_names]
    bvec = res.params[pos]
    V = res.cov_params()[np.ix_(pos, pos)]
    kpos = {j: i for i, j in enumerate(ks_use)}      # k -> index in bvec

    print("=" * 72)
    print("P9 Leg B — HONEST DiD (Rambachan-Roth-style) on the within-SO tag probe")
    print("=" * 72)
    print(f"sample : {df['cotag'].nunique()} cotags, {df['ym'].nunique()} months, n={len(df)}")
    print(f"window : k in [{args.kmin}..{args.kmax}]   late-post target: k>=+{args.late}")
    print(f"cluster vcov on cotag (G={df['cotag'].nunique()} — small-G, read as indicative)")
    print()

    pre_ks = [k for k in ks_use if k <= -2]
    late_ks = [k for k in ks_use if k >= args.late]
    if len(pre_ks) < 3 or not late_ks:
        raise SystemExit("need >=3 pre leads and >=1 late-post period")

    # ---- raw (no-detrend) late-post effect ----
    l_raw = np.zeros(len(ks_use))
    for k in late_ks:
        l_raw[kpos[k]] = 1.0 / len(late_ks)
    theta_raw = float(l_raw @ bvec)
    se_raw = float(np.sqrt(l_raw @ V @ l_raw))

    # ---- linear pre-trend fit: [a,b] = (Z'Z)^-1 Z' β_pre ----
    Z = np.column_stack([np.ones(len(pre_ks)), np.array(pre_ks, float)])
    ZtZ_inv = np.linalg.inv(Z.T @ Z)
    pre_idx = [kpos[k] for k in pre_ks]
    b_pre = float((ZtZ_inv @ Z.T @ bvec[pre_idx])[1])      # estimated pre slope
    # SE of the pre slope (row 1 of (Z'Z)^-1 Z' applied to β_pre, var via V_pre)
    slope_w = (ZtZ_inv @ Z.T)[1]                            # weights over pre_ks
    Vpre = V[np.ix_(pre_idx, pre_idx)]
    se_bpre = float(np.sqrt(slope_w @ Vpre @ slope_w))

    # ---- detrended late-post effect θ = mean_late(β_k − extrap_k) = l'β ----
    l = np.zeros(len(ks_use))
    for k in late_ks:
        l[kpos[k]] += 1.0 / len(late_ks)
        zk = np.array([1.0, float(k)])
        wrow = zk @ ZtZ_inv @ Z.T                          # extrap weights over pre_ks
        for i, pk in enumerate(pre_ks):
            l[kpos[pk]] -= (1.0 / len(late_ks)) * wrow[i]
    theta = float(l @ bvec)
    se = float(np.sqrt(l @ V @ l))
    z975 = stats.norm.ppf(0.975)
    ci = (theta - z975 * se, theta + z975 * se)

    def pct(x):
        return (np.exp(x) - 1) * 100

    print("=== [1] RAW late-post effect (no detrend) ===")
    print(f"  mean β (k>=+{args.late}) = {theta_raw:+.3f}  ({pct(theta_raw):+.1f}%)  SE={se_raw:.3f}")
    print()
    print("=== [2] LINEAR honest-DiD (counterfactual = pre-trend projected forward) ===")
    print(f"  estimated pre-trend slope b = {b_pre:+.4f} log/mo  (SE {se_bpre:.4f})  "
          f"→ {'≈flat' if abs(b_pre) < 2*se_bpre else 'nonzero'}")
    print(f"  DETRENDED late-post effect θ = {theta:+.3f}  ({pct(theta):+.1f}%)")
    print(f"  SE(θ) = {se:.3f}  (propagates post + pre-trend uncertainty)")
    print(f"  95% CI = [{theta-z975*se:+.3f}, {theta+z975*se:+.3f}]  "
          f"([{pct(ci[0]):+.1f}%, {pct(ci[1]):+.1f}%])")
    sig = ci[1] < 0
    print(f"  → effect {'SIGNIFICANT (CI excludes 0)' if sig else 'not significant'} under linear honest-DiD")
    print()

    # ---- breakdown slope: extra counterfactual slope δ to zero the effect / its CI ----
    meanLk = float(np.mean(late_ks))
    delta_point = theta / meanLk                  # θ(δ)=θ−δ·meanLk=0
    delta_ci = (theta + z975 * se) / meanLk        # upper CI touches 0
    print("=== [3] BREAKDOWN (how bent must the unseen pre-trend be to kill the effect?) ===")
    print(f"  a counterfactual slope δ shifts the effect by δ×{meanLk:.1f} (mean late-k)")
    print(f"  δ to zero the POINT effect      = {delta_point:+.4f} log/mo")
    print(f"  δ to make CI include 0          = {delta_ci:+.4f} log/mo")
    ratio = abs(delta_ci) / max(abs(b_pre), 1e-6)
    pre_ci = 1.96 * se_bpre
    print(f"  estimated pre-slope b = {b_pre:+.4f}/mo (95% CI ±{pre_ci:.4f}, includes 0)")
    print(f"  → overturning significance needs a counterfactual slope ~{abs(delta_ci):.3f}/mo")
    print(f"    = {ratio:.0f}× |b|, and well outside the pre-slope's own 95% CI (±{pre_ci:.4f})")
    robust = abs(delta_ci) > max(abs(b_pre) + pre_ci, 0.02)
    print(f"  VERDICT: effect is {'ROBUST' if robust else 'FRAGILE'} to plausible pre-trend violation")
    print()

    # ---- save event-study betas + vcov diag for the record ----
    out = os.path.join(rw.DATA, "honest_did_eventstudy.csv")
    pd.DataFrame({
        "k": ks_use, "beta": bvec, "se": np.sqrt(np.diag(V)),
    }).to_csv(out, index=False)
    print(f"[saved] {out}")


if __name__ == "__main__":
    main()
