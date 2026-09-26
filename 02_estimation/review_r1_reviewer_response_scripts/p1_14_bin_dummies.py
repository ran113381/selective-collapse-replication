# -*- coding: utf-8 -*-
u"""Bin dummies in place of the linear score: a test of the equal-interval assumption.

The main regression enters the ordinal score as if it were interval (s = 1..4), and
"34% more decline per point" depends on that. The test replaces s x post with three
bin x post dummies (s1 as reference) and asks whether the three coefficients lie on
a line.

Specification: lc ~ sum over b in {2,3,4} of 1[bin=b] x post + C(bin) + C(ym),
     month-clustered SE; otherwise identical to the main specification (Section 5.2).

Linearity: H0: delta_2 = g, delta_3 = 2g, delta_4 = 3g, i.e. the two restrictions
     delta_3 - 2 delta_2 = 0 and delta_4 - 3 delta_2 = 0; Wald test with 2 df.

Run for each language. The continuous gamma is reproduced first (python -0.416 /
javascript -0.229 / java -0.123) as a pipeline check; the script stops if it is not.

Output: review_r1/p1_14_bin_dummies.json and a printed table.
"""
import io
import json
import os
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8")

DATA = r"E:\智能体论文\_legB_data"
HERE = os.path.dirname(os.path.abspath(__file__))

PANELS = {"python": "within_so_llm_panel.csv",
          "javascript": "within_so_llm_panel_js.csv",
          "java": "within_so_llm_panel_java.csv"}
PUBLISHED = {"python": -0.416, "javascript": -0.229, "java": -0.123}


def ymi(y):
    a, b = y.split("-")
    return int(a) * 12 + int(b) - 1


EVENT = ymi("2022-12")


def long_panel(fn):
    w = pd.read_csv(os.path.join(DATA, fn))
    d = w.melt(id_vars=["ym"], value_vars=["s1", "s2", "s3", "s4"],
               var_name="bin", value_name="cnt")
    d["s"] = d["bin"].str[1].astype(int)
    d["t"] = d["ym"].map(ymi)
    d["post"] = (d.t >= EVENT).astype(int)
    d["lc"] = np.log(d["cnt"].clip(lower=1))
    return d


out = {}
print("=" * 92)
print("P1-14：连续剂量 vs 分组虚拟变量")
print("=" * 92)

for lang, fn in PANELS.items():
    p = os.path.join(DATA, fn)
    if not os.path.exists(p):
        print("\n[缺文件] %s —— 跳过 %s" % (fn, lang))
        continue
    d = long_panel(fn)

    # --- 1) 先复现连续型主规格 ---
    d["sxp"] = d.s * d.post
    m_lin = smf.ols("lc ~ sxp + C(bin) + C(ym)", d).fit(
        cov_type="cluster", cov_kwds={"groups": d.ym})
    g, gse = m_lin.params["sxp"], m_lin.bse["sxp"]
    want = PUBLISHED[lang]
    ok = abs(g - want) < 0.01
    print("\n--- %s ---" % lang)
    print("  连续型 γ = %+.4f (SE %.4f)   稿件发表值 %+.3f  -> %s"
          % (g, gse, want, "OK 复现" if ok else "!! 对不上，后续不可用"))
    if not ok:
        continue

    # --- 2) 分组虚拟变量 ---
    for b in (2, 3, 4):
        d["d%d" % b] = ((d.s == b) & (d.post == 1)).astype(int)
    m_sat = smf.ols("lc ~ d2 + d3 + d4 + C(bin) + C(ym)", d).fit(
        cov_type="cluster", cov_kwds={"groups": d.ym})
    delta = np.array([m_sat.params["d%d" % b] for b in (2, 3, 4)])
    dse = np.array([m_sat.bse["d%d" % b] for b in (2, 3, 4)])

    print("  分组虚拟变量（s1 为参照）：")
    print("      bin   δ（相对 s1）        SE       p        线性预测 (b−1)·γ     偏离")
    for i, b in enumerate((2, 3, 4)):
        pred = (b - 1) * g
        print("      s%d   %+8.4f  %8.4f  %7.4f      %+8.4f       %+8.4f"
              % (b, delta[i], dse[i], m_sat.pvalues["d%d" % b], pred, delta[i] - pred))

    # --- 3) 线性约束的 Wald 检验：δ3 − 2δ2 = 0, δ4 − 3δ2 = 0 ---
    w = m_sat.wald_test("d3 - 2 * d2 = 0, d4 - 3 * d2 = 0", scalar=True)
    stat, pval = float(w.statistic), float(w.pvalue)
    print("  线性约束 Wald 检验 (H0: δ3=2δ2 且 δ4=3δ2)：χ²(2) = %.3f, p = %.4f" % (stat, pval))
    print("      -> %s" % ("不能拒绝线性——把序数当等距在本数据上没有暴露问题"
                           if pval > 0.05 else "拒绝线性——每分效应不等距，§6.1 的'每分 34%'需改口径"))

    # --- 4) 单调性与各 bin 的百分比变化 ---
    pct = [100 * (np.exp(x) - 1) for x in delta]
    mono = all(delta[i] >= delta[i + 1] for i in range(len(delta) - 1))
    print("  相对 s1 的变化：s2 %+.1f%%   s3 %+.1f%%   s4 %+.1f%%   单调递减：%s"
          % (pct[0], pct[1], pct[2], "是" if mono else "否"))

    out[lang] = {"gamma_linear": float(g), "gamma_se": float(gse), "published": want,
                 "reproduced": bool(ok),
                 "deltas": {"s%d" % b: {"coef": float(delta[i]), "se": float(dse[i]),
                                         "p": float(m_sat.pvalues["d%d" % b]),
                                         "linear_prediction": float((b - 1) * g),
                                         "deviation": float(delta[i] - (b - 1) * g),
                                         "pct_vs_s1": float(pct[i])}
                            for i, b in enumerate((2, 3, 4))},
                 "linearity_wald": {"chi2": stat, "df": 2, "p": pval,
                                     "linearity_rejected": bool(pval < 0.05)},
                 "monotone": bool(mono)}

# ---------------- 汇总 ----------------
print()
print("=" * 92)
print("汇总")
print("=" * 92)
print("  %-12s %10s  %10s %10s %10s  %8s %8s" %
      ("语言", "连续γ", "δ_s2", "δ_s3", "δ_s4", "χ²(2)", "p"))
for lang, r in out.items():
    dd = r["deltas"]
    print("  %-12s %+10.4f  %+10.4f %+10.4f %+10.4f  %8.3f %8.4f" %
          (lang, r["gamma_linear"], dd["s2"]["coef"], dd["s3"]["coef"], dd["s4"]["coef"],
           r["linearity_wald"]["chi2"], r["linearity_wald"]["p"]))
rej = [l for l, r in out.items() if r["linearity_wald"]["linearity_rejected"]]
print()
print("  拒绝线性的语言：%s" % (rej if rej else "无"))
print("  -> %s" % ("三种语言都不能拒绝线性，§6.1 的连续型口径可以保留；"
                   "把本表放进 SI 作为'线性假设已检验'的交代即可。"
                   if not rej else
                   "有语言拒绝线性，§6.1 需要改口径或补分组结果。"))

op = os.path.join(HERE, "p1_14_bin_dummies.json")
json.dump(out, io.open(op, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("\n写入 %s" % op)
