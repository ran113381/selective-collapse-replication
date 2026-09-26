# -*- coding: utf-8 -*-
"""Phase 1.4(a) — cross-family classifier robustness.

Inputs: glm_relabel/labels_<model>.jsonl from glm_run.py relabel (GLM scores
for the 6,000 python questions, same rubric, date-blind).

Reports, mirroring the paper's validation tables so the numbers are directly
comparable:
  (1) GLM vs Claude primary labels, all 6,000: binary kappa (GEN/VER),
      quadratic-weighted kappa (0-4), exact agreement, within-+-1, and the
      2-vs-3 boundary split (Table 2 layout).
  (2) GLM vs the HUMAN consensus standard on the 300 gold questions, built
      EXACTLY as score_adjudication.py builds it (230 binary-agreed + 70
      adjudicated), binary kappa with bootstrap CI — alongside Claude's 0.512
      (Table 4 layout).
  (3) The dose-response re-estimated with GLM labels: log-count OLS with bin
      and month FE, month-clustered SE (+ Poisson), s0 dropped as in the paper.
  (4) Period drift of GLM-vs-Claude agreement (pre/post 2022-12, Fisher).

Usage:  python cross_family_analysis.py [--model glm-5.3]
"""
import os, sys, json, csv, argparse
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf
import statsmodels.api as sm

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
DATA = r"E:\智能体论文\_legB_data"
GOLD = r"E:\智能体论文\P9_金标准_20260704"
HERE = os.path.dirname(os.path.abspath(__file__))


def kappa_bin(a, b):
    a, b = np.asarray(a), np.asarray(b)
    po = (a == b).mean(); p1, p2 = a.mean(), b.mean()
    pe = p1 * p2 + (1 - p1) * (1 - p2)
    return (po - pe) / (1 - pe), po


def kappa_qw(a, b, K=5):
    O = np.zeros((K, K))
    for i, j in zip(a, b):
        O[i][j] += 1
    n = len(a); rx, ry = O.sum(1), O.sum(0); num = den = 0.0
    for i in range(K):
        for j in range(K):
            w = ((i - j) ** 2) / ((K - 1) ** 2)
            num += w * O[i][j]; den += w * rx[i] * ry[j] / n
    return 1 - num / den


def boot_ci(a, b, n=3000, seed=20260906):
    rng = np.random.default_rng(seed); a, b = np.asarray(a), np.asarray(b); ks = []
    for _ in range(n):
        ii = rng.choice(len(a), len(a), replace=True); ks.append(kappa_bin(a[ii], b[ii])[0])
    return float(np.percentile(ks, 2.5)), float(np.percentile(ks, 97.5))


def ymi(y):
    a, b = y.split("-"); return int(a) * 12 + int(b) - 1


def human_consensus():
    """Replicates score_adjudication.py: cons_bin over v2 order -> question_id."""
    C = {int(r["order"]): int(r["score_0_4"]) for r in csv.DictReader(open(os.path.join(GOLD, "coding_sheet_A_v2.csv"), encoding="utf-8-sig")) if r["score_0_4"].strip()}
    B = {int(r["order"]): int(r["score_0_4"]) for r in csv.DictReader(open(os.path.join(GOLD, "coding_sheet_B_v2.csv"), encoding="utf-8-sig")) if r["score_0_4"].strip()}
    gv2 = json.load(open(os.path.join(GOLD, "gold_sample_v2_order.json"), encoding="utf-8"))
    qid = {s["order_v2"]: s["question_id"] for s in gv2}
    adj = {}
    for r in csv.DictReader(open(os.path.join(GOLD, "裁决记录表.csv"), encoding="utf-8-sig")):
        v = r["consensus_0_4"].strip()
        if v:
            adj[int(r["order"])] = int(v)
    cons = {}
    for o in range(1, 301):
        if (C[o] >= 3) == (B[o] >= 3):
            cons[qid[o]] = ("agreed", int(C[o] >= 3))
        elif o in adj:
            cons[qid[o]] = ("adjudicated", int(adj[o] >= 3))
    return cons


def main(model):
    lab_path = os.path.join(HERE, "glm_relabel", f"labels_{model}.jsonl")
    glm = {}
    for line in open(lab_path, encoding="utf-8"):
        r = json.loads(line); glm[int(r["question_id"])] = int(r["score"])
    cl = pd.read_csv(os.path.join(DATA, "question_labels.csv"))
    cl["glm"] = cl.question_id.map(glm)
    n_missing = int(cl.glm.isna().sum())
    d = cl.dropna(subset=["glm"]).copy(); d["glm"] = d.glm.astype(int)
    print(f"model={model}: GLM labels for {len(d)}/6000 (missing {n_missing})")
    res = {"model": model, "n": int(len(d)), "missing": n_missing}

    # (1) vs Claude
    a, b = (d.score >= 3).astype(int), (d.glm >= 3).astype(int)
    k, po = kappa_bin(a, b); kq = kappa_qw(d.score, d.glm)
    exact = float((d.score == d.glm).mean()); within1 = float(((d.score - d.glm).abs() <= 1).mean())
    bnd = d.score.isin([2, 3])
    agree = (a == b)
    print(f"\n(1) GLM vs Claude, N={len(d)}: binary κ={k:.3f} (raw {po:.1%}); weighted κ={kq:.3f}; exact {exact:.1%}; ±1 {within1:.1%}")
    print(f"    off 2–3 boundary (n={int((~bnd).sum())}): {agree[~bnd].mean():.1%};  on boundary (n={int(bnd.sum())}): {agree[bnd].mean():.1%}")
    print("    score distributions  Claude:", d.score.value_counts().sort_index().to_dict(), " GLM:", d.glm.value_counts().sort_index().to_dict())
    print("    confusion (rows Claude 0-4, cols GLM 0-4):\n", pd.crosstab(d.score, d.glm).to_string())
    res["vs_claude"] = {"kappa_bin": float(k), "raw": float(po), "kappa_qw": float(kq), "exact": exact, "within1": within1,
                        "off_boundary_agree": float(agree[~bnd].mean()), "on_boundary_agree": float(agree[bnd].mean()),
                        "glm_gen_share": float(b.mean()), "claude_gen_share": float(a.mean())}

    # (4) drift
    d["post"] = d.ym.map(ymi) >= ymi("2022-12")
    pre_a, post_a = agree[~d.post], agree[d.post]
    _, pdr = stats.fisher_exact([[int(pre_a.sum()), int(len(pre_a) - pre_a.sum())], [int(post_a.sum()), int(len(post_a) - post_a.sum())]])
    print(f"(4) agreement drift pre {pre_a.mean():.1%} vs post {post_a.mean():.1%}, Fisher p={pdr:.3f}")
    res["drift"] = {"pre": float(pre_a.mean()), "post": float(post_a.mean()), "fisher_p": float(pdr)}

    # (2) vs human consensus (300)
    cons = human_consensus()
    hh = [(q, t, v) for q, (t, v) in cons.items() if q in glm]
    hv = np.array([v for _, _, v in hh]); gv = np.array([int(glm[q] >= 3) for q, _, _ in hh])
    kh, poh = kappa_bin(hv, gv); lo, hi = boot_ci(hv, gv)
    print(f"\n(2) GLM vs human consensus, N={len(hh)}: binary κ={kh:.3f} [{lo:.3f}, {hi:.3f}] (raw {poh:.1%})  — Claude: κ=0.512 [0.413, 0.607]")
    for typ in ("agreed", "adjudicated"):
        idx = [i for i, (_, t, _) in enumerate(hh) if t == typ]
        kk, pp = kappa_bin(hv[idx], gv[idx])
        print(f"    on {typ} questions (N={len(idx)}): κ={kk:.3f} ({pp:.1%})")
        res[f"vs_human_{typ}"] = {"kappa": float(kk), "raw": float(pp), "N": len(idx)}
    res["vs_human"] = {"kappa_bin": float(kh), "ci": [lo, hi], "raw": float(poh), "N": len(hh), "claude_reference": 0.512}

    # (3) dose-response with GLM labels
    dd = d[d.glm > 0].copy()
    counts = dd.groupby(["ym", "glm"]).size().reset_index(name="cnt").rename(columns={"glm": "s"})
    counts["post"] = (counts.ym.map(ymi) >= ymi("2022-12")).astype(int); counts["sxp"] = counts.s * counts.post
    counts["lc"] = np.log(counts.cnt)
    m = smf.ols("lc ~ sxp + C(s) + C(ym)", counts).fit(cov_type="cluster", cov_kwds={"groups": counts["ym"]})
    mp = smf.glm("cnt ~ sxp + C(s) + C(ym)", counts, family=sm.families.Poisson()).fit(cov_type="cluster", cov_kwds={"groups": counts["ym"]})
    zero_cells = 4 * counts.ym.nunique() - len(counts)
    print(f"\n(3) dose-response with GLM labels (s0 dropped; {zero_cells} empty bin-months absent from log spec):")
    print(f"    OLS γ={m.params['sxp']:+.3f} (SE {m.bse['sxp']:.3f}) p={m.pvalues['sxp']:.2e}  s4-vs-s1={np.exp(3*m.params['sxp'])-1:+.0%}   "
          f"Poisson γ={mp.params['sxp']:+.3f} (SE {mp.bse['sxp']:.3f}) p={mp.pvalues['sxp']:.2e}   [Claude labels: −0.416]")
    res["dose_glm"] = {"ols": [float(m.params["sxp"]), float(m.bse["sxp"]), float(m.pvalues["sxp"])],
                       "poisson": [float(mp.params["sxp"]), float(mp.bse["sxp"]), float(mp.pvalues["sxp"])], "empty_cells": int(zero_cells)}
    # GEN share pre/post under GLM labels
    gs = dd.groupby("post").apply(lambda x: (x.glm >= 3).mean())
    print(f"    GLM generative share pre {gs[False]:.3f} → post {gs[True]:.3f}   [Claude: .63 → .47]")
    res["glm_gen_share_pre_post"] = [float(gs[False]), float(gs[True])]

    out = os.path.join(HERE, "glm_relabel", f"cross_family_{model}.json")
    json.dump(res, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"\nwritten: {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--model", default="glm-5.3")
    main(ap.parse_args().model)
