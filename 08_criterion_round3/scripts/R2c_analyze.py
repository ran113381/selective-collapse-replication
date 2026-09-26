# -*- coding: utf-8 -*-
"""R2 C 阶段:第三轮效标检验分析(口径照第二轮 weak_tier_analysis.py,分档依据为 A 臂盲标签)。

每个答题者:各档解出率与充分度、Spearman(分值, 解出) 与 (分值, 充分度)、GEN 对 VER 与 s4 对 s1 的
Fisher、每分 logit 优势比、强参考子集(accepted/top_voted)与无参考子集。
合并:四个答题者一起的 logit(answerable ~ s + 答题者固定效应),按题聚类。
新增(本轮样本才有):事件前 / 事件后分开报 Spearman 与 logit 斜率。
可在只有部分答题者评完时运行,缺的跳过。输出 工作文档\\R2c_result.json
"""
import glob, io, json, os, sys
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
CDIR = os.path.join(HERE, "R2_criterion")
EV = 2022 * 12 + 11
S = pd.DataFrame(json.load(io.open(os.path.join(CDIR, "criterion_sample_v3.json"), encoding="utf-8")))
S["post"] = S.ym.map(lambda y: int(int(y[:4]) * 12 + int(y[5:7]) - 1 >= EV))
TIERS = {"sonnet5": "Claude Sonnet 5", "haiku45": "Claude Haiku 4.5", "glm53": "GLM-5.3", "glm46": "GLM-4.6"}


def load(tag):
    fs = sorted(glob.glob(os.path.join(CDIR, "batches_" + tag, "judgment_out_*.json")))
    if len(fs) < 8:
        return None
    J = pd.DataFrame([r for f in fs for r in json.load(io.open(f, encoding="utf-8"))])
    J["qid"] = J.qid.astype(int)
    assert J.qid.is_unique, tag + " 评判有重复题号"
    return S.rename(columns={"sub_score": "s"}).merge(J[["qid", "answerable", "adequacy"]], on="qid")


def metrics(d):
    out = dict(N=int(len(d)))
    out["solve_by_bin"] = {"s%d" % b: round(float(d[d.s == b].answerable.mean()), 6) for b in (1, 2, 3, 4)}
    out["adequacy_by_bin"] = {"s%d" % b: round(float(d[d.s == b].adequacy.mean()), 5) for b in (1, 2, 3, 4)}
    out["n_by_bin"] = {"s%d" % b: int((d.s == b).sum()) for b in (1, 2, 3, 4)}
    r, p = stats.spearmanr(d.s, d.answerable); out["spearman_solved"] = [round(float(r), 6), float(p)]
    r, p = stats.spearmanr(d.s, d.adequacy); out["spearman_adequacy"] = [round(float(r), 6), float(p)]
    g, v = d[d.s >= 3].answerable, d[d.s <= 2].answerable
    _, fp = stats.fisher_exact([[g.sum(), len(g) - g.sum()], [v.sum(), len(v) - v.sum()]])
    out["gen_vs_ver"] = dict(gen=round(float(g.mean()), 6), ver=round(float(v.mean()), 6), fisher_p=float(fp))
    a, b = d[d.s == 4].answerable, d[d.s == 1].answerable
    _, fp = stats.fisher_exact([[a.sum(), len(a) - a.sum()], [b.sum(), len(b) - b.sum()]])
    out["s4_vs_s1"] = dict(s4=round(float(a.mean()), 6), s1=round(float(b.mean()), 6), fisher_p=float(fp))
    m = smf.logit("answerable ~ s", d).fit(disp=0)
    out["logit_slope"] = [round(float(m.params["s"]), 6), round(float(m.bse["s"]), 6), float(m.pvalues["s"])]
    st = d[d.reference_quality.isin(["accepted", "top_voted"])]
    r, p = stats.spearmanr(st.s, st.answerable); out["strong_ref"] = dict(N=int(len(st)), spearman=[round(float(r), 6), float(p)])
    no = d[d.reference_quality == "none"]
    r, p = stats.spearmanr(no.s, no.answerable); out["no_ref"] = dict(N=int(len(no)), spearman=[round(float(r), 6), float(p)])
    for lab, sub in (("pre", d[d.post == 0]), ("post", d[d.post == 1])):
        r, p = stats.spearmanr(sub.s, sub.answerable)
        mm = smf.logit("answerable ~ s", sub).fit(disp=0)
        out["period_" + lab] = dict(N=int(len(sub)), spearman=[round(float(r), 6), float(p)],
                                    logit_slope=[round(float(mm.params["s"]), 6), round(float(mm.bse["s"]), 6), float(mm.pvalues["s"])])
    return out


R, frames = {}, []
for tag, name in TIERS.items():
    d = load(tag)
    if d is None:
        print("[%s] 评判未齐,跳过" % name); continue
    R[tag] = metrics(d)
    d = d.assign(tier=tag); frames.append(d)
    m = R[tag]
    print("\n== %s (N=%d) ==" % (name, m["N"]))
    print("  解出率 s1..s4: %s" % " / ".join("%.3f" % m["solve_by_bin"]["s%d" % b] for b in (1, 2, 3, 4)))
    print("  Spearman(分,解出) ρ=%+.3f p=%.2e;  logit 斜率 %+.3f (SE %.3f)" % (*m["spearman_solved"], *m["logit_slope"][:2]))
    print("  事件前 N=%d ρ=%+.3f p=%.3f;  事件后 N=%d ρ=%+.3f p=%.2e" % (
        m["period_pre"]["N"], *m["period_pre"]["spearman"], m["period_post"]["N"], *m["period_post"]["spearman"]))
if len(frames) >= 2:
    P = pd.concat(frames, ignore_index=True)
    m = smf.logit("answerable ~ s + C(tier)", P).fit(disp=0, cov_type="cluster", cov_kwds={"groups": P.qid})
    R["pooled"] = dict(tiers=[f.tier.iloc[0] for f in frames], N=int(len(P)),
                       slope=[round(float(m.params["s"]), 6), round(float(m.bse["s"]), 6), float(m.pvalues["s"])])
    for lab, sub in (("pre", P[P.post == 0]), ("post", P[P.post == 1])):
        mm = smf.logit("answerable ~ s + C(tier)", sub).fit(disp=0, cov_type="cluster", cov_kwds={"groups": sub.qid})
        R["pooled"]["period_" + lab] = [round(float(mm.params["s"]), 6), round(float(mm.bse["s"]), 6), float(mm.pvalues["s"])]
    print("\n合并 logit(%d 个答题者,N=%d,按题聚类):斜率 %+.3f (SE %.3f, p=%.2e);事件前 %+.3f (p=%.3f),事件后 %+.3f (p=%.2e)" % (
        len(frames), len(P), *R["pooled"]["slope"], R["pooled"]["period_pre"][0], R["pooled"]["period_pre"][2],
        R["pooled"]["period_post"][0], R["pooled"]["period_post"][2]))
    # 与第二轮表 4 乙栏同一规格(check_pooled_logit.py):共同子样本上
    # y ~ s + C(family) + C(cap) + s:C(family) + s:C(cap),按题聚类
    FAM = {"sonnet5": ("claude", "strong"), "haiku45": ("claude", "weak"), "glm53": ("glm", "strong"), "glm46": ("glm", "weak")}
    tags = [f.tier.iloc[0] for f in frames]
    common = set.intersection(*[set(f.qid) for f in frames])
    Q = P[P.qid.isin(common)].copy()
    Q["family"] = Q.tier.map(lambda t: FAM[t][0]); Q["cap"] = Q.tier.map(lambda t: FAM[t][1])
    R["pooled_round2_spec"] = dict(tiers=tags, common_N=len(common))
    if Q.family.nunique() > 1 and Q.cap.nunique() > 1:
        m = smf.logit("answerable ~ s + C(family) + C(cap) + s:C(family) + s:C(cap)", Q).fit(
            disp=0, cov_type="cluster", cov_kwds={"groups": Q.qid})
        for k in ("s", "s:C(family)[T.glm]", "s:C(cap)[T.weak]"):
            R["pooled_round2_spec"][k] = [round(float(m.params[k]), 6), round(float(m.bse[k]), 6), float(m.pvalues[k])]
        print("第二轮同规格(共同子样本 N=%d,%s):s %+.3f (SE %.3f, p=%.2e);s×GLM %+.3f (p=%.3f);s×弱档 %+.3f (p=%.3f)" % (
            len(common), "+".join(tags), *R["pooled_round2_spec"]["s"], R["pooled_round2_spec"]["s:C(family)[T.glm]"][0],
            R["pooled_round2_spec"]["s:C(family)[T.glm]"][2], R["pooled_round2_spec"]["s:C(cap)[T.weak]"][0],
            R["pooled_round2_spec"]["s:C(cap)[T.weak]"][2]))
    W = Q.pivot(index="qid", columns="tier", values="answerable")
    R["agreement"] = {}
    for i in range(len(tags)):
        for j in range(i + 1, len(tags)):
            R["agreement"]["%s_vs_%s" % (tags[i], tags[j])] = round(float((W[tags[i]] == W[tags[j]]).mean()), 6)
    print("逐题一致率(共同子样本):", R["agreement"])
    R["common_subset"] = {t: {"s%d" % b: round(float(Q[(Q.tier == t) & (Q.s == b)].answerable.mean()), 6) for b in (1, 2, 3, 4)} for t in tags}
    # 共同子样本上每个答题者的秩相关、每分优势比、充分度(表 4 甲栏的口径:四者同题比较)
    R["common_subset_metrics"] = {}
    for t in tags:
        q = Q[Q.tier == t]
        r_, p_ = stats.spearmanr(q.s, q.answerable)
        mm = smf.logit("answerable ~ s", q).fit(disp=0)
        R["common_subset_metrics"][t] = dict(N=int(len(q)), spearman=[round(float(r_), 6), float(p_)],
                                             logit_slope=[round(float(mm.params["s"]), 6), round(float(mm.bse["s"]), 6), float(mm.pvalues["s"])],
                                             or_per_point=round(float(np.exp(mm.params["s"])), 5),
                                             overall=round(float(q.answerable.mean()), 6),
                                             adequacy_by_bin={"s%d" % b: round(float(q[q.s == b].adequacy.mean()), 5) for b in (1, 2, 3, 4)})
    print("共同子样本逐答题者:", {t: (v["spearman"][0], v["or_per_point"]) for t, v in R["common_subset_metrics"].items()})
    # 缺答的题(只可能出在脚本调用的答题者):逐档缺失率与卡方
    miss = {}
    for f in frames:
        t = f.tier.iloc[0]
        gone = S[~S.qid.isin(f.qid)]
        if len(gone):
            tab = [[int((gone.sub_score == b).sum()), int((f.s == b).sum())] for b in (1, 2, 3, 4)]
            chi = stats.chi2_contingency(tab)
            miss[t] = dict(n_missing=int(len(gone)), by_bin={"s%d" % b: tab[b - 1][0] for b in (1, 2, 3, 4)},
                           rate_by_bin={"s%d" % b: round(tab[b - 1][0] / 80, 6) for b in (1, 2, 3, 4)},
                           chi2=round(float(chi[0]), 5), p=float(chi[1]))
    R["missing_answers"] = miss
    print("缺答:", miss)
io.open(os.path.join(HERE, "R2c_result.json"), "w", encoding="utf-8").write(json.dumps(R, indent=1, ensure_ascii=False))
