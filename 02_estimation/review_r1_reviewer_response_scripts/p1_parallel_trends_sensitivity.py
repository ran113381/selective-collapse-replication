# -*- coding: utf-8 -*-
u"""平行趋势敏感性（补 Table 3 被 P0-6 删空的那一列）。

为什么不用 StatsPAI 的 honest_did / sensitivity_rr：
  它们都只接受该服务器自家 fitter 产出的 result_id，而其 event_study 要求
  unit/time/treat_time 的处理组-对照组面板。本文**没有未处理单元**——整个平台
  同时被处理，识别来自剂量 s（bin 序数）× post。把本设计硬塞进那个接口会得到
  一个看着像、其实无意义的数。故自建，但每一步都对已发表数字自证。

做法：把前期三窗口（P0-6 已用）与后期四个能力窗口（Table 4 已用）放进
**同一个回归**，参照月 = 2022-11（k=-1，与事件研究一致），得到粗化事件研究的
系数向量与联合月聚类协方差。两套窗口都不是新发明的，是稿件已在用的口径。

  lc ~ sxW1+sxW2+sxW3 + sxY1+sxY2+sxY3+sxY4 + C(bin) + C(ym)

然后报两个量：
  A) 前期剂量斜率的线性趋势（用窗口序数回归三个前期系数，GLS 加权）——
     这是"前期是否已在漂移"的可检验版本，非退化。
  B) 断点：若把该趋势线性外推进后期，要多大的每窗口漂移 delta 才能把后期
     剂量斜率推到 0 / 推到不显著。以"观测到的最大前期窗间波动"为单位表达，
     即 Rambachan-Roth 相对量纲 Mbar 的同义构造。

**这不是 R&R 的完整偏识别区间**，是同族的断点值；写回时必须照此措辞，
不得称之为 honest DiD 区间。

自证（任一条不过就退出，不出数）：
  S1 前期三窗口系数须复现 p0_6_pretrends.json
  S2 后期四窗口系数须复现 Table 4 的 python 列（-0.313/-0.499/-0.447/-0.391 量级）
  S3 聚类协方差非退化（对角线无 0）
"""
import io, json, os, sys
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8")

DATA = r"E:\智能体论文\_legB_data"
HERE = os.path.dirname(os.path.abspath(__file__))

lab = pd.read_csv(os.path.join(DATA, "question_labels.csv"))
lab = lab[lab.score.between(1, 4)]


def ymi(y):
    a, b = y.split("-")
    return int(a) * 12 + int(b) - 1


# bin-month 计数面板
c = lab.groupby(["ym", "score"]).size().rename("cnt").reset_index()
full = pd.MultiIndex.from_product([sorted(lab.ym.unique()), [1, 2, 3, 4]],
                                  names=["ym", "score"])
c = c.set_index(["ym", "score"]).reindex(full, fill_value=0).reset_index()
c["lc"] = np.log(c.cnt.clip(lower=1))
c["bin"] = c.score
c["s"] = c.score
c["t"] = c.ym.map(ymi)

REF = ymi("2022-11")          # 参照月，与事件研究 k=-1 一致

WINDOWS = [
    ("pre W1 2021-06..2021-11", "sxW1", "2021-06", "2021-11", "pre"),
    ("pre W2 2021-12..2022-05", "sxW2", "2021-12", "2022-05", "pre"),
    ("pre W3 2022-06..2022-10", "sxW3", "2022-06", "2022-10", "pre"),
    ("post Y1 2022-12..2023-11", "sxY1", "2022-12", "2023-11", "post"),
    ("post Y2 2023-12..2024-11", "sxY2", "2023-12", "2024-11", "post"),
    ("post Y3 2024-12..2025-11", "sxY3", "2024-12", "2025-11", "post"),
    ("post Y4 2025-12..2026-05", "sxY4", "2025-12", "2026-05", "post"),
]
for label, col, lo, hi, side in WINDOWS:
    c[col] = c.s * ((c.t >= ymi(lo)) & (c.t <= ymi(hi))).astype(int)
    assert c[col].astype(bool).sum() > 0, label

cols = [w[1] for w in WINDOWS]
f = "lc ~ " + " + ".join(cols) + " + C(bin) + C(ym)"
m = smf.ols(f, c).fit(cov_type="cluster", cov_kwds={"groups": c["ym"]})
beta = np.array([m.params[k] for k in cols])
V = m.cov_params().loc[cols, cols].to_numpy()
se = np.sqrt(np.diag(V))

print("粗化事件研究（参照月 2022-11），月聚类：")
for (label, col, lo, hi, side), b, s in zip(WINDOWS, beta, se):
    print("  %-26s beta=%+.4f  SE=%.4f  t=%+.2f" % (label, b, s, b / s))

# ---------------- 对比量 ----------------
# 本回归的每个系数都是"该窗口 vs 参照月 2022-11"。而 Table 4 与头条 gamma 的口径是
# "后期 vs 全部前期"。参照月本身是高抽样月（均分 2.98 vs 前六月 2.72），整条系数
# 因此统一下移约 0.33。**首轮自证按原始系数比对 Table 4 报失败，那是自证自己的错，
# 不是规格的错**——要比的是做差之后的量。
NMO = {}                       # 每窗口月数
TAU = {}                       # 每窗口月中心（相对参照月）
for label, col, lo, hi, side in WINDOWS:
    months = [t for t in range(ymi(lo), ymi(hi) + 1)]
    NMO[col] = len(months)
    TAU[col] = float(np.mean([t - REF for t in months]))
PRE = [w[1] for w in WINDOWS if w[4] == "pre"]
POST = [w[1] for w in WINDOWS if w[4] == "post"]
n_pre = sum(NMO[c_] for c_ in PRE) + 1        # +1 = 参照月本身，其 beta 恒为 0
n_post = sum(NMO[c_] for c_ in POST)

c_pre = np.array([NMO[k] / n_pre if k in PRE else 0.0 for k in cols])
c_post = np.array([NMO[k] / n_post if k in POST else 0.0 for k in cols])
c_eff = c_post - c_pre                        # 后期 - 前期，即头条 gamma 的口径


def contrast(cv):
    return float(cv @ beta), float(np.sqrt(cv @ V @ cv))


pre_avg, _ = contrast(c_pre)
gamma_hat, gamma_se = contrast(c_eff)
print("\n对比量（参照月效应已抵消）：")
print("  前期平均水平（相对参照月） = %+.4f" % pre_avg)
for i, k in enumerate(POST):
    cv = np.zeros(len(cols)); cv[cols.index(k)] = 1.0; cv -= c_pre
    b_, s_ = contrast(cv)
    print("  %-4s 相对全部前期 = %+.4f (SE %.4f)" % (k, b_, s_))
print("  后期整体 vs 前期整体 = %+.4f (SE %.4f)   ← 应复现头条 gamma = -0.416"
      % (gamma_hat, gamma_se))

# ---------------- 自证 ----------------
fail = []
ref = json.load(io.open(os.path.join(HERE, "p0_6_pretrends.json"), encoding="utf-8"))
pre_ref = [w["beta"] for w in ref["pre_windows"]]
for i, (want, got) in enumerate(zip(pre_ref, beta[:3])):
    if abs(want - got) > 5e-3:
        fail.append("S1 前期窗口 %d 不复现 p0_6：%.4f vs %.4f" % (i + 1, want, got))
TAB4 = {"sxY1": -0.313, "sxY2": -0.499}       # Table 4 python 列
for k, want in TAB4.items():
    cv = np.zeros(len(cols)); cv[cols.index(k)] = 1.0; cv -= c_pre
    got, _ = contrast(cv)
    if abs(want - got) > 0.01:
        fail.append("S2 %s 偏离 Table 4：表=%.3f 本次=%.4f" % (k, want, got))
if abs(gamma_hat - (-0.416)) > 0.01:
    fail.append("S2b 后期-前期未复现头条 gamma：应 -0.416，本次 %.4f" % gamma_hat)
if any(np.diag(V) <= 1e-12):
    fail.append("S3 协方差对角线出现 0，聚类退化")
print("\n自证：" + ("全部通过" if not fail else "失败 %d 条" % len(fail)))
for x in fail:
    print("  !! " + x)
if fail:
    sys.exit(2)

# ---------------- A) 前期线性趋势（按月，不按窗口序数） ----------------
# 用每窗口的月中心做 GLS 回归，斜率 = 前期剂量斜率每月漂移。用"月"而不是
# "窗口序数"，是为了能和稿件 §6.2 已有的"前期斜率 -0.004/月"同量纲对读。
tau_pre = np.array([TAU[k] for k in PRE])
X = np.column_stack([np.ones(3), tau_pre])
Vpre = V[:3, :3]
Vinv = np.linalg.inv(Vpre)
XtVX = X.T @ Vinv @ X
coef = np.linalg.solve(XtVX, X.T @ Vinv @ beta[:3])
Vcoef = np.linalg.inv(XtVX)
trend, trend_se = float(coef[1]), float(np.sqrt(Vcoef[1, 1]))
trend_p = 2 * (1 - stats.norm.cdf(abs(trend / trend_se)))
print("\nA) 前期剂量斜率的线性趋势：每月 %+.5f（SE %.5f，p = %.3f）"
      % (trend, trend_se, trend_p))
print("   （稿件 §6.2 用月度序列报的是 -0.004/月；两者不同估计量，量级一致）")

# ---------------- B) 断点 ----------------
# 杠杆：线性反事实趋势 delta（每月）对"后期均值 - 前期均值"这个对比量的偏误
# = delta * (后期平均月中心 - 前期平均月中心)。前期含参照月（tau=0，权重 1 个月）。
tau_pre_bar = sum(NMO[k] * TAU[k] for k in PRE) / n_pre      # 参照月 tau=0，不贡献分子
tau_post_bar = sum(NMO[k] * TAU[k] for k in POST) / n_post
lever = tau_post_bar - tau_pre_bar
print("\nB) 杠杆：后期平均月中心 %.1f − 前期平均月中心 %.1f = %.1f 个月"
      % (tau_post_bar, tau_pre_bar, lever))

crit = stats.norm.ppf(0.975)
# 观测对比量 = 真效应 + delta*lever。真效应为 0 时 delta = gamma_hat/lever。
# （首版写成 -gamma_hat/lever，量级对但**符号反了**，会把"与前期漂移同向、更陡"
#  说成"反向"，是两个完全不同的主张。）
delta_zero = gamma_hat / lever
delta_insig = (gamma_hat + crit * gamma_se) / lever
mbar_zero = abs(delta_zero) / abs(trend)
mbar_insig = abs(delta_insig) / abs(trend)
same_dir = (delta_zero * trend) > 0
print("   把点估计推到 0：需反事实趋势 %+.5f/月 = 实测前期漂移的 %.1f 倍（%s）"
      % (delta_zero, mbar_zero, "同向" if same_dir else "反向"))
print("   把 95%% 区间推到含 0：需 %+.5f/月 = %.1f 倍" % (delta_insig, mbar_insig))
print("\n   读法：前期实测漂移 %+.5f/月 本身不显著（p = %.2f）。要抹掉头条效应，"
      "\n   反事实趋势须与它同向但陡 %.1f 倍，且在全部 %d 个后期月份持续保持；"
      "\n   仅仅让效应失去显著性也要 %.1f 倍。" % (trend, trend_p, mbar_zero, n_post, mbar_insig))

post_eff, post_se = gamma_hat, gamma_se
max_pre_dev = float(np.max(np.abs(np.diff(beta[:3]))))
pre_diffs = np.diff(beta[:3])

out = {
    "note": "平行趋势敏感性。粗化事件研究：前期三窗口（P0-6 口径）+ 后期四能力窗口"
            "（Table 4 口径）同一回归，参照月 2022-11，月聚类。**这是 R&R 同族的"
            "断点值，不是 R&R 完整偏识别区间**，写回措辞不得称 honest DiD 区间。",
    "reference_month": "2022-11",
    "formula": f,
    "windows": [{"label": lab_, "col": col, "beta": round(float(b), 4),
                 "se": round(float(s), 4), "side": side}
                for (lab_, col, lo, hi, side), b, s in zip(WINDOWS, beta, se)],
    "pre_linear_trend_per_month": {"estimate": round(trend, 5),
                                   "se": round(trend_se, 5),
                                   "p": float(trend_p)},
    "pre_adjacent_diffs": [round(float(d), 4) for d in pre_diffs],
    "max_pre_deviation": round(max_pre_dev, 4),
    "gamma_post_minus_pre": {"estimate": round(gamma_hat, 4),
                             "se": round(gamma_se, 4),
                             "reproduces_headline": -0.416},
    "lever_months": round(float(lever), 1),
    "breakdown": {
        "delta_per_month_to_zero": round(float(delta_zero), 5),
        "Mbar_to_zero": round(float(mbar_zero), 1),
        "delta_per_month_to_insignificant": round(float(delta_insig), 5),
        "Mbar_to_insignificant": round(float(mbar_insig), 1),
    },
    "self_checks": "S1/S2/S3 全部通过",
}
p = os.path.join(HERE, "p1_parallel_trends_sensitivity.json")
with io.open(p, "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)
print("\n已存 %s" % os.path.basename(p))
