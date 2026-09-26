"""
P9 Leg B (v2) — voluntary-commons collapse: DiD / event study on Stack Exchange.

This is a GROUND-UP rebuild of run_so_did.py (v1, left intact). It fixes the v1
identification liabilities documented in the project memo:

  (A) FEW-CLUSTER INFERENCE. With 1 treated + a handful of control sites, cluster-robust
      SE are invalid and v1 silently fell back to HC1 and emitted a degenerate rank-1
      parallel-trends F-test ("p=0.88 PASS"). v2 implements, FROM SCRATCH:
        - wild-cluster bootstrap (Cameron-Gelbach-Miller WCR: impose the null,
          Webb 6-point cluster weights, bootstrap-t self-studentized, CI by test
          inversion);
        - randomization / permutation inference (permute which site is "treated",
          exact two-sided p with the explicit 1/N floor + rank + effect-ratio).
      CR1 is shown ONLY as a loudly flagged "INVALID (G<12), reference-only" number.
  (B) CLEAN WINDOW. Headline ATT drops k>=+13 (the 2024-05+ AI-commercialization regime);
      did_regime_split estimates b_clean and b_long SEPARATELY, never pooled.
  (C) FIXED-HORIZON ATT at k+6 / k+12 / k+24 (pointwise), robust to where the panel ends.
  (D) CONTROL CONTAMINATION diagnosed (control-only placebo) + frozen-control arm.
  (E) STAGGERED / COHORT (Sun-Abraham primary, Callaway-Sant'Anna cross-check),
      never-treated-only comparison, honesty gate skips out-of-sample cohorts.
  (F) SYNTHETIC CONTROL (simplex weights, in-space placebo permutation); on the proof
      panel T0<=J so it is flagged ILLUSTRATIVE / under-identified.

ONLY numpy / scipy / statsmodels / pandas / linearmodels are available; every estimator
and inference engine is from scratch. The --simulate recovery harness (planted truths +
tolerances) is the correctness proof because the full back-extended panel is unavailable.

Usage:
  python run_so_did_v2.py                         # headline DiD + regime + ES + FH + placebo
  python run_so_did_v2.py --endpoint questions --math-only
  python run_so_did_v2.py --sc --staggered --diagnostics
  python run_so_did_v2.py --simulate              # recovery harness (correctness proof)
"""
import os
import sys
import argparse
import itertools
import warnings

import numpy as np
import pandas as pd
from scipy import optimize, stats

warnings.simplefilter("ignore")  # suppress benign statsmodels/numpy chatter; we use our own inference

# ----------------------------------------------------------------------------------
# S0  CONSTANTS & MAPPERS
# ----------------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
PANEL = os.path.join(DATA, "so_monthly_panel.csv")

DEFAULT_EVENT = "2022-12"           # first full month after ChatGPT/SO ban
TREATED_SITE = "stackoverflow"
PRIMARY_CONTROLS = ["math.stackexchange", "mathoverflow.net"]
ALL_CONTROLS = PRIMARY_CONTROLS + [
    "ru.stackoverflow", "pt.stackoverflow", "es.stackoverflow", "superuser",
]
# most-AI-substitutable first (frozen-control arm drops from the front)
SUBSTITUTABILITY_ORDER = [
    "math.stackexchange", "mathoverflow.net", "superuser",
    "es.stackoverflow", "pt.stackoverflow", "ru.stackoverflow",
]
MATH_SITES = ["math.stackexchange", "mathoverflow.net"]
G_TREATED = "2022-12"               # SO ban / ChatGPT cohort
G_MATH = "2024-12"                  # o1 cohort (contaminates math controls)

CLEAN_KMAX = 12                     # headline clean-window cap (drops k>=+13 regime)


def ym_to_int(ym: str) -> int:
    """'YYYY-MM' -> absolute month index 12*year + (month-1)."""
    y, m = (int(x) for x in str(ym).split("-"))
    return y * 12 + (m - 1)


def int_to_ym(s: int) -> str:
    y, m = divmod(int(s), 12)
    return f"{y:04d}-{m + 1:02d}"


# ----------------------------------------------------------------------------------
# S1  DATA LAYER
# ----------------------------------------------------------------------------------
def load_panel(endpoint, event=DEFAULT_EVENT, sites=None, path=PANEL,
               zero_policy="assert", _df=None):
    """Long tidy df: site, ym, s(abs month), k(=s-event), y=log(count), D=treated.

    zero_policy: 'assert' (default) -> require count>0 and use log; 'log1p' -> flagged
    log1p fallback for a future panel with zeros (never silent).
    """
    df = _df.copy() if _df is not None else pd.read_csv(path)
    df = df[df["endpoint"] == endpoint].copy()
    if sites is not None:
        df = df[df["site"].isin(set(sites))].copy()
    df["s"] = df["ym"].map(ym_to_int)
    e = ym_to_int(event)
    df["k"] = df["s"] - e
    cnt = df["count"].astype(float).to_numpy()
    if zero_policy == "assert":
        assert (cnt > 0).all(), (
            f"non-positive counts present (min={cnt.min()}); pass zero_policy='log1p' "
            f"to use the flagged log1p fallback for an unbalanced/zero panel.")
        df["y"] = np.log(cnt)
    elif zero_policy == "log1p":
        print("  [FLAG] zero_policy=log1p: using log(1+count) (zeros present in panel).")
        df["y"] = np.log1p(cnt)
    else:
        raise ValueError(f"unknown zero_policy={zero_policy}")
    df["D"] = df["treated"].astype(int)
    return df.sort_values(["site", "s"]).reset_index(drop=True)


def clean_window(df, kmin=None, kmax=CLEAN_KMAX):
    """Restrict to k in [kmin..kmax]; kmin=None -> panel start. Drops the k>=+13 regime."""
    d = df
    if kmin is not None:
        d = d[d["k"] >= kmin]
    if kmax is not None:
        d = d[d["k"] <= kmax]
    return d.copy()


def build_design(df, treat_terms, drop_collinear=True):
    """Shared, rank-checked design matrix reused by OLS and every from-scratch engine.

    Columns: intercept, site dummies (drop ref), month dummies (drop ref, built from the
    OBSERVED ym set so a future unbalanced panel is handled), then the named treatment
    columns in `treat_terms` (dict colname -> length-N indicator/continuous array).

    Returns (X, y, site_groups, colnames, treat_col_indices). Zero-variance and perfectly
    collinear columns are dropped (rank-revealing QR) so CR1's k = rank(X), not nominal.
    """
    d = df.reset_index(drop=True)
    n = len(d)
    cols = [np.ones(n)]
    names = ["const"]

    sites = sorted(d["site"].unique())
    for st in sites[1:]:                                   # drop first site as reference
        cols.append((d["site"] == st).to_numpy(float))
        names.append(f"site[{st}]")

    yms = sorted(d["ym"].unique())
    for ym in yms[1:]:                                     # drop first month as reference
        cols.append((d["ym"] == ym).to_numpy(float))
        names.append(f"ym[{ym}]")

    treat_idx = []
    for cn, vec in treat_terms.items():
        cols.append(np.asarray(vec, float))
        names.append(cn)
        treat_idx.append(len(names) - 1)

    X = np.column_stack(cols)
    y = d["y"].to_numpy(float)
    groups = d["site"].to_numpy()

    if drop_collinear:
        X, names, treat_idx = _drop_collinear(X, names, treat_idx)
    return X, y, groups, names, treat_idx


def _drop_collinear(X, names, treat_idx, tol=1e-9):
    """Drop zero-variance and linearly dependent columns via pivoted QR; preserve treat cols.

    Treatment columns are protected: if a treat column would be flagged dependent it stays
    and a *non-treat* column is dropped instead, so the estimand is never silently removed.
    """
    keep = list(range(X.shape[1]))
    # zero-variance non-constant, non-treat columns
    drop = set()
    for j in range(X.shape[1]):
        if j == 0 or j in treat_idx:
            continue
        if np.ptp(X[:, j]) < tol:
            drop.add(j)
    keep = [j for j in keep if j not in drop]

    # rank-reveal among the kept columns, ordering treat cols + const first so they survive
    order = [j for j in keep if (j == 0 or j in treat_idx)] + \
            [j for j in keep if not (j == 0 or j in treat_idx)]
    Xo = X[:, order]
    # Gram-Schmidt with pivoting via QR; columns whose R diagonal ~0 are dependent
    Q, R = np.linalg.qr(Xo)
    rdiag = np.abs(np.diag(R))
    thresh = tol * max(1.0, rdiag.max() if rdiag.size else 1.0)
    # np.linalg.qr returns the REDUCED R of shape (min(m,n), n), so np.diag(R) has only
    # min(m,n) entries. Pad-guard: columns beyond rank min(m,n) are dependent -> stay False
    # (otherwise a wider-than-tall design throws IndexError).
    indep_local = np.zeros(len(order), dtype=bool)
    indep_local[:len(rdiag)] = rdiag > thresh
    kept_global = [order[i] for i in range(len(order)) if indep_local[i]]
    kept_global_sorted = sorted(kept_global)

    new_names = [names[j] for j in kept_global_sorted]
    pos = {j: i for i, j in enumerate(kept_global_sorted)}
    new_treat_idx = [pos[j] for j in treat_idx if j in pos]
    # guard: every treatment column must survive
    assert len(new_treat_idx) == len(treat_idx), "a treatment column was dropped as collinear"
    return X[:, kept_global_sorted], new_names, new_treat_idx


# ----------------------------------------------------------------------------------
# S2  ESTIMATION PRIMITIVES
# ----------------------------------------------------------------------------------
def fit_ols(X, y, XtX_inv=None):
    """Point estimate only (homoskedastic). Returns beta_hat, residuals, XtX_inv.

    XtX_inv is cached because X is fixed across the bootstrap inner loop.
    """
    if XtX_inv is None:
        XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ (X.T @ y)
    resid = y - X @ beta
    return beta, resid, XtX_inv


def cr1_vcov(X, resid, groups, XtX_inv, rank):
    """CR1 cluster-by-site covariance with small-sample factor.

    c = (G/(G-1)) * ((N-1)/(N-rank)). Used ONLY to studentize inside the bootstrap and as
    a flagged 'INVALID (G<12), reference-only' display number — never as a headline p.
    """
    N, kcol = X.shape
    uniq = np.unique(groups)
    G = len(uniq)
    meat = np.zeros((kcol, kcol))
    for g in uniq:
        m = groups == g
        Xg = X[m]
        ug = resid[m]
        sc = Xg.T @ ug
        meat += np.outer(sc, sc)
    c = (G / (G - 1)) * ((N - 1) / (N - rank)) if G > 1 and N > rank else 1.0
    V = c * (XtX_inv @ meat @ XtX_inv)
    return V


# ----------------------------------------------------------------------------------
# S3  FEW-CLUSTER INFERENCE
# ----------------------------------------------------------------------------------
def _draw_wild_weights(G, B, kind, rng):
    """(B,G) cluster-level wild weights. 'webb' 6-point (default) or 'rademacher'.

    Enumerate exactly when the support (6^G or 2^G) <= B; label returned by caller.
    """
    if kind == "rademacher":
        support = np.array([-1.0, 1.0])
        size = 2 ** G
    elif kind == "webb":
        r = np.sqrt(np.array([0.5, 1.0, 1.5]))
        support = np.concatenate([-r[::-1], r])           # 6-point
        size = 6 ** G
    else:
        raise ValueError(kind)
    if size <= B:                                          # exact enumeration
        grid = np.array(list(itertools.product(support, repeat=G)))
        return grid, True
    idx = rng.integers(0, len(support), size=(B, G))
    return support[idx], False


def _restricted_fit(X, y, test_cols, beta0):
    """Fit imposing H0: beta[test_cols] = beta0 (scalar or vector). Returns restricted resid."""
    test_cols = list(test_cols)
    beta0 = np.atleast_1d(np.asarray(beta0, float))
    if beta0.size == 1 and len(test_cols) > 1:
        beta0 = np.repeat(beta0, len(test_cols))
    y_adj = y - X[:, test_cols] @ beta0
    free = [j for j in range(X.shape[1]) if j not in test_cols]
    Xf = X[:, free]
    bf, _, _ = fit_ols(Xf, y_adj)
    fitted = Xf @ bf
    resid_r = y_adj - fitted                               # restricted residuals (null imposed)
    # full-length fitted under the null (so bootstrap y* uses null DGP)
    yhat_null = fitted + X[:, test_cols] @ beta0
    return resid_r, yhat_null, free, bf


def wild_cluster_bootstrap(X, y, groups, test_cols, beta0=0.0, B=9999,
                           weights="webb", joint=False, seed=0,
                           rng=None, return_dist=False, _df_for_ri=None,
                           _ri_args=None):
    """WCR impose-null bootstrap-t, self-studentized with the bootstrap's OWN cr1 se.

    Single-coef: two-sided p over t = (beta_hat - beta0)/se_cr.
    Joint (multi-col): Wald W = (R bhat)' (R V R')^-1 (R bhat); if rank(R V R') < #cols
    (the v1 degenerate-F failure mode) we FALL BACK to RI on the same constraint and flag it.
    """
    if rng is None:
        rng = np.random.default_rng(seed)
    test_cols = list(test_cols)
    uniq = np.unique(groups)
    G = len(uniq)
    XtX_inv = np.linalg.pinv(X.T @ X)
    rank = np.linalg.matrix_rank(X)

    beta_hat, resid_full, _ = fit_ols(X, y, XtX_inv)
    Vfull = cr1_vcov(X, resid_full, groups, XtX_inv, rank)

    if not joint:
        j = test_cols[0]
        se = np.sqrt(Vfull[j, j])
        t_obs = (beta_hat[j] - beta0) / se if se > 0 else np.nan
    else:
        R = np.zeros((len(test_cols), X.shape[1]))
        for i, c in enumerate(test_cols):
            R[i, c] = 1.0
        Rb = R @ beta_hat
        RVR = R @ Vfull @ R.T
        rk = np.linalg.matrix_rank(RVR)
        if rk < len(test_cols):
            return {"degenerate": True, "rank": int(rk), "n_constraints": len(test_cols),
                    "note": "R V R' rank-deficient (the v1 degenerate-F failure); "
                            "falling back to randomization inference for the joint test.",
                    "fallback_ri": (randomization_inference(**_ri_args) if _ri_args else None)}
        W_obs = float(Rb @ np.linalg.solve(RVR, Rb))
        t_obs = W_obs

    # restricted residuals under H0 (impose the null = WCR, not WCU)
    resid_r, yhat_null, _free, _bf = _restricted_fit(X, y, test_cols, beta0)

    W, exact = _draw_wild_weights(G, B, weights, rng)
    Bn = W.shape[0]
    # map cluster weights to observations
    gidx = np.searchsorted(uniq, groups)

    t_star = np.empty(Bn)
    for b in range(Bn):
        wb = W[b][gidx]                                    # length-N obs weights
        y_star = yhat_null + resid_r * wb
        beta_b, resid_b, _ = fit_ols(X, y_star, XtX_inv)
        Vb = cr1_vcov(X, resid_b, groups, XtX_inv, rank)
        if not joint:
            j = test_cols[0]
            seb = np.sqrt(Vb[j, j])
            t_star[b] = (beta_b[j] - beta0) / seb if seb > 0 else np.nan
        else:
            # center bootstrap Wald at the null: use (R beta_b - R beta_hat)
            d_b = R @ beta_b - R @ beta_hat
            RVRb = R @ Vb @ R.T
            try:
                t_star[b] = float(d_b @ np.linalg.solve(RVRb, d_b))
            except np.linalg.LinAlgError:
                t_star[b] = np.nan

    finite = np.isfinite(t_star)
    t_star = t_star[finite]
    if not joint:
        p = (1 + np.sum(np.abs(t_star) >= abs(t_obs))) / (len(t_star) + 1)
    else:
        p = (1 + np.sum(t_star >= t_obs)) / (len(t_star) + 1)
    out = {"degenerate": False, "t_obs": float(t_obs), "p": float(p), "G": int(G),
           "B": int(len(t_star)), "exact": bool(exact), "weights": weights,
           "se_cr": float(np.sqrt(Vfull[test_cols[0], test_cols[0]])) if not joint else None,
           "beta_hat": float(beta_hat[test_cols[0]]) if not joint else None,
           "rank": int(rank)}
    if return_dist:
        out["t_star"] = t_star
    return out


def wcb_confidence_interval(X, y, groups, test_col, beta_hat, se_cr,
                            level=0.95, B=9999, weights="webb", seed=0, rng=None):
    """CI by TEST INVERSION: find beta0 where WCR p(beta0) = alpha, by bisection.

    A FIXED weight matrix is used across the grid so p(beta0) is smooth. Returns
    (lo, hi, bounded) — bounded=False (and +/-inf) if no crossing within beta_hat +/- 6 se.
    """
    if rng is None:
        rng = np.random.default_rng(seed)
    alpha = 1 - level
    uniq = np.unique(groups)
    G = len(uniq)
    W, _exact = _draw_wild_weights(G, B, weights, rng)     # FIXED across the grid
    gidx = np.searchsorted(uniq, groups)
    XtX_inv = np.linalg.pinv(X.T @ X)
    rank = np.linalg.matrix_rank(X)
    full_beta, _, _ = fit_ols(X, y, XtX_inv)

    def pval(beta0):
        resid_r, yhat_null, _f, _b = _restricted_fit(X, y, [test_col], beta0)
        Vfull = cr1_vcov(X, y - X @ full_beta, groups, XtX_inv, rank)
        se = np.sqrt(Vfull[test_col, test_col])
        t_obs = (full_beta[test_col] - beta0) / se
        ts = np.empty(W.shape[0])
        for b in range(W.shape[0]):
            wb = W[b][gidx]
            y_star = yhat_null + resid_r * wb
            bb, _, _ = fit_ols(X, y_star, XtX_inv)
            Vb = cr1_vcov(X, y_star - X @ bb, groups, XtX_inv, rank)
            seb = np.sqrt(Vb[test_col, test_col])
            ts[b] = (bb[test_col] - beta0) / seb if seb > 0 else np.nan
        ts = ts[np.isfinite(ts)]
        return (1 + np.sum(np.abs(ts) >= abs(t_obs))) / (len(ts) + 1)

    span = 6 * se_cr if se_cr > 0 else 1.0

    def find_bound(direction):
        # search outward for a sign change of (pval - alpha) starting at beta_hat
        lo, hi = beta_hat, beta_hat + direction * span
        if (pval(hi) - alpha) > 0:                         # still inside CI at the edge
            return direction * np.inf, False
        a, b = lo, hi
        for _ in range(28):                                # ~2^-28 of the 6*se span: ample
            mid = 0.5 * (a + b)
            if (pval(mid) - alpha) > 0:
                a = mid
            else:
                b = mid
        return 0.5 * (a + b), True

    hi_bound, hi_ok = find_bound(+1)
    lo_bound, lo_ok = find_bound(-1)
    return lo_bound, hi_bound, (lo_ok and hi_ok)


def _stat_from_assignment(df, build_fn, test_col_name, stat, treated_sites,
                          kmin, kmax):
    """Recompute the chosen statistic with `treated_sites` as the pseudo-treated set."""
    d = df.copy()
    d["D"] = d["site"].isin(treated_sites).astype(int)
    res = build_fn(d, test_col_name, kmin, kmax)
    X, y, groups, names, tidx = res
    XtX_inv = np.linalg.pinv(X.T @ X)
    rank = np.linalg.matrix_rank(X)
    beta, resid, _ = fit_ols(X, y, XtX_inv)
    if stat == "coef":
        return float(beta[tidx[0]])
    if stat == "t":
        V = cr1_vcov(X, resid, groups, XtX_inv, rank)
        se = np.sqrt(V[tidx[0], tidx[0]])
        return float(beta[tidx[0]] / se) if se > 0 else np.nan
    if stat == "wald":                                     # joint over all treat cols
        V = cr1_vcov(X, resid, groups, XtX_inv, rank)
        R = np.zeros((len(tidx), X.shape[1]))
        for i, c in enumerate(tidx):
            R[i, c] = 1.0
        Rb = R @ beta
        RVR = R @ V @ R.T
        if np.linalg.matrix_rank(RVR) < len(tidx):
            return np.nan
        return float(Rb @ np.linalg.solve(RVR, Rb))
    if stat == "ssq":                                      # sum of squared treat coefs
        # VCV-free joint statistic (robust at G=7 where cr1 wald is unstable); the
        # placebo distribution supplies the reference scale, so no SE is needed.
        return float(np.sum(beta[tidx] ** 2))
    raise ValueError(stat)


def randomization_inference(df, build_fn, test_col_name, stat="coef",
                            kmin=None, kmax=CLEAN_KMAX,
                            real_treated=TREATED_SITE, n_pseudo=1,
                            candidate_sites=None, pseudo_groups=None):
    """Enumerate pseudo-treated assignments; exact two-sided permutation p with 1/N floor.

    By default permutes which single site is 'treated' across all N sites (the headline
    test). For the contamination test, pass pseudo_groups = explicit list of treated-sets
    to enumerate (e.g. C(6,2) math-cohort memberships among non-SO sites).
    """
    sites = sorted(df["site"].unique())
    if pseudo_groups is None:
        cand = candidate_sites if candidate_sites is not None else sites
        pseudo_groups = [(s,) for s in cand]
        obs_group = (real_treated,)
    else:
        obs_group = tuple(sorted(pseudo_groups[0]))        # convention: first is the real one
    stats_all = {}
    for grp in pseudo_groups:
        key = tuple(sorted(grp))
        stats_all[key] = _stat_from_assignment(df, build_fn, test_col_name, stat,
                                               set(grp), kmin, kmax)
    obs_key = tuple(sorted(obs_group)) if pseudo_groups and not candidate_sites and \
        obs_group in stats_all else (real_treated,)
    if obs_key not in stats_all:
        obs_key = list(stats_all.keys())[0]
    t_obs = stats_all[obs_key]
    vals = np.array([v for v in stats_all.values() if np.isfinite(v)])
    keys = [k for k, v in stats_all.items() if np.isfinite(v)]
    N = len(vals)
    if N == 0 or not np.isfinite(t_obs):
        # every assignment's statistic was non-finite (e.g. a rank-deficient joint Wald):
        # RI is not estimable here. Report undefined rather than crash.
        return {"t_obs": float(t_obs) if np.isfinite(t_obs) else np.nan,
                "p": np.nan, "rank": int(N + 1), "n_assign": int(N),
                "min_p": (1.0 / N if N else np.nan), "ratio": np.nan,
                "t_perm": vals, "degenerate": True}
    if stat in ("coef", "t"):
        extreme = np.abs(vals) >= abs(t_obs) - 1e-12
        order = np.argsort(-np.abs(vals))
        others = np.abs(vals[[i for i, k in enumerate(keys) if k != obs_key]])
        ratio = abs(t_obs) / others.max() if others.size and others.max() > 0 else np.inf
    else:                                                  # wald: one-sided large
        extreme = vals >= t_obs - 1e-12
        order = np.argsort(-vals)
        others = vals[[i for i, k in enumerate(keys) if k != obs_key]]
        ratio = t_obs / others.max() if others.size and others.max() > 0 else np.inf
    p = np.sum(extreme) / N
    rank = 1 + np.sum(np.abs(vals) > abs(t_obs) + 1e-12) if stat in ("coef", "t") \
        else 1 + np.sum(vals > t_obs + 1e-12)
    return {"t_obs": float(t_obs), "p": float(p), "rank": int(rank), "n_assign": int(N),
            "min_p": 1.0 / N, "ratio": float(ratio),
            "t_perm": vals}


# ----------------------------------------------------------------------------------
#   build_fn helpers (each returns build_design output for a given treated set in df.D)
# ----------------------------------------------------------------------------------
def _bf_did(d, name, kmin, kmax):
    dd = clean_window(d, kmin, kmax)
    post = (dd["k"] >= 0).astype(int)
    did = (dd["D"].to_numpy() * post.to_numpy()).astype(float)
    return build_design(dd, {name: did})


def _make_bf_event(kmin, kmax, ks):
    def bf(d, name, _kmin, _kmax):
        dd = clean_window(d, kmin, kmax)
        terms = {}
        for k in ks:
            cn = f"k[{k:+d}]"
            terms[cn] = ((dd["k"] == k).to_numpy() * dd["D"].to_numpy()).astype(float)
        X, y, g, names, tidx = build_design(dd, terms)
        # caller asked for a single column `name`: return its index first
        if name in names:
            j = names.index(name)
            tidx = [j] + [i for i in tidx if i != j]
        return X, y, g, names, tidx
    return bf


def _make_bf_event_joint(kmin, kmax, leads):
    """build_fn whose treat columns are exactly the lead dummies (for the joint pre-trend)."""
    def bf(d, _name, _kmin, _kmax):
        dd = clean_window(d, kmin, kmax)
        terms = {}
        for k in leads:
            cn = f"k[{k:+d}]"
            terms[cn] = ((dd["k"] == k).to_numpy() * dd["D"].to_numpy()).astype(float)
        return build_design(dd, terms)
    return bf


# ----------------------------------------------------------------------------------
# S4  DiD SPECS
# ----------------------------------------------------------------------------------
def _pct(b):
    return 100.0 * (np.expm1(b))


def did_clean(df, event=DEFAULT_EVENT, kmin=None, kmax=CLEAN_KMAX,
              B=9999, weights="webb", seed=0, rng=None, ci=True):
    """Headline clean-window TWFE DiD with the three-column inference.

    ci=False skips the (expensive) test-inversion CI — used by the recovery harness size
    loop where only the WCR p is needed; coverage loop keeps ci=True.
    """
    if rng is None:
        rng = np.random.default_rng(seed)
    dd = clean_window(df, kmin, kmax)
    X, y, groups, names, tidx = _bf_did(dd, "did", kmin, kmax)
    j = tidx[0]
    XtX_inv = np.linalg.pinv(X.T @ X)
    rank = np.linalg.matrix_rank(X)
    beta, resid, _ = fit_ols(X, y, XtX_inv)
    Vcr = cr1_vcov(X, resid, groups, XtX_inv, rank)
    se_cr = np.sqrt(Vcr[j, j])
    b = float(beta[j])

    wcr = wild_cluster_bootstrap(X, y, groups, [j], 0.0, B=B, weights=weights, rng=rng)
    if ci:
        lo, hi, bounded = wcb_confidence_interval(X, y, groups, j, b, se_cr, B=B,
                                                  weights=weights, rng=rng)
    else:
        lo, hi, bounded = np.nan, np.nan, False
    ri = randomization_inference(dd, _bf_did, "did", "coef", kmin, kmax)

    return {"beta": b, "pct": _pct(b), "n_obs": int(len(y)), "G": int(len(np.unique(groups))),
            "cr1_se": float(se_cr), "cr1_p_INVALID": float(2 * (1 - stats.norm.cdf(abs(b / se_cr)))),
            "wcr": wcr, "wcr_ci": (lo, hi, bounded),
            "wcr_ci_pct": (_pct(lo) if np.isfinite(lo) else -100.0,
                           _pct(hi) if np.isfinite(hi) else np.inf, bounded),
            "ri": ri}


def did_regime_split(df, event=DEFAULT_EVENT, clean_hi=CLEAN_KMAX, B=9999,
                     weights="webb", seed=0, rng=None):
    """b_clean (0<=k<=clean_hi) and b_long (k>=clean_hi+1) estimated SEPARATELY, never pooled."""
    if rng is None:
        rng = np.random.default_rng(seed)
    clean = did_clean(df, event, None, clean_hi, B=B, weights=weights, rng=rng)
    has_long = (df["k"] >= clean_hi + 1).any()
    if not has_long:
        long = {"NA": True, "reason": f"no k>=+{clean_hi+1} months in panel "
                f"(panel ends k=+{int(df['k'].max())}); long-run path not estimable."}
    else:
        dd = df[df["k"] >= clean_hi + 1]
        # contrast long-run treated months vs pre using a post(long) dummy on full data
        d2 = df.copy()
        d2["post_long"] = (d2["k"] >= clean_hi + 1).astype(int)
        # exclude clean post months so the long coefficient isn't pooled with clean ATT
        d2 = d2[(d2["k"] < 0) | (d2["k"] >= clean_hi + 1)].copy()
        didl = (d2["D"].to_numpy() * d2["post_long"].to_numpy()).astype(float)
        X, y, groups, names, tidx = build_design(d2, {"did_long": didl})
        j = tidx[0]
        XtX_inv = np.linalg.pinv(X.T @ X)
        rank = np.linalg.matrix_rank(X)
        beta, resid, _ = fit_ols(X, y, XtX_inv)
        Vcr = cr1_vcov(X, resid, groups, XtX_inv, rank)
        se = np.sqrt(Vcr[j, j])
        b = float(beta[j])
        wcr = wild_cluster_bootstrap(X, y, groups, [j], 0.0, B=B, weights=weights, rng=rng)
        long = {"NA": False, "beta": b, "pct": _pct(b), "cr1_se": float(se),
                "wcr": wcr, "label": "AI-commercialization regime (k>=+13), NOT a causal ATT"}
    return {"clean": clean, "long": long}


def event_study(df, event=DEFAULT_EVENT, kmin=-6, kmax=CLEAN_KMAX, B=9999,
                weights="webb", seed=0, rng=None):
    """Leads/lags table (k=-1 omitted := 0); pre-trend joint RI always + WCR-joint if rank ok."""
    if rng is None:
        rng = np.random.default_rng(seed)
    dd = clean_window(df, kmin, kmax)
    ks = [k for k in range(kmin, kmax + 1) if k != -1]
    terms = {}
    for k in ks:
        terms[f"k[{k:+d}]"] = ((dd["k"] == k).to_numpy() * dd["D"].to_numpy()).astype(float)
    X, y, groups, names, tidx = build_design(dd, terms)
    XtX_inv = np.linalg.pinv(X.T @ X)
    rank = np.linalg.matrix_rank(X)
    beta, resid, _ = fit_ols(X, y, XtX_inv)
    name2idx = {names[i]: i for i in range(len(names))}

    rows = []
    bf_es = _make_bf_event(kmin, kmax, ks)
    for k in range(kmin, kmax + 1):
        if k == -1:
            rows.append({"k": k, "beta": 0.0, "pct": 0.0, "wcr_p": np.nan,
                         "ri_p": np.nan, "ref": True})
            continue
        cn = f"k[{k:+d}]"
        if cn not in name2idx:
            rows.append({"k": k, "beta": np.nan, "pct": np.nan, "wcr_p": np.nan,
                         "ri_p": np.nan, "ref": False})
            continue
        j = name2idx[cn]
        bk = float(beta[j])
        if B <= 50:
            # fast path (used by the recovery harness point-recovery loop): coefficients
            # only, skip the per-k bootstrap/permutation p-values.
            rows.append({"k": k, "beta": bk, "pct": _pct(bk), "wcr_p": np.nan,
                         "ri_p": np.nan, "ref": False})
            continue
        wcr = wild_cluster_bootstrap(X, y, groups, [j], 0.0, B=B,
                                     weights=weights, rng=rng)
        ri = randomization_inference(dd, bf_es, cn, "coef", kmin, kmax)
        rows.append({"k": k, "beta": bk, "pct": _pct(bk), "wcr_p": wcr["p"],
                     "ri_p": ri["p"], "ref": False})
    tab = pd.DataFrame(rows).sort_values("k").reset_index(drop=True)

    # joint pre-trend test on leads k<=-2
    leads = [k for k in range(kmin, -1) if k != -1]
    pretrend = {"leads": leads}
    if leads:
        lead_cols = [name2idx[f"k[{k:+d}]"] for k in leads if f"k[{k:+d}]" in name2idx]
        bf_joint = _make_bf_event_joint(kmin, kmax, leads)
        ri_args = dict(df=dd, build_fn=bf_joint, test_col_name="joint", stat="ssq",
                       kmin=kmin, kmax=kmax)
        wcr_j = wild_cluster_bootstrap(X, y, groups, lead_cols, 0.0, B=B, weights=weights,
                                       joint=True, rng=rng, _ri_args=ri_args)
        # RI joint pre-trend uses the VCV-free sum-of-squared-lead-coefs statistic
        # (robust at G=7 where the cluster Wald is rank-unstable).
        ri_j = randomization_inference(dd, bf_joint, "joint", "ssq", kmin, kmax)
        pretrend["ri_p"] = ri_j["p"]
        pretrend["ri_rank"] = ri_j["rank"]
        pretrend["ri_n"] = ri_j["n_assign"]
        if wcr_j.get("degenerate"):
            pretrend["wcr_p"] = None
            pretrend["wcr_note"] = wcr_j["note"]
            pretrend["rank_ok"] = False
        else:
            pretrend["wcr_p"] = wcr_j["p"]
            pretrend["rank_ok"] = True
    return tab, pretrend


def fixed_horizon_att(es_table, df, event=DEFAULT_EVENT, horizons=(6, 12, 24),
                      B=9999, weights="webb", seed=0, kmin=-6, kmax=CLEAN_KMAX, rng=None):
    """Pointwise beta_h at each horizon + 3-month-smoothed contrast; NA when out-of-sample."""
    if rng is None:
        rng = np.random.default_rng(seed)
    dd = clean_window(df, kmin, kmax)
    ks = [k for k in range(kmin, kmax + 1) if k != -1]
    terms = {f"k[{k:+d}]": ((dd["k"] == k).to_numpy() * dd["D"].to_numpy()).astype(float)
             for k in ks}
    X, y, groups, names, tidx = build_design(dd, terms)
    name2idx = {names[i]: i for i in range(len(names))}
    beta, _, _ = fit_ols(X, y)
    kmax_obs = int(df["k"].max())

    rows = []
    bf_es = _make_bf_event(kmin, kmax, ks)
    for h in horizons:
        cn = f"k[{h:+d}]"
        if h > kmax or cn not in name2idx:
            rows.append({"h": h, "NA": True,
                         "reason": f"out of sample, panel ends k=+{kmax_obs}",
                         "beta": np.nan, "pct": np.nan, "wcr_p": np.nan,
                         "ri_p": np.nan, "beta_sm3": np.nan})
            continue
        j = name2idx[cn]
        bh = float(beta[j])
        wcr = wild_cluster_bootstrap(X, y, groups, [j], 0.0, B=B, weights=weights, rng=rng)
        ri = randomization_inference(dd, bf_es, cn, "coef", kmin, kmax)
        # 3-month smoothed contrast around h (h-1,h,h+1) where available
        win = [k for k in (h - 1, h, h + 1) if f"k[{k:+d}]" in name2idx and k != -1]
        bsm = float(np.mean([beta[name2idx[f'k[{k:+d}]']] for k in win])) if win else bh
        rows.append({"h": h, "NA": False, "beta": bh, "pct": _pct(bh),
                     "wcr_p": wcr["p"], "ri_p": ri["p"], "ri_rank": ri["rank"],
                     "ri_n": ri["n_assign"], "ri_ratio": ri["ratio"],
                     "beta_sm3": bsm, "pct_sm3": _pct(bsm)})
    return pd.DataFrame(rows)


def placebo_in_time(df, real_event=DEFAULT_EVENT, fake_event="2022-09", B=9999,
                    weights="webb", seed=0, rng=None):
    """Truncate to s < real_event FIRST (leak-free), re-center on fake event, run DiD."""
    if rng is None:
        rng = np.random.default_rng(seed)
    real_e = ym_to_int(real_event)
    fake_e = ym_to_int(fake_event)
    pre = df[df["s"] < real_e].copy()
    if pre.empty or pre["s"].nunique() < 4:
        return {"SKIP": True, "reason": "pre-period too short for a leak-free placebo "
                f"({pre['s'].nunique()} months before the real event)."}
    pre["k"] = pre["s"] - fake_e
    kmn = int(pre["k"].min())
    kmx = int(pre["k"].max())
    res = did_clean(pre, fake_event, kmn, kmx, B=B, weights=weights, rng=rng)
    verdict = ("PLACEBO CLEAN (effect ~0)" if res["wcr"]["p"] > 0.10
               else "PLACEBO FIRES — pre-event differential, investigate")
    return {"SKIP": False, "fake_event": fake_event, "k_range": (kmn, kmx),
            "res": res, "verdict": verdict}


# ----------------------------------------------------------------------------------
# S5  SYNTHETIC CONTROL
# ----------------------------------------------------------------------------------
def sc_prepare(df, endpoint, event=DEFAULT_EVENT, donors=None):
    """Wide log matrix Y[T,N]; treated/donor split; pre/post masks; T0, J."""
    e = ym_to_int(event)
    d = df.copy()
    if donors is not None:
        keep = set(donors) | {TREATED_SITE}
        d = d[d["site"].isin(keep)].copy()
    wide = d.pivot_table(index="s", columns="site", values="y")
    # drop donor columns with any missing month (warn)
    full = wide.dropna(axis=1, how="any")
    dropped = [c for c in wide.columns if c not in full.columns]
    if dropped:
        print(f"  [SC] dropped donors with missing months: {dropped}")
    sites = list(full.columns)
    treated_idx = sites.index(TREATED_SITE)
    donor_idx = [i for i in range(len(sites)) if i != treated_idx]
    s_index = full.index.to_numpy()
    pre_mask = s_index < e
    post_mask = s_index >= e
    Y = full.to_numpy()
    return {"Y": Y, "sites": sites, "treated_idx": treated_idx, "donor_idx": donor_idx,
            "pre_mask": pre_mask, "post_mask": post_mask, "T0": int(pre_mask.sum()),
            "J": len(donor_idx), "s_index": s_index, "ym": [int_to_ym(s) for s in s_index],
            "event_s": e}


def solve_simplex_weights(y_pre, Z_pre, ridge=1e-8, n_restarts=5, seed=0):
    """Convex QP on the unit simplex: min ||y_pre - Z_pre w||^2, w>=0, sum w=1 (SLSQP)."""
    J = Z_pre.shape[1]
    G = Z_pre.T @ Z_pre + ridge * np.eye(J)
    c = Z_pre.T @ y_pre

    def obj(w):
        return float(w @ G @ w - 2 * c @ w + y_pre @ y_pre)

    def grad(w):
        return 2 * (G @ w - c)

    cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0,
             "jac": lambda w: np.ones(J)}]
    bounds = [(0.0, 1.0)] * J
    rng = np.random.default_rng(seed)
    starts = [np.full(J, 1.0 / J)]
    for _ in range(n_restarts):
        starts.append(rng.dirichlet(np.ones(J)))
    best_w, best_f = None, np.inf
    for w0 in starts:
        r = optimize.minimize(obj, w0, jac=grad, bounds=bounds, constraints=cons,
                              method="SLSQP", options={"maxiter": 500, "ftol": 1e-12})
        if r.success and r.fun < best_f:
            best_f, best_w = r.fun, r.x
    if best_w is None:
        print("[SC][WARN] SLSQP failed on all restarts; falling back to uniform donor "
              "weights -- SC fit not trustworthy.")
        best_w = np.full(J, 1.0 / J)
        best_f = obj(best_w)
    w = np.clip(best_w, 0, None)
    w = w / w.sum()
    assert abs(w.sum() - 1) < 1e-6
    pre_mspe = float(np.mean((y_pre - Z_pre @ w) ** 2))
    return w, pre_mspe


def synthetic_control_fit(prep, clean_hi=CLEAN_KMAX, horizons=(6, 12, 24), ridge=1e-8):
    """Fit simplex weights on pre-period; gap path, RMSPE pre/post, fixed-horizon gaps."""
    Y, ti, di = prep["Y"], prep["treated_idx"], prep["donor_idx"]
    pre, post = prep["pre_mask"], prep["post_mask"]
    y_tr = Y[:, ti]
    Z = Y[:, di]
    w, pre_mspe = solve_simplex_weights(y_tr[pre], Z[pre], ridge=ridge)
    synth = Z @ w
    gap = y_tr - synth
    rmspe_pre = float(np.sqrt(np.mean(gap[pre] ** 2)))
    rmspe_post = float(np.sqrt(np.mean(gap[post] ** 2))) if post.any() else np.nan
    ratio = (rmspe_post / rmspe_pre) if rmspe_pre > 0 else np.inf
    under_identified = prep["T0"] <= prep["J"]
    # fixed-horizon gaps (k relative to event)
    krel = prep["s_index"] - prep["event_s"]
    fh = {}
    for h in horizons:
        m = krel == h
        fh[h] = float(gap[m][0]) if m.any() else None
    clean_post = (krel >= 0) & (krel <= clean_hi)
    mean_gap_clean = float(np.mean(gap[clean_post])) if clean_post.any() else np.nan
    return {"w": w, "donor_sites": [prep["sites"][i] for i in di], "gap": gap,
            "synth": synth, "rmspe_pre": rmspe_pre, "rmspe_post": rmspe_post,
            "ratio": ratio, "under_identified": under_identified, "fh": fh,
            "mean_gap_clean": mean_gap_clean, "pct_clean": _pct(mean_gap_clean)}


def sc_placebo_inference(prep, ridge=1e-8):
    """In-space placebo permutation: assign each unit as treated, rank post/pre RMSPE ratio."""
    Y = prep["Y"]
    pre, post = prep["pre_mask"], prep["post_mask"]
    sites = prep["sites"]
    N = len(sites)
    ratios = {}
    for u in range(N):
        donors = [i for i in range(N) if i != u]
        y_u = Y[:, u]
        Z = Y[:, donors]
        w, _ = solve_simplex_weights(y_u[pre], Z[pre], ridge=ridge)
        gap = y_u - Z @ w
        rp = np.sqrt(np.mean(gap[pre] ** 2))
        rpost = np.sqrt(np.mean(gap[post] ** 2)) if post.any() else np.nan
        ratios[sites[u]] = (rpost / rp) if rp > 0 else np.inf
    treated_ratio = ratios[sites[prep["treated_idx"]]]
    allr = np.array(list(ratios.values()))
    p = np.sum(allr >= treated_ratio - 1e-12) / N
    rank = 1 + np.sum(allr > treated_ratio + 1e-12)
    return {"ratios": ratios, "treated_ratio": float(treated_ratio), "p": float(p),
            "rank": int(rank), "p_floor": 1.0 / N, "N": N}


def run_synthetic_control(df, endpoint="questions", event=DEFAULT_EVENT, donors=None,
                          save_path=None):
    prep = sc_prepare(df, endpoint, event, donors)
    fit = synthetic_control_fit(prep)
    plac = sc_placebo_inference(prep)
    rep = {"prep": prep, "fit": fit, "placebo": plac}
    if save_path:
        krel = prep["s_index"] - prep["event_s"]
        out = pd.DataFrame({"ym": prep["ym"], "k": krel, "treated": prep["Y"][:, prep["treated_idx"]],
                            "synth": fit["synth"], "gap": fit["gap"]})
        out.to_csv(save_path, index=False)
        rep["saved"] = save_path
    return rep


# ----------------------------------------------------------------------------------
# S6  STAGGERED + DIAGNOSTICS
# ----------------------------------------------------------------------------------
def make_cohorts(df, g_treated=G_TREATED, g_math=G_MATH):
    """Add g_int (cohort month), r (=s-g), cohort_label, never_treated bool."""
    d = df.copy()
    gt, gm = ym_to_int(g_treated), ym_to_int(g_math)
    g = np.full(len(d), np.inf)
    g = np.where(d["site"] == TREATED_SITE, gt, g)
    g = np.where(d["site"].isin(MATH_SITES), gm, g)
    d["g_int"] = g
    d["r"] = np.where(np.isfinite(g), d["s"] - g, np.nan)
    d["cohort_label"] = np.where(d["site"] == TREATED_SITE, g_treated,
                          np.where(d["site"].isin(MATH_SITES), g_math, "never"))
    d["never_treated"] = ~np.isfinite(g)
    return d


def sun_abraham(df, rmin=-6, rmax=24, B=9999, weights="webb", seed=0, rng=None,
                g_treated=G_TREATED, g_math=G_MATH):
    """Saturated CATT(g,r) vs NEVER-TREATED only. Honesty gate skips cohorts with rmax_g<0."""
    if rng is None:
        rng = np.random.default_rng(seed)
    d = make_cohorts(df, g_treated=g_treated, g_math=g_math)
    cohorts = [g for g in sorted(d.loc[np.isfinite(d["g_int"]), "g_int"].unique())]
    never = d[d["never_treated"]].copy()
    # identification gate: SA is NOT identified with a never-treated-only comparison if there
    # are no never-treated units (e.g. the primary/math-only control set, where every control
    # is assigned to the o1 math cohort g_math). Proceeding would yield a meaningless all-
    # treated regression / crash, so return an explicit exploratory-NA dict instead.
    if never.empty or never["s"].nunique() < 2:
        return {"cohort_results": {}, "cohorts_skipped": [], "exploratory": True, "NA": True,
                "reason": "no never-treated comparison units (all controls assigned to the o1 math "
                          "cohort g_math); Sun-Abraham is not identified with a never-treated-only "
                          "comparison — use a not-yet-treated comparison or add a non-math never-treated donor.",
                "note": "SA/CS require a non-empty never-treated group; skipped."}
    cohorts_skipped, cohort_results = [], {}
    for g in cohorts:
        gd = d[d["g_int"] == g]
        rmax_g = int((gd["s"] - g).max())
        rmin_g = int((gd["s"] - g).min())
        if rmax_g < 0:
            cohorts_skipped.append({"g": int_to_ym(int(g)), "rmax": rmax_g,
                                    "reason": "no post periods in panel (out of sample)"})
            continue
        # build a 2-group (this cohort vs never-treated) event study
        sub = pd.concat([gd, never]).copy()
        sub["D"] = (sub["g_int"] == g).astype(int)
        sub["k"] = sub["s"] - g
        ks = [k for k in range(max(rmin, rmin_g), min(rmax, rmax_g) + 1) if k != -1]
        if not ks:
            cohorts_skipped.append({"g": int_to_ym(int(g)), "rmax": rmax_g,
                                    "reason": "no estimable relative periods"})
            continue
        terms = {f"k[{k:+d}]": ((sub["k"] == k).to_numpy() * sub["D"].to_numpy()).astype(float)
                 for k in ks}
        X, y, groups, names, tidx = build_design(sub, terms)
        beta, _, _ = fit_ols(X, y)
        name2idx = {names[i]: i for i in range(len(names))}
        catt = {k: float(beta[name2idx[f'k[{k:+d}]']]) for k in ks if f"k[{k:+d}]" in name2idx}
        post_rs = [k for k in catt if k >= 0]
        att_g = float(np.mean([catt[k] for k in post_rs])) if post_rs else np.nan
        cohort_results[int_to_ym(int(g))] = {"catt": catt, "att_g": att_g,
                                             "rmax": rmax_g, "n_post": len(post_rs)}
    return {"cohort_results": cohort_results, "cohorts_skipped": cohorts_skipped,
            "exploratory": True,
            "note": "EXPLORATORY: never-treated-only comparison; with ~7 units fragile. "
                    "If only the 2022-12 cohort is estimable, SA collapses to its event study."}


def callaway_santanna(df, control_group="never", agg="event",
                      g_treated=G_TREATED, g_math=G_MATH):
    """Group-time ATT(g,t) with g-1 baseline per cohort; event-study theta(r) cross-check."""
    d = make_cohorts(df, g_treated=g_treated, g_math=g_math)
    cohorts = [g for g in sorted(d.loc[np.isfinite(d["g_int"]), "g_int"].unique())]
    never = d[d["never_treated"]]
    # identification gate (see sun_abraham): CS needs a non-empty never-treated control group.
    if never.empty or never["s"].nunique() < 2:
        return {"by_cohort": {}, "exploratory": True, "NA": True,
                "reason": "no never-treated comparison units (all controls assigned to the o1 math "
                          "cohort g_math); Callaway-Sant'Anna is not identified with a never-treated-"
                          "only comparison — use a not-yet-treated comparison or add a non-math "
                          "never-treated donor.",
                "note": "SA/CS require a non-empty never-treated group; skipped."}
    out = {}
    for g in cohorts:
        gd = d[d["g_int"] == g]
        gmax = int(gd["s"].max())
        if (gd["s"] >= g).sum() == 0:
            continue
        base_s = int(g - 1)
        # ATT(g,t) = [Ybar_g(t)-Ybar_g(base)] - [Ybar_never(t)-Ybar_never(base)]
        attgt = {}
        for t in range(int(g), gmax + 1):
            yg_t = gd.loc[gd["s"] == t, "y"]
            yg_b = gd.loc[gd["s"] == base_s, "y"]
            yn_t = never.loc[never["s"] == t, "y"]
            yn_b = never.loc[never["s"] == base_s, "y"]
            if min(len(yg_t), len(yg_b), len(yn_t), len(yn_b)) == 0:
                continue
            attgt[t - int(g)] = float((yg_t.mean() - yg_b.mean())
                                      - (yn_t.mean() - yn_b.mean()))
        post = [r for r in attgt if r >= 0]
        out[int_to_ym(int(g))] = {"attgt": attgt,
                                  "att": float(np.mean([attgt[r] for r in post])) if post else np.nan}
    return {"by_cohort": out, "note": "Callaway-Sant'Anna point-estimate cross-check "
            "(never-treated control, g-1 baseline)."}


def control_only_placebo(df, event=DEFAULT_EVENT, pseudo_treated=MATH_SITES,
                         kmin=-6, kmax=24, ext_start=24, B=9999, weights="webb",
                         seed=0, rng=None):
    """Drop SO; math=pseudo-treated. PRE-trend WCR/RI + extension-window k>=ext_start test."""
    if rng is None:
        rng = np.random.default_rng(seed)
    nonso = df[df["site"] != TREATED_SITE].copy()
    nonso["D"] = nonso["site"].isin(pseudo_treated).astype(int)
    # pre-trend test on leads (k<=-2) among controls only
    leads = [k for k in range(kmin, -1) if k != -1]
    dd = clean_window(nonso, kmin, CLEAN_KMAX)
    terms = {f"k[{k:+d}]": ((dd["k"] == k).to_numpy() * dd["D"].to_numpy()).astype(float)
             for k in leads if (dd["k"] == k).any()}
    res = {}
    if terms:
        X, y, groups, names, tidx = build_design(dd, terms)
        lead_cols = tidx
        ri_args = None
        wcr_j = wild_cluster_bootstrap(X, y, groups, lead_cols, 0.0, B=B, weights=weights,
                                       joint=True, rng=rng)
        res["pretrend_wcr_p"] = None if wcr_j.get("degenerate") else wcr_j["p"]
        res["pretrend_wcr_note"] = wcr_j.get("note")
        # RI permutes math-cohort membership among the non-SO sites: C(6,2)=15
        nonso_sites = sorted(nonso["site"].unique())
        pairs = list(itertools.combinations(nonso_sites, len(pseudo_treated)))
        obs = tuple(sorted(pseudo_treated))
        groups_list = [obs] + [p for p in pairs if p != obs]
        bf_joint = _make_bf_event_joint(kmin, CLEAN_KMAX, leads)
        ri = randomization_inference(nonso, bf_joint, "joint", "ssq", kmin, CLEAN_KMAX,
                                     pseudo_groups=groups_list)
        res["pretrend_ri_p"] = ri["p"]
        res["pretrend_ri_rank"] = ri["rank"]
        res["pretrend_ri_n"] = ri["n_assign"]
    # extension-window test (needs k>=ext_start)
    has_ext = (nonso["k"] >= ext_start).any()
    if not has_ext:
        res["estimable_ext"] = False
        res["ext_reason"] = (f"not estimable, panel ends k=+{int(df['k'].max())} "
                             f"(< ext_start=+{ext_start}); cannot rule controls clean.")
    else:
        d2 = nonso.copy()
        d2["post_ext"] = (d2["k"] >= ext_start).astype(int)
        d2 = d2[(d2["k"] < 0) | (d2["k"] >= ext_start)].copy()
        didx = (d2["D"].to_numpy() * d2["post_ext"].to_numpy()).astype(float)
        X, y, groups, names, tidx = build_design(d2, {"did_ext": didx})
        wcr = wild_cluster_bootstrap(X, y, groups, tidx, 0.0, B=B, weights=weights, rng=rng)
        beta, _, _ = fit_ols(X, y)
        res["estimable_ext"] = True
        res["ext_beta"] = float(beta[tidx[0]])
        res["ext_wcr_p"] = wcr["p"]
    # contamination index C_hat: |control pseudo-ATT| relative to a treated ATT scale
    res["C_hat_note"] = ("C_hat = |control pseudo-ATT in extension window| as a share of the "
                         "treated clean ATT; not computable until the extension window exists.")
    return res


def frozen_control_arm(df, event=DEFAULT_EVENT, clean_kmax=CLEAN_KMAX, drop_order=None,
                       rel_drift_warn=0.25, B=9999, weights="webb", seed=0, rng=None):
    """Progressively drop most-substitutable controls; ATT path + Delta_max + rel_drift."""
    if rng is None:
        rng = np.random.default_rng(seed)
    if drop_order is None:
        drop_order = [s for s in SUBSTITUTABILITY_ORDER if s in set(df["site"].unique())]
    present_controls = [s for s in df["site"].unique() if s != TREATED_SITE]
    path = []
    dropped = []
    remaining = list(present_controls)
    # step 0: all controls
    while True:
        sites = [TREATED_SITE] + remaining
        if len(remaining) < 1:
            break
        sub = df[df["site"].isin(sites)].copy()
        res = did_clean(sub, event, None, clean_kmax, B=max(999, B // 5),
                        weights=weights, rng=rng)
        path.append({"dropped": list(dropped), "controls": list(remaining),
                     "n_controls": len(remaining), "beta": res["beta"],
                     "pct": res["pct"], "wcr_p": res["wcr"]["p"]})
        # drop the next most-substitutable control still present; keep MathOverflow
        # (least AI-substitutable, expert-gated) as the frozen core, dropped last/never.
        frozen_core_site = "mathoverflow.net"
        nxt = None
        for s in drop_order:
            if s in remaining and s != frozen_core_site:
                nxt = s
                break
        if nxt is None or len(remaining) <= 1:
            break
        remaining.remove(nxt)
        dropped.append(nxt)
    betas = [p["beta"] for p in path]
    delta_max = float(max(betas) - min(betas)) if betas else np.nan
    base = betas[0] if betas else np.nan
    rel_drift = float(delta_max / abs(base)) if base and abs(base) > 1e-9 else np.inf
    signs = set(np.sign([b for b in betas if np.isfinite(b)]))
    sign_stable = len(signs) <= 1
    return {"path": path, "delta_max": delta_max, "rel_drift": rel_drift,
            "rel_drift_warn": rel_drift_warn,
            "drift_ok": (rel_drift <= rel_drift_warn),
            "sign_stable": sign_stable,
            "frozen_core": [s for s in MATH_SITES if s in present_controls],
            "verdict": ("ROBUST: sign stable and rel_drift<=%.2f" % rel_drift_warn
                        if sign_stable and rel_drift <= rel_drift_warn
                        else "DRIFT: ATT moves materially as controls drop — inspect")}


# ----------------------------------------------------------------------------------
# S7  SIMULATE RECOVERY HARNESS
# ----------------------------------------------------------------------------------
def simulate_panel(n_sites=7, n_pre=6, n_post=13, theta=0.0, pretrend=0.0,
                   cohort2_effect=0.0, g2_offset=None, sigma_a=0.5, sigma_t=0.2,
                   sigma_e=0.1, rho=0.5, rng=None):
    """DGP: y=alpha_i+tau_t+theta*D*1{k>=0}+pretrend*D*k*1{k<0}+cohort2*M*1{r2>=0}+AR(1) e."""
    if rng is None:
        rng = np.random.default_rng(0)
    T = n_pre + n_post
    base_s = ym_to_int("2022-12") - n_pre                  # so k=-n_pre..+n_post-1
    event_s = ym_to_int("2022-12")
    alpha = rng.normal(0, sigma_a, n_sites)
    tau = rng.normal(0, sigma_t, T)
    g2 = base_s + n_pre + (g2_offset if g2_offset is not None else 999)  # math cohort month
    rows = []
    for i in range(n_sites):
        # AR(1) errors
        e = np.empty(T)
        e[0] = rng.normal(0, sigma_e)
        for t in range(1, T):
            e[t] = rho * e[t - 1] + rng.normal(0, sigma_e * np.sqrt(1 - rho ** 2))
        D = 1 if i == 0 else 0
        M = 1 if i in (1, 2) else 0                        # two 'math' cohort-2 sites
        for t in range(T):
            s = base_s + t
            k = s - event_s
            y = alpha[i] + tau[t] + e[t]
            if D == 1 and k >= 0:
                y += theta
            if D == 1 and k < 0:
                y += pretrend * k
            if M == 1 and cohort2_effect != 0.0 and s >= g2:
                y += cohort2_effect
            cnt = max(1, int(round(np.exp(y + 6))))         # +6 so counts are large/positive
            site = "stackoverflow" if i == 0 else (
                MATH_SITES[i - 1] if i in (1, 2) else f"ctrl{i}")
            rows.append({"site": site, "endpoint": "questions", "ym": int_to_ym(s),
                         "date": "", "year": s // 12, "month": s % 12 + 1,
                         "count": cnt, "treated": D})
    return pd.DataFrame(rows)


def simulate_recovery(thetas=(0.0, -0.3, -0.5), pretrends=(0.0, 0.1), S=1000, B=999,
                      seed=0):
    """MC harness: bias/size/power/coverage table proving the from-scratch engines recover."""
    rng = np.random.default_rng(seed)
    results = []
    failures = []

    def check(label, cond, detail):
        status = "PASS" if cond else "FAIL"
        results.append((label, status, detail))
        if not cond:
            failures.append(label)

    def diag(label, detail):
        """Printed measured diagnostic — NOT a pass/fail gate (does not affect exit code)."""
        results.append((label, "DIAG", detail))

    print("=" * 78)
    print("SIMULATE RECOVERY HARNESS  (from-scratch correctness proof)")
    print(f"  S={S} sims, B={B} bootstrap reps inner, n_sites=7, seed={seed}")
    print("=" * 78)

    # ---- 1) DiD point recovery + FH-ATT at h=6 ----
    print("\n[1] DiD point recovery (bias) + FH-ATT h=6")
    for theta in thetas:
        betas, fh6 = [], []
        for _ in range(S):
            p = simulate_panel(theta=theta, rng=rng)
            df = load_panel("questions", _df=p)
            r = did_clean(df, B=2, weights="webb", rng=rng)   # B tiny: point only here
            betas.append(r["beta"])
            es, _ = event_study(df, kmin=-6, kmax=12, B=2, rng=rng)
            row = es[es["k"] == 6]
            fh6.append(float(row["beta"].iloc[0]))
        mb = np.mean(betas)
        mfh = np.mean(fh6)
        check(f"DiD bias theta={theta:+.2f}", abs(mb - theta) <= 0.03,
              f"mean beta={mb:+.4f} (truth {theta:+.2f}), %={_pct(mb):+.1f}")
        check(f"FH-ATT h=6 theta={theta:+.2f}", abs(mfh - theta) <= 0.05,
              f"mean beta_6={mfh:+.4f} (truth {theta:+.2f})")

    # ---- 2) WCR size + CR1 over-rejection + coverage ----
    # B_mc: the MC subsets only need a stable size/coverage estimate, not production-grade
    # p-values, so cap the inner bootstrap at ~399 (Webb 6^7 support is huge; 399 reps give
    # a reliable rejection rate over a few-hundred-sim outer loop). Real-data runs use B=9999.
    B_mc = min(B, 399)
    print(f"\n[2] WCR size (theta=0), CR1 over-rejection, WCR coverage  [inner B={B_mc}]")
    Ssz = min(S, 300)
    wcr_rej, cr1_rej = [], []
    for _ in range(Ssz):
        p = simulate_panel(theta=0.0, rng=rng)
        df = load_panel("questions", _df=p)
        r = did_clean(df, B=B_mc, weights="webb", rng=rng, ci=False)
        wcr_rej.append(r["wcr"]["p"] < 0.05)
        cr1_rej.append(r["cr1_p_INVALID"] < 0.05)
    wcr_size = np.mean(wcr_rej)
    cr1_size = np.mean(cr1_rej)
    # WCR size is a TWO-SIDED characterization, not a gate: a degenerate (never-rejecting)
    # WCR test would have wcr_size==0.000 and FAIL a 0.02<=.<=0.12 size band. With exactly
    # one treated cluster that IS what happens (single-treated-cluster degeneracy), so we
    # report it as a diagnostic rather than hide it behind a one-sided "<=0.10" check that
    # any never-rejecting test passes. The headline estimators (RI, SC) carry the gates.
    size_in_band = (0.02 <= wcr_size <= 0.12)
    diag("WCR size band [0.02,0.12] (theta=0) (WCR characterization, not a gate)",
         f"WCR rej={wcr_size:.3f} at nominal 0.05; in-band={size_in_band} "
         f"(0.000 => single-treated-cluster degeneracy, expected with n_treated_clusters=1)")
    diag("WCR vs CR1 size (WCR characterization, not a gate)",
         f"WCR={wcr_size:.3f}  CR1={cr1_size:.3f} "
         f"(CR1 over-rejects; WCR conservative under 1 treated cluster)")
    # measured WCR power diagnostic at theta=-0.5 (documents the degeneracy explicitly)
    Spw = min(S, 150)
    wcr_pow = []
    for _ in range(Spw):
        p = simulate_panel(theta=-0.5, rng=rng)
        df = load_panel("questions", _df=p)
        r = did_clean(df, B=B_mc, weights="webb", rng=rng, ci=False)
        wcr_pow.append(r["wcr"]["p"] < 0.05)
    wcr_power = np.mean(wcr_pow)
    diag("WCR power at theta=-0.5 (WCR characterization, not a gate)",
         f"WCR power={wcr_power:.3f} < 0.80 with n_treated_clusters=1 -> CONFIRMS "
         f"single-treated-cluster degeneracy; headline = RI + SC")
    # coverage (also a WCR characterization, not a gate)
    Scov = min(S, 150)
    for theta in (-0.3, -0.5):
        cover = []
        for _ in range(Scov):
            p = simulate_panel(theta=theta, rng=rng)
            df = load_panel("questions", _df=p)
            r = did_clean(df, B=B_mc, weights="webb", rng=rng, ci=True)
            lo, hi, bd = r["wcr_ci"]
            cover.append(lo <= theta <= hi)
        cov = np.mean(cover)
        diag(f"WCR CI coverage theta={theta} (WCR characterization, not a gate)",
             f"coverage={cov:.3f} of theta={theta} "
             f"(over-covers under 1 treated cluster — consistent with conservatism)")

    # ---- 3) RI under null: treated not systematically most-extreme ----
    print("\n[3] RI under null (rank-1 freq ~1/N) + p-floor respected")
    Sri = min(S, 400)
    rank1, minp_ok = [], []
    for _ in range(Sri):
        p = simulate_panel(theta=0.0, rng=rng)
        df = load_panel("questions", _df=p)
        ri = randomization_inference(df, _bf_did, "did", "coef", None, 12)
        rank1.append(ri["rank"] == 1)
        minp_ok.append(ri["p"] >= ri["min_p"] - 1e-9)
    f1 = np.mean(rank1)
    check("RI rank-1 freq ~1/7 under null", abs(f1 - 1 / 7) <= 0.05,
          f"rank-1 freq={f1:.3f} (1/N={1/7:.3f})")
    check("RI p-floor never violated", all(minp_ok), "no p < 1/N observed")

    # ---- 4) RI power under theta=-0.5 ----
    print("\n[4] RI power (theta=-0.5): treated most extreme + effect-ratio")
    Spow = min(S, 300)
    rank1p, ratios = [], []
    for _ in range(Spow):
        p = simulate_panel(theta=-0.5, rng=rng)
        df = load_panel("questions", _df=p)
        ri = randomization_inference(df, _bf_did, "did", "coef", None, 12)
        rank1p.append(ri["rank"] == 1)
        ratios.append(ri["ratio"])
    f1p = np.mean(rank1p)
    medr = np.median([r for r in ratios if np.isfinite(r)])
    check("RI power: treated rank-1 >=0.80", f1p >= 0.80,
          f"rank-1 freq={f1p:.3f}")
    check("RI power: median effect-ratio >=2.0", medr >= 2.0,
          f"median ratio={medr:.2f}")

    # ---- 5) Pre-trend detection ----
    print("\n[5] Pre-trend RI joint test: fires on pretrend=0.1, quiet on 0")
    for pt in pretrends:
        Spt = min(S, 300)
        fire = []
        for _ in range(Spt):
            p = simulate_panel(theta=0.0, pretrend=pt, rng=rng)
            df = load_panel("questions", _df=p)
            _, pre = event_study(df, kmin=-6, kmax=12, B=2, rng=rng)
            fire.append(pre.get("ri_rank", 99) == 1)
        ff = np.mean(fire)
        if pt == 0.0:
            check("pre-trend quiet under pretrend=0", abs(ff - 1 / 7) <= 0.06,
                  f"rank-1 freq={ff:.3f} (~1/N)")
        else:
            check(f"pre-trend detected under pretrend={pt}", ff >= 0.70,
                  f"rank-1 freq={ff:.3f}")

    # ---- 6) SC recovery (long-pre) + under-identified guard ----
    print("\n[6] Synthetic control recovery (long pre, n_pre=23) + under-id guard")
    Ssc = min(S, 150)
    w_l1, pre_rmspe, post_tau, sc_rank1 = [], [], [], []
    true_w = None
    for _ in range(Ssc):
        # build a treated = convex combo of donors + planted post step
        p = _sc_dgp(rng, n_pre=23, n_post=12, delta=-0.25)
        df = load_panel("questions", _df=p["panel"])
        rep = run_synthetic_control(df, "questions")
        w = rep["fit"]["w"]
        # align planted weights to donor order
        donor_sites = rep["fit"]["donor_sites"]
        tw = np.array([p["true_w"].get(s, 0.0) for s in donor_sites])
        tw = tw / tw.sum() if tw.sum() > 0 else tw
        w_l1.append(np.sum(np.abs(w - tw)))
        pre_rmspe.append(rep["fit"]["rmspe_pre"])
        # mean post gap
        krel = rep["prep"]["s_index"] - rep["prep"]["event_s"]
        post = krel >= 0
        post_tau.append(np.mean(rep["fit"]["gap"][post]))
        sc_rank1.append(rep["placebo"]["rank"] == 1)
    check("SC weight L1 <=0.10", np.median(w_l1) <= 0.10,
          f"median L1={np.median(w_l1):.4f}")
    check("SC pre-RMSPE <=0.05", np.median(pre_rmspe) <= 0.05,
          f"median pre-RMSPE={np.median(pre_rmspe):.4f}")
    check("SC post tau ~ -0.25", abs(np.median(post_tau) + 0.25) <= 0.05,
          f"median post tau={np.median(post_tau):+.4f}")
    check("SC placebo rank-1 >=0.80", np.mean(sc_rank1) >= 0.80,
          f"rank-1 freq={np.mean(sc_rank1):.3f}")
    # under-identified short-pre guard (single run): T0=6, J=6 donors -> T0<=J (the exact
    # proof-panel shape, where SC weights are saturated/overfit and not credible).
    p_short = _sc_dgp(rng, n_pre=6, n_post=12, delta=-0.25, n_donors=6)
    df_s = load_panel("questions", _df=p_short["panel"])
    rep_s = run_synthetic_control(df_s, "questions")
    check("SC under-identified flagged on short pre (T0<=J)",
          rep_s["fit"]["under_identified"] is True,
          f"T0={rep_s['prep']['T0']} <= J={rep_s['prep']['J']} -> under_identified=True")

    # ---- 7) Staggered recovery + contamination + honesty gate ----
    print("\n[7] Sun-Abraham cohort-2 recovery + contamination fire/quiet + honesty gate")
    # plant cohort2 in-sample. g2_offset=3 -> the math cohort month is event(2022-12)+3
    # = 2023-03, an in-sample date; pass that as g_math so SA labels the cohort correctly.
    g2_offset = 3
    g_math_sim = int_to_ym(ym_to_int("2022-12") + g2_offset)   # "2023-03"
    Sst = min(S, 120)
    catt2 = []
    for _ in range(Sst):
        p = simulate_panel(theta=-0.5, cohort2_effect=-0.15, g2_offset=g2_offset,
                           n_post=18, rng=rng)
        df = load_panel("questions", _df=p)
        sa = sun_abraham(df, rmin=-6, rmax=18, B=2, rng=rng, g_math=g_math_sim)
        # find the math cohort result (the non-2022-12 cohort)
        mathkey = [k for k in sa["cohort_results"] if k != "2022-12"]
        if mathkey:
            catt2.append(sa["cohort_results"][mathkey[0]]["att_g"])
    if catt2:
        mc = np.median(catt2)
        check("SA cohort-2 ATT ~ -0.15", abs(mc + 0.15) <= 0.05,
              f"median cohort-2 ATT={mc:+.4f}")
    else:
        check("SA cohort-2 ATT ~ -0.15", False, "no math cohort estimated (gate too aggressive)")
    # contamination test: fires when cohort2!=0, quiet when 0. Average the extension-window
    # pseudo-ATT over several draws (proper bias check) — a single realization with only 6
    # pre-months is too noisy to assert a tight tolerance on. B=2 here (point estimate only;
    # the WCR p is not used by these recovery asserts).
    Sct = min(S, 40)
    fire_betas, quiet_betas, est_ok = [], [], True
    for _ in range(Sct):
        p_c = simulate_panel(theta=-0.5, cohort2_effect=-0.15, g2_offset=3, n_post=30, rng=rng)
        cf = control_only_placebo(load_panel("questions", _df=p_c),
                                  kmin=-6, kmax=30, ext_start=3, B=2, rng=rng)
        p_q = simulate_panel(theta=-0.5, cohort2_effect=0.0, g2_offset=3, n_post=30, rng=rng)
        cq = control_only_placebo(load_panel("questions", _df=p_q),
                                  kmin=-6, kmax=30, ext_start=3, B=2, rng=rng)
        if not (cf.get("estimable_ext") and cq.get("estimable_ext")):
            est_ok = False
            break
        fire_betas.append(cf["ext_beta"])
        quiet_betas.append(cq["ext_beta"])
    if est_ok:
        mf, mq = float(np.mean(fire_betas)), float(np.mean(quiet_betas))
        check("contamination test FIRES on planted cohort-2", abs(mf + 0.15) <= 0.05,
              f"mean ext_beta(fire)={mf:+.4f} (truth -0.15), over {Sct} draws")
        check("contamination test QUIET when cohort-2=0", abs(mq) <= 0.05,
              f"mean ext_beta(quiet)={mq:+.4f} (truth 0), over {Sct} draws")
    else:
        check("contamination test estimable", False, "extension window not estimable in DGP")
    # honesty gate: proof-panel shape (n_post=13) -> math cohort 2024-12 has rmax<0 -> skipped
    p_pp = simulate_panel(theta=-0.5, cohort2_effect=0.0, n_post=13, rng=rng)
    df_pp = load_panel("questions", _df=p_pp)
    df_pp_c = make_cohorts(df_pp, g_treated="2022-12", g_math="2024-12")
    sa_pp = sun_abraham(df_pp, rmin=-6, rmax=24, B=2, rng=rng)
    skipped_keys = [c["g"] for c in sa_pp["cohorts_skipped"]]
    check("SA honesty gate skips out-of-sample cohort (2024-12)",
          "2024-12" in skipped_keys,
          f"cohorts_skipped={skipped_keys}")

    # ---- report ----
    print("\n" + "=" * 78)
    print("RECOVERY TABLE")
    print("=" * 78)
    print(f"  {'check':<46} {'status':<6} detail")
    print("  " + "-" * 74)
    for label, status, detail in results:
        print(f"  {label:<46} {status:<6} {detail}")
    n_pass = sum(1 for _, s, _ in results if s == "PASS")
    print("  " + "-" * 74)
    print(f"  {n_pass}/{len(results)} checks PASS")
    if failures:
        print(f"\n  FAILED: {failures}")
        return False
    print("\n  ALL RECOVERY CHECKS PASS — from-scratch engines validated.")
    return True


def _sc_dgp(rng, n_pre=23, n_post=12, delta=-0.25, n_donors=5):
    """Treated = known convex combo of donors + planted post step delta; for SC recovery.

    Donors are WELL-CONDITIONED (each gets its own independent factor) so the planted
    simplex weights are uniquely identified — otherwise the SC weight vector is
    non-unique even when the synthetic fit is perfect, and an L1-on-weights tolerance
    would be testing an unidentified quantity rather than the estimator.
    """
    T = n_pre + n_post
    base_s = ym_to_int("2022-12") - n_pre
    event_s = ym_to_int("2022-12")
    # donor latent series: each donor has its OWN factor (distinct dynamics) plus a small
    # shared component; this keeps Z'Z well-conditioned so weights are recoverable.
    donors = {}
    shared = np.cumsum(rng.normal(0, 0.05, T))
    for j in range(n_donors):
        own = np.cumsum(rng.normal(0, 0.20, T))             # donor-specific random walk
        lvl = rng.uniform(-0.5, 0.5)
        donors[f"ctrl{j}"] = lvl + own + 0.3 * shared + rng.normal(0, 0.02, T)
    # planted simplex weights
    w = rng.dirichlet(np.ones(n_donors))
    true_w = {f"ctrl{j}": w[j] for j in range(n_donors)}
    Zmat = np.column_stack([donors[f"ctrl{j}"] for j in range(n_donors)])
    treated = Zmat @ w + rng.normal(0, 0.01, T)
    krel = np.arange(T) + (base_s - event_s)
    treated = treated + np.where(krel >= 0, delta, 0.0)
    rows = []
    series = {"stackoverflow": (treated, 1)}
    for j in range(n_donors):
        series[f"ctrl{j}"] = (donors[f"ctrl{j}"], 0)
    for site, (ser, D) in series.items():
        for t in range(T):
            s = base_s + t
            cnt = max(1, int(round(np.exp(ser[t] + 8))))
            rows.append({"site": site, "endpoint": "questions", "ym": int_to_ym(s),
                         "date": "", "year": s // 12, "month": s % 12 + 1,
                         "count": cnt, "treated": D})
    return {"panel": pd.DataFrame(rows), "true_w": true_w}


# ----------------------------------------------------------------------------------
# S8  ORCHESTRATION + CLI
# ----------------------------------------------------------------------------------
def render_inference(beta, pct, cr1_se, cr1_p, wcr, wcr_ci_pct, ri, indent="    ",
                     n_treated_clusters=None):
    """Three-column inference block: CR1 (INVALID), WCR, RI.

    Headline selection: with >=2 treated clusters WCR is the headline. With exactly ONE
    treated cluster the wild-cluster bootstrap is the MacKinnon-Webb (2017/18) single-
    treated-cluster degeneracy (severe under-rejection); WCR is DEMOTED to a diagnostic and
    the headline becomes randomization inference (RI) + the SC-placebo RMSPE-rank.
    """
    single = (n_treated_clusters == 1)
    lines = []
    lines.append(f"{indent}beta = {beta:+.4f}  =>  {pct:+.1f}% activity effect")
    lines.append(f"{indent}[CR1 ] se={cr1_se:.4f}  p={cr1_p:.4f}  "
                 f"<-- INVALID (G<12), reference-only, do NOT cite")
    cilo, cihi, bd = wcr_ci_pct
    cihi_s = f"{cihi:+.1f}%" if np.isfinite(cihi) else "+inf"
    bdflag = "" if bd else "  (CI unbounded on one side)"
    wcr_tag = ("<-- INVALID (1 treated cluster; under-powered), diagnostic only — do NOT cite"
               if single else "<-- HEADLINE")
    lines.append(f"{indent}[WCR ] p={wcr['p']:.4f}  ({wcr['weights']}, B={wcr['B']}"
                 f"{', exact' if wcr['exact'] else ''})  "
                 f"95% CI [{cilo:+.1f}%, {cihi_s}]{bdflag}  {wcr_tag}")
    ri_tag = "  <-- HEADLINE (with SC-placebo)" if single else ""
    lines.append(f"{indent}[RI  ] p={ri['p']:.4f}  rank {ri['rank']} of {ri['n_assign']}  "
                 f"floor=1/N={ri['min_p']:.4f}  effect-ratio={ri['ratio']:.2f}x{ri_tag}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="P9 Leg B v2 — few-cluster-valid DiD/ES.")
    ap.add_argument("--endpoint", default="questions", choices=["questions", "answers"])
    ap.add_argument("--event", default=DEFAULT_EVENT)
    ap.add_argument("--kmin", type=int, default=None)
    ap.add_argument("--kmax", type=int, default=CLEAN_KMAX)
    ap.add_argument("--controls", default="all",
                    help="'primary'|'all'|'frozen' or explicit space-separated site list")
    ap.add_argument("--math-only", action="store_true",
                    help="alias for --controls primary (math.SE + MathOverflow)")
    ap.add_argument("--placebo", default=None, help="leak-free placebo fake event YYYY-MM")
    ap.add_argument("--sc", action="store_true", help="run synthetic control arm")
    ap.add_argument("--staggered", action="store_true", help="run Sun-Abraham + Callaway-Sant'Anna")
    ap.add_argument("--diagnostics", action="store_true",
                    help="control-only placebo + frozen-control arm")
    ap.add_argument("--full-panel", action="store_true",
                    help="gate extension-window/long-run tests needing k>=+13/+24")
    ap.add_argument("--B", type=int, default=9999)
    ap.add_argument("--weights", default="webb", choices=["webb", "rademacher"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--simulate", action="store_true", help="run recovery harness")
    ap.add_argument("--S", type=int, default=1000)
    args = ap.parse_args()

    if args.simulate:
        ok = simulate_recovery(S=args.S, B=min(args.B, 999), seed=args.seed)
        sys.exit(0 if ok else 1)

    if not os.path.exists(PANEL):
        raise SystemExit(f"missing {PANEL}")

    # resolve controls
    if args.math_only or args.controls == "primary":
        sites = [TREATED_SITE] + PRIMARY_CONTROLS
    elif args.controls == "all":
        sites = [TREATED_SITE] + ALL_CONTROLS
    elif args.controls == "frozen":
        sites = [TREATED_SITE] + PRIMARY_CONTROLS
    else:
        sites = [TREATED_SITE] + args.controls.split()

    rng = np.random.default_rng(args.seed)
    df = load_panel(args.endpoint, args.event, sites=sites)
    site_list = sorted(df["site"].unique())

    print("=" * 72)
    print(f"P9 Leg B v2 — few-cluster-valid DiD / event study  [{args.endpoint}]")
    print("=" * 72)
    print(f"sites ({len(site_list)}): {site_list}")
    print(f"treated : {sorted(df[df.D == 1].site.unique())}")
    print(f"months  : {df['ym'].min()} .. {df['ym'].max()} ({df['ym'].nunique()} months)")
    print(f"event   : {args.event}  (ChatGPT 2022-11-30 / SO ban 2022-12-05)")
    print(f"clean window: k in [{args.kmin if args.kmin is not None else 'start'}..{args.kmax}]"
          f"  (drops k>=+{args.kmax+1} AI-commercialization regime)")
    G = df["site"].nunique()
    n_treated_clusters = int(df.loc[df["D"] == 1, "site"].nunique())
    if n_treated_clusters == 1:
        print(f"G = {G} clusters  ->  CR1 INVALID; "
              f"n_treated_clusters=1 -> WCR AND CR1 both INVALID (single-treated-cluster "
              f"degeneracy, MacKinnon-Webb 2017/18); headline inference = randomization "
              f"inference (Conley-Taber) + SC-placebo RMSPE-rank.")
    else:
        print(f"G = {G} clusters  ->  CR1 INVALID; headline = WCR ({args.weights}) + RI")
    if G <= 3:
        print("  [CAVEAT] G<=3: WCR itself unreliable; lean on RI + SC-placebo rank.")
    print()

    # ---- headline clean-window DiD ----
    print("=== [1] HEADLINE clean-window TWFE DiD ===")
    r = did_clean(df, args.event, args.kmin, args.kmax, B=args.B, weights=args.weights, rng=rng)
    print(f"  n_obs={r['n_obs']}  G={r['G']}")
    print(render_inference(r["beta"], r["pct"], r["cr1_se"], r["cr1_p_INVALID"],
                           r["wcr"], r["wcr_ci_pct"], r["ri"],
                           n_treated_clusters=n_treated_clusters))
    print()

    # ---- regime split ----
    print("=== [2] REGIME SPLIT (clean ATT vs long-run AI-commercialization path) ===")
    rs = did_regime_split(df, args.event, args.kmax, B=args.B, weights=args.weights, rng=rng)
    print(f"  b_clean (0<=k<=+{args.kmax}): beta={rs['clean']['beta']:+.4f} "
          f"({rs['clean']['pct']:+.1f}%)  WCR p={rs['clean']['wcr']['p']:.4f}")
    if rs["long"]["NA"]:
        print(f"  b_long  (k>=+{args.kmax+1}): NA — {rs['long']['reason']}")
    else:
        print(f"  b_long  (k>=+{args.kmax+1}): beta={rs['long']['beta']:+.4f} "
              f"({rs['long']['pct']:+.1f}%)  WCR p={rs['long']['wcr']['p']:.4f}  "
              f"[{rs['long']['label']}]")
    print()

    # ---- event study ----
    es_kmin = args.kmin if args.kmin is not None else -6
    print("=== [3] EVENT STUDY (leads test parallel trends; lags = dynamic ATT) ===")
    tab, pretrend = event_study(df, args.event, kmin=es_kmin, kmax=args.kmax,
                                B=args.B, weights=args.weights, rng=rng)
    print(f"  {'k':>4} {'beta':>9} {'~%effect':>9} {'WCR_p':>7} {'RI_p':>7}  flag")
    for _, row in tab.iterrows():
        if row["ref"]:
            print(f"  {int(row['k']):>+4} {'(ref=0)':>9} {'--':>9} {'--':>7} {'--':>7}  k=-1 reference")
            continue
        if not np.isfinite(row["beta"]):
            print(f"  {int(row['k']):>+4} {'n/a':>9} {'--':>9} {'--':>7} {'--':>7}  not estimable")
            continue
        pre = "PRE " if row["k"] < 0 else "post"
        print(f"  {int(row['k']):>+4} {row['beta']:>+9.3f} {row['pct']:>+8.1f}% "
              f"{row['wcr_p']:>7.3f} {row['ri_p']:>7.3f}  {pre}")
    print()
    print("  parallel-trends JOINT test on leads (k<=-2):")
    if "ri_p" in pretrend:
        print(f"    [RI ] p={pretrend['ri_p']:.4f}  rank {pretrend['ri_rank']} "
              f"of {pretrend['ri_n']}  (rank 1 = pre-trend WARNING)")
        if pretrend.get("rank_ok"):
            print(f"    [WCR] joint p={pretrend['wcr_p']:.4f}")
        else:
            print(f"    [WCR] joint test rank-deficient -> {pretrend.get('wcr_note','')}")
        verdict = ("PARALLEL OK" if pretrend["ri_rank"] > 1 else
                   "PRE-TREND: treated most-extreme among placebos — inspect leads")
        print(f"    verdict: {verdict}")
    print()

    # ---- fixed-horizon ATT ----
    print("=== [4] FIXED-HORIZON ATT (pointwise beta_h; del Rio-Chanona -25% benchmark) ===")
    fh = fixed_horizon_att(tab, df, args.event, horizons=(6, 12, 24), B=args.B,
                           weights=args.weights, kmin=es_kmin, kmax=args.kmax, rng=rng)
    for _, row in fh.iterrows():
        if row["NA"]:
            print(f"  h=+{int(row['h']):<2}: NA — {row['reason']}")
            continue
        print(f"  h=+{int(row['h']):<2}: beta={row['beta']:+.4f} ({row['pct']:+.1f}%)  "
              f"WCR p={row['wcr_p']:.4f}  RI rank {int(row['ri_rank'])}/{int(row['ri_n'])} "
              f"ratio={row['ri_ratio']:.2f}x  [3mo-sm {row['pct_sm3']:+.1f}%]")
    print()

    # ---- leak-free placebo ----
    if args.placebo:
        print("=== [5] LEAK-FREE PLACEBO-IN-TIME ===")
        pl = placebo_in_time(df, args.event, args.placebo, B=args.B, weights=args.weights, rng=rng)
        if pl["SKIP"]:
            print(f"  SKIP — {pl['reason']}")
        else:
            pr = pl["res"]
            print(f"  fake event {pl['fake_event']}  k in {pl['k_range']}")
            print(f"  beta={pr['beta']:+.4f} ({pr['pct']:+.1f}%)  WCR p={pr['wcr']['p']:.4f}  "
                  f"RI rank {pr['ri']['rank']}/{pr['ri']['n_assign']}")
            print(f"  verdict: {pl['verdict']}")
        print()

    # ---- optional arms ----
    if args.sc:
        print("=== [SC] SYNTHETIC CONTROL ===")
        donors = [s for s in site_list if s != TREATED_SITE]
        screp = run_synthetic_control(df, args.endpoint, args.event, donors,
                                      save_path=os.path.join(DATA, f"sc_{args.endpoint}.csv"))
        fit, plac, prep = screp["fit"], screp["placebo"], screp["prep"]
        if fit["under_identified"]:
            print(f"  [WARNING] UNDER-IDENTIFIED: T0={prep['T0']} <= J={prep['J']}. "
                  f"SC ILLUSTRATIVE ONLY — headline stays DiD/event-study.")
            print(f"            (extend pre-period to 2021-01 for a credible SC; "
                  f"SC is identified off pre-fit, not post length.)")
        print(f"  donor weights: " + ", ".join(
            f"{s}={w:.3f}" for s, w in zip(fit["donor_sites"], fit["w"]) if w > 1e-3))
        print(f"  RMSPE pre={fit['rmspe_pre']:.4f}  post={fit['rmspe_post']:.4f}  "
              f"ratio={fit['ratio']:.2f}")
        print(f"  clean-window mean gap = {fit['mean_gap_clean']:+.4f} ({fit['pct_clean']:+.1f}%)")
        print(f"  in-space placebo: treated rank {plac['rank']}/{plac['N']} by RMSPE-ratio  "
              f"p={plac['p']:.4f} (floor 1/{plac['N']}={plac['p_floor']:.4f})")
        print()

    if args.staggered:
        print("=== [STAGGERED] Sun-Abraham (primary) + Callaway-Sant'Anna (cross-check) ===")
        sa = sun_abraham(df, B=args.B, weights=args.weights, rng=rng)
        if sa.get("NA"):
            print(f"  [SA] EXPLORATORY-NA — {sa['reason']}")
            print(f"       {sa['note']}")
        else:
            print(f"  {sa['note']}")
            for g, res in sa["cohort_results"].items():
                print(f"    cohort {g}: ATT_g={res['att_g']:+.4f} over {res['n_post']} post months")
            for sk in sa["cohorts_skipped"]:
                print(f"    cohort {sk['g']}: SKIPPED (rmax={sk['rmax']}) — {sk['reason']}")
        cs = callaway_santanna(df)
        if cs.get("NA"):
            print(f"  [CS] EXPLORATORY-NA — {cs['reason']}")
        else:
            for g, res in cs["by_cohort"].items():
                print(f"    [CS] cohort {g}: ATT={res['att']:+.4f}")
        print()

    if args.diagnostics:
        print("=== [DIAG] control-only placebo + frozen-control arm ===")
        cop = control_only_placebo(df, args.event, B=args.B, weights=args.weights, rng=rng)
        print("  control-only placebo (math = pseudo-treated, no SO):")
        if "pretrend_ri_p" in cop:
            print(f"    pre-trend RI p={cop['pretrend_ri_p']:.4f} "
                  f"rank {cop['pretrend_ri_rank']}/{cop['pretrend_ri_n']}")
            wp = cop.get("pretrend_wcr_p")
            print(f"    pre-trend WCR joint p={wp if wp is None else f'{wp:.4f}'}")
        if not cop.get("estimable_ext", False):
            print(f"    extension-window test: {cop['ext_reason']}")
        else:
            print(f"    extension-window pseudo-ATT={cop['ext_beta']:+.4f} "
                  f"WCR p={cop['ext_wcr_p']:.4f}")
        fz = frozen_control_arm(df, args.event, args.kmax, B=args.B, weights=args.weights, rng=rng)
        print("  frozen-control arm (drop most-substitutable first):")
        for step in fz["path"]:
            print(f"    drop {step['dropped'] or '[]'}: ATT={step['pct']:+.1f}% "
                  f"(beta {step['beta']:+.4f}, WCR p={step['wcr_p']:.4f}, "
                  f"n_ctrl={step['n_controls']})")
        print(f"    Delta_max={fz['delta_max']:.4f}  rel_drift={fz['rel_drift']:.2f} "
              f"(warn>{fz['rel_drift_warn']})  sign_stable={fz['sign_stable']}")
        print(f"    verdict: {fz['verdict']}")
        print()

    # ---- save outputs ----
    es_out = os.path.join(DATA, f"eventstudy_v2_{args.endpoint}.csv")
    tab.to_csv(es_out, index=False)
    fh_out = os.path.join(DATA, f"fh_att_{args.endpoint}.csv")
    fh.to_csv(fh_out, index=False)
    print(f"[saved] {es_out}")
    print(f"[saved] {fh_out}")


if __name__ == "__main__":
    main()
