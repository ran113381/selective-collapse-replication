# -*- coding: utf-8 -*-
"""R2 A 臂分析:按设计书第三节(写于标签产生之前,sha256 见 R2_blind\\R2_design_sha256.txt)。

1 头条:盲标签重估 python 剂量反应——对数计数 OLS(月固定效应、按月聚类)、固定总量 FE-PPML、
  s4/s1 对数比 Newey-West(L=6),以及二元 GEN/VER 规格。估计量直接取包内 phaseA_composition.py 的函数。
  自证:同一套函数在原标签面板上必须复现稿件的 γ = −0.416,否则退出不出数。
2 一致性:盲标签对人工共识(二元,N=300)、对原主分类器、对 GLM-4.6 的二元 κ。
3 量表使用:s0 题数与占比;若 >2%,加报「s0 并入 s1」敏感性。
输出 工作文档\\R2_analyze_result.json
"""
import csv, importlib.util, io, json, os, sys
import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
PKG = r"E:\智能体论文\P9b_OSF_复现包_20260920"
DATA = os.path.join(PKG, "01_panels_and_classification", "data")
B = os.path.join(HERE, "R2_blind")
GS = os.path.join(PKG, "03_validation", "gold_standard")

spec = importlib.util.spec_from_file_location("pa", os.path.join(PKG, "02_estimation", "phaseA_composition.py"))
src = io.open(spec.origin, encoding="utf-8").read()
cut = src.find('print("=" * 74)')          # 只取函数定义,不跑脚本主体
ns = {}
exec(compile(src[:cut], spec.origin, "exec"), ns)
EVENT, ym_int, ols_dose, ppml_dose, logratio_nw = ns["EVENT"], ns["ym_int"], ns["ols_dose"], ns["ppml_dose"], ns["logratio_nw"]


def long_panel(w):
    recs = []
    for _, r in w.iterrows():
        t = ym_int(r["ym"])
        for b in (1, 2, 3, 4):
            recs.append({"ym": r["ym"], "t": t, "score": b, "count": int(r["s%d" % b]), "post": int(t >= EVENT)})
    d = pd.DataFrame(recs); d["dose"] = d["score"] * d["post"]
    return d


def binary(w):
    recs = []
    for _, r in w.iterrows():
        t = ym_int(r["ym"])
        for g, c in ((1, r["GEN"]), (0, r["VER"])):
            recs.append({"ym": r["ym"], "gen": g, "count": int(c), "post": int(t >= EVENT)})
    d = pd.DataFrame(recs); d["gp"] = d["gen"] * d["post"]; d["y"] = np.log(d["count"].clip(lower=1))
    mo = pd.get_dummies(d["ym"], prefix="m", drop_first=True).astype(float)
    X = sm.add_constant(pd.concat([d[["gp", "gen"]].astype(float), mo], axis=1))
    r = sm.OLS(d["y"].to_numpy(), X.to_numpy()).fit(cov_type="cluster", cov_kwds={"groups": d["ym"].to_numpy()})
    i = list(X.columns).index("gp")
    return r.params[i], r.bse[i], r.pvalues[i]


def fits(w):
    d = long_panel(w)
    o = ols_dose(d); p = ppml_dose(d); lr = logratio_nw(w); bn = binary(w)
    f = lambda t: dict(coef=round(float(t[0]), 4), se=round(float(t[1]), 4), p=float(t[2]),
                       ci=[round(float(t[0] - 1.96 * t[1]), 4), round(float(t[0] + 1.96 * t[1]), 4)])
    zero = int((d["count"] == 0).sum())
    return dict(ols=f(o), ppml=f(p), logratio_nw=f(lr), binary=f(bn), zero_cells=zero)


# ---------------------------------------------------------------- 自证:原标签复现 −0.416
w0 = pd.read_csv(os.path.join(DATA, "within_so_llm_panel_python.csv"))
F0 = fits(w0)
assert round(F0["ols"]["coef"], 3) == -0.416, F0["ols"]
print("自证通过:原标签 OLS γ = %+.4f" % F0["ols"]["coef"])

# ---------------------------------------------------------------- 1 头条
w1 = pd.read_csv(os.path.join(B, "within_so_llm_panel_python_blind.csv"))
assert len(w1) == 60 and (w1["n"] == 100).all()
F1 = fits(w1)
R = dict(original=F0, blind=F1)
tot = w1[["s%d" % i for i in range(5)]].sum()
R["blind_bin_counts"] = {k: int(v) for k, v in tot.items()}
s0share = float(tot["s0"] / tot.sum())
R["blind_s0_share"] = round(s0share, 4)
if s0share > 0.02:
    w2 = w1.copy(); w2["s1"] = w2["s1"] + w2["s0"]; w2["s0"] = 0
    R["blind_s0_folded_into_s1"] = fits(w2)
pre, post = w1[w1.ym.map(ym_int) < EVENT], w1[w1.ym.map(ym_int) >= EVENT]
ms = lambda x: float(sum(x["s%d" % b].sum() * b for b in range(5)) / x[["s%d" % b for b in range(5)]].sum().sum())
R["blind_mean_score"] = dict(pre=round(ms(pre), 3), post=round(ms(post), 3))
R["original_mean_score"] = dict(pre=round(ms(w0[w0.ym.map(ym_int) < EVENT]), 3), post=round(ms(w0[w0.ym.map(ym_int) >= EVENT]), 3))

# ---------------------------------------------------------------- 2 一致性
def kbin(a, b):
    a, b = np.asarray(a) >= 3, np.asarray(b) >= 3
    po = (a == b).mean(); pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    return round(float((po - pe) / (1 - pe)), 4), round(float(po), 4), int(len(a))

bl = {int(r["question_id"]): int(r["score"]) for r in csv.DictReader(io.open(os.path.join(B, "question_labels_python_blind.csv"), encoding="utf-8"))}
orig = {}
for fn in ("question_labels_python_2021-2024.csv", "question_labels_python_ext_2024-07_2026-05.csv"):
    orig.update({int(r["question_id"]): int(r["score"]) for r in csv.DictReader(io.open(os.path.join(DATA, fn), encoding="utf-8"))})
glm = {}
for line in io.open(os.path.join(PKG, "05_additional_checks", "glm_relabel", "labels_glm-4.6.jsonl"), encoding="utf-8"):
    r = json.loads(line); glm[int(r["question_id"])] = int(r["score"])
# 人工共识(二元):两人同侧取同侧,异侧取裁决共识
A = {int(r["order"]): int(r["score_0_4"]) for r in csv.DictReader(io.open(os.path.join(GS, "coding_sheet_A_v2.csv"), encoding="utf-8-sig"))}
Bc = {int(r["order"]): int(r["score_0_4"]) for r in csv.DictReader(io.open(os.path.join(GS, "coding_sheet_B_v2.csv"), encoding="utf-8-sig"))}
adj = {int(r["order"]): int(r["consensus_0_4"]) for r in csv.DictReader(io.open(os.path.join(GS, "裁决记录表.csv"), encoding="utf-8-sig"))}
q_of = {s["order_v2"]: int(s["question_id"]) for s in json.load(io.open(os.path.join(GS, "gold_sample_v2_order.json"), encoding="utf-8"))}
cons = {}
for o in range(1, 301):
    cons[q_of[o]] = int(A[o] >= 3) * 3 if (A[o] >= 3) == (Bc[o] >= 3) else (3 if adj[o] >= 3 else 0)
# 自证:原标签对共识的 κ 必须复现稿件 0.512
ks = sorted(cons)
k_orig = kbin([orig[q] for q in ks], [cons[q] for q in ks])
assert round(k_orig[0], 3) == 0.512, k_orig
R["kappa"] = dict(
    original_vs_consensus=k_orig,
    blind_vs_consensus=kbin([bl[q] for q in ks], [cons[q] for q in ks]),
    blind_vs_original=kbin([bl[q] for q in sorted(bl)], [orig[q] for q in sorted(bl)]),
    blind_vs_glm46=kbin([bl[q] for q in sorted(glm)], [glm[q] for q in sorted(glm)]),
    original_vs_glm46=kbin([orig[q] for q in sorted(glm)], [glm[q] for q in sorted(glm)]))

io.open(os.path.join(HERE, "R2_analyze_result.json"), "w", encoding="utf-8").write(json.dumps(R, indent=1, ensure_ascii=False))
for k in ("ols", "ppml", "logratio_nw", "binary"):
    print("%-12s 原 %+.4f (SE %.4f)   盲 %+.4f (SE %.4f, p=%.3g, CI [%+.3f, %+.3f])"
          % (k, F0[k]["coef"], F0[k]["se"], F1[k]["coef"], F1[k]["se"], F1[k]["p"], *F1[k]["ci"]))
print("盲标签零格 %d;s0 占比 %.2f%%;均分 前 %.3f 后 %.3f(原 %.3f → %.3f)"
      % (F1["zero_cells"], 100 * s0share, R["blind_mean_score"]["pre"], R["blind_mean_score"]["post"],
         R["original_mean_score"]["pre"], R["original_mean_score"]["post"]))
print("κ:", R["kappa"])
