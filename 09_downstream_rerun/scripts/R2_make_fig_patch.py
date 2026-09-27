# -*- coding: utf-8 -*-
"""由共用图脚本 P9_legB_短文_20260704\\make_figures_p9b.py 派生 IPM 专用 make_figures_ipm.py(R2 盲标签版)。

只做以下替换,每处断言恰好命中一次,其余画法、字号、配色、版面逐字不动:
  1 数据目录 → 盲标签镜像(R2_downstream\\blind\\data);量重构序列 → 盲镜像的 absolute_volume_series_python.csv
  2 图 4A 三语言:四行(python 盲 / python 原 / javascript 原 / java 原),数值读 R2_analyze_result.json 与原镜像 capability_ramp.json
  3 图 5B 效标:读 R2c_result.json 的共同子样本解出率(第三轮)
  4 图 3 估计量、图 6 窗口、图 7 κ、图 8 绝对量:数值全部改为读 R2 产物 JSON,不再照抄表格
输出目录 P9b_IPM_20260919\\figures(与 PNAS 版分开;PNAS 版图不再更新)。
"""
import io, os, sys

sys.stdout.reconfigure(encoding="utf-8")
SRC = r"E:\智能体论文\P9_legB_短文_20260704\make_figures_p9b.py"
DST = r"E:\智能体论文\P9b_IPM_20260919\make_figures_ipm.py"
t = io.open(SRC, encoding="utf-8").read()
R = []


def rep(old, new):
    global t
    assert t.count(old) == 1, "未命中或多处命中: " + old[:60]
    t = t.replace(old, new)
    R.append(old[:40])


rep('"""P9b figures v2 — three multi-panel figures at PNAS Nexus spec.',
    '"""P9b figures — IPM version on the R2 blind labels (derived from make_figures_p9b.py by\n'
    '工作文档\\\\R2_make_fig_patch.py; do not edit by hand, re-run the patch).\n'
    'Every number is read from an R2 result file; nothing is copied from a table.\n\n'
    'Original header follows.\nP9b figures v2 — three multi-panel figures at PNAS Nexus spec.')
rep('DATA = r"E:\\智能体论文\\_legB_data"  # persistent extract of the leg-B panels/questions/labels',
    'R2 = r"E:\\智能体论文\\P9b_IPM_20260919\\工作文档"\n'
    'DATA = os.path.join(R2, "R2_downstream", "blind", "data")   # 盲标签镜像:python 面板、题级标签、事件研究\n'
    'ORIG_EST = os.path.join(R2, "R2_downstream", "orig", "02_estimation")\n'
    'BLIND_EST = os.path.join(R2, "R2_downstream", "blind", "02_estimation")\n'
    'J = lambda *p: json.load(open(os.path.join(*p), encoding="utf-8"))\n'
    'A2 = J(R2, "R2_analyze_result.json")\n'
    'RAMP_B = {r["window"]: r for r in J(BLIND_EST, "capability_ramp.json")["python"]["windowed"]}\n'
    'RAMP_O = J(ORIG_EST, "capability_ramp.json")\n'
    'WT = J(R2, "R2d_extra_result.json")["blind"]["stats"]["window_tests"]\n'
    'KP = J(R2, "R2d_kappa_result.json")\n'
    'AVJ = J(BLIND_EST, "absolute_volume.json")')
rep('ABS = "E:/智能体论文/P9_修订_20260703/replication_additions/absolute_volume_series_python.csv"',
    'ABS = os.path.join(BLIND_EST, "absolute_volume_series_python.csv")')
# ---- 图 4A:三语言 → 四行 ----
rep('''langs = [("python", -0.42, 0.07), ("javascript", -0.23, 0.07), ("java", -0.12, 0.05)]
for y, (lg, g, se) in zip([2, 1, 0], langs):
    c = LANGC[lg]''',
    '''_full = lambda lang: next(r for r in RAMP_O[lang]["windowed"] if r["window"].startswith("full"))
langs = [("python", "python, blind", A2["blind"]["ols"]["coef"], A2["blind"]["ols"]["se"], True),
         ("python", "python, earlier", _full("python")["gamma"], _full("python")["se"], False),
         ("javascript", "javascript, earlier", _full("javascript")["gamma"], _full("javascript")["se"], False),
         ("java", "java, earlier", _full("java")["gamma"], _full("java")["se"], False)]
axA.axhline(2.5, color=GRID, lw=LW_REF, zorder=1)   # 盲 python 与其余三行分开:跨评分者不作比较
for y, (lg, lab4, g, se, filled) in zip([3, 2, 1, 0], langs):
    c = LANGC[lg]''')
rep('''    axA.plot(g, y, "o", color=c, ms=MS_MAIN, markeredgecolor=SURFACE,
             markeredgewidth=MEW, zorder=4)
    axA.annotate(f"{lg}  {g:+.2f}", xy=(g + 1.96 * se, y), xytext=(10, 0),''',
    '''    axA.plot(g, y, "o", color=c if filled else SURFACE, ms=MS_MAIN,
             markeredgecolor=c if not filled else SURFACE, markeredgewidth=MEW * (2 if not filled else 1), zorder=4)
    axA.annotate(f"{lab4}  {g:+.2f}", xy=(g + 1.96 * se, y), xytext=(10, 0),''')
rep('axA.set_yticks([]); axA.set_ylim(-0.6, 2.6); axA.set_xlim(-0.62, 0.30)',
    'axA.set_yticks([]); axA.set_ylim(-0.6, 3.6); axA.set_xlim(-0.62, 0.42)')
rep('axA.set_xlabel("Dose slope γ, 95% CI  (ordered by model coverage)")',
    'axA.set_xlabel("Dose slope γ, 95% CI")')
# ---- 图 5B:第三轮效标 ----
rep('''CRIT = "E:/智能体论文/P9_金标准_20260704/criterion"
wt = json.load(open(os.path.join(CRIT, "weak_tier_results.json"), encoding="utf-8"))["common_subset"]
tiers = [("Sonnet 5", "Sonnet 5 (paper)", "#14497F", "-", "o"),
         ("GLM-5.3", "GLM-5.3", "#3E85C6", "-", "s"),
         ("Haiku 4.5", "Haiku 4.5", "#C2603E", "--", "o"),
         ("GLM-4.6", "GLM-4.6", "#E8A07E", "--", "s")]''',
    '''wt = J(R2, "R2c_result.json")["common_subset"]      # 第三轮:四个答题者共同完成的题
tiers = [t_ for t_ in [("Sonnet 5", "sonnet5", "#14497F", "-", "o"),
                       ("GLM-5.3", "glm53", "#3E85C6", "-", "s"),
                       ("Haiku 4.5", "haiku45", "#C2603E", "--", "o"),
                       ("GLM-4.6", "glm46", "#E8A07E", "--", "s")] if t_[1] in wt]''')
rep('''    ys = [wt[key]["solve_by_bin"][f"s{b}"] for b in xs]''',
    '''    ys = [wt[key][f"s{b}"] for b in xs]''')
rep('axB.set_xlim(0.85, 4.65); axB.set_ylim(0.25, 1.02)',
    'axB.set_xlim(0.85, 4.65); axB.set_ylim(0.35, 1.02)')
# ---- 图 3:估计量 ----
rep('''SPECS = [  # (标签, γ, SE, 是否主规格)  —— 与 Table 3 完全一致
    ("log-count OLS (python)",        -0.42,  0.07, True),
    ("Fixed-total FE-PPML",           -0.37,  0.05, False),
    ("Newey–West log(s4/s1)",    -0.41,  0.04, False),
    ("Independent-family labels",     -0.227, 0.036, False),
    ("log-count OLS (javascript)",    -0.23,  0.07, False),
    ("log-count OLS (java)",          -0.12,  0.05, False),
]''',
    '''_cf = J(R2, "R2d_kappa_result.json")["cross_family"]["glm"]["per_point"]
SPECS = [  # (标签, γ, SE, 是否主规格) —— 读 R2 产物
    ("log-count OLS (python, blind)",   A2["blind"]["ols"]["coef"], A2["blind"]["ols"]["se"], True),
    ("Fixed-total FE-PPML",             A2["blind"]["ppml"]["coef"], A2["blind"]["ppml"]["se"], False),
    ("Newey–West log(s4/s1), per point", A2["blind"]["logratio_nw"]["coef"] / 3, A2["blind"]["logratio_nw"]["se"] / 3, False),
    ("Independent-family labels",       _cf[0], _cf[1], False),
    ("Earlier classification (python)", A2["original"]["ols"]["coef"], A2["original"]["ols"]["se"], False),
    ("Earlier (javascript)",            _full("javascript")["gamma"], _full("javascript")["se"], False),
    ("Earlier (java)",                  _full("java")["gamma"], _full("java")["se"], False),
]''')
rep('''ax.set_title("sign, order and significance hold across every estimator",''',
    '''ax.set_title("sign and significance hold across every estimator and classification",''')
# ---- 图 6:窗口 ----
rep('''WIN = [  # (窗口, python(γ,se), javascript, java) —— 与 Table 4 完全一致
    ("GPT-3.5 only\\n(3 mo)",   (-0.203, 0.169), (-0.015, 0.106), (-0.004, 0.101)),
    ("First 6 months",         (-0.271, 0.154), (-0.123, 0.120), (-0.066, 0.070)),
    ("Year 1",                 (-0.313, 0.102), (-0.088, 0.081), (-0.092, 0.066)),
    ("Year 2",                 (-0.499, 0.087), (-0.316, 0.081), (-0.204, 0.057)),
    ("Year 3",                 (-0.447, 0.071), (-0.296, 0.079), (-0.191, 0.067)),
    ("Year 4",                 (-0.391, 0.125), (-0.203, 0.112), (+0.110, 0.089)),
    ("Full post period",       (-0.416, 0.067), (-0.229, 0.067), (-0.123, 0.052)),
]''',
    '''_WK = [("GPT-3.5 only\\n(3 mo)", "GPT-3.5 only"), ("First 6 months", "first 6m"), ("Year 1", "y1 "),
       ("Year 2", "y2 "), ("Year 3", "y3 "), ("Year 4", "y4 "), ("Full post period", "full")]
def _w(rows, key):
    r = next(r for r in rows if r["window"].startswith(key)); return (r["gamma"], r["se"])
WIN = [(lab, _w(list(RAMP_B.values()), k), _w(RAMP_O["javascript"]["windowed"], k), _w(RAMP_O["java"]["windowed"], k))
       for lab, k in _WK]   # python 盲标签;javascript、java 原标签(唯一一套)''')
rep('''ax.set_title("windows are not statistically distinguishable (F = 1.10, p = .36)",''',
    '''ax.set_title(f"python (blind): four post years not equal, F = {WT['F']:.2f}, p = {WT['F_p']:.3f}".replace("p = 0.", "p = ."),''')
rep('''langs3 = [("python", 0), ("javascript", 1), ("java", 2)]''',
    '''langs3 = [("python", 0), ("javascript", 1), ("java", 2)]
_LBL3 = {"python": "python (blind)", "javascript": "javascript (earlier)", "java": "java (earlier)"}''')
rep('''                markeredgewidth=MEW_S, label=lname, zorder=3)''',
    '''                markeredgewidth=MEW_S, label=_LBL3[lname], zorder=3)''')
# ---- 图 7:κ ----
rep('''RATERS = [  # (标签, κ, lo, hi) —— 与 Table 5 完全一致
    ("Claude Sonnet 4.6 (primary)",   0.511, 0.412, 0.605),
    ("GLM-4.6",                       0.525, 0.423, 0.619),
    ("GLM-5.3 (frontier tier)",       0.571, 0.476, 0.659),
]''',
    '''_k = KP["kappa_vs_consensus"]
RATERS = [(lab, _k[key]["kappa"], _k[key]["ci"][0], _k[key]["ci"][1]) for lab, key in (
    ("Claude Sonnet 5 (blind, primary)", "blind"), ("Claude Sonnet 4.6 (earlier)", "orig"),
    ("GLM-4.6", "glm46"), ("GLM-5.3 (frontier tier)", "glm53"))]''')
rep('ax.set_ylim(-0.95, 2.5); ax.invert_yaxis()', 'ax.set_ylim(-0.95, 3.5); ax.invert_yaxis()')
rep('fig = plt.figure(figsize=(COL140, 2.4))', 'fig = plt.figure(figsize=(COL140, 2.75))')
# ---- 图 8:绝对量 ----
rep('''VOL = {  # 与 Table 11 完全一致（s1..s4 的 Δ%）
    "python":     [-63.6, -71.1, -76.7, -86.0],
    "javascript": [-74.9, -75.3, -81.1, -80.7],
    "java":       [-69.0, -71.6, -75.5, -78.7],
}
PLAT = {"python": -76.0, "javascript": -78.6, "java": -73.4}''',
    '''VOL = {lang: [round(100 * AVJ[f"absolute_by_bin_{lang}"][f"s{b}"]["pct_change"], 1) for b in (1, 2, 3, 4)]
       for lang in ("python", "javascript", "java")}   # python 盲标签;另两种原标签
PLAT = {lang: round(100 * AVJ[f"platform_total_{lang}"]["pct_change"], 1) for lang in ("python", "javascript", "java")}''')
# ---- 图 5A:盲标签下前期有点在零线之上,标签改放零线下方,免得压点 ----
rep('''axA.annotate("reference month", xy=(-1, 0), xytext=(-8, 4),
             textcoords="offset points", ha="right", va="bottom",''',
    '''axA.annotate("reference month", xy=(-1, 0), xytext=(-3, 0.135),
             textcoords="data", ha="right", va="center",
             arrowprops=dict(arrowstyle="-", color="#4a4a4a", lw=LW_REF, shrinkA=1, shrinkB=4),''')
rep("axA.set_xlim(kk.min() - 1.5, kk.max() + 1.5)",
    "axA.set_xlim(kk.min() - 1.5, kk.max() + 1.5); axA.set_ylim(top=0.19)")
# ---- 图 5B 线尾标签:旧版按模型名写死上下偏移,第三轮 GLM-5.3 终点高于 Sonnet 5、GLM-4.6 高于 Haiku 4.5,
#      标签会贴到对方的点上。改为同档两条线里终点高者标签在上 ----
rep('''    dy = {"Sonnet 5": 9, "GLM-5.3": -9, "Haiku 4.5": 8, "GLM-4.6": -8}[lab]''',
    '''    _grp = [t_ for t_ in tiers if t_[3] == ls]
    _hi = max(_grp, key=lambda t_: wt[t_[1]]["s4"])[0]
    dy = (9 if lab == _hi else -9) if len(_grp) > 1 else 0''')
# ---- save():PNG 紧边界与 PDF 紧边界可差 0.02 in(图 2B 右端数值标签),投出去的是 PDF,故存完按 PDF 实宽再校 ----
rep('''    fig.savefig(os.path.join(OUT, f"{name}.pdf"), bbox_inches="tight",
                pad_inches=PAD, facecolor=SURFACE)
    plt.close(fig)''',
    '''    fig.savefig(os.path.join(OUT, f"{name}.pdf"), bbox_inches="tight",
                pad_inches=PAD, facecolor=SURFACE)
    import re as _re
    for _ in range(5):   # 读 PDF MediaBox 实宽,偏离目标超过 0.003 in 就按差值收放画布重存两份
        _mb = _re.search(rb"/MediaBox\\s*\\[\\s*[\\d.]+\\s+[\\d.]+\\s+([\\d.]+)", open(os.path.join(OUT, f"{name}.pdf"), "rb").read())
        _w = float(_mb.group(1)) / 72.0
        if abs(_w - target) < 0.003:
            break
        w, h = fig.get_size_inches()
        fig.set_size_inches(w + (target - _w), h)
        fig.savefig(os.path.join(OUT, f"{name}.png"), bbox_inches="tight", pad_inches=PAD, facecolor=SURFACE, dpi=600)
        fig.savefig(os.path.join(OUT, f"{name}.pdf"), bbox_inches="tight", pad_inches=PAD, facecolor=SURFACE)
    plt.close(fig)''')
# ---- 图 1 箭头标签(2026-09-27 模拟审稿 I-22):同一构念不得拆到两支箭头上。只改 IPM 版,PNAS 源脚本不动 ----
rep('''for x1, x2, lab in ((22.7, 38.8, "AI substitutability"),
                    (61.2, 77.3, "task\\u2013technology fit")):
    arrow(x1, 37, x2, 37)
    ax.text((x1 + x2) / 2, 39.2, lab, ha="center", va="bottom",
            fontsize=FS_NOTE, color=MUTED, zorder=4)''',
    '''# 2026-09-27 模拟审稿 I-22:原先第一支标「AI substitutability」、第二支标「task–technology fit」,
# 把 §2.3 所说的同一构念拆到了两支箭头上。改为第一支标构念及其理论名,第二支标选择如何汇成可观测结果。
for x1, x2, lab in ((22.7, 38.8, "AI substitutability\\n(task\\u2013technology fit)"),
                    (61.2, 77.3, "choices aggregate\\ninto what is asked")):
    arrow(x1, 37, x2, 37)
    ax.text((x1 + x2) / 2, 39.2, lab, ha="center", va="bottom", linespacing=1.15,
            fontsize=FS_NOTE, color=MUTED, zorder=4)''')
io.open(DST, "w", encoding="utf-8").write(t)
print("写出 %s,替换 %d 处" % (DST, len(R)))
