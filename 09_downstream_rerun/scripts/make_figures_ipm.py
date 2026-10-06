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
PKG_ROOT = os.path.dirname(os.path.dirname(HERE))   # scripts -> 09_downstream_rerun -> 包根；不写绝对路径
# 输出目录：默认 <脚本所在目录>/figures；环境变量 P9B_FIG_OUT 可改到别处(仅改输出位置)
OUT = os.environ.get("P9B_FIG_OUT") or os.path.join(HERE, "figures")
os.makedirs(OUT, exist_ok=True)

_PKG_MAP = {  # 根里相对路径(工作文档\ 下；OSF 件为其包内路径) -> 包内相对路径；由 audit hook 实测的 24 个输入生成
    "步骤3_SHAP/shap_oof.npz": "10_shap_transparency/shap_oof.npz",
    "步骤3_SHAP/shap_result.json": "10_shap_transparency/shap_result.json",
    "R2_analyze_result.json": "07_blind_reclassification/results/R2_analyze_result.json",
    "R2_blind_s46/R2s46_analyze_result.json": "07_blind_reclassification/same_model_sonnet46/results/R2s46_analyze_result.json",
    "R2_downstream/blind/02_estimation/absolute_volume.json": "09_downstream_rerun/blind/outputs/02_estimation/absolute_volume.json",
    "R2_downstream/blind/02_estimation/absolute_volume_series_python.csv": "09_downstream_rerun/blind/outputs/02_estimation/absolute_volume_series_python.csv",
    "R2_downstream/blind/02_estimation/asker_rival_exact.json": "09_downstream_rerun/blind/outputs/02_estimation/asker_rival_exact.json",
    "R2_downstream/blind/02_estimation/asker_tenure.json": "09_downstream_rerun/blind/outputs/02_estimation/asker_tenure.json",
    "R2_downstream/blind/02_estimation/capability_ramp.json": "09_downstream_rerun/blind/outputs/02_estimation/capability_ramp.json",
    "R2_downstream/blind/02_estimation/closure_check.json": "09_downstream_rerun/blind/outputs/02_estimation/closure_check.json",
    "R2_downstream/blind/02_estimation/review_r1/p0_2_staging_ground.json": "09_downstream_rerun/blind/outputs/02_estimation/review_r1/p0_2_staging_ground.json",
    "R2_downstream/blind/05_additional_checks/glm_relabel/cross_family_glm-4.6.json": "09_downstream_rerun/blind/outputs/05_additional_checks/glm_relabel/cross_family_glm-4.6.json",
    "R2_downstream/blind/data/question_labels.csv": "09_downstream_rerun/blind/data/question_labels.csv",
    "R2_downstream/blind/data/question_labels_ext_py.csv": "09_downstream_rerun/blind/data/question_labels_ext_py.csv",
    "R2_downstream/blind/data/so_questions_ext_py.json": "01_panels_and_classification/data/so_questions_python_ext_2024-07_2026-05.json",
    "R2_downstream/blind/data/so_questions_full.json": "01_panels_and_classification/data/so_questions_python_2021-2024.json",
    "R2_downstream/blind/data/within_so_llm_eventstudy.csv": "09_downstream_rerun/blind/outputs/within_so_llm_eventstudy.csv",
    "R2_downstream/blind/data/within_so_llm_panel.csv": "07_blind_reclassification/labels/within_so_llm_panel_python_blind.csv",
    "R2_downstream/blind/logs/check_cap_sensitivity.log": "09_downstream_rerun/blind/logs/check_cap_sensitivity.log",
    "R2_downstream/orig/02_estimation/capability_ramp.json": "09_downstream_rerun/orig/outputs/02_estimation/capability_ramp.json",
    "R2c_result.json": "08_criterion_round3/results/R2c_result.json",
    "R2d_extra_result.json": "09_downstream_rerun/results/R2d_extra_result.json",
    "R2_downstream/blind/02_estimation/memorization_check.json": "09_downstream_rerun/blind/outputs/02_estimation/memorization_check.json",
    "R2_downstream/orig/02_estimation/memorization_check.json": "09_downstream_rerun/orig/outputs/02_estimation/memorization_check.json",
    "R2d_kappa_result.json": "09_downstream_rerun/results/R2d_kappa_result.json",
    "04_crosssite_engine/data/so_monthly_panel.csv": "04_crosssite_engine/data/so_monthly_panel.csv",
    # 加图第1步新增（fig_bins / fig_agree / fig_answer / fig_sampling 的输入；键 = 值 = 包内相对路径）
    "R2figbins_result.json": "09_downstream_rerun/results/R2figbins_result.json",
    **{_p: _p for _p in (
        "03_validation/gold_standard/coding_sheet_A_v2.csv",
        "03_validation/gold_standard/coding_sheet_B_v2.csv",
        "07_blind_reclassification/labels/question_labels_python_blind.csv",
        "01_panels_and_classification/data/question_labels_python_2021-2024.csv",
        "05_additional_checks/glm_relabel/labels_glm-4.6.jsonl",
        "02_estimation/legB_first_answer.csv",
        "02_estimation/platform_monthly_totals.csv",
        "09_downstream_rerun/blind/data/question_labels.csv",
        "09_downstream_rerun/blind/data/question_labels_ext_py.csv",
        *[f"01_panels_and_classification/data/so_questions_{_l}_{_r}.json"
          for _l in ("python", "javascript", "java") for _r in ("2021-2024", "ext_2024-07_2026-05")],
    )},
}
_PKG_BARE = {}
for _k in _PKG_MAP:
    _PKG_BARE.setdefault(_k.rsplit("/", 1)[-1], []).append(_k)


def resolve(name_or_relpath, *more):
    """文件名／根里相对路径 -> 包内绝对路径。查不到映射或文件不在包内则报错并写明文件名，不静默跳过。"""
    key = "/".join([name_or_relpath, *more]).replace("\\", "/").strip("/")
    if key not in _PKG_MAP:
        hits = _PKG_BARE.get(key, [])
        if len(hits) == 1:
            key = hits[0]
        elif len(hits) > 1:
            raise KeyError(f"resolve: file name '{key}' is ambiguous, give a relative path; candidates: {hits}")
        else:
            raise KeyError(f"resolve: no package mapping for '{key}'")
    p = os.path.join(PKG_ROOT, *_PKG_MAP[key].split("/"))
    if not os.path.isfile(p):
        raise FileNotFoundError(f"resolve: '{key}' should be at package path '{_PKG_MAP[key]}' but is missing")
    return p


# 以下三个仅是「根里相对路径」前缀(不是磁盘路径)，取文件时一律过 resolve()
DATA = "R2_downstream/blind/data"           # 盲标签镜像:python 面板、题级标签、事件研究
ORIG_EST = "R2_downstream/orig/02_estimation"
BLIND_EST = "R2_downstream/blind/02_estimation"
J = lambda *p: json.load(open(os.path.join(*p), encoding="utf-8"))
A2 = J(resolve("R2_analyze_result.json"))
RAMP_B = {r["window"]: r for r in J(resolve(BLIND_EST, "capability_ramp.json"))["python"]["windowed"]}
RAMP_O = J(resolve(ORIG_EST, "capability_ramp.json"))
WT = J(resolve("R2d_extra_result.json"))["blind"]["stats"]["window_tests"]
KP = J(resolve("R2d_kappa_result.json"))
AVJ = J(resolve(BLIND_EST, "absolute_volume.json"))
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
# 2026-09-28 终版独立复核 m-25：不给 PDF 写 CreationDate（带时区是弱地理信号）；
# 传给 savefig(..., metadata=...) 的 PDF 后端接受 None 值＝不写该字段。
PDF_METADATA = {"CreationDate": None}
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
    "axes.unicode_minus": True, "savefig.dpi": 600, "figure.dpi": 600,
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
    # 2026-09-28 终版独立复核 m-25：PDF 的 CreationDate 带 "+09'00'" 时区，是弱地
    # 理信号；PDF_METADATA 不写 CreationDate，matplotlib 因此不生成该字段。
    fig.savefig(os.path.join(OUT, f"{name}.pdf"), bbox_inches="tight",
                pad_inches=PAD, facecolor=SURFACE, metadata=PDF_METADATA)
    import re as _re
    for _ in range(5):   # 读 PDF MediaBox 实宽,偏离目标超过 0.003 in 就按差值收放画布重存两份
        _mb = _re.search(rb"/MediaBox\s*\[\s*[\d.]+\s+[\d.]+\s+([\d.]+)", open(os.path.join(OUT, f"{name}.pdf"), "rb").read())
        _w = float(_mb.group(1)) / 72.0
        if abs(_w - target) < 0.003:
            break
        w, h = fig.get_size_inches()
        fig.set_size_inches(w + (target - _w), h)
        fig.savefig(os.path.join(OUT, f"{name}.png"), bbox_inches="tight", pad_inches=PAD, facecolor=SURFACE, dpi=600)
        fig.savefig(os.path.join(OUT, f"{name}.pdf"), bbox_inches="tight", pad_inches=PAD, facecolor=SURFACE, metadata=PDF_METADATA)
    plt.close(fig)
    print(f"[fig] {name}  存出 {bb.width + 2*PAD:.2f} x {bb.height + 2*PAD:.2f} in")


# ---- load python panel + questions once ----
wpy = pd.read_csv(resolve(DATA, "within_so_llm_panel.csv"))
labels = {}
for fn in ("question_labels.csv", "question_labels_ext_py.csv"):
    for r in csv.DictReader(open(resolve(DATA, fn), encoding="utf-8")):
        labels[int(r["question_id"])] = int(r["score"])
qrows = []
for fn in ("so_questions_full.json", "so_questions_ext_py.json"):
    qs = json.load(open(resolve(DATA, fn), encoding="utf-8"))
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

# 2026-10-05 加图第1步（含补修）：顶框加高并上移（y 50->53，h 16->19，ylim 上界 68->74、画布高按比例加，纵向比例不变；箭头 53->48.6），
# 使向下箭头的尖与 H2b 行文字留出间隙；框内文字内容与相对框顶的位置不变。
fig = plt.figure(figsize=(COL, 3.6 * 76 / 70))
ax = fig.add_subplot(111)
ax.set_xlim(0, 100); ax.set_ylim(-2, 74); ax.axis("off")

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
    ["question volume falls,", "ordered by substitutability", "(Sections 6.1, 6.5)"])

# 2026-09-27 模拟审稿 I-22:原先第一支标「AI substitutability」、第二支标「task–technology fit」,
# 把 §2.3 所说的同一构念拆到了两支箭头上。改为第一支标构念及其理论名,第二支标选择如何汇成可观测结果。
for x1, x2, lab in ((22.7, 38.8, "AI substitutability\n(task\u2013technology fit)"),
                    (61.2, 77.3, "choices aggregate\ninto what is asked")):
    arrow(x1, 37, x2, 37)
    ax.text((x1 + x2) / 2, 39.2, lab, ha="center", va="bottom", linespacing=1.15,
            fontsize=FS_NOTE, color=MUTED, zorder=4)

# ---- 上：移动的能力前沿（H2）----
# 2026-10-05 收口第3步：H2 拆为 H2a/H2b，框内标题与两行文字按正文 §6.2/§8.1 的措辞改。
# 2026-09-28 终版独立复核 M-3：原先一行 "the gradient predates the release and
# persists after it" 正是正文 §6.2 说本设计确立不了的前半句，虚线又把已检验并
# 支持的负半句（不是发布日断点，§6.2、Table 3）一并标成"未识别"。改为两行，
# 分别对应正文 §6.2 的负半句（已检验，实线）与前半句（未识别）。
box(29.0, 53, 42, 19, "Capability frontier, moving (H2a, H2b)",
    ["H2a: no discontinuity at the release (Section 6.2)",
     "H2b: present before it, not supported (Section 6.2)"],
    fc=SOFT, edge=BOXE)
arrow(50, 53, 50, 48.6, ls=(0, (4, 2)), color=DASHE)

# ---- 下左：构念验证（H3）----
box(6.0, 4, 38, 16, "Construct validation (H3)",
    ["models solve what the rubric scores high;",
     "humans and moderators recover the order"],
    fc=SOFT, edge=BOXE)
arrow(25.0, 20, 12.0, 26, rad=-0.18, color=BOXE)

# ---- 下右：供给侧（H4，虚线＝探索性）----
# 2026-09-28 终版独立复核 m-22：框已是虚线并标 exploratory，
# 行内再加 "\u2014 not established" 是把结果陈述重复写进图（断言口呴），删去。
box(56.0, 4, 38, 16, "Supply side (H4, exploratory)",
    ["answered-rate decline steepest where",
     "substitutability is lowest"],
    fc=SOFT, edge=DASHE, ls=(0, (4, 2)))
arrow(88.0, 26, 81.5, 20, rad=-0.18, ls=(0, (4, 2)), color=DASHE)

# 2026-09-28 终版独立复核 m-22：图内图例改为与题注（L109）一致的措辞。
ax.text(0, -1.5, "Solid outlines mark what this design observes or tests.    "
                 "Dashed outlines mark what it does not identify.",
        ha="left", va="bottom", fontsize=FS_NOTE, color=MUTED)
save(fig, "fig0_framework")

# ============ FIGURE 1 — absolute volume + composition ============
ABS = resolve(BLIND_EST, "absolute_volume_series_python.csv")
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
# 2026-10-05 加图第1步：纵轴刻度由科学记数改为普通数字（千分位），范围不变
_yl = axA.get_ylim()
axA.set_yticks([100, 300, 1000, 3000]); axA.set_yticklabels(["100", "300", "1,000", "3,000"])
axA.set_ylim(_yl)
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
es = pd.read_csv(resolve(DATA, "within_so_llm_eventstudy.csv"))
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
wt = J(resolve("R2c_result.json"))["common_subset"]      # 第三轮:四个答题者共同完成的题
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
    # 2026-10-05 加图第1步：虚线组偏移 +9/-9 改 +4/-12，把 Sonnet 5 与 GLM-4.6 两个标签拉开
    _up, _dn = (9, -9) if ls == "-" else (4, -12)
    dy = (_up if lab == _hi else _dn) if len(_grp) > 1 else 0
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
_cf = J(resolve("R2d_kappa_result.json"))["cross_family"]["glm"]["per_point"]
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
# 2026-10-05 加图第1步：零线改深灰（红色与 java 的橙红易混）；「全事后期间」一组与上面各窗口之间加一道细分隔
ax.axhline(0, color=BASE, lw=LW_REF, zorder=2)
ax.axvline(len(WIN) - 1.5, color=BASE, lw=LW_GRID + 0.2, zorder=1)
ax.set_xticks(range(len(WIN)))
ax.set_xticklabels([w[0] for w in WIN], fontsize=FS_TICK)
ax.set_ylabel("Dose slope γ, 95% CI")
ax.grid(axis="y", color=GRID, lw=LW_GRID)
below_legend(ax, ncol=3, y=-0.185)  # 让开两行 x 轴标签即可；再往下只是白高
framed(ax)
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
fig = plt.figure(figsize=(COL, 4.25))   # 2026-10-05 加图第1步：4.05->4.25，组间留白加大以容纳 platform 标注
ax = fig.add_subplot(111)
VOL = {lang: [round(100 * AVJ[f"absolute_by_bin_{lang}"][f"s{b}"]["pct_change"], 1) for b in (1, 2, 3, 4)]
       for lang in ("python", "javascript", "java")}   # python 盲标签;另两种原标签
PLAT = {lang: round(100 * AVJ[f"platform_total_{lang}"]["pct_change"], 1) for lang in ("python", "javascript", "java")}
names = list(VOL)
w = 0.175
# 横向条形：数值标签因此不必旋转 90°，语言名也能横排，比竖版好读。
# 组内 s1 在上、s4 在下，与右侧图例的上下顺序一致。
for i, b in enumerate(("s1", "s2", "s3", "s4")):
    ys_ = [j + (i - 1.5) * w for j in range(len(names))]
    vals = [VOL[n][i] for n in names]
    ax.barh(ys_, vals, height=w, color=RAMP[i], label=LEGLBL[i], zorder=3,
            edgecolor=SURFACE, linewidth=0.4)
    for yy, vv in zip(ys_, vals):
        ax.annotate(f"{vv:.1f}".replace("-", "−"), xy=(0, yy), xytext=(6, 0),
                    textcoords="offset points", ha="left", va="center",
                    fontsize=FS_SMALL, color=SURFACE, fontweight="bold", zorder=6)
for j, n in enumerate(names):
    ax.plot([PLAT[n], PLAT[n]], [j - 0.42, j + 0.42], color=INK, lw=LW_REF,
            ls=(0, (3.5, 1.85)), zorder=5)
    ax.annotate(f"platform {PLAT[n]:.1f}".replace("-", "−"), xy=(PLAT[n], j - 0.42), xytext=(0, 1),
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
save(fig, "fig_volume")

print("DONE — 3 multi-panel + 4 single-panel figures")



# =====================================================================================
# 第 3 步新增（2026-10-04）：fig_design / fig_crosssite / fig_shap / fig_forest / fig_placebo
# 只新增函数与输出，上面既有七张图的代码一字未动。图内不写图题；凡画出的数一律从产物读。
# =====================================================================================
STEP3 = os.path.dirname(resolve("步骤3_SHAP/shap_result.json"))   # 包内 10_shap_transparency；自检 json 与 forest 行表写回此处
OSF_PANEL = resolve("04_crosssite_engine/data/so_monthly_panel.csv")
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.ticker, matplotlib.cm, matplotlib.colors
from matplotlib.lines import Line2D
from matplotlib.text import Text as _Text
from matplotlib.textpath import TextPath as _TextPath
from matplotlib.font_manager import FontProperties as _FP
from scipy.stats import rankdata

# 报告「最小印出字号」用：save() 把成品宽钉在 target，故缩放系数恒为 1，印出字号 = 写下的磅值。
STEP3_FONT_LOG = {}


def _min_font(fig, name):
    sizes = [t.get_fontsize() for t in fig.findobj(_Text) if t.get_visible() and t.get_text().strip()]
    STEP3_FONT_LOG[name] = min(sizes) if sizes else None
    print(f"[minfont] {name}  最小字号 {STEP3_FONT_LOG[name]} pt (成品宽/存出宽 = 1)")


def _wrap_pt(text, fs, width_pt, weight="normal"):
    """按真实字形宽度贪心折行（宽度单位：磅）。"""
    fp = _FP(weight=weight)
    wd = lambda s: _TextPath((0, 0), s, size=fs, prop=fp).get_extents().width
    out, cur = [], ""
    for word in text.split():
        t = (cur + " " + word).strip()
        if cur and wd(t) > width_pt:
            out.append(cur)
            cur = word
        else:
            cur = t
    if cur:
        out.append(cur)
    return out


# ------------------------------------------------------------------ fig_design
def fig_design():
    global ax
    H = 3.35
    fig = plt.figure(figsize=(COL, H))
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax = fig.add_subplot(111)
    XL = 101.0
    unit = COL * 72 / XL                    # 每个 x 单位的磅数；y 与 x 同比例，圆角不变形
    YT = H * 72 / unit
    ax.set_xlim(-0.5, 100.5); ax.set_ylim(0, YT); ax.axis("off")

    def tbox(x, y, w, h, title, paras, edge=BOXE, fc=BOXC, ls="-", lw=None):
        ax.add_patch(mpatches.FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0,rounding_size=1.0",
            linewidth=lw or LW_CI_THIN, edgecolor=edge, facecolor=fc, linestyle=ls, zorder=3))
        wpt = (w - 2.0) * unit
        lh_t, lh = FS_VALUE * 1.28 / unit, FS_ANNOT * 1.28 / unit
        tl = _wrap_pt(title, FS_VALUE, wpt, "bold") if title else []
        pls = [_wrap_pt(p, FS_ANNOT, wpt) for p in paras]
        bh = len(tl) * lh_t + (0.3 * lh_t if tl and pls else 0) + sum(len(p) for p in pls) * lh + 0.25 * lh * max(len(pls) - 1, 0)
        if bh > h - 0.8:
            print(f"[fig_design] 警告：文字块 {bh:.1f} 超出框高 {h:.1f}：{title!r}")
        yy = y + h / 2 + bh / 2
        for s in tl:
            ax.text(x + w / 2, yy, s, ha="center", va="top", zorder=4, fontsize=FS_VALUE,
                    fontweight="bold", color=INK)
            yy -= lh_t
        if tl and pls:
            yy -= 0.3 * lh_t
        for p in pls:
            for s in p:
                ax.text(x + w / 2, yy, s, ha="center", va="top", zorder=4, fontsize=FS_ANNOT, color=INK2)
                yy -= lh
            yy -= 0.25 * lh

    # 主线四框
    bw, gap = 21.5, 4.6
    top = YT - 0.6
    mh = 19.0
    my = top - mh
    xs_ = [0.0 + i * (bw + gap) for i in range(4)]
    tbox(xs_[0], my, bw, mh, "Sample",
         ["18,000 Stack Overflow questions; python, java, javascript; 100 per month, June 2021\u2013May 2026"])
    tbox(xs_[1], my, bw, mh, "Classifier",
         ["AI-substitutability rubric, 0\u20134.", "python: blind to date and outcomes.",
          "java, javascript: earlier, date-visible classification"])
    tbox(xs_[2], my, bw, mh, "Within-platform dose-response", ["bin \u00d7 post, bin and month fixed effects"])
    tbox(xs_[3], my, bw, mh, "Composition of asking (\u03b3)", ["reconstructed volumes (descriptive)"])
    for i in range(3):
        arrow(xs_[i] + bw + 0.6, my + mh / 2, xs_[i + 1] - 0.6, my + mh / 2)

    # 验证行：两组
    gy, gh = 0.6, 19.2
    ginside = (0.0, gy, 57.2, gh)
    goutside = (61.0, gy, 38.8, gh)
    ax.add_patch(mpatches.FancyBboxPatch(
        (ginside[0], ginside[1]), ginside[2], ginside[3], boxstyle="round,pad=0,rounding_size=1.0",
        linewidth=LW_CI_THIN, edgecolor=DASHE, facecolor="none", linestyle=(0, (4, 2)), zorder=2))
    ax.add_patch(mpatches.FancyBboxPatch(
        (goutside[0], goutside[1]), goutside[2], goutside[3], boxstyle="round,pad=0,rounding_size=1.0",
        linewidth=LW_CI_THIN, edgecolor=BOXE, facecolor="none", linestyle="-", zorder=2))
    ax.text(ginside[0] + 1.2, gy + gh - 0.9, "Inside the model loop", ha="left", va="top",
            fontsize=FS_VALUE, fontweight="bold", color=INK, zorder=4)
    ax.text(goutside[0] + 1.2, gy + gh - 0.9, "Outside the model loop", ha="left", va="top",
            fontsize=FS_VALUE, fontweight="bold", color=INK, zorder=4)
    iw, ih, iy = 17.4, 12.6, gy + 1.0
    inside = ["Second raters: same family, independent family",
              "Answering models and judges: four models, 320 questions",
              "Surrogate model with SHAP"]
    outside = ["Two human coders: 300 questions", "Moderators' duplicate closures"]
    for k, t in enumerate(inside):
        tbox(1.0 + k * (iw + 1.5), iy, iw, ih, None, [t], edge=BASE, fc=SOFT, lw=LW_CAP)
    for k, t in enumerate(outside):
        tbox(goutside[0] + 1.0 + k * (iw + 1.5), iy, iw, ih, None, [t], edge=BASE, fc=SOFT, lw=LW_CAP)
    # 向上箭头指向框 2
    b2x = xs_[1] + bw / 2
    arrow(ginside[0] + ginside[2] / 2, gy + gh + 0.4, b2x - 3.0, my - 0.6, color=DASHE, ls=(0, (4, 2)), rad=0.0)
    arrow(goutside[0] + goutside[2] / 2, gy + gh + 0.4, b2x + 3.0, my - 0.6, color=BOXE, rad=0.0)
    _min_font(fig, "fig_design")
    save(fig, "fig_design")


# ------------------------------------------------------------------ fig_protocol
def fig_protocol():
    """Measurement-validation protocol: six steps in three groups (no data read, no new numbers).
    Built from 工作文档\\协议图_草稿_20261006\\draft_protocol.py; cards are sized to content,
    cards in one row share a top edge, group frames shrink to the tallest content."""
    XL = 101.0
    unit = COL * 72 / XL                    # points per x unit; y uses the same scale (y downward)
    LH = lambda fs: fs * 1.28 / unit
    STEPS = [
        (1, "Blind and audit the scorer", "Scores absorb outcome or period; silent run errors",
         "here: date- and outcome-blind classification; coverage and model-identity checks (Sections 4.2, 4.6)"),
        (2, "Replicate across raters", "Scores reflect one model’s habits",
         "here: same- and independent-family raters (Sections 4.5, 6.1)"),
        (3, "Test a behavioural criterion", "Scale does not measure what models can answer",
         "here: four answering models, blind judges, 320 questions (Section 6.3)"),
        (4, "Explain what the score follows", "Scores track irrelevant surface features",
         "here: surrogate model with SHAP (Section 6.3)"),
        (5, "Step outside the model loop", "The construct is defined by the model itself",
         "here: two human coders, 300 questions; moderators’ duplicate closures (Sections 4.4, 6.4)"),
        (6, "Stress-test over time", "Time-varying measurement error passes as an effect",
         "here: memorisation, edit exposure, relabelling (Sections 7.5, 7.6)"),
    ]
    R = 1.7                                  # step-badge radius (units)
    PADX = 1.2

    def card_lines(step, w):
        n, title, threat, here = STEPS[step - 1]
        tw = (w - 2 * PADX - 2 * R - 0.8) * unit           # title sits right of the badge
        bw_ = (w - 2 * PADX) * unit
        return (_wrap_pt(title, FS_VALUE, tw, "bold"), _wrap_pt(threat, FS_ANNOT, bw_),
                _wrap_pt(here, FS_SMALL, bw_))

    def card_need(step, w):
        t, th, he = card_lines(step, w)
        return (0.9 + max(len(t) * LH(FS_VALUE), 2 * R) + 0.5 + len(th) * LH(FS_ANNOT)
                + 0.5 + len(he) * LH(FS_SMALL) + 0.9)

    # ---------------- layout (y downward) ----------------
    bw, gap = 21.5, 4.6
    xs = [i * (bw + gap) for i in range(4)]
    sh = 8.0                                 # strip box height
    y_strip = 0.6
    y_inst = y_strip + sh + 1.6
    GAPX = 1.6
    w_in_card = 23.8
    w_in = 2 * w_in_card + 3 * 1.0           # inside group width
    w_out = 27.6
    w_ot = 100.0 - w_in - w_out - 2 * GAPX
    x_in, x_out, x_ot = 0.0, w_in + GAPX, w_in + GAPX + w_out + GAPX
    inst_lines = _wrap_pt("Here: AI-substitutability rubric; 18,000 Stack Overflow questions, 100 per month, "
                          "June 2021–May 2026; within-platform dose-response.", FS_SMALL, (100.0 - 49.0) * unit)
    y_bus = y_inst + len(inst_lines) * LH(FS_SMALL) + 1.8
    y_grp = y_bus + 3.0
    lab_h = LH(FS_VALUE) + 1.0
    w_out_card, w_ot_card = w_out - 2.0, w_ot - 2.0
    need = {s: card_need(s, w_in_card) for s in (1, 2, 3, 4)}
    need[5] = card_need(5, w_out_card)
    need[6] = card_need(6, w_ot_card)
    row_h = [max(need[1], need[2]), max(need[3], need[4])]      # row height = tallest card in the row
    h_in = lab_h + 1.0 + row_h[0] + 1.0 + row_h[1] + 1.0
    h_out = lab_h + 1.0 + need[5] + 1.0
    h_ot = lab_h + 1.0 + need[6] + 1.0
    grp_h = max(h_in, h_out, h_ot)           # canvas height only; each frame keeps its own tight height
    YT = y_grp + grp_h + 0.6

    H = YT * unit / 72
    fig = plt.figure(figsize=(COL, H))
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax = fig.add_subplot(111)
    ax.set_xlim(-0.5, 100.5); ax.set_ylim(YT, 0); ax.axis("off")

    def rbox(x, y, w, h, edge, fc, ls="-", lw=LW_CI_THIN, z=3):
        ax.add_patch(mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.0",
                                             linewidth=lw, edgecolor=edge, facecolor=fc, linestyle=ls, zorder=z))

    def parrow(x1, y1, x2, y2):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1), zorder=5,
                    arrowprops=dict(arrowstyle="-|>", color=INK2, linewidth=LW_REF, linestyle="-",
                                    shrinkA=0, shrinkB=0))

    def seg(x1, y1, x2, y2, color=INK2, ls="-"):
        ax.plot([x1, x2], [y1, y2], color=color, lw=LW_REF, ls=ls, zorder=2, solid_capstyle="butt")

    # top strip of four boxes
    strip = ["Item-level rubric (anchored, 0–4)", "Validation protocol (six steps below)",
             "Validated measure", "Design that uses it"]
    for i, t in enumerate(strip):
        rbox(xs[i], y_strip, bw, sh, BOXE, BOXC)
        tl = _wrap_pt(t, FS_VALUE, (bw - 2.0) * unit, "bold")
        th = len(tl) * LH(FS_VALUE)
        yy = y_strip + sh / 2 - th / 2
        for s in tl:
            ax.text(xs[i] + bw / 2, yy, s, ha="center", va="top", zorder=4, fontsize=FS_VALUE,
                    fontweight="bold", color=INK)
            yy += LH(FS_VALUE)
    for i in range(3):
        parrow(xs[i] + bw + 0.4, y_strip + sh / 2, xs[i + 1] - 0.4, y_strip + sh / 2)

    # instance line (right part, clear of the bus arrow)
    x_inst = 100.0 - (100.0 - 49.0)
    yy = y_inst
    for s in inst_lines:
        ax.text(x_inst + 0.5, yy, s, ha="left", va="top", zorder=4, fontsize=FS_SMALL, color=MUTED)
        yy += LH(FS_SMALL)

    def group_frame(x, w, h, label, edge, ls):
        rbox(x, y_grp, w, h, edge, "none", ls=ls, z=2)
        ax.text(x + 1.2, y_grp + 0.9, label, ha="left", va="top", zorder=4, fontsize=FS_VALUE,
                fontweight="bold", color=INK)

    def card(step, x, y, w, h):
        n, title, threat, here = STEPS[step - 1]
        tl, th, he = card_lines(step, w)
        rbox(x, y, w, h, BASE, SOFT, lw=LW_CAP)
        cx, cy = x + PADX + R, y + 0.9 + R
        ax.add_patch(mpatches.Circle((cx, cy), R, facecolor=INK2, edgecolor="none", zorder=4))
        ax.text(cx, cy, str(n), ha="center", va="center", fontsize=FS_SMALL, fontweight="bold",
                color="white", zorder=5)
        yy = y + 0.9
        for s in tl:
            ax.text(x + PADX + 2 * R + 0.8, yy, s, ha="left", va="top", zorder=4, fontsize=FS_VALUE,
                    fontweight="bold", color=INK)
            yy += LH(FS_VALUE)
        yy = y + 0.9 + max(len(tl) * LH(FS_VALUE), 2 * R) + 0.5
        for s in th:
            ax.text(x + PADX, yy, s, ha="left", va="top", zorder=4, fontsize=FS_ANNOT, color=INK2)
            yy += LH(FS_ANNOT)
        yy += 0.5
        for s in he:
            ax.text(x + PADX, yy, s, ha="left", va="top", zorder=4, fontsize=FS_SMALL, color=MUTED)
            yy += LH(FS_SMALL)
        assert yy - y <= h + 1e-6, ("card overflow", step, yy - y, h)

    group_frame(x_in, w_in, h_in, "Inside the model loop", DASHE, (0, (4, 2)))
    group_frame(x_out, w_out, h_out, "Outside the model loop", BOXE, "-")
    group_frame(x_ot, w_ot, h_ot, "Over time", BOXE, "-")
    y0 = y_grp + lab_h + 1.0
    ys_in = [y0, y0 + row_h[0] + 1.0]
    for k, s in enumerate((1, 2, 3, 4)):
        r_, c_ = divmod(k, 2)
        card(s, x_in + 1.0 + c_ * (w_in_card + 1.0), ys_in[r_], w_in_card, need[s])
    card(5, x_out + 1.0, y0, w_out_card, need[5])
    card(6, x_ot + 1.0, y0, w_ot_card, need[6])

    # arrows: stubs to a bus, one arrow from the bus to box 2
    cx_in, cx_out, cx_ot = x_in + w_in / 2, x_out + w_out / 2, x_ot + w_ot / 2
    bx = xs[1] + bw / 2
    seg(cx_in, y_grp, cx_in, y_bus, DASHE, (0, (4, 2)))
    seg(cx_out, y_grp, cx_out, y_bus, BOXE)
    seg(cx_ot, y_grp, cx_ot, y_bus, BOXE)
    seg(min(cx_in, bx), y_bus, cx_ot, y_bus, BOXE)
    parrow(bx, y_bus, bx, y_strip + sh + 0.4)
    print("[fig_protocol] needs", {k: round(v, 2) for k, v in need.items()}, "row_h", [round(v, 2) for v in row_h],
          "grp_h %.2f (in %.2f out %.2f ot %.2f)" % (grp_h, h_in, h_out, h_ot))
    _min_font(fig, "fig_protocol")
    save(fig, "fig_protocol")


# ------------------------------------------------------------------ fig_crosssite
def fig_crosssite():
    d_ = pd.read_csv(OSF_PANEL)
    q_ = d_[d_.endpoint == "questions"]
    p_ = q_.pivot(index="ym", columns="site", values="count").sort_index()
    base_ = p_.loc["2022-06":"2022-11"].mean()
    win_ = (p_.loc["2022-12":"2023-12"].mean() / base_ - 1) * 100
    late_ = (p_.loc["2025-06":"2026-05"].mean() / base_ - 1) * 100
    targets = [("stackoverflow", "2022-12 to 2023-12", win_, -37.5),
               ("ru.stackoverflow", "2022-12 to 2023-12", win_, -32.7),
               ("math.stackexchange", "2022-12 to 2023-12", win_, -10.4),
               ("mathoverflow.net", "2022-12 to 2023-12", win_, -2.2),
               ("math.stackexchange", "2025-06 to 2026-05", late_, -76.8),
               ("mathoverflow.net", "2025-06 to 2026-05", late_, -41.5)]
    chk = []
    for site, wname, ser, want in targets:
        got = float(ser[site])
        chk.append(dict(site=site, window=wname, got=got, got_1dp=round(got, 1), want=want, ok=bool(round(got, 1) == want)))
    json.dump(chk, open(os.path.join(STEP3, "crosssite_selfcheck.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for c in chk:
        print(f"[crosssite selfcheck] {c['site']:20s} {c['window']}  got {c['got']:.3f}  -> {c['got_1dp']:.1f}  want {c['want']:.1f}  {'OK' if c['ok'] else 'MISMATCH'}")
    if not all(c["ok"] for c in chk):
        raise SystemExit("fig_crosssite 自证未过：与 §5.1 六个数不吻合，停止，不画图")

    idx = (p_ / base_ * 100).loc["2021-06":"2026-05"]
    idx = idx.where(p_.loc["2021-06":"2026-05"] > 0)   # 三个零计数月（pt.stackoverflow）在对数轴上无定义，留空不连线
    x = pd.to_datetime(idx.index + "-01")
    fig = plt.figure(figsize=(COL, 2.95))
    ax_ = fig.add_subplot(111)
    ax_.axvspan(pd.Timestamp("2022-06-01"), pd.Timestamp("2023-12-01"), color="#f2f4f7", zorder=0)
    ax_.axvline(pd.Timestamp("2022-12-01"), color=INK2, ls=(0, (3.5, 1.5)), lw=LW_REF, zorder=2)
    GREYC = "#b9b9b9"
    for k, s in enumerate(("es.stackoverflow", "pt.stackoverflow", "superuser")):
        ax_.plot(x, idx[s], color=GREYC, lw=0.9, zorder=2.5,
                 label="Other candidate controls" if k == 0 else "_nolegend_")
    CS = [("ru.stackoverflow", RAMP[0], "Russian Stack Overflow"), ("math.stackexchange", "#3E85C6", "Mathematics Stack Exchange"), ("mathoverflow.net", "#C2603E", "MathOverflow")]
    ax_.plot(x, idx["stackoverflow"], color=ACCENT, lw=2.4, zorder=5, label="English Stack Overflow", solid_capstyle="round")
    for s, c, lab in CS:
        ax_.plot(x, idx[s], color=c, lw=LW_SERIES + 0.2, zorder=4, label=lab, solid_capstyle="round")
    ax_.set_yscale("log")
    lo, hi = float(np.nanmin(idx.values)), float(np.nanmax(idx.values))
    ax_.set_ylim(lo * 0.85, hi * 1.12)
    ticks = [t for t in (3, 10, 30, 100, 200) if ax_.get_ylim()[0] <= t <= ax_.get_ylim()[1]]
    ax_.set_yticks(ticks); ax_.set_yticklabels([str(t) for t in ticks])
    ax_.yaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    ax_.set_xlim(x[0], x[-1])
    ax_.set_ylabel("Monthly questions, index\n(2022-06 to 2022-11 mean = 100)", fontsize=FS_LABEL)
    ax_.grid(color=GRID, lw=LW_GRID)
    year_axis(ax_); framed(ax_)
    # 图例顺序：强调线、三条彩线、灰线
    hh, ll = ax_.get_legend_handles_labels()
    order = [ll.index(n) for n in ("English Stack Overflow", "Russian Stack Overflow", "Mathematics Stack Exchange", "MathOverflow", "Other candidate controls")]
    ax_.legend([hh[i] for i in order], [ll[i] for i in order], frameon=False, fontsize=FS_LEG, ncol=3,
               loc="upper center", bbox_to_anchor=(0.5, -0.12), handlelength=1.6, columnspacing=1.5, borderaxespad=0.0)
    _min_font(fig, "fig_crosssite")
    save(fig, "fig_crosssite")


# ------------------------------------------------------------------ fig_shap
def fig_shap():
    R_ = json.load(open(resolve("步骤3_SHAP/shap_result.json"), encoding="utf-8"))
    if not R_["C1"]["passed"]:
        print("[fig_shap] C1 未过，不出图")
        return
    Z = np.load(resolve("步骤3_SHAP/shap_oof.npz"))
    sv, Xm, fn = Z["shap"], Z["X"], [str(s) for s in Z["feature_names"]]
    disp = R_["display_names"]
    ms_ = np.abs(sv).mean(axis=0)
    order = list(np.argsort(-ms_, kind="stable")[:12])
    assert [fn[i] for i in order] == [r["id"] for r in R_["per_feature"][:12]], "前 12 名与 shap_result.json 不一致"
    rng = np.random.default_rng(20261004)
    cmap = LinearSegmentedColormap.from_list("coldwarm", RAMP)
    fig = plt.figure(figsize=(COL, 3.75))
    gs = GridSpec(1, 2, width_ratios=[1.75, 1.0], wspace=0.85, figure=fig)
    axA = fig.add_subplot(gs[0])
    n = sv.shape[0]
    for r, j in enumerate(order):
        col = Xm[:, j]
        q = (rankdata(col, method="average") - 1) / (n - 1)
        yj = r + rng.uniform(-0.32, 0.32, size=n)
        perm = rng.permutation(n)
        axA.scatter(sv[perm, j], yj[perm], c=q[perm], cmap=cmap, vmin=0, vmax=1, s=2.2, linewidths=0,
                    rasterized=True, zorder=3)
    axA.axvline(0, color=BASE, lw=LW_REF, zorder=2)
    axA.set_yticks(range(12)); axA.set_yticklabels([disp[fn[j]] for j in order], fontsize=FS_TICK)
    axA.set_ylim(11.6, -0.6)
    axA.set_xlabel("SHAP value (score points)", fontsize=FS_LABEL)
    axA.grid(axis="x", color=GRID, lw=LW_GRID)
    framed(axA); panel_label(axA, "A")
    sm = matplotlib.cm.ScalarMappable(cmap=cmap, norm=matplotlib.colors.Normalize(0, 1))
    cb = fig.colorbar(sm, ax=axA, fraction=0.035, pad=0.02, aspect=28)
    cb.set_ticks([]); cb.outline.set_linewidth(LW_SPINE); cb.outline.set_edgecolor(BASE)
    cb.set_label("Feature value (low \u2192 high)", fontsize=FS_ANNOT, color=INK2)

    axB = fig.add_subplot(gs[1])
    gsh = R_["group_share"]
    gnames = R_["group_names"]
    groups = ["P1", "P2", "P3", "P4", "P5", "T"]
    vals = [gsh[g] for g in groups]
    ybar = list(range(len(groups)))
    axB.barh(ybar, vals, height=0.62, color=[RAMP[0]] * 5 + ["#9a9a9a"], zorder=3, edgecolor=SURFACE, linewidth=0.4)
    for yy, v in zip(ybar, vals):
        axB.annotate(f"{v:.2f}", xy=(v, yy), xytext=(4, 0), textcoords="offset points", ha="left", va="center",
                     fontsize=FS_VALUE, color=INK, fontweight="bold")
    axB.set_yticks(ybar); axB.set_yticklabels([f"{g} {gnames[g]}" for g in groups], fontsize=FS_TICK)
    axB.set_ylim(len(groups) - 0.4, -0.6)
    axB.set_xlim(0, max(vals) * 1.38)
    axB.set_xlabel("Share of total |SHAP|", fontsize=FS_LABEL)
    axB.grid(axis="x", color=GRID, lw=LW_GRID)
    framed(axB); panel_label(axB, "B")
    _min_font(fig, "fig_shap")
    save(fig, "fig_shap")


# ------------------------------------------------------------------ fig_forest
def _jload(rel):
    return json.load(open(resolve(rel), encoding="utf-8"))


def fig_forest():
    import re as _re
    A2_ = "R2_analyze_result.json"
    a2 = _jload(A2_)
    s46p = r"R2_blind_s46\R2s46_analyze_result.json"; s46 = _jload(s46p)
    glmp = r"R2_downstream\blind\05_additional_checks\glm_relabel\cross_family_glm-4.6.json"; glm = _jload(glmp)
    orp = r"R2_downstream\orig\02_estimation\capability_ramp.json"; orr = _jload(orp)
    clp = r"R2_downstream\blind\02_estimation\closure_check.json"; cl = _jload(clp)
    sgp = r"R2_downstream\blind\02_estimation\review_r1\p0_2_staging_ground.json"; sg = _jload(sgp)["panel_b_corrected_split"]
    tnp = r"R2_downstream\blind\02_estimation\asker_tenure.json"; tn = _jload(tnp)["stratified_gamma"]
    rvp = r"R2_downstream\blind\02_estimation\asker_rival_exact.json"; rv = _jload(rvp)["ppml"]["novice_x_month_fe"]
    capp = r"R2_downstream\blind\logs\check_cap_sensitivity.log"
    caplines = open(resolve(capp), encoding="utf-8").read().splitlines()

    def capline(prefix):
        for i, s in enumerate(caplines, 1):
            if s.startswith(prefix):
                m = _re.search(r"\u03b3 = (-?[\d.]+) \(SE ([\d.]+)\)", s)
                return float(m.group(1)), float(m.group(2)), i
        raise KeyError(prefix)

    def full(lang):
        r = next(r for r in orr[lang]["windowed"] if r["window"].startswith("full"))
        return r["gamma"], r["se"]

    cap1, cap1se, cap1l = capline("\u5254\u9664\u89e6\u9876\u95ee\u9898")        # 剔除触顶问题
    cap2, cap2se, cap2l = capline("\u5254\u9664 \u22651,000")                      # 剔除 ≥1,000
    nw_c, nw_s = a2["blind"]["logratio_nw"]["coef"] / 3, a2["blind"]["logratio_nw"]["se"] / 3
    # (group, label, est, se, estimator, source_path, source_key, expected_value, digits)
    ROWS = [
        ("Estimators (python, blind)", "log-count OLS", a2["blind"]["ols"]["coef"], a2["blind"]["ols"]["se"], "log-count OLS", A2_, "blind.ols.coef; blind.ols.se", -0.304, 3),
        ("Estimators (python, blind)", "fixed-total FE-PPML", a2["blind"]["ppml"]["coef"], a2["blind"]["ppml"]["se"], "FE-PPML", A2_, "blind.ppml.coef; blind.ppml.se", -0.29, 2),
        ("Estimators (python, blind)", "Newey\u2013West log(s4/s1) per point", nw_c, nw_s, "Newey-West log-ratio, coef and SE divided by 3", A2_, "blind.logratio_nw.coef / 3; blind.logratio_nw.se / 3", -0.30, 2),
        ("Raters (python)", "blind classification (Sonnet 5)", a2["blind"]["ols"]["coef"], a2["blind"]["ols"]["se"], "log-count OLS", A2_, "blind.ols.coef; blind.ols.se", -0.304, 3),
        ("Raters (python)", "earlier classifier re-run blind (Sonnet 4.6)", s46["headline_s46"]["ols"]["coef"], s46["headline_s46"]["ols"]["se"], "log-count OLS", s46p, "headline_s46.ols.coef; headline_s46.ols.se", -0.346, 3),
        ("Raters (python)", "independent family (GLM-4.6)", glm["dose_glm"]["ols"][0], glm["dose_glm"]["ols"][1], "log-count OLS", glmp, "dose_glm.ols[0]; dose_glm.ols[1]", -0.227, 3),
        ("Languages (earlier, date-visible classification)", "python", full("python")[0], full("python")[1], "log-count OLS", orp, "python.windowed[window startswith 'full'].gamma; .se", -0.416, 3),
        ("Languages (earlier, date-visible classification)", "javascript", full("javascript")[0], full("javascript")[1], "log-count OLS", orp, "javascript.windowed[window startswith 'full'].gamma; .se", -0.229, 3),
        ("Languages (earlier, date-visible classification)", "java", full("java")[0], full("java")[1], "log-count OLS", orp, "java.windowed[window startswith 'full'].gamma; .se", -0.123, 3),
        ("Sample and specification (python, blind)", "excluding questions at the 1,400-character cap", cap1, cap1se, "log-count OLS (SE printed to 3 dp in log)", capp, f"line {cap1l}: gamma and SE parsed from the log line", -0.292, 3),
        ("Sample and specification (python, blind)", "stricter exclusion at 1,000 characters", cap2, cap2se, "log-count OLS (SE printed to 3 dp in log)", capp, f"line {cap2l}: gamma and SE parsed from the log line", -0.278, 3),
        ("Sample and specification (python, blind)", "s0 folded into s1", a2["blind_s0_folded_into_s1"]["ols"]["coef"], a2["blind_s0_folded_into_s1"]["ols"]["se"], "log-count OLS", A2_, "blind_s0_folded_into_s1.ols.coef; .se", -0.318, 3),
        ("Sample and specification (python, blind)", "closed questions dropped", cl["gamma_excl_closed_ols"]["gamma"], cl["gamma_excl_closed_ols"]["se"], "log-count OLS", clp, "gamma_excl_closed_ols.gamma; .se", -0.311, 3),
        ("Sample and specification (python, blind)", "before Staging Ground", sg["before"]["gamma"], sg["before"]["se"], "log-count OLS, post window 2022-12..2024-05", sgp, "panel_b_corrected_split.before.gamma; .se", -0.263, 3),
        ("Sample and specification (python, blind)", "after Staging Ground", sg["after"]["gamma"], sg["after"]["se"], "log-count OLS, post window 2024-06..2026-05", sgp, "panel_b_corrected_split.after.gamma; .se", -0.335, 3),
        ("Asker composition (python, blind)", "youngest tenure tercile", tn["young"]["gamma"], tn["young"]["se"], "log-count OLS", tnp, "stratified_gamma.young.gamma; .se", -0.322, 3),
        ("Asker composition (python, blind)", "middle tenure tercile", tn["mid"]["gamma"], tn["mid"]["se"], "log-count OLS", tnp, "stratified_gamma.mid.gamma; .se", -0.299, 3),
        ("Asker composition (python, blind)", "oldest tenure tercile", tn["old"]["gamma"], tn["old"]["se"], "log-count OLS", tnp, "stratified_gamma.old.gamma; .se", -0.327, 3),
        ("Asker composition (python, blind)", "FE-PPML with novice-by-month effects", rv["gamma"], rv["se"], "FE-PPML", rvp, "ppml.novice_x_month_fe.gamma; .se", -0.307, 3),
    ]
    # 点估计与稿件现有数对账（按稿件写的位数）；对不上就停
    bad = []
    for r in ROWS:
        if round(r[2], r[8]) != r[7]:
            bad.append((r[1], r[2], r[7]))
    if bad:
        raise SystemExit(f"fig_forest：点估计与稿件数对不上，停止：{bad}")
    with open(os.path.join(STEP3, "fig_forest_rows.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w_ = csv.writer(f)
        w_.writerow(["group", "row", "estimate", "se", "estimator", "source_path", "source_key"])
        for r in ROWS:
            w_.writerow([r[0], r[1], f"{r[2]:.6f}", f"{r[3]:.6f}", r[4], r[5], r[6]])
    print(f"[fig_forest] {len(ROWS)} rows, all with estimate and SE; none dropped")

    fig = plt.figure(figsize=(COL, 4.72))
    ax_ = fig.add_subplot(111)
    y = 0.0
    yt, yl, heads, sep = [], [], [], []
    last = None
    for r in ROWS:
        if r[0] != last:
            if last is not None:
                y -= 0.35
                sep.append(y + 0.0)
            heads.append((y, r[0]))
            y -= 1.0
            last = r[0]
        yt.append(y); yl.append(r[1]); y -= 1.0
    HL = -0.304
    ax_.axvline(0, color=ACCENT, lw=LW_REF, zorder=2)
    ax_.axvline(HL, color=INK2, lw=LW_REF, ls=(0, (3.5, 1.5)), zorder=2)
    for yy, r in zip(yt, ROWS):
        main = r[1] in ("log-count OLS", "blind classification (Sonnet 5)")
        c = RAMP[0] if main else INK2
        ax_.plot([r[2] - 1.96 * r[3], r[2] + 1.96 * r[3]], [yy, yy], color=c, lw=LW_CI if main else LW_CI_THIN,
                 solid_capstyle="round", zorder=3)
        ax_.plot(r[2], yy, "o", color=c, ms=MS_MAIN if main else MS_MID, markeredgecolor=SURFACE,
                 markeredgewidth=MEW, zorder=4)
    for yy, name in heads:
        ax_.text(0.006, yy, name, transform=ax_.get_yaxis_transform(), ha="left", va="center",
                 fontsize=FS_VALUE, fontweight="bold", color=INK, zorder=5)
    for ys in sep:
        ax_.axhline(ys + 0.0 + 0.0, color=GRID, lw=LW_GRID, zorder=1)
    ax_.set_yticks(yt); ax_.set_yticklabels(yl, fontsize=FS_TICK)
    ax_.set_ylim(y + 0.45, 0.6)
    ax_.set_xlim(-0.64, 0.05)
    ax_.set_xlabel("Dose slope \u03b3, 95% CI", fontsize=FS_LABEL)
    ax_.grid(axis="x", color=GRID, lw=LW_GRID)
    framed(ax_)
    _min_font(fig, "fig_forest")
    save(fig, "fig_forest")


# ------------------------------------------------------------------ fig_placebo
def fig_placebo():
    # 与 fig3_robustness 的 B 面板同一读取、同一算法：直接用上面该图算出的 gs_c（逐截点 γ）、wpy、EVENT、W
    evs_ = sorted(gs_c)
    xs_ = [pd.Timestamp(year=e // 12, month=e % 12 + 1, day=1) for e in evs_]
    assert abs(gs_c[EVENT] - (-0.145)) < 0.0006, "真实截点 γ 与稿件 −0.145 不一致"
    fig = plt.figure(figsize=(COL, 3.3))
    axB = fig.add_subplot(111)
    for xi, e in zip(xs_, evs_):
        v = gs_c[e]
        if e == EVENT:
            axB.plot(xi, v, "o", ms=MS_EMPH, color=ACCENT, zorder=5, markeredgecolor=SURFACE, markeredgewidth=MEW)
        elif e + W - 1 < EVENT:
            axB.plot(xi, v, "s", ms=MS_SMALL + 1, color="#4a4a4a", zorder=5, markeredgecolor=SURFACE, markeredgewidth=MEW)
        elif e < EVENT:
            axB.plot(xi, v, "o", ms=MS_SMALL, color="#4a4a4a", zorder=4, markeredgecolor=SURFACE, markeredgewidth=MEW_S)
        else:
            axB.plot(xi, v, "o", ms=MS_TINY, color="#b9b9b9", zorder=3, markeredgecolor=SURFACE, markeredgewidth=MEW_S)
    axB.axvspan(pd.Timestamp("2022-12-01"), xs_[-1], color="#f2f4f7", zorder=0)
    axB.axvline(pd.Timestamp("2022-12-01"), color=ACCENT, ls=(0, (3.5, 1.5)), lw=LW_REF, alpha=0.75, zorder=2)
    axB.axhline(0, color=BASE, lw=LW_REF, zorder=1)
    tx = pd.Timestamp(year=EVENT // 12, month=EVENT % 12 + 1, day=1)
    axB.annotate("true event", xy=(tx, gs_c[EVENT]), xytext=(-9, 0), textcoords="offset points", ha="right",
                 va="center", fontsize=FS_ANNOT, color=ACCENT, fontweight="bold")
    _h = [Line2D([], [], ls="none", marker="s", ms=MS_SMALL + 1, color="#4a4a4a", markeredgecolor=SURFACE,
                 markeredgewidth=MEW, label="window entirely pre-event"),
          Line2D([], [], ls="none", marker="o", ms=MS_SMALL, color="#4a4a4a", markeredgecolor=SURFACE,
                 markeredgewidth=MEW_S, label="window overlaps treatment")]
    axB.legend(handles=_h, frameon=False, fontsize=FS_LEG, loc="upper left", handletextpad=0.5,
               borderaxespad=0.2, labelspacing=0.25)
    axB.text(0.985, 0.04, "cutoffs inside the treated period", transform=axB.transAxes, ha="right", va="bottom",
             fontsize=FS_ANNOT, color=MUTED)
    axB.set_ylabel("Dose slope \u03b3, matched \u00b19-month window")
    axB.set_xlabel("Candidate cutoff date")
    year_axis(axB)
    axB.grid(axis="y", color=GRID, lw=LW_GRID); finish(axB)
    _min_font(fig, "fig_placebo")
    save(fig, "fig_placebo")


# ------------------------------------------------------------------ fig_outside
# 2026-10-05：图 8 由单面板 κ 图（fig_kappa，仍留在上面，不再进 artwork 与闸门）扩为三面板
# 「模型环路之外的证据」。A=κ 对人工共识（沿用 fig_kappa 的内容与读取）；
# B=金标准 300 题平均可替代度分事件前→后的变化（memorization_check.json 的 diff/se）；
# C=版主按「重复问题」关闭的比例（R2d_extra_result.json 盲分类臂 closure_reasons）。
# 凡画出的数一律从产物读；读出后先做自证，不符即抛错，不调数据。
def fig_outside():
    mc_b = J(resolve(BLIND_EST, "memorization_check.json"))
    mc_o = J(resolve(ORIG_EST, "memorization_check.json"))
    cr_all = J(resolve("R2d_extra_result.json"))
    cr = cr_all["blind"]["stats"]["closure_reasons"]       # 注意：要 blind 臂，不是 orig
    # --- B 数据 ---
    rowsB = [("Human\nconsensus", mc_b["human"]["diff"], mc_b["human"]["se"], (-0.613, (-0.852, -0.375))),
             ("Blind\nclassification", mc_b["model"]["diff"], mc_b["model"]["se"], (-0.760, (-1.052, -0.469))),
             ("Earlier\nclassification", mc_o["model"]["diff"], mc_o["model"]["se"], (-0.535, (-0.784, -0.286)))]
    for lab, d_, se_, (dd, (a_, b_)) in rowsB:
        lo_, hi_ = d_ - 1.96 * se_, d_ + 1.96 * se_
        assert round(d_, 3) == dd, f"B 自证失败：{lab!r} diff {d_:.4f} != {dd}"
        assert abs(lo_ - a_) <= 0.0011 and abs(hi_ - b_) <= 0.0011, f"B 自证失败：{lab!r} 区间 [{lo_:.3f}, {hi_:.3f}] != [{a_}, {b_}]"
    # --- C 数据 ---
    dup = list(cr["dup_pct"])
    assert [round(v, 1) for v in dup] == [2.8, 2.6, 5.4, 12.5], f"C 自证失败：dup_pct {dup}"
    assert round(cr["spearman"][0], 3) == 0.135, f"C 自证失败：spearman {cr['spearman'][0]}"
    print("[fig_outside] 自证通过：B diff/区间、C dup_pct/spearman；closure_reasons.N =", cr["N"])

    fig = plt.figure(figsize=(COL, 2.7))
    gs_ = GridSpec(1, 3, figure=fig, width_ratios=[1.35, 0.95, 1.1], wspace=0.62)
    axA, axB, axC = (fig.add_subplot(gs_[0, i]) for i in range(3))

    # ---- A：κ 对人工共识（内容与数值同 fig_kappa，不改读取方式）----
    _kk = KP["kappa_vs_consensus"]
    RAT = [(lab, _kk[key]["kappa"], _kk[key]["ci"][0], _kk[key]["ci"][1]) for lab, key in (
        ("Claude Sonnet 5\n(blind, primary)", "blind"), ("Claude Sonnet 4.6\n(earlier)", "orig"),
        ("GLM-4.6", "glm46"), ("GLM-5.3\n(frontier tier)", "glm53"))]
    HUM_, HLO_, HHI_ = 0.533, 0.439, 0.627
    axA.axvspan(HLO_, HHI_, color="#ebe7f5", zorder=0)
    axA.axvline(HUM_, color=RAMP[1], lw=LW_REF, ls=(0, (3.5, 1.5)), zorder=2)
    axA.annotate("human–human\nagreement\nκ = 0.533", xy=(HUM_, 3.7), xytext=(4, 0),
                 textcoords="offset points", ha="left", va="center", fontsize=FS_ANNOT, color=RAMP[1], fontweight="bold")
    for i, (lab, k, lo, hi) in enumerate(RAT):
        axA.plot([lo, hi], [i, i], color=RAMP[0], lw=LW_CI, solid_capstyle="round", zorder=3)
        axA.plot(k, i, "o", color=RAMP[0], ms=MS_MAIN, markeredgecolor=SURFACE, markeredgewidth=MEW, zorder=4)
        axA.annotate(f"{k:.3f}", xy=(hi, i), xytext=(5, 0), textcoords="offset points",
                     va="center", fontsize=FS_VALUE, color=RAMP[0], fontweight="bold")
    axA.set_yticks(range(len(RAT)))
    axA.set_yticklabels([r[0] for r in RAT], fontsize=FS_TICK)
    axA.set_ylim(-0.6, 4.35); axA.invert_yaxis()
    axA.set_xlim(0.30, 0.84)
    axA.set_xticks([0.4, 0.5, 0.6, 0.7])
    axA.set_xlabel("Binary κ vs. human consensus", fontsize=FS_LABEL)
    axA.grid(axis="x", color=GRID, lw=LW_GRID)
    framed(axA)
    panel_label(axA, "A")

    # ---- B：金标准 300 题，平均可替代度分 事件前→后 ----
    axB.axvline(0, color=BASE, lw=LW_REF, zorder=1)
    for i, (lab, d_, se_, _x) in enumerate(rowsB):
        lo_, hi_ = d_ - 1.96 * se_, d_ + 1.96 * se_
        axB.plot([lo_, hi_], [i, i], color=RAMP[0], lw=LW_CI, solid_capstyle="round", zorder=3)
        axB.plot(d_, i, "o", color=RAMP[0], ms=MS_MAIN, markeredgecolor=SURFACE, markeredgewidth=MEW, zorder=4)
        axB.annotate(f"{d_:.2f}".replace("-", "−"), xy=(d_, i), xytext=(0, 6), textcoords="offset points",
                     ha="center", va="bottom", fontsize=FS_VALUE, color=RAMP[0], fontweight="bold")
    axB.set_yticks(range(3)); axB.set_yticklabels([r[0] for r in rowsB], fontsize=FS_TICK)
    axB.set_ylim(2.6, -0.75)
    axB.set_xlim(-1.2, 0.1)
    axB.set_xticks([-1.0, -0.5, 0.0])
    axB.set_xticklabels(["−1.0", "−0.5", "0"])
    axB.set_xlabel("Change in mean score, pre to post\n(0–4 scale)", fontsize=FS_LABEL)
    axB.grid(axis="x", color=GRID, lw=LW_GRID)
    framed(axB)
    panel_label(axB, "B")

    # ---- C：版主按「重复问题」关闭的比例 ----
    for i, v in enumerate(dup):
        axC.bar(i, v, width=0.68, color=RAMP[i], zorder=3, edgecolor=SURFACE, linewidth=0.4)
        axC.annotate(f"{v:.1f}", xy=(i, v), xytext=(0, 2), textcoords="offset points",
                     ha="center", va="bottom", fontsize=FS_VALUE, color=INK, fontweight="bold")
    axC.set_xticks(range(4)); axC.set_xticklabels(["s1", "s2", "s3", "s4"], fontsize=FS_TICK)
    axC.set_ylim(0, 14.5)
    axC.set_ylabel("Closed as duplicate, % of questions", fontsize=FS_LABEL)
    axC.set_xlabel("Substitutability bin", fontsize=FS_LABEL)
    axC.grid(axis="y", color=GRID, lw=LW_GRID)
    framed(axC)
    panel_label(axC, "C")

    _min_font(fig, "fig_outside")
    save(fig, "fig_outside")


# =====================================================================================
# 加图第 1 步新增（2026-10-05）：fig_bins / fig_agree / fig_answer / fig_sampling
# 新图一律读复现包里的文件（_pkg）；fig_bins 读 R2figbins.py 的结果。凡画出的数先自证，不符即抛错。
# 草稿：工作文档\图加_草稿_20261005\（样式常量、版式、自证沿用；辅助函数用本脚本既有的）。
# =====================================================================================
_pkg = resolve                                    # 键 = 包内相对路径本身（见 _PKG_MAP 末尾新增项）
FIGBINS = resolve("R2figbins_result.json")
Z95 = 1.959964


def _grid(ax, axis):
    ax.grid(axis=axis, color=GRID, lw=LW_GRID)


def _subtitle(ax, text, x=0.06):
    ax.set_title(text, fontsize=FS_ANNOT, color=INK2, loc="left", x=x, y=1.005)


# ------------------------------------------------------------------ fig_bins
def fig_bins():
    R_ = json.load(open(FIGBINS, encoding="utf-8"))
    assert [round(R_["blind"]["deltas"][k]["coef"], 3) for k in ("s2", "s3", "s4")] == [-0.213, -0.495, -0.919], "fig_bins 自证失败：blind δ"
    assert [round(R_["earlier"]["deltas"][k]["coef"], 3) for k in ("s2", "s3", "s4")] == [-0.258, -0.630, -1.261], "fig_bins 自证失败：earlier δ"
    for k, want in (("blind", -0.304), ("earlier", -0.416), ("s46_rerun_blind", -0.346), ("glm46", -0.227)):
        assert round(R_[k]["gamma_linear"], 3) == want, f"fig_bins 自证失败：γ {k}"
    print("[fig_bins] 自证通过：blind/earlier δ 与四个 γ")

    def series(name):
        r = R_[name]
        return (r["gamma_linear"], np.array([0.0] + [r["deltas"][k]["coef"] for k in ("s2", "s3", "s4")]),
                np.array([0.0] + [r["deltas"][k]["se"] for k in ("s2", "s3", "s4")]))

    fig, axes = plt.subplots(1, 2, figsize=(COL, 2.75), sharey=True)
    yt = [2.0, 1.5, 1.0, 0.7, 0.5, 0.3, 0.2]
    for k, ax in enumerate(axes):
        framed(ax); _grid(ax, "y")
        ax.set_yscale("log"); ax.set_ylim(0.15, 2.3)
        ax.set_yticks(yt); ax.set_yticks([], minor=True)
        ax.set_yticklabels(["0%" if v == 1 else ("+%d%%" % round(100 * (v - 1)) if v > 1 else "\u2212%d%%" % round(100 * (1 - v))) for v in yt])
        ax.axhline(1.0, color=BASE, lw=LW_REF)
        ax.set_xlim(0.6, 4.9 if k == 1 else 5.35)
        ax.set_xticks([1, 2, 3, 4]); ax.set_xticklabels(["s1", "s2", "s3", "s4"])
        ax.set_xlabel("Substitutability bin (s1 least, s4 most substitutable)")
    axes[0].set_ylabel("Post-to-pre ratio relative to s1")

    def draw(ax, name, color, dx, marker, filled, label, ms=MS_MAIN, direct=None):
        g, c, se = series(name)
        x = np.array([1, 2, 3, 4]) + dx
        xs = np.linspace(1, 4, 50)
        ax.plot(xs + dx, np.exp(g * (xs - 1)), ls=(0, (4, 2.5)), color=color, lw=LW_REF, zorder=2)
        for i in range(1, 4):
            ax.plot([x[i]] * 2, [np.exp(c[i] - Z95 * se[i]), np.exp(c[i] + Z95 * se[i])], color=color,
                    lw=LW_CI_THIN if dx else LW_CI, solid_capstyle="butt", zorder=3)
        ax.plot(x, np.exp(c), ls="none", marker=marker, ms=ms, mfc=color if filled else SURFACE,
                mec=SURFACE if filled else color, mew=MEW if filled else 1.1, zorder=4, label=label)
        if direct:
            ax.text(4.32, np.exp(c[3]), direct, color=color, fontsize=FS_ANNOT, va="center", ha="left")

    draw(axes[0], "blind", LANGC["python"], 0.0, "o", True, "blind (Sonnet 5)", direct="blind\n(Sonnet 5)")
    panel_label(axes[0], "A")
    _subtitle(axes[0], "headline classification")
    draw(axes[1], "earlier", "#3f3f3f", -0.13, "o", False, "earlier (Sonnet 4.6, date-visible)")
    draw(axes[1], "s46_rerun_blind", "#3f3f3f", 0.0, "s", True, "Sonnet 4.6 re-run blind", ms=MS_MID + 0.6)
    draw(axes[1], "glm46", "#8a8a8a", +0.13, "D", True, "GLM-4.6 (independent family)", ms=MS_MID)
    axes[1].legend(frameon=False, fontsize=FS_LEG, loc="lower left", handletextpad=0.4)
    panel_label(axes[1], "B")
    _subtitle(axes[1], "three other classifications of the same questions")
    fig.subplots_adjust(wspace=0.08)
    _min_font(fig, "fig_bins")
    save(fig, "fig_bins")


# ------------------------------------------------------------------ fig_agree
def _kappa_bin(a, b):
    a = np.asarray(a) >= 3; b = np.asarray(b) >= 3
    po = np.mean(a == b); pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    return (po - pe) / (1 - pe)


def fig_agree():
    import io
    A = pd.read_csv(_pkg("03_validation/gold_standard/coding_sheet_A_v2.csv"), encoding="utf-8-sig")
    Bc = pd.read_csv(_pkg("03_validation/gold_standard/coding_sheet_B_v2.csv"), encoding="utf-8-sig")
    hb = A[["question_id", "score_0_4"]].merge(Bc[["question_id", "score_0_4"]], on="question_id", suffixes=("_a", "_b"))
    assert len(hb) == 300
    blind = pd.read_csv(_pkg("07_blind_reclassification/labels/question_labels_python_blind.csv"))
    earlier = pd.read_csv(_pkg("01_panels_and_classification/data/question_labels_python_2021-2024.csv"))
    glm = pd.DataFrame([json.loads(l) for l in io.open(_pkg("05_additional_checks/glm_relabel/labels_glm-4.6.jsonl"), encoding="utf-8") if l.strip()])
    glm = glm[["question_id", "score"]].drop_duplicates("question_id")
    be = blind[["question_id", "score"]].merge(earlier[["question_id", "score"]], on="question_id", suffixes=("_b", "_e"))
    bg = blind[["question_id", "score"]].merge(glm, on="question_id", suffixes=("_b", "_g"))
    k_h, k_be, k_bg = _kappa_bin(hb.score_0_4_a, hb.score_0_4_b), _kappa_bin(be.score_b, be.score_e), _kappa_bin(bg.score_b, bg.score_g)
    print("[fig_agree] kappa coders %.4f  blind-earlier %.4f (n=%d)  blind-glm %.4f (n=%d)" % (k_h, k_be, len(be), k_bg, len(bg)))
    assert round(k_h, 3) == 0.533 and round(k_be, 3) == 0.605 and round(k_bg, 3) == 0.613, "fig_agree 自证失败：κ"
    assert len(be) == 6000 and len(bg) == 5999, "fig_agree 自证失败：N"

    cmap = LinearSegmentedColormap.from_list("ink", ["#ffffff", "#e9e4f7", "#9b8fd0", "#4b2fa6", "#1d0a6b"])
    fig, axes = plt.subplots(1, 3, figsize=(COL, 2.75))
    spec = [(hb.score_0_4_a, hb.score_0_4_b, "Coder A", "Coder B", "two human coders, N = 300"),
            (be.score_b, be.score_e, "Blind classification", "Earlier classification", "blind vs earlier, N = 6,000"),
            (bg.score_b, bg.score_g, "Blind classification", "GLM-4.6", "blind vs GLM-4.6, N = 5,999")]
    for k, (ax, (yv, xv, ylab, xlab, ttl)) in enumerate(zip(axes, spec)):
        M = pd.crosstab(pd.Categorical(yv, categories=range(5)), pd.Categorical(xv, categories=range(5)), dropna=False).to_numpy().astype(float)
        Pm = 100 * M / M.sum()
        # 加图第1步补修：热图由 imshow（PDF 内嵌位图）改为矢量 pcolormesh；格线 edgecolors=face 防缝
        ax.pcolormesh(np.arange(-0.5, 5.5), np.arange(-0.5, 5.5), Pm, cmap=cmap, vmin=0, vmax=max(28, Pm.max()),
                      edgecolors="face", linewidth=0.15, antialiased=False)
        ax.set_xlim(-0.5, 4.5); ax.set_ylim(-0.5, 4.5); ax.set_aspect("equal")
        for i in range(5):
            for j in range(5):
                v = Pm[i, j]
                ax.text(j, i, ("%.0f" % v) if v >= 0.5 else ("<1" if M[i, j] > 0 else "0"), ha="center", va="center",
                        fontsize=FS_SMALL, color=SURFACE if v > 12 else INK2)
        ax.axhline(2.5, color=INK, lw=0.9, ls=(0, (3, 2))); ax.axvline(2.5, color=INK, lw=0.9, ls=(0, (3, 2)))
        ax.set_xticks(range(5)); ax.set_yticks(range(5))
        ax.set_xlabel(xlab); ax.set_ylabel(ylab, labelpad=2)
        for sp in ax.spines.values():
            sp.set_color(BASE); sp.set_linewidth(LW_SPINE)
        ax.tick_params(length=2, color=BASE)
        ax.text(-0.02, 1.02, "ABC"[k], transform=ax.transAxes, fontsize=FS_PANEL, fontweight="bold", va="bottom", ha="left", color=INK)
        _subtitle(ax, ttl, x=0.10)
    fig.subplots_adjust(wspace=0.42)
    _min_font(fig, "fig_agree")
    save(fig, "fig_agree")


# ------------------------------------------------------------------ fig_answer
def fig_answer():
    fa = {int(r["question_id"]): r for r in csv.DictReader(open(_pkg("02_estimation/legB_first_answer.csv"), encoding="utf-8"))}
    lab_ = {}
    for rel in ("09_downstream_rerun/blind/data/question_labels.csv", "09_downstream_rerun/blind/data/question_labels_ext_py.csv"):
        for r in csv.DictReader(open(_pkg(rel), encoding="utf-8")):
            lab_[int(r["question_id"])] = int(r["score"])
    rows = []
    for rel in ("01_panels_and_classification/data/so_questions_python_2021-2024.json",
                "01_panels_and_classification/data/so_questions_python_ext_2024-07_2026-05.json"):
        for q in json.load(open(_pkg(rel), encoding="utf-8")):
            qid = int(q["question_id"]); s = lab_.get(qid)
            if s is None or s == 0 or qid not in fa:
                continue
            cd = int(q["creation_date"]); cm = pd.to_datetime(cd, unit="s").to_period("M")
            fad = fa[qid]["first_answer_date"]
            lat = (int(fad) - cd) / 86400 if fad else np.inf
            rows.append({"score": s, "post": int(cm.year * 12 + cm.month - 1 >= EVENT), "a30": int(lat <= 30), "a90": int(lat <= 90)})
    d = pd.DataFrame(rows)
    assert len(d) == 5500, "fig_answer 自证失败：N"
    T = {w: d.groupby(["score", "post"])[w].mean().unstack() for w in ("a30", "a90")}
    chk = {w: [round(T[w].loc[s, p], 3) for s in (1, 4) for p in (0, 1)] for w in T}
    print("[fig_answer] check", chk)
    assert chk["a30"] == [0.761, 0.681, 0.906, 0.888] and chk["a90"] == [0.769, 0.703, 0.906, 0.896], "fig_answer 自证失败：比例"

    fig, axes = plt.subplots(1, 2, figsize=(COL, 2.3), sharey=True)
    for k, (ax, w, ttl) in enumerate(zip(axes, ("a30", "a90"), ("answered within 30 days of publication", "answered within 90 days of publication"))):
        framed(ax); _grid(ax, "x")
        for s in (1, 2, 3, 4):
            pre, post = 100 * T[w].loc[s, 0], 100 * T[w].loc[s, 1]
            y = 5 - s
            ax.annotate("", xy=(post, y), xytext=(pre, y),
                        arrowprops=dict(arrowstyle="-|>", color=RAMP[s - 1], lw=1.5, shrinkA=3.2, shrinkB=3.0, mutation_scale=7))
            ax.plot(pre, y, "o", ms=MS_MAIN, mfc=SURFACE, mec=PRE, mew=1.1, zorder=4)
            ax.plot(post, y, "o", ms=MS_MAIN, mfc=RAMP[s - 1], mec=SURFACE, mew=MEW, zorder=5)
        ax.set_xlim(62, 96)
        ax.set_xlabel("Questions answered, %")
        ax.set_yticks([4, 3, 2, 1]); ax.set_yticklabels(["s1 (least)", "s2", "s3", "s4 (most)"])
        ax.set_ylim(0.4, 4.6)
        panel_label(ax, "AB"[k])
        _subtitle(ax, ttl)
    h1, = axes[1].plot([], [], "o", ms=MS_MAIN, mfc=SURFACE, mec=PRE, mew=1.1, label="pre-ChatGPT")
    h2, = axes[1].plot([], [], "o", ms=MS_MAIN, mfc=INK2, mec=SURFACE, mew=MEW, label="post-ChatGPT")
    axes[1].legend(handles=[h1, h2], frameon=False, fontsize=FS_LEG, loc="upper right")
    fig.subplots_adjust(wspace=0.06)
    _min_font(fig, "fig_answer")
    save(fig, "fig_answer")


# ------------------------------------------------------------------ fig_sampling
def fig_sampling():
    import io
    tot = pd.read_csv(_pkg("02_estimation/platform_monthly_totals.csv"))
    fills = {}
    for lang in ("python", "javascript", "java"):
        qs = []
        for rel in (f"01_panels_and_classification/data/so_questions_{lang}_2021-2024.json",
                    f"01_panels_and_classification/data/so_questions_{lang}_ext_2024-07_2026-05.json"):
            qs += json.load(io.open(_pkg(rel), encoding="utf-8"))
        df = pd.DataFrame(qs)[["question_id", "ym", "creation_date"]].drop_duplicates("question_id")
        df["creation_date"] = df.creation_date.astype(int)
        out = []
        for ym, gg in df.groupby("ym"):
            assert len(gg) == 100, ("fig_sampling 自证失败：每月应恰 100 题", lang, ym, len(gg))
            cd = np.sort(gg.creation_date.to_numpy())
            y_, mo_ = map(int, ym.split("-"))
            out.append({"ym": ym, "fill_h": (cd[-1] - cd[0]) / 3600.0, "t": y_ * 12 + mo_ - 1})
        fills[lang] = pd.DataFrame(out).sort_values("t")
    f = fills["python"]; pre, post = f[f.t < EVENT], f[f.t >= EVENT]
    chk = (round(pre.fill_h.mean(), 1), round(post.fill_h.mean(), 1), round(post.fill_h.max() / 24, 2))
    chk2 = tuple(round(fills[l][fills[l].t >= EVENT].fill_h.mean(), 1) for l in ("javascript", "java"))
    chk3 = tuple(round(fills[l][fills[l].t >= EVENT].fill_h.max() / 24, 1) for l in ("javascript", "java"))
    print("[fig_sampling] fill check", chk, chk2, chk3)
    assert chk == (6.8, 55.4, 9.75) and chk2 == (119.6, 129.9) and chk3 == (23.3, 21.1), "fig_sampling 自证失败"

    dts = lambda ym: pd.to_datetime(pd.Series(ym) + "-15")
    fig, axes = plt.subplots(1, 2, figsize=(COL, 2.6))
    for k, ax in enumerate(axes):
        framed(ax); _grid(ax, "y")
        ax.set_yscale("log")
        ax.axvline(pd.Timestamp("2022-12-01"), color=BASE, lw=LW_REF, ls=(0, (4, 2.5)))
        year_axis(ax)
        panel_label(ax, "AB"[k])
    for lang in ("python", "javascript", "java"):
        t = tot[tot.tag == lang].sort_values("ym")
        axes[0].plot(dts(t.ym), t.total, color=LANGC[lang], lw=LW_SERIES, label=lang)
        g = fills[lang]
        axes[1].plot(dts(g.ym), g.fill_h, color=LANGC[lang], lw=LW_SERIES, label=lang)
    axes[0].set_ylabel("Questions per month")
    axes[0].set_yticks([300, 1000, 3000, 10000, 30000]); axes[0].set_yticks([], minor=True)
    axes[0].set_yticklabels(["300", "1,000", "3,000", "10,000", "30,000"])
    _subtitle(axes[0], "all questions with the tag, platform-wide")
    axes[1].set_ylabel("Hours")
    for hh, lab in ((24, "1 day"), (168, "1 week")):
        axes[1].axhline(hh, color=GRID, lw=0.9, zorder=0)
        axes[1].text(pd.Timestamp("2021-06-20"), hh * 1.08, lab, fontsize=FS_SMALL, color=MUTED, va="bottom")
    axes[1].set_yticks([1, 3, 10, 30, 100, 300]); axes[1].set_yticks([], minor=True)
    axes[1].set_yticklabels(["1", "3", "10", "30", "100", "300"])
    _subtitle(axes[1], "first to hundredth sampled question of the month")
    axes[0].legend(frameon=False, fontsize=FS_LEG, loc="lower left")
    fig.subplots_adjust(wspace=0.28)
    _min_font(fig, "fig_sampling")
    save(fig, "fig_sampling")


fig_design()
fig_protocol()
fig_crosssite()
fig_shap()
fig_forest()
fig_placebo()
fig_outside()
print("DONE — step 3 new figures: fig_design, fig_crosssite, fig_shap, fig_forest, fig_placebo; step 5: fig_outside")
fig_bins()
fig_agree()
fig_answer()
fig_sampling()
print("DONE — 加图第 1 步：fig_bins, fig_agree, fig_answer, fig_sampling")
