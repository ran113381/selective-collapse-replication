# -*- coding: utf-8 -*-
u"""Truncation sensitivity: the share of question bodies cut at 1,400 characters
rises over time; does that move the gradient?

First reproduce the main specification on the full sample (gamma = -0.416), then
re-estimate excluding questions that reach the cap.
Main specification: log(count_{s,m}) ~ s x post + bin FE + month FE, s1..s4 (s0
dropped), month-clustered SE.
"""
import json, os, sys, numpy as np, pandas as pd, statsmodels.formula.api as smf
sys.stdout.reconfigure(encoding="utf-8")

D = r"E:\智能体论文\_legB_data"
CAP = 1400

lab = pd.concat([pd.read_csv(os.path.join(D, "question_labels.csv")),
                 pd.read_csv(os.path.join(D, "question_labels_ext_py.csv"))]).drop_duplicates("question_id")
txt = {}
for f in ("so_questions_full.json", "so_questions_ext_py.json"):
    for q in json.load(open(os.path.join(D, f), encoding="utf-8")):
        txt[q["question_id"]] = len(q.get("body_excerpt") or "")
lab["blen"] = lab["question_id"].map(txt)
print("标签 %d 条，能配上正文长度的 %d 条，触顶(≥%d) %d 条 = %.1f%%"
      % (len(lab), lab.blen.notna().sum(), CAP, (lab.blen >= CAP).sum(), 100 * (lab.blen >= CAP).mean()))
lab["post"] = (lab.ym >= "2022-12").astype(int)
cap = lab.groupby(["post"]).apply(lambda g: (g.blen >= CAP).mean() * 100)
print("触顶率：前期 %.1f%%，后期 %.1f%%" % (cap[0], cap[1]))
print("触顶率按 bin（后期）：", lab[lab.post == 1].groupby("score").apply(lambda g: round((g.blen >= CAP).mean() * 100, 1)).to_dict())


def gamma(df, tag):
    c = df[df.score.between(1, 4)].groupby(["ym", "score"]).size().rename("cnt").reset_index()
    # 补零：某月某 bin 若无题，计数 0 → log(clip 1)
    full = pd.MultiIndex.from_product([sorted(df.ym.unique()), [1, 2, 3, 4]], names=["ym", "score"])
    c = c.set_index(["ym", "score"]).reindex(full, fill_value=0).reset_index()
    c["lc"] = np.log(c.cnt.clip(lower=1))
    c["post"] = (c.ym >= "2022-12").astype(int)
    c["sxp"] = c.score * c.post
    m = smf.ols("lc ~ sxp + C(score) + C(ym)", c).fit(cov_type="cluster", cov_kwds={"groups": c.ym})
    print("%-34s γ = %+.3f (SE %.3f), p = %.2g,  N题 = %d" % (tag, m.params["sxp"], m.bse["sxp"], m.pvalues["sxp"], len(df)))
    return m.params["sxp"]


g0 = gamma(lab, "全样本（应复现 −0.416）")
g1 = gamma(lab[lab.blen < CAP], "剔除触顶问题")
g2 = gamma(lab[lab.blen < 1000], "剔除 ≥1,000 字符（更狠）")
print("\n触顶剔除后 γ 变化 %+.3f（%.0f%%）" % (g1 - g0, 100 * (g1 - g0) / abs(g0)))
