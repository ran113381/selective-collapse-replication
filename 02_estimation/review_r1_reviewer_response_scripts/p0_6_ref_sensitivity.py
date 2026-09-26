# -*- coding: utf-8 -*-
u"""Sensitivity of the joint pre-period test to the choice of reference month.

The first-pass results are all measured against the single month 2022-11, whose
mean score of 2.98 is the highest of the surrounding half-year. With 100 questions
a month, a reference month that happens to draw a high batch can turn "all three
pre-period windows are significantly negative" into an artefact of the reference
rather than a trend.

Three versions that do not rest on 2022-11 alone:
  V1  reference = the mean of September to November 2022
  V2  reference = the whole six months June to November 2022
  V3  test whether the windows differ from each other (W1 = W2 = W3), which
      involves no reference level at all and so removes the confound entirely.
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


def ymi(y):
    a, b = y.split("-")
    return int(a) * 12 + int(b) - 1


EVENT = ymi("2022-12")
REF = ymi("2022-11")

wpy = pd.read_csv(os.path.join(DATA, "within_so_llm_panel.csv"))
d = wpy.melt(id_vars=["ym"], value_vars=["s1", "s2", "s3", "s4"], var_name="bin", value_name="cnt")
d["s"] = d["bin"].str[1].astype(int)
d["t"] = d["ym"].map(ymi)
d["lc"] = np.log(d["cnt"].clip(lower=1))

print("=" * 78)
print("先确认参照月本身是不是异常值（不看回归，直接看原始面板）")
print("=" * 78)
w = wpy.copy()
w["n"] = w.s1 + w.s2 + w.s3 + w.s4
w["mean_s"] = (w.s1 * 1 + w.s2 * 2 + w.s3 * 3 + w.s4 * 4) / w.n
nov = w[w.ym == "2022-11"].mean_s.iloc[0]
near = w[(w.ym >= "2022-05") & (w.ym <= "2022-10")].mean_s
print("  2022-11（REF）mean_s = %.3f" % nov)
print("  前 6 个月（2022-05..2022-10）mean_s：%s，均值 %.3f，SD %.3f"
      % ([round(x, 2) for x in near], near.mean(), near.std()))
z = (nov - near.mean()) / near.std()
print("  2022-11 相对前 6 个月的 z 分数 = %.2f（|z|>1.5 视为可疑偏高）" % z)


def fit_pre_windows(ref_mask, tag):
    u"""ref_mask: 布尔序列，标出哪些月份充当参照（这些月不参与任何窗口虚拟变量）。"""
    pre = d[d.t <= REF].copy()
    is_ref = pre.t.isin(d.loc[ref_mask, "t"].unique())
    windows = [("W1", ymi("2021-06"), ymi("2021-11")),
               ("W2", ymi("2021-12"), ymi("2022-05")),
               ("W3", ymi("2022-06"), ymi("2022-10"))]
    # 把参照月排除出所有窗口（若某窗口与参照月重叠，收窄该窗口）
    active_windows = []
    for name, lo, hi in windows:
        months_in = sorted(t for t in pre.t.unique() if lo <= t <= hi and t not in d.loc[ref_mask, "t"].unique())
        if len(months_in) == 0:
            continue
        active_windows.append((name, months_in))
    for name, months_in in active_windows:
        pre[f"sx_{name}"] = pre.s * pre.t.isin(months_in).astype(int)
    win_cols = [f"sx_{n}" for n, _ in active_windows]
    f = "lc ~ " + " + ".join(win_cols) + " + C(bin) + C(ym)"
    m = smf.ols(f, pre).fit(cov_type="cluster", cov_kwds={"groups": pre["ym"]})
    beta = np.array([m.params[c] for c in win_cols])
    V = m.cov_params().loc[win_cols, win_cols].to_numpy()
    Vinv = np.linalg.inv(V)
    wald = float(beta @ Vinv @ beta)
    df = len(beta)
    p = float(1 - stats.chi2.cdf(wald, df))
    print("\n[%s]  参照 = %s" % (tag, sorted(d.loc[ref_mask, 'ym'].unique().tolist())))
    for (name, months_in), b in zip(active_windows, beta):
        se = np.sqrt(V[win_cols.index(f"sx_{name}"), win_cols.index(f"sx_{name}")])
        print("  %-4s (%d月, %s..%s)  beta=%+.4f  SE=%.4f  t=%+.2f"
              % (name, len(months_in),
                 f"{months_in[0]//12:04d}-{months_in[0]%12+1:02d}",
                 f"{months_in[-1]//12:04d}-{months_in[-1]%12+1:02d}", b, se, b / se))
    print("  联合 Wald: W=%.2f df=%d p=%.4f  -> %s" % (wald, df, p, "显著非零" if p < 0.05 else "不能拒绝为零"))
    return {"tag": tag, "windows": [{"name": n, "months": len(mi), "beta": float(b), "se": float(np.sqrt(V[i, i]))}
                                     for i, (n, mi) in enumerate(active_windows) for b in [beta[i]]],
            "wald": wald, "df": df, "p": p}


print()
print("=" * 78)
print("稳健性：换不同参照，看'前期显著非零'这个结论还在不在")
print("=" * 78)

r_v0 = fit_pre_windows(d.t == REF, "V0 原版：参照=2022-11 单月")
r_v1 = fit_pre_windows(d.t.isin([ymi("2022-09"), ymi("2022-10"), ymi("2022-11")]),
                        "V1：参照=2022年9-11月三月均值")
r_v2 = fit_pre_windows(d.t.isin([ymi(f"2022-{m:02d}") for m in range(6, 12)]),
                        "V2：参照=2022年6-11月六月均值")

print()
print("=" * 78)
print("V3：不设任何单独参照——直接检验三窗口彼此是否有别（H0: W1=W2=W3）")
print("=" * 78)
pre = d[d.t <= REF].copy()
windows = [("W1", ymi("2021-06"), ymi("2021-11")),
           ("W2", ymi("2021-12"), ymi("2022-05")),
           ("W3", ymi("2022-06"), ymi("2022-11"))]  # 含 REF，三窗口均分整个前期
for name, lo, hi in windows:
    pre[f"sx_{name}"] = pre.s * ((pre.t >= lo) & (pre.t <= hi)).astype(int)
win_cols = [f"sx_{n}" for n, _, _ in windows]
# 不省略任何窗口，改省略 C(bin)/C(ym) 之外再删一个窗口列防止完全共线
f3 = "lc ~ sx_W2 + sx_W3 + C(bin) + C(ym)"   # W1 隐式做参照——此时"参照"是 6 个月的窗口，不是单月
m3 = smf.ols(f3, pre).fit(cov_type="cluster", cov_kwds={"groups": pre["ym"]})
b23 = np.array([m3.params["sx_W2"], m3.params["sx_W3"]])
V23 = m3.cov_params().loc[["sx_W2", "sx_W3"], ["sx_W2", "sx_W3"]].to_numpy()
wald23 = float(b23 @ np.linalg.inv(V23) @ b23)
p23 = float(1 - stats.chi2.cdf(wald23, 2))
print("  以 W1(6月, 2021-06..2021-11) 为参照：")
print("  W2 相对 W1: beta=%+.4f SE=%.4f" % (b23[0], np.sqrt(V23[0, 0])))
print("  W3 相对 W1: beta=%+.4f SE=%.4f" % (b23[1], np.sqrt(V23[1, 1])))
print("  联合检验 H0: W2=W1 且 W3=W1（即前期内部无结构）：W=%.2f df=2 p=%.4f -> %s"
      % (wald23, p23, "前期内部确有结构（窗口间有别）" if p23 < 0.05 else "不能拒绝——前期内部平坦，窗口间无显著差异"))

print()
print("=" * 78)
print("汇总：三种不同参照下，'联合非零'检验的 p 值")
print("=" * 78)
for r in (r_v0, r_v1, r_v2):
    print("  %-32s W=%6.2f  p=%.2e" % (r["tag"], r["wald"], r["p"]))
print("  V3（窗口互比，不涉及参照月绝对水平）             W=%6.2f  p=%.4f" % (wald23, p23))

out = {"note": "Reference-month sensitivity: the pre-period test against V0 (one month), V1 (three months) "
               "and V2 (six months), and V3, windows compared with each other with no reference.",
       "reference_month_check": {"ref_2022_11_mean_s": float(nov),
                                  "neighbor_6mo_mean": float(near.mean()),
                                  "neighbor_6mo_sd": float(near.std()),
                                  "z_score": float(z)},
       "variants": [r_v0, r_v1, r_v2],
       "v3_within_pretrend_structure": {"beta_W2_vs_W1": float(b23[0]), "beta_W3_vs_W1": float(b23[1]),
                                         "wald": wald23, "df": 2, "p": p23}}
op = os.path.join(OUT_DIR, "p0_6_ref_sensitivity.json")
json.dump(out, io.open(op, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("\n写入 %s" % op)
