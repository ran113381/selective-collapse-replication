# -*- coding: utf-8 -*-
u"""Exploratory version of p0_2: reproduce the Staging Ground split at July 2024
(19/23 months), then recompute at the official date, 4 June 2024 (18/24 months).

Specification as in the capability-window table: log(count) ~ s x post + bin FE +
month FE, month-clustered SE, post period restricted to the stated window, full
pre-period kept.
"""
import os, sys, numpy as np, pandas as pd, statsmodels.formula.api as smf
sys.stdout.reconfigure(encoding="utf-8")

wpy = pd.read_csv(r"E:\智能体论文\_legB_data\within_so_llm_panel.csv")
d = []
for _, r in wpy.iterrows():
    for b in (1, 2, 3, 4):
        d.append({"ym": r.ym, "score": b, "cnt": int(r["s%d" % b])})
d = pd.DataFrame(d)
d["lc"] = np.log(d.cnt.clip(lower=1))


def g(lo, hi, tag):
    dd = d[(d.ym < "2022-12") | ((d.ym >= lo) & (d.ym <= hi))].copy()
    dd["post"] = (dd.ym >= "2022-12").astype(int)
    dd["sxp"] = dd.score * dd.post
    m = smf.ols("lc ~ sxp + C(score) + C(ym)", dd).fit(cov_type="cluster", cov_kwds={"groups": dd.ym})
    n = dd[dd.post == 1].ym.nunique()
    print("%-44s %2d 个后期月  γ = %+.3f (SE %.3f)  p = %.2g" % (tag, n, m.params["sxp"], m.bse["sxp"], m.pvalues["sxp"]))


print("稿件口径（切在 2024-07，GA 误记为 7 月）：")
g("2022-12", "2024-06", "  before SG（稿件 −0.349, SE 0.086）")
g("2024-07", "2026-05", "  after SG （稿件 −0.464, SE 0.077）")
print("\n官方口径（GA = 2024-06-04，切在 2024-06）：")
g("2022-12", "2024-05", "  before SG")
g("2024-06", "2026-05", "  after SG")
print("\n过渡月敏感性（把 2024-06 单独丢掉）：")
g("2022-12", "2024-05", "  before")
g("2024-07", "2026-05", "  after（不含 2024-06）")
