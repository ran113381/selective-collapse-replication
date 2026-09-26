# -*- coding: utf-8 -*-
"""R2 B 臂:看得见日期的诊断臂——收标签、核验、按设计书第二节检验(写于标签产生之前)。

d = 看得见分(B 臂) − 盲分(A 臂,同一题)。报:
  E[d | 事件前]、E[d | 事件后],以及 E[d | 后] − E[d | 前]:
  - 正态区间:题级回归 d ~ post,按月聚类(18 簇);
  - Welch 区间:18 个月均值的 Welch t。
另报二元标签(≥3)层面的同一对比,作参照。输出 工作文档\\R2v_result.json
"""
import csv, io, json, os, sys
import numpy as np
import statsmodels.api as sm
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "R2_blind", "armB")
EV = 2022 * 12 + 11
mon = json.load(io.open(os.path.join(D, "R2v_months.json"), encoding="utf-8"))
months = mon["pre"] + mon["post"]
blind = {int(r["question_id"]): int(r["score"]) for r in csv.DictReader(
    io.open(os.path.join(HERE, "R2_blind", "question_labels_python_blind.csv"), encoding="utf-8"))}

rows, bad, missing = [], [], []
for m in months:
    qf, lf = os.path.join(D, "R2v_%s.json" % m), os.path.join(D, "R2v_labels_%s.json" % m)
    qs = [int(r["question_id"]) for r in json.load(io.open(qf, encoding="utf-8"))]
    if not os.path.exists(lf):
        missing.append(m); continue
    lab = json.load(io.open(lf, encoding="utf-8"))
    got = [int(r["question_id"]) for r in lab]
    if sorted(got) != sorted(qs) or len(set(got)) != len(got):
        bad.append((m, "题号集合不符")); continue
    if any((not isinstance(r["score"], int)) or not 0 <= r["score"] <= 4 or r["label"] != ("GEN" if r["score"] >= 3 else "VER") for r in lab):
        bad.append((m, "分值或标签不合法")); continue
    post = int(int(m[:4]) * 12 + int(m[5:7]) - 1 >= EV)
    for r in lab:
        q = int(r["question_id"])
        rows.append(dict(ym=m, post=post, vis=r["score"], bl=blind[q]))
print("合格 %d 个月;缺 %s;不合格 %s" % (len(months) - len(missing) - len(bad), missing, bad))
if missing or bad:
    raise SystemExit(0)

y = np.array([r["vis"] - r["bl"] for r in rows], float)
yb = np.array([int(r["vis"] >= 3) - int(r["bl"] >= 3) for r in rows], float)
post = np.array([r["post"] for r in rows], float)
g = np.array([r["ym"] for r in rows])


def did(v):
    X = sm.add_constant(post)
    f = sm.OLS(v, X).fit(cov_type="cluster", cov_kwds={"groups": g})
    b, se = f.params[1], f.bse[1]
    mm = {m: v[g == m].mean() for m in months}
    a = [mm[m] for m in mon["pre"]]; c = [mm[m] for m in mon["post"]]
    t = stats.ttest_ind(c, a, equal_var=False)
    va, vc = np.var(a, ddof=1) / len(a), np.var(c, ddof=1) / len(c)
    dfw = (va + vc) ** 2 / (va ** 2 / (len(a) - 1) + vc ** 2 / (len(c) - 1))
    hw = stats.t.ppf(0.975, dfw) * np.sqrt(va + vc)
    return dict(mean_pre=round(float(v[post == 0].mean()), 4), mean_post=round(float(v[post == 1].mean()), 4),
                diff=round(float(b), 4), se_cluster=round(float(se), 4),
                ci_normal=[round(float(b - 1.96 * se), 4), round(float(b + 1.96 * se), 4)],
                ci_welch=[round(float(np.mean(c) - np.mean(a) - hw), 4), round(float(np.mean(c) - np.mean(a) + hw), 4)],
                p_welch=float(t.pvalue), n=int(len(v)), months=len(months))


R = dict(score_diff=did(y), binary_diff=did(yb),
         agreement=dict(exact=round(float(np.mean(y == 0)), 4),
                        binary=round(float(np.mean(yb == 0)), 4)))
io.open(os.path.join(HERE, "R2v_result.json"), "w", encoding="utf-8").write(json.dumps(R, indent=1, ensure_ascii=False))
s = R["score_diff"]
print("d=看得见−盲:事件前 %+.3f  事件后 %+.3f  差 %+.3f  正态 [%+.3f, %+.3f]  Welch [%+.3f, %+.3f] p=%.3f"
      % (s["mean_pre"], s["mean_post"], s["diff"], *s["ci_normal"], *s["ci_welch"], s["p_welch"]))
b = R["binary_diff"]
print("二元:事件前 %+.3f  事件后 %+.3f  差 %+.3f  Welch [%+.3f, %+.3f]" % (b["mean_pre"], b["mean_post"], b["diff"], *b["ci_welch"]))
print("同题两臂精确一致 %.1f%%,二元一致 %.1f%%" % (100 * R["agreement"]["exact"], 100 * R["agreement"]["binary"]))
