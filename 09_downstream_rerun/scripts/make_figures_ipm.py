# -*- coding: utf-8 -*-
"""P9b figures — IPM version on the R2 blind labels (derived from make_figures_p9b.py by
工作文档\\R2_make_fig_patch.py; do not edit by hand, re-run the patch).
Every number is read from an R2 result file; nothing is copied from a table.

Original header follows.
P9b figures v2 — three multi-panel figures at PNAS Nexus spec.
600 dpi PNG + vector PDF. Palette from the dataviz skill (validated):
  ordinal blue ramp (bins s1-s4)  #86b6ef #5598e7 #2a78d6 #184f95
  categorical (languages)         #2a78d6 python / #1baf7a javascript / #4a3aa7 java
Chrome: surface #fcfcfb, ink #0b0b0b/#52514e, muted #898781, grid #e1e0d9, baseline #c3c2b7.

Figure 1 (headline)     A scissors (indexed monthly counts by bin)  | B estimator robustness (OLS/PPML/log-ratio)
Figure 3 (robustness)   A three-language dose slopes                | B matched-window placebo cutoffs
Figure 3 (dynamics)     A event-study pre-trend                     | B answer margin: full vs cohort-age-restricted
Every panel recomputes from raw data; nothing is hardcoded except the archived
composition/permutation numbers cross-checked against phaseA_composition.py.
"""
import os, json, csv
import numpy as np
import pandas as pd
import statsmodels.api as sm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.gridspec import GridSpec

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "figures")
os.makedirs(OUT, exist_ok=True)
R2 = r"E:\智能体论文\P9b_IPM_20260919\工作文档"
DATA = os.path.join(R2, "R2_downstream", "blind", "data")   # 盲标签镜像:python 面板、题级标签、事件研究
ORIG_EST = os.path.join(R2, "R2_downstream", "orig", "02_estimation")
BLIND_EST = os.path.join(R2, "R2_downstream", "blind", "02_estimation")
J = lambda *p: json.load(open(os.path.join(*p), encoding="utf-8"))
A2 = J(R2, "R2_analyze_result.json")
RAMP_B = {r["window"]: r for r in J(BLIND_EST, "capability_ramp.json")["python"]["windowed"]}
RAMP_O = J(ORIG_EST, "capability_ramp.json")
WT = J(R2, "R2d_extra_result.json")["blind"]["stats"]["window_tests"]
KP = J(R2, "R2d_kappa_result.json")
AVJ = J(BLIND_EST, "absolute_volume.json")
EVENT = 2022 * 12 + 11

SURFACE, INK, INK2, MUTED = "#ffffff", "#111111", "#3f3f3f", "#767676"
GRID, BASE = "#d4d4d4", "#6e6e6e"
TICK = "#4a4a4a"      # 刻度数字：比 MUTED 深，缩印后仍读得出；MUTED 留给次要注记
# 配色对照过真实 IPM 论文(如 IPM 63(1) 的开放获取稿)与作者本人已过 IPM 评审的
# paper1：该刊惯用 viridis/spectral 这类**有真实色相变化**的科学色图，而不是
# 单一色相只改深浅。此处取 plasma 在 0.05/0.38/0.62/0.82 四点的采样，既保持
# s1->s4 的序（明度与色相同向推进），四档之间又两两可辨，且 plasma 本身是
# 感知均匀、对色觉障碍友好的色图：明度沿 s1->s4 单调上升，灰度打印仍能排序。
# (曾另备一组线型做冗余编码，但四条线同时虚线化会让图 1A 过于花，已弃用。)
RAMP = ["#290593", "#AA2494", "#E46A5D", "#FCAD31"]           # s1..s4
# 语言按代码模型覆盖度有序(python>javascript>java)，同族深->浅
LANGC = {"python": "#290593", "javascript": "#AA2494", "java": "#E46A5D"}
PRE, POST = "#9a9a9a", "#290593"
ACCENT = "#C1272D"

# ---- 线宽体系：按"角色"统一，而不是把所有线改成同一个数 ----
# 同一角色在七张图里必须同宽；不同角色之间靠宽度分层，读者不看图注也能知道
# 哪条是数据、哪条是区间、哪条是参考线。此前是一张图一张图微调出来的，
# 数据序列有 2.0/1.5/2.3 三种、区间主杆有 3.0/2.6/2.2/1.6 四种。
# 下列数值是按 190 mm 成品宽定的。**线宽和点径与字号一样以「点」为单位**，
# 画布从 11–12 in 收到 7.48 in 之后，若不同步收，墨量相对就重了三成。
LW_SERIES = 1.3    # 数据序列（时间序列折线）
LW_LEVEL = 1.7     # 由数据算出、且本身就是结论的水平线（图1B 的后期均值）
LW_CI = 1.7        # 森林图里的主置信区间
LW_CI_THIN = 1.2   # 同图中的次要规格，或密集排布的区间（图5 的 21 条）
LW_CAP = 1.0       # 区间端帽
LW_REF = 0.8       # 参考线：零线、基线、事件线、天花板线、拟合外推线
LW_GRID = 0.4      # 网格
LW_SPINE = 0.6     # 外框
MEW, MEW_S = 0.7, 0.5   # 标记描边（小点用 MEW_S，免得白圈吃掉点）
# 点径同理，也按角色统一
MS_EMPH = 7.8      # 需要一眼找到的点（图3B 的真实事件）
MS_MAIN = 5.5      # 森林图主点
MS_MID = 4.3       # 次级点 / 折线上的标记
MS_SMALL = 3.8     # 小点
MS_TINY = 3.2      # 密排背景点

# ---- 版面：按刊方真实印出尺寸出图 ----
# Elsevier 会把投来的图按栏宽缩放。此前七张画布宽 6.9–12.2 in 不等，缩放系数
# 0.61–1.08，同样写 9.5 pt 的刻度，图1 印出来只有 5.8 pt、图6 有 10.3 pt——
# 差 1.8 倍，读者翻页直接看得出。解法是**按最终尺寸出图**：七张一律做成双栏
# 190 mm 宽，缩放系数恒为 1，写多少就印多少，字号这才谈得上统一。
COL = 7.48         # 190 mm 双栏
COL140 = 5.51      # 140 mm —— Elsevier 标准栏宽之一（30/90/140/190）。
                   # 只给 κ 图用：它只有三行数据，强行拉到 190 mm 后宽高比 3.33:1，
                   # 而其余七张都在 2.16–2.66，独它像一条带子。save() 是按**存出宽度**
                   # 反推画布的，而 matplotlib 字号是绝对磅值，所以换宽度不动印出字号。
PAD = 0.02         # savefig 两侧留白
FS_TICK = 7.5      # 刻度数字 / 行标签
FS_LABEL = 8.5     # 轴标题
FS_PANEL = 9.5     # 面板字母 A/B
FS_LEG = 7.5       # 图例条目
FS_LEGT = 8.0      # 图例标题
FS_ANNOT = 7.5     # 图内注记
FS_VALUE = 8.0     # 数值标签
FS_NOTE = 7.0      # 角注
FS_SMALL = 7.0     # 柱内数值 / 密排注记
# ACCENT 的零线只用在森林图上（读者要读"区间是否跨零"）；散点/事件研究里的
# y=0 只是坐标锚点，用 BASE 灰，不抢红色。

plt.rcParams.update({
    "font.sans-serif": ["DejaVu Sans", "Arial"], "font.family": "sans-serif",
    "axes.unicode_minus": False, "savefig.dpi": 600, "figure.dpi": 600,
    "font.size": FS_LABEL, "axes.labelsize": FS_LABEL,
    "xtick.labelsize": FS_TICK, "ytick.labelsize": FS_TICK,
    "axes.edgecolor": BASE, "axes.linewidth": LW_SPINE, "text.color": INK,
    "axes.labelcolor": INK2, "xtick.color": TICK, "ytick.color": TICK,
    # Type 3 是 matplotlib 默认，字形虽嵌入但文字不可选中/检索；42=TrueType 可选中，
    # 也是多数出版社偏好的内嵌方式。外观零变化。
    "pdf.fonttype": 42, "ps.fonttype": 42,
})


LEGLBL = ("s1 (least substitutable)", "s2", "s3", "s4 (most substitutable)")


def ym_int(ym): y, m = ym.split("-"); return int(y) * 12 + (int(m) - 1)


def panel_label(ax, s):
    # IPM 惯例：面板标签小号朴素置于左上，不是超大粗体
    ax.text(0.0, 1.02, s, transform=ax.transAxes, fontsize=FS_PANEL, fontweight="bold",
            va="bottom", ha="left", color=INK)


def framed(ax):
    """IPM/ggplot theme_bw 风格：四周细框 + 细网格。"""
    for sp in ax.spines.values():
        sp.set_visible(True)
        sp.set_color(BASE)
        sp.set_linewidth(LW_SPINE)
    ax.tick_params(length=2, color=BASE)
    ax.set_axisbelow(True)


def below_legend(ax, ncol, y=-0.20, **kw):
    """图例横排放在 x 轴下方。条目少而短时比右侧竖排省地方：右侧图例要占掉约
    13% 的画布宽，而三个条目只用掉那一竖列的上半截，右下角空出一大块。横排后
    绘图区吃满整幅宽度。条目名自明时不给图例标题，省一行。"""
    lg = ax.legend(frameon=False, fontsize=FS_LEG, ncol=ncol,
                   loc="upper center", bbox_to_anchor=(0.5, y),
                   handlelength=1.9, columnspacing=2.6, borderaxespad=0.0, **kw)
    return lg


def side_legend(ax, title, **kw):
    """IPM 惯例：图例出框放右侧并带图例标题，不占数据区。"""
    lg = ax.legend(title=title, frameon=False, fontsize=FS_LEG,
                   loc="upper left", bbox_to_anchor=(1.01, 1.0),
                   handlelength=1.9, labelspacing=0.45, borderaxespad=0.0, **kw)
    lg.get_title().set_fontsize(FS_LEGT)
    lg.get_title().set_color(INK2)
    lg.get_title().set_fontweight("bold")
    return lg


def year_axis(ax):
    import matplotlib.dates as mdates
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))


def finish(ax, right=True, left=True):
    for sp in (["top", "right"] if right else ["top"]):
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(BASE)
    if left:
        ax.spines["left"].set_color(BASE)
    ax.tick_params(length=2.2)


def save(fig, name, target=COL):
    """让**存出来的图**正好是目标栏宽，而不是让 figsize 正好是目标栏宽。
    这两件事不是一回事：bbox_inches="tight" 会把跑到画布外的图例和长标签一起
    框进来，存出来常比 figsize 宽一大截（图7 曾 figsize 7.6 in、存成 8.72 in）。
    刊方按图的实际宽度缩放，盯错对象，前面调的字号全部白调。
    tight 宽度 = f*画布宽 + 常数（图例/标签的固定占位），故可迭代反推，
    收敛因子 |1-f| 约 0.22，几轮到位。"""
    fig.patch.set_facecolor(SURFACE)
    for ax in fig.axes:
        ax.set_facecolor(SURFACE)
    goal = target - 2 * PAD
    bb = None
    for _ in range(10):
        fig.canvas.draw()
        bb = fig.get_tightbbox(fig.canvas.get_renderer())
        if abs(bb.width - goal) < 0.004:
            break
        w, h = fig.get_size_inches()
        fig.set_size_inches(w + (goal - bb.width), h)
    fig.savefig(os.path.join(OUT, f"{name}.png"), bbox_inches="tight",
                pad_inches=PAD, facecolor=SURFACE, dpi=600)
    fig.savefig(os.path.join(OUT, f"{name}.pdf"), bbox_inches="tight",
                pad_inches=PAD, facecolor=SURFACE)
    import re as _re
    for _ in range(5):   # 读 PDF MediaBox 实宽,偏离目标超过 0.003 in 就按差值收放画布重存两份
        _mb = _re.search(rb"/MediaBox\s*\[\s*[\d.]+\s+[\d.]+\s+([\d.]+)", open(os.path.join(OUT, f"{name}.pdf"), "rb").read())
        _w = float(_mb.group(1)) / 72.0
        if abs(_w - target) < 0.003:
            break
        w, h = fig.get_size_inches()
        fig.set_size_inches(w + (target - _w), h)
        fig.savefig(os.path.join(OUT, f"{name}.png"), bbox_inches="tight", pad_inches=PAD, facecolor=SURFACE, dpi=600)
        fig.savefig(os.path.join(OUT, f"{name}.pdf"), bbox_inches="tight", pad_inches=PAD, facecolor=SURFACE)
    plt.close(fig)
    print(f"[fig] {name}  存出 {bb.width + 2*PAD:.2f} x {bb.height + 2*PAD:.2f} in")


# ---- load python panel + questions once ----
wpy = pd.read_csv(os.path.join(DATA, "within_so_llm_panel.csv"))
labels = {}
for fn in ("question_labels.csv", "question_labels_ext_py.csv"):
    for r in csv.DictReader(open(os.path.join(DATA, fn), encoding="utf-8")):
        labels[int(r["question_id"])] = int(r["score"])
qrows = []
for fn in ("so_questions_full.json", "so_questions_ext_py.json"):
    qs = json.load(open(os.path.join(DATA, fn), encoding="utf-8"))
    scrape = max(q["creation_date"] for q in qs)
    sc = pd.to_datetime(scrape, unit="s").to_period("M")
    sci = sc.year * 12 + (sc.month - 1)
    for q in qs:
        s = labels.get(q["question_id"])
        if s is None or s == 0:
            continue
        cm = pd.to_datetime(q["creation_date"], unit="s").to_period("M")
        ci = cm.year * 12 + (cm.month - 1)
        qrows.append({"score": s, "t": ci, "ym": q["ym"], "age": sci - ci,
                      "ans": int(bool(q.get("is_answered")))})
qd = pd.DataFrame(qrows); qd["post"] = (qd.t >= EVENT).astype(int)



# ============ FIGURE（研究模型）——放在 §3.2 之后，故为正文第一张图 ============
# 只画 §3 已写定的关系，不引入任何新主张。虚线一律表示「探索性/未识别」。
import matplotlib.patches as mpatches

fig = plt.figure(figsize=(COL, 3.6))
ax = fig.add_subplot(111)
ax.set_xlim(0, 100); ax.set_ylim(-2, 68); ax.axis("off")

BOXC = "#f4f2fb"     # 主链条底色
SOFT = "#fbfbfd"
# 边框/箭头只用两色，与图注「Solid = identified, dashed = exploratory」一一对应：
# 此前四个框各挪用 RAMP[0..2]（s1-s4 替代率梯度色，语言配色也共用同一组），
# 与本图无关的含义混进了框线，读者若先看过图 8/图 2 的图例会误读。现在
# 全图只有实/虚两种线型两种色，色彩不再携带本图之外的编码。
BOXE = INK2          # 实线＝已识别（主链条 + H3）
DASHE = MUTED         # 虚线＝探索性/未识别（H2 + H4）


def box(x, y, w, h, title, lines, edge=BOXE, fc=BOXC, ls="-", lw=None):
    ax.add_patch(mpatches.FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.5,rounding_size=1.4",
        linewidth=lw or LW_CI_THIN, edgecolor=edge, facecolor=fc,
        linestyle=ls, zorder=3))
    ax.text(x + w / 2, y + h - 3.4, title, ha="center", va="top", zorder=4,
            fontsize=FS_VALUE, fontweight="bold", color=INK)
    for k, t in enumerate(lines):
        ax.text(x + w / 2, y + h - 8.8 - k * 4.4, t, ha="center", va="top",
                zorder=4, fontsize=FS_ANNOT, color=INK2)


def arrow(x1, y1, x2, y2, ls="-", color=None, rad=0.0):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), zorder=5,
                arrowprops=dict(arrowstyle="-|>", color=color or INK2,
                                linewidth=LW_REF, linestyle=ls,
                                connectionstyle="arc3,rad=%.2f" % rad,
                                shrinkA=2, shrinkB=2))


# ---- 主链条：三箱各宽 24，两处间隙各 13，标签抬到箭头上方 ----
box(1.0, 26, 21, 22, "Question properties",
    ["self-contained", "determinate answer", "one exchange suffices"])
# H1 原先是正文里孤零零的一行 "(H1)"：7.5 pt 常规灰字，而 H2/H3/H4 都在框标题里
# 8.0 pt 粗体黑字。四个假设编号三种呈现。提进标题后四者一致，语义上也更对——
# 渠道选择本身就是 H1。
# 2026-09-23 R1 复核 2.3：渠道选择本身未被识别，只是从构成推断，改为虚线框；H1 的
# 陈述是「降幅随可替代性上升」，即观测到的结果，故 H1 标签移到结果框。
box(39.5, 26, 21, 22, "Channel choice",
    ["ask the platform, or", "ask a model instead", "(inferred)"],
    edge=DASHE, ls=(0, (4, 2)))
box(78.0, 26, 21, 22, "Observed outcome (H1)",
    ["question volume falls,", "ordered by substitutability", "(Sections 6.1, 7.6)"])

# 2026-09-27 模拟审稿 I-22:原先第一支标「AI substitutability」、第二支标「task–technology fit」,
# 把 §2.3 所说的同一构念拆到了两支箭头上。改为第一支标构念及其理论名,第二支标选择如何汇成可观测结果。
for x1, x2, lab in ((22.7, 38.8, "AI substitutability\n(task\u2013technology fit)"),
                    (61.2, 77.3, "choices aggregate\ninto what is asked")):
    arrow(x1, 37, x2, 37)
    ax.text((x1 + x2) / 2, 39.2, lab, ha="center", va="bottom", linespacing=1.15,
            fontsize=FS_NOTE, color=MUTED, zorder=4)

# ---- 上：移动的能力前沿（H2）----
box(29.0, 54, 42, 12, "Capability frontier, moving (H2)",
    ["the gradient predates the release and persists after it"],
    fc=SOFT, edge=DASHE, ls=(0, (4, 2)))
arrow(50, 54, 50, 48, ls=(0, (4, 2)), color=DASHE)

# ---- 下左：构念验证（H3）----
box(6.0, 4, 38, 16, "Construct validation (H3)",
    ["models solve what the rubric scores high;",
     "humans and moderators recover the order"],
    fc=SOFT, edge=BOXE)
arrow(25.0, 20, 12.0, 26, rad=-0.18, color=BOXE)

# ---- 下右：供给侧（H4，虚线＝探索性）----
box(56.0, 4, 38, 16, "Supply side (H4, exploratory)",
    ["answered-rate decline steepest where",
     "substitutability is lowest \u2014 not established"],
    fc=SOFT, edge=DASHE, ls=(0, (4, 2)))
arrow(88.0, 26, 81.5, 20, rad=-0.18, ls=(0, (4, 2)), color=DASHE)

ax.text(0, -1.5, "Solid outline: observed or tested by this design.    "
                 "Dashed outline: inferred, exploratory, or not identified here.",
        ha="left", va="bottom", fontsize=FS_NOTE, color=MUTED)
save(fig, "fig0_framework")

# ============ FIGURE 1 — absolute volume + composition ============
ABS = os.path.join(BLIND_EST, "absolute_volume_series_python.csv")
fig = plt.figure(figsize=(COL, 3.5))
gs = GridSpec(1, 2, width_ratios=[1.0, 1.0], wspace=0.34, figure=fig)

# 1A reconstructed absolute volume, log axis
axA = fig.add_subplot(gs[0])
av = pd.read_csv(ABS)
xa = pd.to_datetime(av["ym"] + "-01")
for i, b in enumerate(("s1", "s2", "s3", "s4")):
    v = av[f"Nhat_{b}"].rolling(3, center=True, min_periods=1).mean()
    axA.plot(xa, v, color=RAMP[i], lw=LW_SERIES, solid_capstyle="round",
             zorder=3 + i, label=LEGLBL[i])
axA.set_yscale("log")
axA.axvspan(pd.Timestamp("2022-12-01"), xa.iloc[-1], color="#f4f5f8", zorder=0)
axA.axvline(pd.Timestamp("2022-12-01"), color=INK2, ls=(0, (3.5, 1.5)),
            lw=LW_REF, zorder=2)
axA.text(pd.Timestamp("2022-12-01"), axA.get_ylim()[1], " ChatGPT", fontsize=FS_ANNOT,
         color=INK2, ha="left", va="top", fontweight="bold")
axA.set_xlim(xa.iloc[0], xa.iloc[-1])
axA.set_ylabel("Estimated questions per month (log scale)")
axA.grid(color=GRID, lw=LW_GRID)
year_axis(axA); framed(axA); panel_label(axA, "A")

# 1B indexed composition (fixed 100/month sample)
# 旧版把四条原始月度线同等画出，噪声盖过了本图真正要讲的那句话
# ——"后期均值严格有序"。现在原始线降为背景，后期均值升为主角并标注数值。
# 再修：均值一度画成 lw=3.0 的粗横条，成了全图最重的墨，把真正的数据压成了
# 背景，而且"横条"这个体裁读起来像柱状图的柱（编码长度），可它编码的是水平。
# 改为虚线 + 右端实心端点：虚线是"算出来的参考线"的通用记号，与锯齿状的月度
# 实线不会混。三修：靠 alpha 压制月度线是错的手法——alpha 对浅色(s3/s4)的损伤
# 远大于深色(s1)，等于按颜色明度不均匀地削弱数据；而且 B 的线宽远细于 A，同一
# 组数据两个面板粗细不一致。现在月度线回到接近满不透明，均值线同步加重，靠"虚线
# +白描边+端点"而不是靠墨量差来区分两者。
axB = fig.add_subplot(gs[1])
wpy["t"] = wpy["ym"].map(ym_int)
pre = wpy[wpy.t < EVENT]
post = wpy[wpy.t >= EVENT]
x = pd.to_datetime(wpy["ym"] + "-01")
xpost0, xpost1 = pd.Timestamp("2022-12-01"), x.iloc[-1]
axB.axvspan(xpost0, xpost1, color="#f2f4f7", zorder=0)
postmean = {}
for i, b in enumerate(("s1", "s2", "s3", "s4")):
    idx = (wpy[b] / pre[b].mean() * 100).rolling(3, center=True, min_periods=1).mean()
    axB.plot(x, idx, color=RAMP[i], lw=LW_SERIES, alpha=0.85, solid_capstyle="round",
             zorder=2, label=LEGLBL[i])
    pm = float((post[b] / pre[b].mean() * 100).mean())
    postmean[b] = pm
    # 段长参数按 lw 反算（scale_dashes=True），渲染出来仍是 9pt 实 / 4pt 虚
    axB.plot([xpost0, xpost1], [pm, pm], color=RAMP[i], lw=LW_LEVEL,
             ls=(0, (3.5, 1.55)), zorder=4,
             path_effects=[pe.Stroke(linewidth=LW_LEVEL + 1.5, foreground=SURFACE),
                           pe.Normal()])
    # clip_on=False：端点正落在右轴线上，默认裁剪会把它切成半圆
    axB.plot([xpost1], [pm], "o", color=RAMP[i], ms=MS_SMALL, markeredgecolor=SURFACE,
             markeredgewidth=MEW, zorder=5, clip_on=False)
    axB.annotate(f"{pm:.0f}", xy=(xpost1, pm), xytext=(9, 0), textcoords="offset points",
                 va="center", ha="left", fontsize=FS_VALUE, color=RAMP[i],
                 fontweight="bold", annotation_clip=False)
# 侧置图例在 190 mm 画幅里要吃掉近 1.6 in，而且第四条恰好压住右侧的 "159"。
# 两个面板本来就共用这一套分档，改成整图底部一行：撞车消失，A/B 也拉回等宽。
_h, _l = axB.get_legend_handles_labels()
axB.axvline(xpost0, color=INK2, ls=(0, (3.5, 1.5)), lw=LW_REF, zorder=3)
axB.axhline(100, color=BASE, lw=LW_REF, zorder=1)
axB.set_ylim(15, 215); axB.set_yticks(range(50, 201, 50))
axB.set_xlim(x.iloc[0], xpost1)
axB.set_ylabel("Share of the fixed monthly sample, indexed")
axB.set_title("dashed levels = post-period means", fontsize=FS_NOTE, color=MUTED,
              loc="right", pad=4)
axB.grid(color=GRID, lw=LW_GRID)
year_axis(axB); framed(axB); panel_label(axB, "B")
_lg = fig.legend(_h, _l, title="Substitutability bin", loc="lower center", ncol=4,
                 frameon=False, fontsize=FS_LEG, handlelength=1.9,
                 columnspacing=1.8, bbox_to_anchor=(0.5, -0.06))
_lg.get_title().set_fontsize(FS_LEGT)
_lg.get_title().set_color(INK2)
_lg.get_title().set_fontweight("bold")
save(fig, "fig1_main")
print(f"    [1B post-period means] " + "  ".join(f"{k}={v:.2f}" for k, v in postmean.items()))


# ============ FIGURE 3 (was 2) — replication + robustness ============
fig = plt.figure(figsize=(COL, 3.1))
gs = GridSpec(1, 2, width_ratios=[1.0, 1.15], wspace=0.26, figure=fig)

# 2A three-language slopes
axA = fig.add_subplot(gs[0])
_full = lambda lang: next(r for r in RAMP_O[lang]["windowed"] if r["window"].startswith("full"))
langs = [("python", "python, blind", A2["blind"]["ols"]["coef"], A2["blind"]["ols"]["se"], True),
         ("python", "python, earlier", _full("python")["gamma"], _full("python")["se"], False),
         ("javascript", "javascript, earlier", _full("javascript")["gamma"], _full("javascript")["se"], False),
         ("java", "java, earlier", _full("java")["gamma"], _full("java")["se"], False)]
axA.axhline(2.5, color=GRID, lw=LW_REF, zorder=1)   # 盲 python 与其余三行分开:跨评分者不作比较
for y, (lg, lab4, g, se, filled) in zip([3, 2, 1, 0], langs):
    c = LANGC[lg]
    axA.plot([g - 1.96 * se, g + 1.96 * se], [y, y], color=c, lw=LW_CI,
             solid_capstyle="round", zorder=3)
    axA.plot([g - 1.96 * se, g - 1.96 * se], [y - 0.09, y + 0.09], color=c,
             lw=LW_CAP, zorder=3)
    axA.plot([g + 1.96 * se, g + 1.96 * se], [y - 0.09, y + 0.09], color=c,
             lw=LW_CAP, zorder=3)
    axA.plot(g, y, "o", color=c if filled else SURFACE, ms=MS_MAIN,
             markeredgecolor=c if not filled else SURFACE, markeredgewidth=MEW * (2 if not filled else 1), zorder=4)
    axA.annotate(f"{lab4}  {g:+.2f}", xy=(g + 1.96 * se, y), xytext=(10, 0),
                 textcoords="offset points", va="center", fontsize=FS_VALUE, color=c,
                 fontweight="bold")
# 零线**不**跟图2/图5 一样用 ACCENT 红：本图 B 面板已把红色专门给了"真实事件"
# （竖虚线+大红点），A 面板再用红画零线，同一张图里红就有两个意思。
# 图内一致优先于跨图一致——读者一次只看一张图。
axA.axvline(0, color=INK2, lw=LW_REF, zorder=2)
axA.set_yticks([]); axA.set_ylim(-0.6, 3.6); axA.set_xlim(-0.62, 0.42)
axA.set_xlabel("Dose slope γ, 95% CI")
axA.grid(axis="x", color=GRID, lw=LW_GRID); finish(axA, left=False)
axA.spines["left"].set_visible(False); panel_label(axA, "A")

# 2B placebo cutoffs — recompute per-cutoff gamma
axB = fig.add_subplot(gs[1])
d = []
for _, r in wpy.iterrows():
    for b in (1, 2, 3, 4):
        d.append({"ym": r["ym"], "t": ym_int(r["ym"]), "score": b, "count": int(r[f"s{b}"])})
d = pd.DataFrame(d); d["y"] = np.log(d["count"].clip(lower=1))
ts = sorted(d.t.unique())
# matched-window placebo: each candidate uses a fixed +-9-month window, so a later
# cutoff is not handed a mechanical advantage by absorbing more post-period months.
# (The earlier design restricted candidates to dates at or before the true event and
# let each use every later month; with a growing effect the true date wins by
# construction. Section 7.2 of the manuscript records that.)
W = 9
cands = [t for t in ts if t - W >= ts[0] and t + W - 1 <= ts[-1]]
gs_c = {}
for ev in cands:
    dd = d[(d.t >= ev - W) & (d.t < ev + W)].copy()
    dd["dz"] = dd.score * (dd.t >= ev).astype(int)
    bb = pd.get_dummies(dd.score, prefix="b", drop_first=True).astype(float)
    mm = pd.get_dummies(dd.ym, prefix="m", drop_first=True).astype(float)
    X = sm.add_constant(pd.concat([dd[["dz"]].astype(float), bb, mm], axis=1))
    gs_c[ev] = sm.OLS(dd.y.values, X.values).fit().params[list(X.columns).index("dz")]
evs = sorted(gs_c)
xs = [pd.Timestamp(year=e // 12, month=e % 12 + 1, day=1) for e in evs]
for xi, e in zip(xs, evs):
    v = gs_c[e]
    if e == EVENT:
        axB.plot(xi, v, "o", ms=MS_EMPH, color=ACCENT, zorder=5,
                 markeredgecolor=SURFACE, markeredgewidth=MEW)
    elif e + W - 1 < EVENT:               # 窗口整段落在事件前 = 唯一干净的安慰剂
        # 十八个前期月装不下第二个十八月窗口,所以这一类只有 2022-03 一个成员。
        # 方形而非圆形:形状差异在灰度印刷下仍可辨,颜色差异不一定。
        axB.plot(xi, v, "s", ms=MS_SMALL + 1, color="#4a4a4a", zorder=5,
                 markeredgecolor=SURFACE, markeredgewidth=MEW)
    elif e < EVENT:                       # 截点在事件前,但 ±9 月窗口与处理期重叠
        axB.plot(xi, v, "o", ms=MS_SMALL, color="#4a4a4a", zorder=4,
                 markeredgecolor=SURFACE, markeredgewidth=MEW_S)
    else:                                 # cutoffs inside the treated period
        # 旧版用 GRID(#e1e0d9)，浅到印刷上会消失；改为可辨认的中灰并加描边
        axB.plot(xi, v, "o", ms=MS_TINY, color="#b9b9b9", zorder=3,
                 markeredgecolor=SURFACE, markeredgewidth=MEW_S)
axB.axvspan(pd.Timestamp("2022-12-01"), xs[-1], color="#f2f4f7", zorder=0)
axB.axvline(pd.Timestamp("2022-12-01"), color=ACCENT, ls=(0, (3.5, 1.5)),
            lw=LW_REF, alpha=0.75, zorder=2)
axB.axhline(0, color=BASE, lw=LW_REF, zorder=1)
tx = pd.Timestamp(year=EVENT // 12, month=EVENT % 12 + 1, day=1)
# 放到红点左侧的空白里：新版面下点本身已靠近底框，标注再往下会压住外框
axB.annotate("true event", xy=(tx, gs_c[EVENT]), xytext=(-9, 0),
             textcoords="offset points", ha="right", va="center",
             fontsize=FS_ANNOT, color=ACCENT, fontweight="bold")
# 旧标签写的是 "pre-event placebos",指着全部九个深灰点——但其中八个的 ±9 月窗口
# 与处理期重叠(1 到 8 个月),只有 2022-03 是干净的。题注已按 P0-3 改过,图内标签
# 当时没跟着改,于是图自己还在说题注已经撤回的话。
#
# 这九个点挤在 43 个月横轴的一小段里,任何贴点的文字标签都会压住数据(试过两行
# 文字,分别撞上方块和那串圆点)。改用图例:位置与数据解耦,且形状差异在灰度下可辨。
from matplotlib.lines import Line2D
_h = [Line2D([], [], ls="none", marker="s", ms=MS_SMALL + 1, color="#4a4a4a",
             markeredgecolor=SURFACE, markeredgewidth=MEW,
             label="window entirely pre-event"),
      Line2D([], [], ls="none", marker="o", ms=MS_SMALL, color="#4a4a4a",
             markeredgecolor=SURFACE, markeredgewidth=MEW_S,
             label="window overlaps treatment")]
axB.legend(handles=_h, frameon=False, fontsize=FS_LEG, loc="upper left",
           handletextpad=0.5, borderaxespad=0.2, labelspacing=0.25)
# 原来锚在某个数据点上、再往下偏 30 pt；画布一窄就正好落到零线上。
# 改用轴坐标钉在右下角的空白区，与数据点的具体位置解耦。
axB.text(0.985, 0.04, "cutoffs inside the treated period", transform=axB.transAxes,
         ha="right", va="bottom", fontsize=FS_ANNOT, color=MUTED)
axB.set_ylabel("Dose slope γ, matched ±9-month window")
axB.set_xlabel("Candidate cutoff date")
year_axis(axB)
axB.grid(axis="y", color=GRID, lw=LW_GRID); finish(axB); panel_label(axB, "B")
save(fig, "fig3_robustness")


# ============ FIGURE 2 (was 3) — dynamics + criterion validity ============
fig = plt.figure(figsize=(COL, 3.2))
gs = GridSpec(1, 2, width_ratios=[1.2, 1.0], wspace=0.28, figure=fig)

# 3A event-study pre-trend
axA = fig.add_subplot(gs[0])
es = pd.read_csv(os.path.join(DATA, "within_so_llm_eventstudy.csv"))
kk, gk = es["k"].values, es["gamma_k"].values
pre_m = kk < 0
# 处理发生在最后一个前期月(k=-1)与第一个后期月(k=0)**之间**,故分界线与阴影
# 起点都在 -0.5,不在 0。画在 0 上会把 k=0 这个已经受处理的月份读成分界本身。
axA.axvspan(-0.5, kk.max(), color="#f2f4f7", zorder=0)
axA.scatter(kk[pre_m], gk[pre_m], s=14, color=PRE, zorder=4, label="pre",
            edgecolor=SURFACE, linewidth=MEW_S)
axA.scatter(kk[~pre_m], gk[~pre_m], s=14, color=POST, zorder=4, label="post",
            edgecolor=SURFACE, linewidth=MEW_S)
# 参照月 k=-1：它被省略，故定义了纵轴的零点。正文 §6.2 说明前期水平对这一选择敏感，
# 图上就必须把它标出来，而不是留一条已不再使用的外推线。
axA.scatter([-1], [0], s=30, facecolor="none", edgecolor="#4a4a4a",
            linewidth=MEW, zorder=5)
# 标注必须落在圈的**左**侧。旧版用 xytext=(9,5)+ha="left" 把文字推过了分界线,
# 整行字坐进后期阴影里、与圈之间又无引线,读者会把参照月读成 k=0 或整个后期——
# 而 §6.2 的全部论证正好就建立在"相对哪一个月"这件事上。
axA.annotate("reference month", xy=(-1, 0), xytext=(-3, 0.135),
             textcoords="data", ha="right", va="center",
             arrowprops=dict(arrowstyle="-", color="#4a4a4a", lw=LW_REF, shrinkA=1, shrinkB=4),
             fontsize=FS_ANNOT, color="#4a4a4a")
axA.axvline(-0.5, color=INK2, ls=(0, (3.5, 1.5)), lw=LW_REF, zorder=2)
axA.axhline(0, color=BASE, lw=LW_REF, zorder=1)
axA.set_xlim(kk.min() - 1.5, kk.max() + 1.5); axA.set_ylim(top=0.19)
axA.set_xlabel("Months relative to ChatGPT (k)")
axA.set_ylabel(r"Dose slope $\gamma_k$")
axA.legend(frameon=False, fontsize=FS_LEG, loc="lower left")
axA.grid(axis="y", color=GRID, lw=LW_GRID); finish(axA); panel_label(axA, "A")

# 3B criterion validity across four answerers (answer margin -> supplementary)
axB = fig.add_subplot(gs[1])
wt = J(R2, "R2c_result.json")["common_subset"]      # 第三轮:四个答题者共同完成的题
tiers = [t_ for t_ in [("Sonnet 5", "sonnet5", "#14497F", "-", "o"),
                       ("GLM-5.3", "glm53", "#3E85C6", "-", "s"),
                       ("Haiku 4.5", "haiku45", "#C2603E", "--", "o"),
                       ("GLM-4.6", "glm46", "#E8A07E", "--", "s")] if t_[1] in wt]
xs = [1, 2, 3, 4]
for lab, key, col, ls, mk in tiers:
    ys = [wt[key][f"s{b}"] for b in xs]
    axB.plot(xs, ys, color=col, lw=LW_SERIES, ls=ls, marker=mk, ms=MS_MID,
             markeredgecolor=SURFACE, markeredgewidth=MEW, zorder=3)
    _grp = [t_ for t_ in tiers if t_[3] == ls]
    _hi = max(_grp, key=lambda t_: wt[t_[1]]["s4"])[0]
    dy = (9 if lab == _hi else -9) if len(_grp) > 1 else 0
    axB.annotate(lab, xy=(4, ys[-1]), xytext=(8, dy), textcoords="offset points",
                 va="center", fontsize=FS_VALUE, color=col, fontweight="bold",
                 annotation_clip=False)
axB.text(0.02, 0.97, "solid = strong tier\ndashed = weak tier", transform=axB.transAxes,
         fontsize=FS_ANNOT, color=MUTED, va="top", ha="left", linespacing=1.5)
axB.set_xticks(xs); axB.set_xticklabels([f"s{b}" for b in xs])
axB.set_xlim(0.85, 4.65); axB.set_ylim(0.35, 1.02)
axB.set_xlabel("AI-substitutability bin")
axB.set_ylabel("Share of questions solved from text alone")
axB.grid(axis="y", color=GRID, lw=LW_GRID); finish(axB); panel_label(axB, "B")
save(fig, "fig2_dynamics")

print("DONE — 3 multi-panel figures (600dpi PNG + vector PDF)")


# ============ 新增图（第四轮，用户要求"多画一些图丰富文稿"）============
# 下列四张图承担的都是论文正文已有的论断，只是此前只以表格呈现。数值一律照抄
# 对应表格（Table 3 / Table 4 / Table 5 / Table 11），不另做计算，避免与正文口径分叉。

# ---- 新图 A：估计量稳健性（对应 Table 3）----
fig = plt.figure(figsize=(COL, 3.5))
ax = fig.add_subplot(111)
_cf = J(R2, "R2d_kappa_result.json")["cross_family"]["glm"]["per_point"]
SPECS = [  # (标签, γ, SE, 是否主规格) —— 读 R2 产物
    ("log-count OLS (python, blind)",   A2["blind"]["ols"]["coef"], A2["blind"]["ols"]["se"], True),
    ("Fixed-total FE-PPML",             A2["blind"]["ppml"]["coef"], A2["blind"]["ppml"]["se"], False),
    ("Newey–West log(s4/s1), per point", A2["blind"]["logratio_nw"]["coef"] / 3, A2["blind"]["logratio_nw"]["se"] / 3, False),
    ("Independent-family labels",       _cf[0], _cf[1], False),
    ("Earlier classification (python)", A2["original"]["ols"]["coef"], A2["original"]["ols"]["se"], False),
    ("Earlier (javascript)",            _full("javascript")["gamma"], _full("javascript")["se"], False),
    ("Earlier (java)",                  _full("java")["gamma"], _full("java")["se"], False),
]
ys = list(range(len(SPECS)))[::-1]
for y, (lab, g, se, main) in zip(ys, SPECS):
    c = RAMP[0] if main else INK2
    ax.plot([g - 1.96 * se, g + 1.96 * se], [y, y], color=c,
            lw=LW_CI if main else LW_CI_THIN,
            solid_capstyle="round", zorder=3)
    ax.plot(g, y, "o", color=c, ms=MS_MAIN if main else MS_MID,
            markeredgecolor=SURFACE, markeredgewidth=MEW, zorder=4)
    ax.annotate(f"{g:+.3f}".rstrip("0").rstrip("."), xy=(g, y), xytext=(0, 9),
                textcoords="offset points", ha="center", fontsize=FS_VALUE,
                color=c, fontweight="bold")
ax.axvline(0, color=ACCENT, lw=LW_REF, zorder=2)
ax.set_xlim(-0.60, 0.035)   # 给零线留出余量，免得贴在右外框上
ax.set_yticks(ys); ax.set_yticklabels([s[0] for s in SPECS], fontsize=FS_TICK)
ax.set_ylim(-0.7, len(SPECS) - 0.3)
ax.set_xlabel("Dose slope γ, 95% CI")
ax.grid(axis="x", color=GRID, lw=LW_GRID)
framed(ax)
ax.set_title("sign and significance hold across every estimator and classification",
             fontsize=FS_NOTE, color=MUTED, loc="left", pad=6)
save(fig, "fig_estimators")

# ---- 新图 B：能力窗口（对应 Table 4）----
fig = plt.figure(figsize=(COL, 3.4))
ax = fig.add_subplot(111)
_WK = [("GPT-3.5 only\n(3 mo)", "GPT-3.5 only"), ("First 6 months", "first 6m"), ("Year 1", "y1 "),
       ("Year 2", "y2 "), ("Year 3", "y3 "), ("Year 4", "y4 "), ("Full post period", "full")]
def _w(rows, key):
    r = next(r for r in rows if r["window"].startswith(key)); return (r["gamma"], r["se"])
WIN = [(lab, _w(list(RAMP_B.values()), k), _w(RAMP_O["javascript"]["windowed"], k), _w(RAMP_O["java"]["windowed"], k))
       for lab, k in _WK]   # python 盲标签;javascript、java 原标签(唯一一套)
langs3 = [("python", 0), ("javascript", 1), ("java", 2)]
_LBL3 = {"python": "python (blind)", "javascript": "javascript (earlier)", "java": "java (earlier)"}
off = {0: -0.23, 1: 0.0, 2: 0.23}
for lname, li in langs3:
    c = LANGC[lname]
    xs_, ys_, es_ = [], [], []
    for xi, row in enumerate(WIN):
        g, se = row[1 + li]
        xs_.append(xi + off[li]); ys_.append(g); es_.append(1.96 * se)
    # 21 条区间密排，用次级宽度；与图2 里的非主规格同宽
    ax.errorbar(xs_, ys_, yerr=es_, fmt="o", color=c, ms=MS_SMALL, lw=LW_CI_THIN,
                capsize=3, capthick=LW_CAP, markeredgecolor=SURFACE,
                markeredgewidth=MEW_S, label=_LBL3[lname], zorder=3)
ax.axhline(0, color=ACCENT, lw=LW_REF, zorder=2)
ax.set_xticks(range(len(WIN)))
ax.set_xticklabels([w[0] for w in WIN], fontsize=FS_TICK)
ax.set_ylabel("Dose slope γ, 95% CI")
ax.grid(axis="y", color=GRID, lw=LW_GRID)
below_legend(ax, ncol=3, y=-0.185)  # 让开两行 x 轴标签即可；再往下只是白高
framed(ax)
ax.set_title(f"python (blind): four post years not equal, F = {WT['F']:.2f}, p = {WT['F_p']:.3f}".replace("p = 0.", "p = ."),
             fontsize=FS_NOTE, color=MUTED, loc="left", pad=5)
save(fig, "fig_windows")

# ---- 新图 C：评分者一致性 κ 与人-人上限（对应 Table 5）----
fig = plt.figure(figsize=(COL140, 2.75))
ax = fig.add_subplot(111)
_k = KP["kappa_vs_consensus"]
RATERS = [(lab, _k[key]["kappa"], _k[key]["ci"][0], _k[key]["ci"][1]) for lab, key in (
    ("Claude Sonnet 5 (blind, primary)", "blind"), ("Claude Sonnet 4.6 (earlier)", "orig"),
    ("GLM-4.6", "glm46"), ("GLM-5.3 (frontier tier)", "glm53"))]
HUM, HLO, HHI = 0.533, 0.439, 0.627
# 横向点图:三个评分者名称很长,放 y 轴才能横排;本图与图 2/图 3A 同属
# "点 + 置信区间"的森林图体裁,该体裁的惯例本就是横向。
ax.axvspan(HLO, HHI, color="#ebe7f5", zorder=0)
ax.axvline(HUM, color=RAMP[1], lw=LW_REF, ls=(0, (3.5, 1.5)), zorder=2)
ax.annotate("human–human agreement\nκ = 0.533 [0.439, 0.627]",
            xy=(HUM, -0.78), xytext=(6, 0), textcoords="offset points",
            ha="left", va="top", fontsize=FS_ANNOT, color=RAMP[1], fontweight="bold")
for i, (lab, k, lo, hi) in enumerate(RATERS):
    ax.plot([lo, hi], [i, i], color=RAMP[0], lw=LW_CI, solid_capstyle="round", zorder=3)
    ax.plot(k, i, "o", color=RAMP[0], ms=MS_MAIN, markeredgecolor=SURFACE,
            markeredgewidth=MEW, zorder=4)
    ax.annotate(f"{k:.3f}", xy=(hi, i), xytext=(8, 0), textcoords="offset points",
                va="center", fontsize=FS_VALUE, color=RAMP[0], fontweight="bold")
ax.set_yticks(range(len(RATERS)))
ax.set_yticklabels([r[0] for r in RATERS], fontsize=FS_TICK)
ax.set_ylim(-0.95, 3.5); ax.invert_yaxis()
ax.set_xlim(0.36, 0.72)
ax.set_xlabel("Binary κ against the human consensus standard", fontsize=FS_LABEL)
ax.grid(axis="x", color=GRID, lw=LW_GRID)
framed(ax)
save(fig, "fig_kappa", target=COL140)

# ---- 新图 D：绝对量降幅（对应 Table 11 Panel B）----
# 图例原在右侧（side_legend）：190 mm 定宽下，四档图例连同较长的端点标签
# （"s1 (least substitutable)"）吃掉画布右端约 15%，柱状区被挤窄、显得
# 又长又局促。改横排放底部（below_legend，与图 6 同款修法），柱状区吃满
# 全宽；多出的图例一行从画布高度里加回来，宽度不变，仍是 190 mm 标准栏宽。
fig = plt.figure(figsize=(COL, 4.05))
ax = fig.add_subplot(111)
VOL = {lang: [round(100 * AVJ[f"absolute_by_bin_{lang}"][f"s{b}"]["pct_change"], 1) for b in (1, 2, 3, 4)]
       for lang in ("python", "javascript", "java")}   # python 盲标签;另两种原标签
PLAT = {lang: round(100 * AVJ[f"platform_total_{lang}"]["pct_change"], 1) for lang in ("python", "javascript", "java")}
names = list(VOL)
w = 0.185
# 横向条形：数值标签因此不必旋转 90°，语言名也能横排，比竖版好读。
# 组内 s1 在上、s4 在下，与右侧图例的上下顺序一致。
for i, b in enumerate(("s1", "s2", "s3", "s4")):
    ys_ = [j + (i - 1.5) * w for j in range(len(names))]
    vals = [VOL[n][i] for n in names]
    ax.barh(ys_, vals, height=w, color=RAMP[i], label=LEGLBL[i], zorder=3,
            edgecolor=SURFACE, linewidth=0.4)
    for yy, vv in zip(ys_, vals):
        ax.annotate(f"{vv:.1f}", xy=(0, yy), xytext=(6, 0),
                    textcoords="offset points", ha="left", va="center",
                    fontsize=FS_SMALL, color=SURFACE, fontweight="bold", zorder=6)
for j, n in enumerate(names):
    ax.plot([PLAT[n], PLAT[n]], [j - 0.46, j + 0.46], color=INK, lw=LW_REF,
            ls=(0, (3.5, 1.85)), zorder=5)
    ax.annotate(f"platform {PLAT[n]:.1f}", xy=(PLAT[n], j - 0.46), xytext=(0, 2),
                textcoords="offset points", ha="center", va="bottom",
                fontsize=FS_SMALL, color=INK, zorder=6,
                bbox=dict(boxstyle="round,pad=0.15", fc=SURFACE, ec="none", alpha=0.92))
ax.set_yticks(range(len(names))); ax.set_yticklabels(names, fontsize=FS_TICK)
ax.set_ylim(-0.74, len(names) - 0.30)
ax.invert_yaxis()          # python 在最上，与表格和正文叙述次序一致
# 0 放左端:柱子随之从左向右生长,与阅读方向一致;负号保留,与 Table 11 口径不分叉
ax.set_xlim(0, -95)
ax.set_xlabel("Change in monthly questions, pre- to post-ChatGPT (%)", fontsize=FS_LABEL)
ax.grid(axis="x", color=GRID, lw=LW_GRID)
# below_legend 的 y 是给 below_legend 自己排两行 x 轴刻度用的；这里 x 轴刻度只有
# 一行数字加一行 set_xlabel，与 fig_windows 的两行刻度标签同量级，救回同档 y。
below_legend(ax, ncol=4, y=-0.20, title="Substitutability bin", title_fontsize=FS_LEGT)
framed(ax)
ax.set_title("every bin collapsed; the least substitutable collapsed least",
             fontsize=FS_NOTE, color=MUTED, loc="left", pad=5)
save(fig, "fig_volume")

print("DONE — 3 multi-panel + 4 single-panel figures")
