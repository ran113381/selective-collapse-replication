# -*- coding: utf-8 -*-
u"""Event-study rebuild, windowed joint pre-period test, and its power.

The monthly coefficients gamma_k use a month-by-s regressor that lies inside a
single month cluster, so the OLS first-order conditions zero out that cluster's
score and the month-clustered SE is identically zero (degenerate). A joint Wald
test on the monthly coefficients is therefore impossible (singular covariance).
Instead the pre-period (k <= -2, before the reference month 2022-11) is split into
three windows of five to six months, and the windowed DiD with month-clustered SE
that the manuscript applies to the post period is applied to them. The windows
span several month clusters and are not degenerate.

Outputs:
  1) the monthly gamma_k, checked month by month against within_so_llm_eventstudy.csv;
  2) the three pre-period window regressions: coefficients and 3x3 clustered covariance;
  3) the joint Wald test H0: all three window slopes are zero;
  4) power against a linear-trend alternative (built as in StatsPAI pretrends_power:
     in units of the smallest SE, growing linearly with window order);
  5) three self-checks (chi2 cross-check, monotone power, power at the null = alpha).
"""
import io, json, os, sys
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8")

DATA = r"E:\智能体论文\_legB_data"
REP = r"E:\智能体论文\P9_修订_20260703\replication_additions"
OUT_DIR = os.path.join(REP, "review_r1")
os.makedirs(OUT_DIR, exist_ok=True)


def ymi(y):
    a, b = y.split("-")
    return int(a) * 12 + int(b) - 1


EVENT = ymi("2022-12")
REF = ymi("2022-11")

# ---------------- 数据（复用 capability_ramp.py 的口径：仅 python）----------------
wpy = pd.read_csv(os.path.join(DATA, "within_so_llm_panel.csv"))
d = wpy.melt(id_vars=["ym"], value_vars=["s1", "s2", "s3", "s4"], var_name="bin", value_name="cnt")
d["s"] = d["bin"].str[1].astype(int)
d["t"] = d["ym"].map(ymi)
d["lc"] = np.log(d["cnt"].clip(lower=1))

# ==================================================================
# 1) 重建月度 gamma_k，核对与已归档的 within_so_llm_eventstudy.csv 一致
# ==================================================================
months = sorted(d.t.unique())
cols = []
dd = d.copy()
for k in months:
    if k == REF:
        continue
    c = f"k{k}"
    dd[c] = (dd.t == k).astype(int) * dd.s
    cols.append(c)
formula = "lc ~ " + " + ".join(cols) + " + C(bin) + C(ym)"
m_month = smf.ols(formula, dd).fit()
es = pd.DataFrame({"t": [int(c[1:]) for c in cols], "gamma_k": [m_month.params[c] for c in cols]})
es["rel_month"] = es.t - EVENT

ref_file = pd.read_csv(os.path.join(DATA, "within_so_llm_eventstudy.csv"))
cmp = es.merge(ref_file, left_on="rel_month", right_on="k", suffixes=("_mine", "_ref"))
maxdiff = float((cmp.gamma_k_mine - cmp.gamma_k_ref).abs().max())
print("[1] 月度 gamma_k 重建 vs 归档文件：%d 个月匹配，最大差 = %.2e  -> %s"
      % (len(cmp), maxdiff, "OK 一致" if maxdiff < 1e-6 else "!! 不一致"))

# 月聚类 SE 是否真的退化（验证 capability_ramp.py 注释里的说法，不凭信任）
m_month_clustered = smf.ols(formula, dd).fit(cov_type="cluster", cov_kwds={"groups": dd["ym"]})
import numpy as _np
degenerate = all((_np.isnan(m_month_clustered.bse[c]) or m_month_clustered.bse[c] < 1e-8) for c in cols[:5])
print("[1'] 月聚类 SE 是否退化（抽查前 5 个月度系数）：%s（前 5 个 SE=%s）"
      % (degenerate, [round(m_month_clustered.bse[c], 6) for c in cols[:5]]))

# ==================================================================
# 2) 前期三窗口回归（非退化：每窗口跨 5-6 个月份簇）
# ==================================================================
# patsy 会把列名里的连字符/数字段解析成算术表达式（"2021-06" 被当成减法），
# 窗口标签只用于打印，参与公式的列名必须是纯字母数字、不含连字符。
PRE_WINDOWS = [("pre W1 2021-06..2021-11", "sxW1", ymi("2021-06"), ymi("2021-11")),
               ("pre W2 2021-12..2022-05", "sxW2", ymi("2021-12"), ymi("2022-05")),
               ("pre W3 2022-06..2022-10", "sxW3", ymi("2022-06"), ymi("2022-10"))]
pre = d[d.t <= REF].copy()  # 含参照月本身（不设虚拟变量，天然充当比较点）
for label, col, lo, hi in PRE_WINDOWS:
    pre[col] = pre.s * ((pre.t >= lo) & (pre.t <= hi)).astype(int)
    assert pre[col].astype(bool).sum() > 0

win_cols = [c for _, c, _, _ in PRE_WINDOWS]
f2 = "lc ~ " + " + ".join(win_cols) + " + C(bin) + C(ym)"
m_pre = smf.ols(f2, pre).fit(cov_type="cluster", cov_kwds={"groups": pre["ym"]})
beta = np.array([m_pre.params[c] for c in win_cols])
V = m_pre.cov_params().loc[win_cols, win_cols].to_numpy()
se = np.sqrt(np.diag(V))
print("\n[2] 前期三窗口回归（非退化聚类 SE）：")
for (label, col, lo, hi), b, s in zip(PRE_WINDOWS, beta, se):
    nmo = pre[(pre.t >= lo) & (pre.t <= hi)].t.nunique()
    print("  %-26s %2d 月  beta=%+.4f  SE=%.4f  t=%+.2f" % (label, nmo, b, s, b / s))
print("  月聚类 SE 是否退化（应为否）：%s" % any(s < 1e-8 for s in se))

# ==================================================================
# 3) 联合 Wald 检验：H0 三窗口斜率皆为 0
# ==================================================================
Vinv = np.linalg.inv(V)
wald = float(beta @ Vinv @ beta)
df = len(beta)
p_wald = float(1 - stats.chi2.cdf(wald, df))
print("\n[3] 联合 Wald 检验  H0: beta_W1=beta_W2=beta_W3=0")
print("  W = %.3f, df = %d, p = %.4f" % (wald, df, p_wald))
print("  结论：%s" % ("不能拒绝——与'前期无加速'相容（但见下方功效，判断这是否只是没查出来）"
                      if p_wald > 0.05 else "拒绝——前期存在联合显著的斜率变化"))

# ==================================================================
# 4) 功效：针对线性趋势备择（仿 StatsPAI 默认：以最小 SE 为单位、按窗口序数线性增长）
# ==================================================================
alpha = 0.05
crit = stats.chi2.ppf(1 - alpha, df)
min_se = float(se.min())


def power_at(scale):
    """delta_j = scale * j * min_se，j=1,2,3（离参照月越远，假设的偏离越大）。"""
    delta = scale * np.arange(1, len(beta) + 1) * min_se
    ncp = float(delta @ Vinv @ delta)
    return 1 - stats.ncx2.cdf(crit, df, ncp), ncp


rows = []
for scale in (0.0, 0.5, 1.0, 2.0, 4.0):
    pw, ncp = power_at(scale)
    rows.append((scale, ncp, pw))
    print("  scale=%.1f  (最远窗口偏离 = %.1f 个最小SE)  ncp=%.2f  功效=%.3f" % (scale, scale * 3, ncp, pw))

# 默认备择（scale=1，即"最远窗口偏离一个最小 SE，线性衰减到近端"）
pw_default, ncp_default = power_at(1.0)
print("\n  默认备择下的功效 = %.3f" % pw_default)
print("  解读：功效%s——'前期没查出联合显著'%s"
      % ("低" if pw_default < 0.5 else "尚可",
         "主要是没查出来，不能读成'确认平坦'" if pw_default < 0.5 else "在这个备择规模下确有一定说服力"))

# ---------------- 自检（不写进稿件，写进日志）----------------
print("\n[自检]")
# a) chi2 计算对照 scipy 直接实现
chk = stats.chi2.sf(wald, df)
print("  a) 1-cdf 与 sf 应等价：|%.10f - %.10f| = %.2e -> %s"
      % (p_wald, chk, abs(p_wald - chk), "OK" if abs(p_wald - chk) < 1e-9 else "FAIL"))
# b) 功效应随 scale 单调不减
pw_seq = [power_at(s)[0] for s in (0.0, 0.5, 1.0, 2.0, 4.0)]
mono = all(pw_seq[i] <= pw_seq[i + 1] + 1e-9 for i in range(len(pw_seq) - 1))
print("  b) 功效随备择规模单调不减：%s  序列=%s" % (mono, [round(x, 3) for x in pw_seq]))
# c) scale=0 时功效应等于 alpha（无偏离即退回到检验水平）
print("  c) scale=0 功效应≈alpha=0.05：得 %.4f -> %s" % (pw_seq[0], "OK" if abs(pw_seq[0] - alpha) < 1e-6 else "FAIL"))

bad = (maxdiff >= 1e-6) or (not degenerate) or any(s < 1e-8 for s in se) or (abs(p_wald - chk) >= 1e-9) or (not mono) or (abs(pw_seq[0] - alpha) >= 1e-6)
print("\n自检总结：%s" % ("全部通过" if not bad else "!! 有未通过项，不要下游使用"))

# ---------------- 归档 ----------------
out = {
    "note": "Monthly gamma_k have degenerate month-clustered SEs (as capability_ramp.py notes), "
            "so the joint pre-period test uses three pre-period window regressions, not the monthly estimates.",
    "monthly_gamma_k_validated_against_archive": {"n_matched": len(cmp), "max_abs_diff": maxdiff},
    "monthly_cluster_se_degenerate": bool(degenerate),
    "pre_windows": [{"window": label, "lo": lo, "hi": hi,
                      "months": pre[(pre.t >= lo) & (pre.t <= hi)].t.nunique(),
                      "beta": float(b), "se": float(s)}
                     for (label, col, lo, hi), b, s in zip(PRE_WINDOWS, beta, se)],
    "pre_window_vcov": V.tolist(),
    "joint_wald": {"statistic": wald, "df": df, "p": p_wald},
    "power_by_scale": [{"scale": s, "ncp": ncp, "power": pw} for s, ncp, pw in rows],
    "power_default_scale1": pw_default,
    "self_checks_all_passed": bool(not bad),
}
op = os.path.join(OUT_DIR, "p0_6_pretrends.json")
json.dump(out, io.open(op, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("\n写入 %s" % op)
