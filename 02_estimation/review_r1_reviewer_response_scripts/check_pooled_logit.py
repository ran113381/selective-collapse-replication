# -*- coding: utf-8 -*-
u"""Pooled four-answerer logit (+0.867, SE 0.157 as first reported): does it account
for each question being answered four times?

four_tier_2x2.json stores only beta/se/p, not the SE type, and the script that
produced it is not in the tree. Recompute from the per-question file with default
and question-clustered SEs; if the default SE reproduces 0.157, the original was
not clustered.
"""
import sys, numpy as np, pandas as pd, statsmodels.formula.api as smf
sys.stdout.reconfigure(encoding="utf-8")

w = pd.read_csv(r"E:\智能体论文\P9_金标准_20260704\criterion\weak_tier_per_question.csv")
tiers = {"Sonnet 5 (paper)": ("claude", "strong"), "Haiku 4.5": ("claude", "weak"),
         "GLM-5.3": ("glm", "strong"), "GLM-4.6": ("glm", "weak")}
common = w.dropna(subset=list(tiers))
print("共同子样本 N = %d（稿件 288）" % len(common))
rows = []
for t, (fam, cap) in tiers.items():
    for _, r in common.iterrows():
        rows.append({"qid": r.qid, "s": r.s, "y": r[t], "family": fam, "cap": cap})
d = pd.DataFrame(rows)
f = "y ~ s + C(family) + C(cap) + s:C(family) + s:C(cap)"
m0 = smf.logit(f, d).fit(disp=0)
m1 = smf.logit(f, d).fit(disp=0, cov_type="cluster", cov_kwds={"groups": d.qid})
for k in ("s", "s:C(family)[T.glm]", "s:C(cap)[T.weak]"):
    print("%-22s β = %+.3f   默认 SE %.3f (p=%.2g)   按题聚类 SE %.3f (p=%.2g)"
          % (k, m0.params[k], m0.bse[k], m0.pvalues[k], m1.bse[k], m1.pvalues[k]))
print("\n稿件报的是 SE 0.157 / p = 3.5e-08 → 与哪一列吻合，就是当初用的哪种 SE。")
