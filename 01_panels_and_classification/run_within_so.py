"""
P9 Leg B — WITHIN-SO DiD: do GENERATION-type questions fall more than VERIFICATION-type
after ChatGPT? Identifies the generation-vs-verification mechanism INSIDE Stack Overflow,
so the network-wide collapse (which sank the cross-site design) is absorbed by month FE.

Design (reads so_tag_panel.csv from fetch_so_tags.py):
  unit      = co-tag (python;<cotag>), 15 of them: 8 GENERATION, 7 VERIFICATION
  outcome   = y = log(monthly question count)
  treated   = gen = 1 if the cotag is a GENERATION type (more AI-substitutable)
  event     = 2022-12 (first full month after ChatGPT 2022-11-30); post = 1[k>=0]
  DiD       : y_it = β·(gen×post) + cotag_FE + month_FE + ε
              gen and post main effects are absorbed by the two-way FE; β is the within-SO
              differential — how much MORE generation questions fell vs verification, net of
              the common (network-wide) monthly shock. β<0 ⇒ consistent with the mother thesis.

Why inference finally works here (vs the 1-treated-cluster cross-site dead end):
  15 units split 8/7 ⇒ RANDOMIZATION INFERENCE by relabeling which cotags are "generation"
  has real power. The panel is BALANCED (every cotag has every month) ⇒ two-way FE demeaning
  is one-shot exact (x_dd = x − mean_cotag − mean_month + grand_mean), so RI is fast & exact.

Inference reported:
  - cotag-clustered robust SE (15 clusters; better than 3 but still read RI as primary)
  - exact-ish RI: relabel 8-of-15 cotags as "generation", recompute β, two-sided p
  - event study: gen×k coefficients (leads test parallel pre-trends; lags = dynamic effect)
  - robustness: drop sparse cotags (mean monthly count < --min-mean)

⚠ The gen/ver co-tag split is a hand-curated PROXY for AI-substitutability (see fetch_so_tags
  docstring). This is a probe; the rigorous version classifies question TEXT via the SE dump.

Usage:
  python run_within_so.py
  python run_within_so.py --kmin -18 --kmax 12      # clean window, long leads
  python run_within_so.py --min-mean 50             # drop sparse cotags
  python run_within_so.py --B 4999 --seed 0
"""
import os
import argparse
import itertools
import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
PANEL = os.path.join(DATA, "so_tag_panel.csv")
EVENT = "2022-12"


def ym_to_int(ym):
    y, m = (int(x) for x in str(ym).split("-"))
    return y * 12 + (m - 1)


def load(min_mean=0.0, kmin=None, kmax=None):
    df = pd.read_csv(PANEL)
    e = ym_to_int(EVENT)
    df["s"] = df["ym"].map(ym_to_int)
    df["k"] = df["s"] - e
    if kmin is not None:
        df = df[df["k"] >= kmin]
    if kmax is not None:
        df = df[df["k"] <= kmax]
    # drop cotags that are ever zero (log undefined) or too sparse on average
    bad = set()
    for ct, g in df.groupby("cotag"):
        if (g["count"] <= 0).any() or g["count"].mean() < min_mean:
            bad.add(ct)
    if bad:
        print(f"  [drop] sparse/zero cotags removed: {sorted(bad)}")
        df = df[~df["cotag"].isin(bad)].copy()
    df["y"] = np.log(df["count"].astype(float))
    df["gen"] = (df["group"] == "generation").astype(int)
    df["post"] = (df["k"] >= 0).astype(int)
    # keep only cotags present in ALL retained months (balance for one-shot demeaning)
    nmonths = df["ym"].nunique()
    counts = df.groupby("cotag")["ym"].nunique()
    keep = counts[counts == nmonths].index
    if len(keep) < df["cotag"].nunique():
        print(f"  [balance] keeping {len(keep)}/{df['cotag'].nunique()} cotags present in all {nmonths} months")
        df = df[df["cotag"].isin(keep)].copy()
    return df.sort_values(["cotag", "s"]).reset_index(drop=True)


def twoway_demean(v, cot_idx, ym_idx, n_cot, n_ym):
    """One-shot exact two-way demeaning for a BALANCED panel."""
    grand = v.mean()
    cot_mean = np.zeros(n_cot)
    np.add.at(cot_mean, cot_idx, v)
    cot_mean /= np.bincount(cot_idx, minlength=n_cot)
    ym_mean = np.zeros(n_ym)
    np.add.at(ym_mean, ym_idx, v)
    ym_mean /= np.bincount(ym_idx, minlength=n_ym)
    return v - cot_mean[cot_idx] - ym_mean[ym_idx] + grand


def did_beta(y_dd, x, cot_idx, ym_idx, n_cot, n_ym):
    x_dd = twoway_demean(x, cot_idx, ym_idx, n_cot, n_ym)
    denom = float(x_dd @ x_dd)
    if denom <= 1e-12:
        return np.nan, None, None
    beta = float(y_dd @ x_dd) / denom
    return beta, x_dd, denom


def did_multi(y_dd, raw_cols, cot_idx, ym_idx, n_cot, n_ym):
    """Multivariate demeaned OLS. Returns the coefficient vector for the demeaned
    raw_cols (first column = the object of interest, gen×post)."""
    Xd = np.column_stack([twoway_demean(c, cot_idx, ym_idx, n_cot, n_ym) for c in raw_cols])
    try:
        beta = np.linalg.solve(Xd.T @ Xd, Xd.T @ y_dd)
    except np.linalg.LinAlgError:
        beta = np.linalg.lstsq(Xd, y_dd, rcond=None)[0]
    return beta, Xd


def cluster_se(y_dd, x_dd, denom, resid, cot_idx, n_cot, kparams):
    """CR1 cluster-robust SE on cotag for the single demeaned regressor."""
    G = n_cot
    meat = 0.0
    for g in range(n_cot):
        sel = cot_idx == g
        sg = float(x_dd[sel] @ resid[sel])
        meat += sg * sg
    n = len(resid)
    adj = (G / (G - 1.0)) * ((n - 1.0) / max(n - kparams, 1.0))
    var = adj * meat / (denom ** 2)
    return np.sqrt(var), G


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kmin", type=int, default=None)
    ap.add_argument("--kmax", type=int, default=None)
    ap.add_argument("--min-mean", type=float, default=0.0)
    ap.add_argument("--B", type=int, default=4999, help="RI relabelings (exact if <= C(n,k))")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    if not os.path.exists(PANEL):
        raise SystemExit(f"missing {PANEL} — run fetch_so_tags.py first")

    df = load(min_mean=args.min_mean, kmin=args.kmin, kmax=args.kmax)
    cotags = sorted(df["cotag"].unique())
    yms = sorted(df["ym"].unique())
    n_cot, n_ym = len(cotags), len(yms)
    cot_ix = {c: i for i, c in enumerate(cotags)}
    ym_ix = {m: i for i, m in enumerate(yms)}
    cot_idx = df["cotag"].map(cot_ix).to_numpy()
    ym_idx = df["ym"].map(ym_ix).to_numpy()
    y = df["y"].to_numpy()
    post = df["post"].to_numpy().astype(float)

    # cotag -> group (gen=1)
    gen_of_cotag = (df.drop_duplicates("cotag").set_index("cotag")["group"] == "generation").astype(int)
    gen_of_cotag = gen_of_cotag.reindex(cotags).to_numpy()
    n_gen = int(gen_of_cotag.sum())

    print("=" * 72)
    print("P9 Leg B — WITHIN-SO DiD (generation vs verification questions)")
    print("=" * 72)
    print(f"cotags ({n_cot}): {n_gen} generation, {n_cot - n_gen} verification")
    print(f"  GEN: {[c for c in cotags if gen_of_cotag[cot_ix[c]]==1]}")
    print(f"  VER: {[c for c in cotags if gen_of_cotag[cot_ix[c]]==0]}")
    print(f"months  : {yms[0]} .. {yms[-1]} ({n_ym})   event={EVENT}  n_obs={len(df)}")
    kwin = f"[{args.kmin if args.kmin is not None else 'start'}..{args.kmax if args.kmax is not None else 'end'}]"
    print(f"k window : {kwin}")
    print()

    gen_obs = gen_of_cotag[cot_idx].astype(float)
    x = gen_obs * post                        # gen×post DiD regressor
    y_dd = twoway_demean(y, cot_idx, ym_idx, n_cot, n_ym)
    beta, x_dd, denom = did_beta(y_dd, x, cot_idx, ym_idx, n_cot, n_ym)
    resid = y_dd - beta * x_dd
    kparams = n_cot + n_ym - 1 + 1
    se, G = cluster_se(y_dd, x_dd, denom, resid, cot_idx, n_cot, kparams)
    pct = (np.exp(beta) - 1) * 100

    print("=== [1] HEADLINE within-SO DiD  (β = gen×post) ===")
    print(f"  beta = {beta:+.4f}   => generation questions {pct:+.1f}% vs verification, post-ChatGPT")
    print(f"  [cluster] SE={se:.4f} (G={G} cotag clusters)  t={beta/se:+.2f}  "
          f"p≈{2*(1-stats.norm.cdf(abs(beta/se))):.4f}  (G small — read RI as primary)")

    # ---- randomization inference: relabel which cotags are "generation" ----
    rng = np.random.default_rng(args.seed)
    all_splits = list(itertools.combinations(range(n_cot), n_gen))
    exact = len(all_splits) <= args.B
    if exact:
        splits = all_splits
    else:
        seen, splits = set(), []
        while len(splits) < args.B:
            s = tuple(sorted(rng.choice(n_cot, size=n_gen, replace=False)))
            if s not in seen:
                seen.add(s); splits.append(s)
    ge = 0
    for s in splits:
        lab = np.zeros(n_cot); lab[list(s)] = 1.0
        xb = lab[cot_idx] * post
        b, _, _ = did_beta(y_dd, xb, cot_idx, ym_idx, n_cot, n_ym)
        if np.isfinite(b) and abs(b) >= abs(beta) - 1e-12:
            ge += 1
    p_ri = ge / len(splits)
    print(f"  [RI] {'EXACT' if exact else f'{len(splits)} random'} relabelings of {n_gen}-of-{n_cot} "
          f"as generation: two-sided p = {p_ri:.4f}")
    print(f"       (real β is {'MORE' if p_ri<0.1 else 'NOT clearly more'} extreme than relabeling null)")
    print()

    # ---- [1b] PRE-TREND-ROBUST DiD: net out a GEN-specific linear trend ----
    # month_FE absorbs the common (network-wide) trend; gen×t_c is GEN's OWN linear
    # deviation; gen×post is then the level JUMP net of that GEN trend. If the jump
    # survives, the post drop is not just pre-existing GEN decline extrapolated forward.
    tc = df["k"].to_numpy().astype(float)
    tc = tc - tc.mean()
    x_post = gen_obs * post
    x_trend = gen_obs * tc
    bvec, _ = did_multi(y_dd, [x_post, x_trend], cot_idx, ym_idx, n_cot, n_ym)
    beta_dt, slope_dt = float(bvec[0]), float(bvec[1])
    pct_dt = (np.exp(beta_dt) - 1) * 100
    ge2 = 0
    for s in splits:
        lab = np.zeros(n_cot); lab[list(s)] = 1.0
        labo = lab[cot_idx]
        bv, _ = did_multi(y_dd, [labo * post, labo * tc], cot_idx, ym_idx, n_cot, n_ym)
        if np.isfinite(bv[0]) and abs(bv[0]) >= abs(beta_dt) - 1e-12:
            ge2 += 1
    p_ri_dt = ge2 / len(splits)
    print("=== [1b] PRE-TREND-ROBUST DiD (gen×post, controlling a GEN-specific linear trend) ===")
    print(f"  GEN own linear trend = {slope_dt:+.4f} log-pts/month (this is what we net out)")
    print(f"  detrended beta = {beta_dt:+.4f}  => {pct_dt:+.1f}% level jump net of GEN trend  "
          f"(raw was {beta:+.4f})")
    print(f"  [RI] two-sided p = {p_ri_dt:.4f}   (raw RI p was {p_ri:.4f})")
    surv = (abs(beta_dt) > 0.15) and (p_ri_dt < 0.10)
    print(f"  VERDICT: post effect {'SURVIVES' if surv else 'does NOT clearly survive'} "
          f"pre-trend control")
    print()

    # ---- event study: gen×k ----
    print("=== [2] EVENT STUDY (gen×k; leads test parallel pre-trends, ref k=-1) ===")
    ks = sorted(df["k"].unique())
    print(f"  {'k':>4} {'beta':>9} {'~%diff':>9}  flag")
    es_rows = []
    for kk in ks:
        if kk == -1:
            print(f"  {kk:>+4} {'(ref)':>9} {'--':>9}  ref")
            es_rows.append({"k": kk, "beta": 0.0, "pct": 0.0, "ref": True})
            continue
        xk = gen_obs * (df["k"].to_numpy() == kk).astype(float)
        bk, _, _ = did_beta(y_dd, xk, cot_idx, ym_idx, n_cot, n_ym)
        pk = (np.exp(bk) - 1) * 100 if np.isfinite(bk) else np.nan
        tag = "PRE " if kk < 0 else "post"
        print(f"  {kk:>+4} {bk:>+9.3f} {pk:>+8.1f}%  {tag}")
        es_rows.append({"k": kk, "beta": bk, "pct": pk, "ref": False})
    pre = [r for r in es_rows if r["k"] < -1 and not r["ref"]]
    if pre:
        mx = max(abs(r["beta"]) for r in pre)
        print(f"\n  max |pre-trend gen×k| (k<=-2) = {mx:.3f}  "
              f"({'flat ✓' if mx < abs(beta)/2 else 'inspect'})")
    # ---- [2b] HONEST pre-trend extrapolation: counterfactual = leads' own linear trend ----
    leads = [(r["k"], r["beta"]) for r in es_rows
             if r["k"] <= -2 and not r["ref"] and np.isfinite(r["beta"])]
    if len(leads) >= 3:
        lk = np.array([k for k, _ in leads], float)
        lb = np.array([b for _, b in leads], float)
        a, b = np.linalg.lstsq(np.column_stack([np.ones_like(lk), lk]), lb, rcond=None)[0]
        posts = [(r["k"], r["beta"]) for r in es_rows if r["k"] >= 0 and np.isfinite(r["beta"])]
        det = [(k, bb - (a + b * k)) for k, bb in posts]
        late = [d for k, d in det if k >= 12]
        mean_det = float(np.mean([d for _, d in det])) if det else float("nan")
        mean_late = float(np.mean(late)) if late else float("nan")
        print("=== [2b] HONEST pre-trend extrapolation (counterfactual = leads' linear trend) ===")
        print(f"  leads linear fit: intercept={a:+.3f}, slope={b:+.4f}/month "
              f"(projected forward as the no-ChatGPT counterfactual)")
        print(f"  mean detrended post effect (all post) = {mean_det:+.3f} "
              f"({(np.exp(mean_det)-1)*100:+.1f}%)")
        print(f"  mean detrended LATE post (k>=+12)      = {mean_late:+.3f} "
              f"({(np.exp(mean_late)-1)*100:+.1f}%)")
        print()

    out = os.path.join(DATA, "within_so_eventstudy.csv")
    pd.DataFrame(es_rows).to_csv(out, index=False)
    print(f"\n[saved] {out}")


if __name__ == "__main__":
    main()
