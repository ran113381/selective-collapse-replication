# -*- coding: utf-8 -*-
"""Criterion-validity step 4 — does the substitutability score predict AI answerability?

Joins substitutability scores (criterion_sample.json) with blind judgments
(judgment_out_k.json: {qid, answerable 0/1, adequacy 1-5}). If higher-substitutability
questions are answered correctly (from text alone) more often, the 0-4 rubric has
CRITERION VALIDITY against actual LLM answerability.
Reports: answerability by bin, Spearman/Pearson correlation, generative-vs-verification
contrast, and an OLS/logit gradient test.
"""
import json, os, glob
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm

HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(HERE, "batches")

score = {r["qid"]: r["sub_score"] for r in json.load(open(os.path.join(HERE, "criterion_sample.json"), encoding="utf-8"))}
judg = {}
for f in sorted(glob.glob(os.path.join(B, "judgment_out_*.json"))):
    for j in json.load(open(f, encoding="utf-8")):
        judg[j["qid"]] = j

rows = [{"qid": q, "sub": score[q], "answerable": int(judg[q]["answerable"]),
         "adequacy": float(judg[q]["adequacy"])} for q in score if q in judg]
d = pd.DataFrame(rows)
print(f"N judged = {len(d)}  (of {len(score)} sampled)")
print("\n=== AI answerability by substitutability bin ===")
g = d.groupby("sub").agg(n=("qid", "size"), answerable=("answerable", "mean"),
                         adequacy=("adequacy", "mean"))
for s, r in g.iterrows():
    print(f"  s{s}: n={int(r.n):2d}  AI-answerable={r.answerable:.2f}  mean-adequacy(1-5)={r.adequacy:.2f}")

print("\n=== Criterion-validity tests (score should PREDICT answerability) ===")
rho, p_rho = stats.spearmanr(d["sub"], d["adequacy"])
print(f"  Spearman(sub, adequacy)      rho = {rho:+.3f}  p = {p_rho:.4g}")
rho2, p2 = stats.spearmanr(d["sub"], d["answerable"])
print(f"  Spearman(sub, answerable)    rho = {rho2:+.3f}  p = {p2:.4g}")

# generative (s>=3) vs verification (s<=2)
d["gen"] = (d["sub"] >= 3).astype(int)
ver, gen = d[d.gen == 0], d[d.gen == 1]
t, pt = stats.mannwhitneyu(gen["adequacy"], ver["adequacy"], alternative="greater")
print(f"  generative(s3-4) adequacy {gen.adequacy.mean():.2f} vs verification(s1-2) {ver.adequacy.mean():.2f}  "
      f"Mann-Whitney p(one-sided) = {pt:.4g}")
print(f"  generative answerable {gen.answerable.mean():.2f} vs verification {ver.answerable.mean():.2f}")

# OLS gradient: adequacy ~ sub  (per-point slope) with HC3 SE
X = sm.add_constant(d["sub"].astype(float))
m = sm.OLS(d["adequacy"].to_numpy(), X.to_numpy()).fit(cov_type="HC3")
b, se, pv = m.params[1], m.bse[1], m.pvalues[1]
print(f"  OLS adequacy ~ sub: slope = {b:+.3f} per point (HC3 se {se:.3f}, p = {pv:.4g})")

# logit: answerable ~ sub
try:
    ml = sm.Logit(d["answerable"].to_numpy(), X.to_numpy()).fit(disp=0)
    print(f"  Logit answerable ~ sub: coef = {ml.params[1]:+.3f} (p = {ml.pvalues[1]:.4g})")
except Exception as e:
    print(f"  (logit skipped: {e})")

verdict = "CRITERION VALIDITY SUPPORTED" if (rho > 0 and p_rho < 0.05) else "not established at .05"
print(f"\nVERDICT: {verdict}  (Spearman rho={rho:+.3f}, p={p_rho:.3g})")
d.to_csv(os.path.join(HERE, "criterion_results.csv"), index=False)
print("saved criterion_results.csv")
