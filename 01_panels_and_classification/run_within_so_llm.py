"""
P9 Leg B — RIGOROUS within-SO: dose-response DiD on LLM-classified AI-substitutability.

Reads within_so_llm_panel.csv (monthly counts of python questions by substitutability score
0-4, from aggregate_labels.py). Tests the mother thesis at the QUESTION level, immune to the
tag-proxy critique: as generation gets cheap, the MORE-substitutable questions should fall
MORE on SO after ChatGPT.

Designs:
  [1] DOSE-RESPONSE (headline): log(count_{s,m}) ~ score·post + bin_FE + month_FE, clustered
      on MONTH (37 clusters — finally enough for cluster-robust inference). γ = how much more
      a +1-score question's log-count moves post-ChatGPT. γ<0 ⇒ more-substitutable falls more.
  [2] GEN/VER binary DiD (compare to the tag probe): log(count) ~ gen·post + bin_FE + month_FE.
  [3] EVENT STUDY: score·1[k] — leads test the dose-response parallel-trend.
  [4] HONEST extrapolation: project the pre-period dose slope forward (Rambachan-Roth logic).
  Plus transparent descriptives: gen_share and mean-score, pre vs post.

s0 is dropped (near-empty: the classifier almost never assigns 0). Bins s1-s4 are all >0 so
log is clean. event = 2022-12.

Usage:  python run_within_so_llm.py
"""
import os
import sys
import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows console is GBK; we print γ/Δ/⇒

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
PANEL = os.path.join(DATA, "within_so_llm_panel.csv")
EVENT = "2022-12"


def ym_to_int(ym):
    y, m = (int(x) for x in str(ym).split("-"))
    return y * 12 + (m - 1)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default="within_so_llm_panel.csv")
    args = ap.parse_args()
    w = pd.read_csv(os.path.join(DATA, args.panel))
    e = ym_to_int(EVENT)

    # ---- long dose panel: (score bin 1-4 × month), drop s0 (near-empty) ----
    recs = []
    for _, r in w.iterrows():
        for b in (1, 2, 3, 4):
            recs.append({"ym": r["ym"], "score": b, "count": int(r[f"s{b}"])})
    d = pd.DataFrame(recs)
    d["s"] = d["ym"].map(ym_to_int)
    d["k"] = d["s"] - e
    d["post"] = (d["k"] >= 0).astype(int)
    assert (d["count"] > 0).all(), f"zero in s1-s4 (min={d['count'].min()})"
    d["y"] = np.log(d["count"].astype(float))

    print("=" * 72)
    print("P9 Leg B — RIGOROUS within-SO: dose-response on LLM substitutability")
    print("=" * 72)
    print(f"panel: bins s1-s4 × {d['ym'].nunique()} months ({len(d)} obs)  event={EVENT}")
    print(f"months: {w['ym'].min()}..{w['ym'].max()}   clusters (month) = {d['ym'].nunique()}")
    print()

    # descriptives
    w["s"] = w["ym"].map(ym_to_int)
    w["post"] = (w["s"] >= e).astype(int)
    pre, post = w[w.post == 0], w[w.post == 1]
    print("=== [0] DESCRIPTIVES (pre vs post ChatGPT) ===")
    print(f"  gen_share : pre {pre['gen_share'].mean():.3f}  post {post['gen_share'].mean():.3f}  "
          f"Δ {post['gen_share'].mean()-pre['gen_share'].mean():+.3f}")
    meanscore_pre = (sum(pre[f's{b}'].sum()*b for b in range(5)) / pre[[f's{b}' for b in range(5)]].sum().sum())
    meanscore_post = (sum(post[f's{b}'].sum()*b for b in range(5)) / post[[f's{b}' for b in range(5)]].sum().sum())
    print(f"  mean score: pre {meanscore_pre:.3f}  post {meanscore_post:.3f}  "
          f"Δ {meanscore_post-meanscore_pre:+.3f}")
    for b in (1, 2, 3, 4):
        print(f"  s{b} per-mo: pre {pre[f's{b}'].mean():5.1f}  post {post[f's{b}'].mean():5.1f}  "
              f"Δ {post[f's{b}'].mean()-pre[f's{b}'].mean():+5.1f}")
    print()

    # ---- [1] dose-response DiD ----
    bin_d = pd.get_dummies(d["score"], prefix="b", drop_first=True).astype(float)
    ym_d = pd.get_dummies(d["ym"], prefix="m", drop_first=True).astype(float)
    d["dose"] = d["score"] * d["post"]
    X = pd.concat([d[["dose"]].astype(float), bin_d, ym_d], axis=1)
    X = sm.add_constant(X)
    res = sm.OLS(d["y"].to_numpy(), X.to_numpy()).fit(
        cov_type="cluster", cov_kwds={"groups": d["ym"].to_numpy()})
    gi = list(X.columns).index("dose")
    gamma, gse = res.params[gi], res.bse[gi]
    print("=== [1] DOSE-RESPONSE DiD (headline; γ = score×post, month-clustered) ===")
    print(f"  γ = {gamma:+.4f}  SE {gse:.4f}  t {gamma/gse:+.2f}  p {res.pvalues[gi]:.4f}")
    print(f"  → each +1 substitutability point ⇒ {(np.exp(gamma)-1)*100:+.1f}% on log-count post-ChatGPT")
    print(f"  → s4-vs-s1 differential post = {(np.exp(3*gamma)-1)*100:+.1f}% (3 score points apart)")
    print()

    # ---- [2] GEN/VER binary DiD ----
    recs2 = []
    for _, r in w.iterrows():
        recs2.append({"ym": r["ym"], "gen": 1, "count": int(r["GEN"])})
        recs2.append({"ym": r["ym"], "gen": 0, "count": int(r["VER"])})
    b2 = pd.DataFrame(recs2)
    b2["s"] = b2["ym"].map(ym_to_int)
    b2["post"] = (b2["s"] >= e).astype(int)
    b2["y"] = np.log(b2["count"].astype(float))
    b2["gp"] = b2["gen"] * b2["post"]
    g_d = pd.get_dummies(b2["gen"], prefix="g", drop_first=True).astype(float)
    m_d = pd.get_dummies(b2["ym"], prefix="m", drop_first=True).astype(float)
    X2 = sm.add_constant(pd.concat([b2[["gp"]].astype(float), g_d, m_d], axis=1))
    res2 = sm.OLS(b2["y"].to_numpy(), X2.to_numpy()).fit(
        cov_type="cluster", cov_kwds={"groups": b2["ym"].to_numpy()})
    bi = list(X2.columns).index("gp")
    beta, bse = res2.params[bi], res2.bse[bi]
    print("=== [2] GEN vs VER binary DiD (compare to tag probe) ===")
    print(f"  β = {beta:+.4f}  SE {bse:.4f}  p {res2.pvalues[bi]:.4f}  "
          f"→ GEN vs VER post {(np.exp(beta)-1)*100:+.1f}%")
    print()

    # ---- [3] event study: score × 1[k] (dose-response over event time) ----
    ks = sorted(d["k"].unique())
    ks_use = [k for k in ks if k != -1]
    cols = {f"d{j}": (d["score"] * (d["k"] == j)).astype(float) for j in ks_use}
    G = pd.DataFrame(cols, index=d.index)
    Xe = sm.add_constant(pd.concat([G, bin_d, ym_d], axis=1))
    rese = sm.OLS(d["y"].to_numpy(), Xe.to_numpy()).fit(
        cov_type="cluster", cov_kwds={"groups": d["ym"].to_numpy()})
    names = list(Xe.columns)
    gk = {j: rese.params[names.index(f"d{j}")] for j in ks_use}
    print("=== [3] EVENT STUDY (dose slope γ_k by event time; k=-1 ref) ===")
    print(f"  {'k':>4} {'gamma_k':>9}")
    for j in ks_use:
        flag = "PRE" if j < 0 else "post"
        print(f"  {j:>+4} {gk[j]:>+9.4f}  {flag}")
    leads = [(j, gk[j]) for j in ks_use if j <= -2]
    lk = np.array([j for j, _ in leads], float)
    lb = np.array([v for _, v in leads])
    a, slope = np.linalg.lstsq(np.column_stack([np.ones_like(lk), lk]), lb, rcond=None)[0]
    print(f"\n  pre dose-slope trend: intercept {a:+.4f}, slope {slope:+.5f}/mo  "
          f"({'≈flat' if abs(slope) < 0.01 else 'trending'})")
    posts = [(j, gk[j]) for j in ks_use if j >= 0]
    det = [v - (a + slope * j) for j, v in posts]
    print(f"  honest detrended mean post dose-γ = {np.mean(det):+.4f} "
          f"(raw mean post dose-γ {np.mean([v for _, v in posts]):+.4f})")
    print()

    out = os.path.join(DATA, "within_so_llm_eventstudy.csv")
    pd.DataFrame({"k": ks_use, "gamma_k": [gk[j] for j in ks_use]}).to_csv(out, index=False)
    print(f"[saved] {out}")


if __name__ == "__main__":
    main()
