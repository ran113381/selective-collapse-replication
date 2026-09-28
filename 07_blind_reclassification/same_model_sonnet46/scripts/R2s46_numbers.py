# -*- coding: utf-8 -*-
"""Sonnet 4.6 同模型盲跑:稿件(正文 §4.2、§6.1、§8.3、Table 4)所引各数的出处与换算,逐条记公式。

不做新分析。只做两件事:
  1. 从 R2s46_analyze_result.json 取数,按稿件惯例换算(百分数 = 比例 × 100;取 3 位小数);
  2. 对 d(原分 − 盲分)的两期均值、差、按月聚类 SE、正态与 Welch 区间,按 R2s46_analyze.py 的 did() 同一口径
     在全精度上重算(该 JSON 只存 4 位,−0.0365 这类值取 3 位时会有歧义),并断言与 JSON 的 4 位值一致;
     另记两期 d 的原始计数(分子/分母),说明两期均值「恰好相等」不是舍入巧合。
输入只读:本目录 question_labels_python_blind_s46.csv、R2s46_analyze_result.json;包内原分类标签。
输出:本目录 R2s46_numbers_result.json(新文件)。
"""
import csv, io, json, os, sys
from fractions import Fraction
import numpy as np
import statsmodels.api as sm
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = r"E:\智能体论文\P9b_OSF_复现包_20260920\01_panels_and_classification\data"
EVENT_YM = "2022-12"
R = json.load(io.open(os.path.join(HERE, "R2s46_analyze_result.json"), encoding="utf-8"))

s46 = {int(r["question_id"]): (int(r["score"]), r["ym"]) for r in csv.DictReader(io.open(os.path.join(HERE, "question_labels_python_blind_s46.csv"), encoding="utf-8"))}
orig = {}
for fn in ("question_labels_python_2021-2024.csv", "question_labels_python_ext_2024-07_2026-05.csv"):
    for r in csv.DictReader(io.open(os.path.join(DATA, fn), encoding="utf-8")):
        orig[int(r["question_id"])] = int(r["score"])
assert len(s46) == 6000 and set(s46) <= set(orig)
qs = sorted(s46)
g = np.array([s46[q][1] for q in qs])
post = np.array([int(s46[q][1] >= EVENT_YM) for q in qs], float)
mp = sorted({m for m in g if m < EVENT_YM}); mq = sorted({m for m in g if m >= EVENT_YM})
assert len(mp) == 18 and len(mq) == 42


def did(v):
    f = sm.OLS(v, sm.add_constant(post)).fit(cov_type="cluster", cov_kwds={"groups": g})
    b, se = float(f.params[1]), float(f.bse[1])
    a = [v[g == m].mean() for m in mp]; c = [v[g == m].mean() for m in mq]
    va, vc = np.var(a, ddof=1) / len(a), np.var(c, ddof=1) / len(c)
    dfw = (va + vc) ** 2 / (va ** 2 / (len(a) - 1) + vc ** 2 / (len(c) - 1))
    hw = float(stats.t.ppf(0.975, dfw) * np.sqrt(va + vc))
    dm = float(np.mean(c) - np.mean(a))
    return dict(mean_pre=float(v[post == 0].mean()), mean_post=float(v[post == 1].mean()), diff=b, se_cluster=se,
                ci_normal=[b - 1.96 * se, b + 1.96 * se], ci_welch=[dm - hw, dm + hw])


out = {"_note": "由 R2s46_numbers.py 生成;稿件所引 Sonnet 4.6 同模型盲跑各数的出处与换算。取整一律 round(x, 3) 或 round(100x, 1)。"}
for key, vec in (("d_score", np.array([orig[q] - s46[q][0] for q in qs], float)),
                 ("d_binary", np.array([int(orig[q] >= 3) - int(s46[q][0] >= 3) for q in qs], float))):
    full = did(vec)
    j = R["s46_vs_original"][key]
    for k in ("mean_pre", "mean_post", "diff", "se_cluster"):
        assert round(full[k], 4) == j[k] or (k == "diff" and abs(round(full[k], 4) - j[k]) < 1e-12), (key, k, full[k], j[k])
    for k in ("ci_normal", "ci_welch"):
        assert [round(x, 4) for x in full[k]] == j[k], (key, k, full[k], j[k])
    pre_sum = int(vec[post == 0].sum()); post_sum = int(vec[post == 1].sum())
    n_pre = int((post == 0).sum()); n_post = int((post == 1).sum())
    out[key] = {"full_precision": full,
                "rounded_3dp": {k: (round(v, 3) if not isinstance(v, list) else [round(x, 3) for x in v]) for k, v in full.items()},
                "raw": {"sum_pre": pre_sum, "n_pre": n_pre, "sum_post": post_sum, "n_post": n_post,
                        "mean_pre_exact": str(Fraction(pre_sum, n_pre)), "mean_post_exact": str(Fraction(post_sum, n_post)),
                        "means_exactly_equal": Fraction(pre_sum, n_pre) == Fraction(post_sum, n_post)}}
o = R["s46_vs_original"]
out["percent"] = {
    "exact_agree_vs_original_pct": {"value": round(100 * o["exact_agree"], 1), "formula": "100 × s46_vs_original.exact_agree"},
    "binary_agree_vs_original_pct": {"value": round(100 * o["kbin"]["agree"], 1), "formula": "100 × s46_vs_original.kbin.agree"},
    "binary_agree_vs_sonnet5_blind_pct": {"value": round(100 * R["s46_vs_sonnet5_blind"]["kbin"]["agree"], 1), "formula": "100 × s46_vs_sonnet5_blind.kbin.agree"},
    "binary_agree_vs_consensus_pct": {"value": round(100 * R["kappa_vs_consensus"]["s46"]["agree"], 1), "formula": "100 × kappa_vs_consensus.s46.agree"},
}
out["rounded_3dp"] = {
    "kappa_vs_original": round(o["kbin"]["kappa"], 3),
    "kappa_vs_sonnet5_blind": round(R["s46_vs_sonnet5_blind"]["kbin"]["kappa"], 3),
    "kappa_vs_consensus_s46": round(R["kappa_vs_consensus"]["s46"]["kappa"], 3),
    "ols": {k: (round(v, 3) if not isinstance(v, list) else [round(x, 3) for x in v]) for k, v in R["headline_s46"]["ols"].items() if k != "p"},
    "ppml": {k: (round(v, 3) if not isinstance(v, list) else [round(x, 3) for x in v]) for k, v in R["headline_s46"]["ppml"].items() if k != "p"},
    "ols_2dp": round(R["headline_s46"]["ols"]["coef"], 2),
}
io.open(os.path.join(HERE, "R2s46_numbers_result.json"), "w", encoding="utf-8").write(json.dumps(out, indent=1, ensure_ascii=False))
print(json.dumps(out, indent=1, ensure_ascii=False))
