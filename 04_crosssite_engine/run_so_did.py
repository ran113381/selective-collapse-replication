"""
P9 Leg B — difference-in-differences / event study on Stack Exchange activity.

Hypothesis (bifurcation, lemons pole):
  The ChatGPT release (2022-11-30) + the SO AI-answer BAN (2022-12-05) is a discrete
  enforcement shock to a VOLUNTARY commons. Treated = English Stack Overflow (full
  early-ChatGPT exposure); controls = sites with weaker early exposure (Russian/
  Portuguese/Spanish SO, math.SE, MathOverflow). Prediction: treated participation
  (questions, and answers) falls sharply RELATIVE to controls, starting at the event,
  with flat pre-trends.

Specs:
  (1) Two-way FE DiD on log(count):
        log(count_{i,t}) = beta * (treated_i * post_t) + alpha_i + tau_t + eps
      post_t = 1 for months >= event (default 2022-12). beta = average log-points
      effect (approx % drop). SE clustered by site, and wild-cluster note for few
      clusters.
  (2) Event study (leads/lags): replace post with month dummies relative to the event;
        log(count_{i,t}) = sum_k beta_k * (treated_i * 1{t = event+k}) + alpha_i + tau_t
      k<0 coefficients test PARALLEL TRENDS (should be ~0); k>=0 trace the dynamic drop.
      Reference period k = -1 (month before the event) is omitted.
  (3) Robustness: drop Russian control (Russia-Ukraine confound); restrict controls to
      math.SE + MathOverflow (English, expert-gated, low LLM substitutability); per-site
      log-linear trend break (placebo at a fake event date).

This reads legB/data/so_monthly_panel.csv (produced by fetch_so_activity.py). It runs
whatever sites/months are present, so it is usable on the 2-site proof panel and on the
full panel later.

Usage:
  python run_so_did.py
  python run_so_did.py --endpoint questions --event 2022-12 --drop-russian
  python run_so_did.py --placebo 2022-03      # falsification: fake event, expect ~0
"""
import os
import argparse
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
PANEL = os.path.join(DATA, "so_monthly_panel.csv")

# event = first FULL month after ChatGPT(2022-11-30)/SO ban(2022-12-05): 2022-12.
DEFAULT_EVENT = "2022-12"


def ym_to_int(ym):
    y, m = (int(x) for x in str(ym).split("-"))
    return y * 12 + (m - 1)


def load(endpoint, drop_russian=False, controls_only=None):
    df = pd.read_csv(PANEL)
    df = df[df["endpoint"] == endpoint].copy()
    if drop_russian:
        df = df[df["site"] != "ru.stackoverflow"].copy()
    if controls_only is not None:
        keep = set(controls_only) | {"stackoverflow"}
        df = df[df["site"].isin(keep)].copy()
    df["t"] = df["ym"].map(ym_to_int)
    df["log_count"] = np.log(df["count"].astype(float))
    df["treated"] = df["treated"].astype(int)
    return df


def _fit(formula, d):
    """OLS with site-clustered SE when >=3 clusters, else HC1 robust.

    With only 2 clusters the cluster-robust variance is degenerate (and the small-G
    correction divides by zero), so we fall back to HC1 and flag it. The honest fix is
    a wild-cluster bootstrap / randomization inference on the full multi-site panel.
    """
    base = smf.ols(formula, data=d)
    n_clusters = d["site"].nunique()
    if n_clusters >= 3:
        return base.fit(cov_type="cluster",
                        cov_kwds={"groups": d["site"]}), "cluster", n_clusters
    return base.fit(cov_type="HC1"), "HC1(<3 clusters)", n_clusters


def did(df, event):
    """Two-way FE DiD, SE clustered by site (HC1 fallback if <3 clusters)."""
    e = ym_to_int(event)
    d = df.copy()
    d["post"] = (d["t"] >= e).astype(int)
    d["did"] = d["treated"] * d["post"]
    # absorb site + month FE via categorical dummies; cluster by site
    m, cov, _ = _fit("log_count ~ did + C(site) + C(ym)", d)
    b = m.params["did"]
    se = m.bse["did"]
    p = m.pvalues["did"]
    pct = (np.exp(b) - 1) * 100
    n_clusters = d["site"].nunique()
    return {
        "beta": float(b), "se": float(se), "p": float(p),
        "pct_effect": float(pct), "n_obs": int(m.nobs),
        "n_clusters": int(n_clusters), "cov": cov,
        "ci95_pct": ((np.exp(b - 1.96 * se) - 1) * 100,
                     (np.exp(b + 1.96 * se) - 1) * 100),
    }


def event_study(df, event, kmin=-6, kmax=12):
    """Leads/lags relative to event; reference k=-1. Returns coef table."""
    e = ym_to_int(event)
    d = df.copy()
    d["k"] = d["t"] - e
    d = d[(d["k"] >= kmin) & (d["k"] <= kmax)].copy()
    # build treated x relative-month dummies, omit k=-1 as reference
    terms = []
    for k in range(kmin, kmax + 1):
        if k == -1:
            continue
        name = f"L{abs(k)}" if k < 0 else f"F{k}"
        d[name] = ((d["k"] == k) & (d["treated"] == 1)).astype(int)
        terms.append(name)
    formula = "log_count ~ " + " + ".join(terms) + " + C(site) + C(ym)"
    m, _cov, _nc = _fit(formula, d)
    rows = []
    for k in range(kmin, kmax + 1):
        if k == -1:
            rows.append({"k": k, "coef": 0.0, "se": 0.0, "ref": True})
            continue
        name = f"L{abs(k)}" if k < 0 else f"F{k}"
        rows.append({"k": k, "coef": float(m.params[name]),
                     "se": float(m.bse[name]), "ref": False})
    tab = pd.DataFrame(rows).sort_values("k").reset_index(drop=True)
    # parallel-trends joint test: all leads (k <= -2) == 0
    leads = [f"L{abs(k)}" for k in range(kmin, -1)]  # kmin..-2 (-1 is the omitted ref)
    pt_p = None
    if leads:
        hyp = ", ".join(f"{n} = 0" for n in leads)
        try:
            ft = m.f_test(hyp).pvalue
            pt_p = float(ft) if np.isfinite(ft) else None
        except Exception:
            pt_p = None
    return tab, pt_p, m


def fmt_es(tab, pt_p):
    lines = ["  k   coef(log)   ~%effect    se        flag"]
    for _, r in tab.iterrows():
        if r["ref"]:
            lines.append(f"  {int(r['k']):+d}    (ref=0)        --        --     k=-1 reference")
            continue
        pct = (np.exp(r["coef"]) - 1) * 100
        sig = ""
        if r["se"] > 0:
            z = r["coef"] / r["se"]
            if abs(z) > 2.58: sig = "***"
            elif abs(z) > 1.96: sig = "**"
            elif abs(z) > 1.64: sig = "*"
        pre = "PRE " if r["k"] < 0 else "post"
        lines.append(f"  {int(r['k']):+d}   {r['coef']:+8.3f}   {pct:+7.1f}%   "
                     f"{r['se']:6.3f}   {pre} {sig}")
    if pt_p is not None:
        verdict = "PARALLEL OK" if pt_p > 0.10 else "PRE-TREND WARNING"
        lines.append(f"\n  parallel-trends joint test on leads: p = {pt_p:.4f}  [{verdict}]")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default="questions",
                    choices=["questions", "answers"])
    ap.add_argument("--event", default=DEFAULT_EVENT, help="YYYY-MM (first post month)")
    ap.add_argument("--drop-russian", action="store_true",
                    help="exclude ru.stackoverflow (Russia-Ukraine confound)")
    ap.add_argument("--math-only", action="store_true",
                    help="controls = math.stackexchange + mathoverflow.net only")
    ap.add_argument("--placebo", default=None,
                    help="fake event YYYY-MM for falsification (expect ~0 effect). "
                         "The sample is truncated to months STRICTLY BEFORE the real "
                         "event so the placebo cannot pick up the true treatment.")
    ap.add_argument("--kmin", type=int, default=-6)
    ap.add_argument("--kmax", type=int, default=12)
    args = ap.parse_args()

    if not os.path.exists(PANEL):
        raise SystemExit(f"missing {PANEL}; run fetch_so_activity.py first")

    controls_only = ["math.stackexchange", "mathoverflow.net"] if args.math_only else None
    df = load(args.endpoint, drop_russian=args.drop_russian,
              controls_only=controls_only)
    if args.placebo:
        # valid placebo: keep only months strictly BEFORE the real event, so a
        # significant "effect" cannot be the true treatment leaking in.
        real_e = ym_to_int(args.event)
        df = df[df["t"] < real_e].copy()
    sites = sorted(df["site"].unique())
    print("=" * 64)
    print(f"P9 Leg B — DiD / event study  [{args.endpoint}]")
    print("=" * 64)
    print(f"sites ({len(sites)}): {sites}")
    print(f"treated : {sorted(df[df.treated==1].site.unique())}")
    print(f"months  : {df['ym'].min()} .. {df['ym'].max()} "
          f"({df['ym'].nunique()} months)")
    event = args.placebo or args.event
    print(f"event   : {event}" + ("  [PLACEBO]" if args.placebo else
                                   "  (ChatGPT 2022-11-30 / SO ban 2022-12-05)"))
    if df["treated"].nunique() < 2 or df["site"].nunique() < 2:
        raise SystemExit("need >=1 treated and >=1 control site in the panel")
    print()

    r = did(df, event)
    star = "***" if r["p"] < 0.01 else "**" if r["p"] < 0.05 else "*" if r["p"] < 0.10 else ""
    print(f"=== DiD (two-way FE, SE = {r['cov']}) ===")
    print(f"  beta(treated x post) = {r['beta']:+.4f}  (se {r['se']:.4f}, p {r['p']:.4f}{star})")
    print(f"  => activity effect   = {r['pct_effect']:+.1f}%  "
          f"(95% CI [{r['ci95_pct'][0]:+.1f}%, {r['ci95_pct'][1]:+.1f}%])")
    print(f"  n_obs={r['n_obs']}  n_clusters={r['n_clusters']}")
    if r["n_clusters"] < 5:
        print(f"  NOTE: only {r['n_clusters']} clusters -> cluster-robust SE are "
              f"anti-conservative; report wild-cluster bootstrap / randomization "
              f"inference in the paper.")
    print()

    print("=== event study (leads test parallel trends; lags = dynamic effect) ===")
    tab, pt_p, _ = event_study(df, event, kmin=args.kmin, kmax=args.kmax)
    print(fmt_es(tab, pt_p))
    print()

    # save event-study coefs for plotting
    out = os.path.join(DATA, f"eventstudy_{args.endpoint}"
                       + ("_placebo" if args.placebo else "") + ".csv")
    tab.to_csv(out, index=False)
    print(f"[saved] {out}")


if __name__ == "__main__":
    main()
