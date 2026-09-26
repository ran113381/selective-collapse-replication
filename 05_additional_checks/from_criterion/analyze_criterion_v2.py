# -*- coding: utf-8 -*-
"""Criterion-validity v2 — final analysis (N=320, selection-bias-corrected design).

Round 1 (N=88) required a credible human reference answer to enter the sample,
which correlated with substitutability bin (s1 11% inclusion vs s4 31%+) and
biased the test conservative. Round 2 samples unconditionally (every drawn
question is kept regardless of answer availability) and grades reference
quality instead of gating on it. This script:
  1. reports answerability/adequacy by bin (headline)
  2. Spearman/OLS/logit gradient tests (headline)
  3. power check given the realized effect size
  4. robustness: restrict to reference_quality in {accepted, top_voted} only
     (comparable to round-1's implicit filter) vs the full N=320 sample
  5. descriptive: reference_quality distribution by bin (the selection-bias
     diagnostic itself, now unconditional on inclusion)
  6. cross-check against round-1 (N=88) for consistency
"""
import json, glob, os
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
from statsmodels.stats.power import NormalIndPower

HERE = os.path.dirname(os.path.abspath(__file__))
BV = os.path.join(HERE, "batches_v2")

sample = {r["qid"]: r for r in json.load(open(os.path.join(HERE, "criterion_sample_v2.json"), encoding="utf-8"))}
judg = {}
for f in sorted(glob.glob(os.path.join(BV, "judgment_out_*.json"))):
    for j in json.load(open(f, encoding="utf-8")):
        judg[j["qid"]] = j

rows = []
for q, r in sample.items():
    j = judg.get(q)
    if not j:
        continue
    rows.append({"qid": q, "sub": r["sub_score"], "ref_quality": r["reference_quality"],
                "answerable": int(j["answerable"]), "adequacy": float(j["adequacy"])})
d = pd.DataFrame(rows)
print(f"N judged = {len(d)}  (of {len(sample)} sampled)")

print("\n=== 0. Reference-quality distribution by bin (the selection-bias diagnostic) ===")
rq = pd.crosstab(d["sub"], d["ref_quality"], normalize="index")
for s in (1, 2, 3, 4):
    row = rq.loc[s] if s in rq.index else None
    if row is not None:
        print(f"  s{s}: " + "  ".join(f"{c}={row.get(c,0):.0%}" for c in ("none","weak","top_voted","accepted")))

print("\n=== 1. AI answerability by substitutability bin (N=320, unconditional sample) ===")
g = d.groupby("sub").agg(n=("qid", "size"), answerable=("answerable", "mean"),
                         adequacy=("adequacy", "mean"))
for s, r in g.iterrows():
    print(f"  s{s}: n={int(r.n):3d}  AI-answerable={r.answerable:.3f}  mean-adequacy(1-5)={r.adequacy:.2f}")

print("\n=== 2. Criterion-validity tests ===")
rho, p_rho = stats.spearmanr(d["sub"], d["adequacy"])
print(f"  Spearman(sub, adequacy)      rho = {rho:+.3f}  p = {p_rho:.4g}")
rho2, p2 = stats.spearmanr(d["sub"], d["answerable"])
print(f"  Spearman(sub, answerable)    rho = {rho2:+.3f}  p = {p2:.4g}")

d["gen"] = (d["sub"] >= 3).astype(int)
ver, gen = d[d.gen == 0], d[d.gen == 1]
p1, p2v = gen["answerable"].mean(), ver["answerable"].mean()
_, pt = stats.mannwhitneyu(gen["adequacy"], ver["adequacy"], alternative="greater")
_, pbin = stats.ttest_ind(gen["answerable"], ver["answerable"], alternative="greater")
tab = [[int(gen.answerable.sum()), len(gen)-int(gen.answerable.sum())],
       [int(ver.answerable.sum()), len(ver)-int(ver.answerable.sum())]]
odds, pf = stats.fisher_exact(tab, alternative="greater")
print(f"  generative(s3-4) {p1:.3f} (n={len(gen)}) vs verification(s1-2) {p2v:.3f} (n={len(ver)})  "
      f"diff {100*(p1-p2v):+.1f}pp,  OR={odds:.2f}")
print(f"  Mann-Whitney (adequacy, one-sided) p = {pt:.4g}")
print(f"  Fisher exact (answerable, one-sided) p = {pf:.4g}")

X = sm.add_constant(d["sub"].astype(float))
m = sm.OLS(d["adequacy"].to_numpy(), X.to_numpy()).fit(cov_type="HC3")
print(f"  OLS adequacy ~ sub: slope = {m.params[1]:+.3f}/pt (HC3 se {m.bse[1]:.3f}, p = {m.pvalues[1]:.4g})")
ml = sm.Logit(d["answerable"].to_numpy(), X.to_numpy()).fit(disp=0)
print(f"  Logit answerable ~ sub: coef = {ml.params[1]:+.3f} (se {ml.bse[1]:.3f}, p = {ml.pvalues[1]:.4g}, "
      f"OR/pt = {np.exp(ml.params[1]):.3f})")

s1e, s4e = d[d["sub"] == 1], d[d["sub"] == 4]
tab2 = [[int(s4e.answerable.sum()), len(s4e)-int(s4e.answerable.sum())],
        [int(s1e.answerable.sum()), len(s1e)-int(s1e.answerable.sum())]]
_, pf2 = stats.fisher_exact(tab2, alternative="greater")
print(f"  endpoint s4 {s4e.answerable.mean():.3f} vs s1 {s1e.answerable.mean():.3f}: Fisher p = {pf2:.4g}")

print("\n=== 3. Power check (realized effect size, N=320) ===")
h = 2*np.arcsin(np.sqrt(p1)) - 2*np.arcsin(np.sqrt(p2v))
pw = NormalIndPower()
power = pw.power(effect_size=h, nobs1=len(gen), ratio=len(ver)/len(gen), alpha=0.05)
print(f"  Cohen's h = {h:.3f}  =>  achieved power = {power:.2f}  (target was 0.80 at design effect size)")

print("\n=== 4. Robustness: restrict to accepted/top_voted only (round-1-comparable subset) ===")
strong = d[d.ref_quality.isin(["accepted", "top_voted"])]
print(f"  N = {len(strong)}")
rho_s, p_s = stats.spearmanr(strong["sub"], strong["adequacy"])
rho_sb, p_sb = stats.spearmanr(strong["sub"], strong["answerable"])
print(f"  Spearman(sub, adequacy)   rho = {rho_s:+.3f}  p = {p_s:.4g}")
print(f"  Spearman(sub, answerable) rho = {rho_sb:+.3f}  p = {p_sb:.4g}")
gen_s, ver_s = strong[strong["sub"] >= 3], strong[strong["sub"] <= 2]
print(f"  gen {gen_s.answerable.mean():.3f} (n={len(gen_s)}) vs ver {ver_s.answerable.mean():.3f} (n={len(ver_s)})")

print("\n=== 5. Robustness: reference_quality='none' items only (no human answer existed) ===")
none_d = d[d["ref_quality"] == "none"]
print(f"  N = {len(none_d)}  (pure judge-merit grading, no reference)")
if len(none_d) > 5:
    rho_n, p_n = stats.spearmanr(none_d["sub"], none_d["answerable"])
    print(f"  Spearman(sub, answerable) rho = {rho_n:+.3f}  p = {p_n:.4g}")
    parts = []
    for s in (1, 2, 3, 4):
        sub_d = none_d[none_d["sub"] == s]
        if len(sub_d) > 0:
            parts.append(f"s{s}={sub_d['answerable'].mean():.2f}(n={len(sub_d)})")
    print("  answerable by bin: " + "  ".join(parts))

print("\n=== 6. Cross-check against round 1 (N=88) ===")
r1 = os.path.join(HERE, "criterion_results.csv")
if os.path.exists(r1):
    d1 = pd.read_csv(r1)
    gen1 = d1[d1["sub"] >= 3]["answerable"].mean()
    ver1 = d1[d1["sub"] <= 2]["answerable"].mean()
    rho1 = stats.spearmanr(d1["sub"], d1["adequacy"])[0]
    print(f"  round 1: gen {gen1:.3f} vs ver {ver1:.3f}  (N={len(d1)}, rho={rho1:+.3f})")
    print(f"  round 2: gen {p1:.3f} vs ver {p2v:.3f}  (N={len(d)}, rho={rho:+.3f})")

verdict = "CRITERION VALIDITY ESTABLISHED" if (rho2 > 0 and p2 < 0.05) else "not established at .05"
print(f"\nVERDICT (primary, answerable~sub Spearman): {verdict}  (rho={rho2:+.3f}, p={p2:.4g})")
d.to_csv(os.path.join(HERE, "criterion_results_v2.csv"), index=False)
print("saved criterion_results_v2.csv")
