# -*- coding: utf-8 -*-
"""R2 C 阶段补充:同一批 320 道第三轮效标题,三套标签(盲标签 / 原主分类器 / GLM-4.6)各自预测答题的力度。

对照第二轮表 4 丁栏(那一轮只比了原主分类器与 GLM-4.6)。每个答题者:
  单预测量 logit answerable ~ label,报斜率、McFadden 伪 R²、Spearman;
  联合 logit answerable ~ blind + other,按题无需聚类(一题一答)。
另报按盲标签分层抽样的逆概率加权版本(样本每档 80 题,面板各档题数不同),因为分层变量本身是盲标签,
不加权会给盲标签多一点方差。输出 工作文档\\R2c_labelsets_result.json
"""
import glob, io, json, os, sys
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
PKG = r"E:\智能体论文\P9b_OSF_复现包_20260920"
CDIR = os.path.join(HERE, "R2_criterion")
S = pd.DataFrame(json.load(io.open(os.path.join(CDIR, "criterion_sample_v3.json"), encoding="utf-8")))
orig = pd.read_csv(os.path.join(PKG, "01_panels_and_classification", "data", "question_labels_python_2021-2024.csv"))
blind = pd.read_csv(os.path.join(HERE, "R2_blind", "question_labels_python_blind.csv"))
glm = {}
for line in io.open(os.path.join(PKG, "05_additional_checks", "glm_relabel", "labels_glm-4.6.jsonl"), encoding="utf-8"):
    r = json.loads(line); glm[int(r["question_id"])] = int(r["score"])
S["qid"] = S.qid.astype(int)
S = S.merge(blind[["question_id", "score"]].rename(columns={"question_id": "qid", "score": "blind"}), on="qid")
assert (S.blind == S.sub_score).all(), "效标样本的分档不是盲标签"
S = S.merge(orig[["question_id", "score"]].rename(columns={"question_id": "qid", "score": "orig"}), on="qid")
S["glm46lab"] = S.qid.map(glm)
assert len(S) == 320 and S[["blind", "orig", "glm46lab"]].notna().all().all()
panel_share = blind[blind.score >= 1].score.value_counts(normalize=True)
S["w"] = S.blind.map(lambda b: panel_share[b] / 0.25)

R = {"N": len(S), "label_means": {k: round(float(S[k].mean()), 5) for k in ("blind", "orig", "glm46lab")},
     "kappa_binary_blind_orig": None}
g = lambda x: (x >= 3).astype(int)
from sklearn.metrics import cohen_kappa_score as ck
R["kappa_binary_blind_orig"] = round(float(ck(g(S.blind), g(S.orig))), 6)
R["kappa_binary_blind_glm"] = round(float(ck(g(S.blind), g(S.glm46lab))), 6)
for tag in ("sonnet5", "haiku45", "glm46", "glm53"):
    fs = sorted(glob.glob(os.path.join(CDIR, "batches_" + tag, "judgment_out_*.json")))
    if len(fs) < 8:
        continue
    J = pd.DataFrame([r for f in fs for r in json.load(io.open(f, encoding="utf-8"))])
    J["qid"] = J.qid.astype(int)
    d = S.merge(J[["qid", "answerable"]], on="qid")
    out = {}
    for lab in ("blind", "orig", "glm46lab"):
        m = smf.logit("answerable ~ %s" % lab, d).fit(disp=0)
        mw = sm.GLM(d.answerable, sm.add_constant(d[[lab]]), family=sm.families.Binomial(), freq_weights=d.w).fit()
        r, p = stats.spearmanr(d[lab], d.answerable)
        out[lab] = dict(slope=[round(float(m.params[lab]), 6), round(float(m.bse[lab]), 6), float(m.pvalues[lab])],
                        pseudo_r2=round(float(m.prsquared), 6), spearman=[round(float(r), 6), float(p)],
                        weighted_slope=[round(float(mw.params[lab]), 6), round(float(mw.bse[lab]), 6)])
    for other in ("orig", "glm46lab"):
        m = smf.logit("answerable ~ blind + %s" % other, d).fit(disp=0)
        out["joint_blind_" + other] = {k: [round(float(m.params[k]), 6), float(m.pvalues[k])] for k in ("blind", other)}
    R[tag] = out
    print("\n== %s (N=%d) ==" % (tag, len(d)))
    for lab in ("blind", "orig", "glm46lab"):
        o = out[lab]
        print("  %-9s 斜率 %+.3f (SE %.3f, p=%.3g)  伪R² %.4f  ρ %+.3f  加权斜率 %+.3f" % (
            lab, *o["slope"], o["pseudo_r2"], o["spearman"][0], o["weighted_slope"][0]))
    for other in ("orig", "glm46lab"):
        j = out["joint_blind_" + other]
        print("  联合 blind %+.3f (p=%.3g) | %s %+.3f (p=%.3g)" % (*j["blind"], other, *j[other]))
_tags = [t for t in ("sonnet5", "haiku45", "glm46", "glm53") if t in R]
R["mean_pseudo_r2"] = {lab: round(float(np.mean([R[t][lab]["pseudo_r2"] for t in _tags])), 6) for lab in ("blind", "orig", "glm46lab")}
R["best_label_set_by_answerer"] = {t: max(("blind", "orig", "glm46lab"), key=lambda lab: R[t][lab]["pseudo_r2"]) for t in _tags}
print("\n平均伪 R²(%d 个答题者):" % len(_tags), R["mean_pseudo_r2"], " 各答题者最佳:", R["best_label_set_by_answerer"])
print("\n三套标签均值:", R["label_means"], " 二元 κ 盲-原 %.3f 盲-GLM %.3f" % (R["kappa_binary_blind_orig"], R["kappa_binary_blind_glm"]))
io.open(os.path.join(HERE, "R2c_labelsets_result.json"), "w", encoding="utf-8").write(json.dumps(R, indent=1, ensure_ascii=False))
