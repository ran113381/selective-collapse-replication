# -*- coding: utf-8 -*-
u"""Interval for the linear-detrending column of an earlier draft.

The event-study coefficients gamma_k are relative to the reference month (the CSV
has no k = -1; 2022-11 is the reference). The earlier draft fitted a linear trend
to the k <= -2 coefficients, extrapolated it over the post period and subtracted it,
and reported only the point estimate -0.26. This script propagates the trend-fit
uncertainty to give an interval.
"""
import numpy as np, pandas as pd, sys
sys.stdout.reconfigure(encoding="utf-8")

d = pd.read_csv(r"E:\智能体论文\_legB_data\within_so_llm_eventstudy.csv")
print("k 范围 %d..%d，缺失的 k：%s" % (d.k.min(), d.k.max(),
      sorted(set(range(d.k.min(), d.k.max() + 1)) - set(d.k))))
pre = d[d.k <= -2]; post = d[d.k >= 0]
print("前期(k<=-2) %d 个月：均值 %.3f，SD %.3f，min %.2f，max %.2f"
      % (len(pre), pre.gamma_k.mean(), pre.gamma_k.std(), pre.gamma_k.min(), pre.gamma_k.max()))
print("后期(k>=0)  %d 个月：均值 %.3f" % (len(post), post.gamma_k.mean()))
print("后期均值 − 前期均值（=把参照换成前期均值）：%.3f" % (post.gamma_k.mean() - pre.gamma_k.mean()))

# 线性趋势 OLS on lead coefficients
X = np.column_stack([np.ones(len(pre)), pre.k.values])
y = pre.gamma_k.values
beta, res, *_ = np.linalg.lstsq(X, y, rcond=None)
resid = y - X @ beta
s2 = (resid @ resid) / (len(pre) - 2)
V = s2 * np.linalg.inv(X.T @ X)
print("\n前期线性趋势：截距 %.3f (SE %.3f)，斜率 %.4f/月 (SE %.4f)，t = %.2f"
      % (beta[0], np.sqrt(V[0, 0]), beta[1], np.sqrt(V[1, 1]), beta[1] / np.sqrt(V[1, 1])))

# 外推到后期各月、取均值
kp = post.k.values
proj = beta[0] + beta[1] * kp
mean_proj = proj.mean()
g = np.array([1.0, kp.mean()])            # 均值投影的梯度
se_proj = float(np.sqrt(g @ V @ g))
detr = post.gamma_k.mean() - mean_proj
print("外推的前期水平（后期均值处）：%.3f (SE %.3f, 仅趋势拟合的不确定性)" % (mean_proj, se_proj))
print("去趋势后的后期均值：%.3f   （稿件表 3 写 −0.26）" % detr)
print("只算趋势外推不确定性的 95%% 区间：[%.2f, %.2f]" % (detr - 1.96 * se_proj, detr + 1.96 * se_proj))

# 还有后期均值本身的抽样误差：用后期系数的离散度粗估（系数本身没有 SE）
se_post = post.gamma_k.std() / np.sqrt(len(post))
se_tot = float(np.sqrt(se_proj ** 2 + se_post ** 2))
print("再加后期均值的粗略 SE %.3f → 合并 SE %.3f，区间 [%.2f, %.2f]"
      % (se_post, se_tot, detr - 1.96 * se_tot, detr + 1.96 * se_tot))
print("\n结论线索：斜率 t=%.2f；外推 %d 个月把一个不显著的斜率放大了 %.0f 倍。"
      % (beta[1] / np.sqrt(V[1, 1]), int(kp.mean() - pre.k.mean()), kp.mean() - pre.k.mean()))
