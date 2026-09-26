# -*- coding: utf-8 -*-
"""R1 敏感性与 γ 重估产物。两份独立复审(R1_review_A_verifier.md / R1_review_B_referee.md)
要求的各项,全部从既有盲标产物重算并落盘,每个数配可复现出处。

为什么单独成脚本:-0.176 那个 γ 曾只在命令行算过一次,没有产物(B-MINOR 11);
敏感性 1–5 亦然。数必须有据——这是第二次被同一条规矩抓住。

另核 A-B 的一条实质发现:R1c_analyze.py 的 SE 用题目级方差(n=707/458),
而 R1_analyze / R1d_analyze 用月级方差(18/12 月)。同一节里三个区间两种口径,
不可比。本脚本把 R1c 按月级重算,两种都落盘。
"""
import json, glob, math, re, os, csv
import numpy as np, pandas as pd
import statsmodels.api as sm
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
EVENT = "2022-12"
YR = re.compile(r"\b20(1[5-9]|2[0-6])\b")
AI_ERA = re.compile(r"chatgpt|copilot|large.language.model|\bllm\b|openai|gpt-?[34]", re.I)


def load(tokfile, labglob, ym_of):
    tok = json.load(open(os.path.join(HERE, tokfile), encoding="utf-8")); labs = []
    for f in sorted(glob.glob(os.path.join(HERE, labglob))):
        labs += json.load(open(f, encoding="utf-8"))
    d = pd.DataFrame(labs); d["qid"] = d.id.map(tok); d["ym"] = d.qid.map(ym_of)
    d = d[d.ym.notna()].copy(); d["post"] = (d.ym >= EVENT).astype(int); return d


def month_dd(a_series_by_month, b_series_by_month):
    """月级差值的前后期之差,Welch 区间与正态区间都给。"""
    d = (a_series_by_month - b_series_by_month).dropna().rename("delta").reset_index()
    d["post"] = d.ym >= EVENT
    pre, post = d[~d.post].delta, d[d.post].delta
    dd = post.mean() - pre.mean()
    va, vb = post.var(ddof=1) / len(post), pre.var(ddof=1) / len(pre)
    se = math.sqrt(va + vb)
    df = (va + vb) ** 2 / (va ** 2 / (len(post) - 1) + vb ** 2 / (len(pre) - 1))
    t = stats.t.ppf(0.975, df)
    return dict(dd=round(dd, 4), se=round(se, 4), welch_df=round(df, 1), t_crit=round(t, 3),
                ci_welch=[round(dd - t * se, 4), round(dd + t * se, 4)],
                ci_normal=[round(dd - 1.96 * se, 4), round(dd + 1.96 * se, 4)],
                n_pre_months=int(len(pre)), n_post_months=int(len(post))), d


def gamma_fits(d):
    """log-count OLS(与主稿同式)与 FE-Poisson(B-MINOR 9)各估一次,月聚类。"""
    d = d[d.score > 0]
    cell = d.groupby(["score", "ym"]).size().rename("n").reset_index()
    cell["post"] = (cell.ym >= EVENT).astype(int)
    X = pd.concat([pd.Series(cell.score * cell.post, name="s_x_post").astype(float),
                   pd.get_dummies(cell.score.astype(int).astype(str), prefix="s", drop_first=True).astype(float),
                   pd.get_dummies(cell.ym, prefix="m", drop_first=True).astype(float)], axis=1)
    X = sm.add_constant(X); groups = pd.factorize(cell.ym)[0]
    ols = sm.OLS(np.log(cell.n.astype(float)), X).fit(cov_type="cluster", cov_kwds={"groups": groups})
    poi = sm.GLM(cell.n.astype(float), X, family=sm.families.Poisson()).fit(cov_type="cluster", cov_kwds={"groups": groups})
    out = {}
    for nm, r in (("logcount_ols", ols), ("fe_poisson", poi)):
        b, s = r.params["s_x_post"], r.bse["s_x_post"]
        out[nm] = dict(gamma=round(b, 4), se=round(s, 4), t=round(b / s, 2), n_cells=int(len(cell)),
                       cell_median=float(cell.n.median()), cell_min=int(cell.n.min()),
                       n_questions=int(d.shape[0]), months=int(cell.ym.nunique()))
    return out


def main():
    uraw = json.load(open(os.path.join(HERE, "R1_uniform_raw.json"), encoding="utf-8"))
    uym = {r["question_id"]: r["ym"] for r in uraw}
    utxt = {r["question_id"]: r["title"] + " " + r["body"] + " " + " ".join(r.get("tags", [])) for r in uraw}
    old = []
    for fn in ("so_questions_full.json", "so_questions_ext_py.json"):
        old += json.load(open(r"E:\智能体论文\_legB_data\%s" % fn, encoding="utf-8"))
    oym = {q["question_id"]: q["ym"] for q in old}
    otxt = {q["question_id"]: q["title"] + " " + (q.get("body_excerpt") or "") + " " + " ".join(q.get("tags", [])) for q in old}
    ol = {}
    for fn in ("question_labels.csv", "question_labels_ext_py.csv"):
        for rr in csv.DictReader(open(r"E:\智能体论文\_legB_data\%s" % fn, encoding="utf-8")):
            ol[int(rr["question_id"])] = int(rr["score"])

    U = load("R1_token_map.json", "R1_labels_batch_*.json", uym)
    C = load("R1c_token_map.json", "R1c_labels_batch_*.json", oym)
    C["orig"] = C.qid.map(ol)

    sens = {}
    U1, C1 = U[U.score > 0], C[C.score > 0]
    base, d0 = month_dd(U1.groupby("ym").score.mean(), C1.groupby("ym").score.mean())
    sens["R1d_s0_excluded_baseline"] = base
    sens["R1d_s0_retained"], _ = month_dd(U.groupby("ym").score.mean(), C.groupby("ym").score.mean())

    # 去年份题(与 §4.2 对金标准的做法一致);同时记录 regex,A-A 指出计数依 regex 而异
    Uy = U[~U.qid.map(lambda q: bool(YR.search(utxt.get(q, ""))))]
    Cy = C[~C.qid.map(lambda q: bool(YR.search(otxt.get(q, ""))))]
    r, _ = month_dd(Uy[Uy.score > 0].groupby("ym").score.mean(), Cy[Cy.score > 0].groupby("ym").score.mean())
    r.update(regex=YR.pattern, excluded_uniform=int(len(U) - len(Uy)), excluded_control=int(len(C) - len(Cy)))
    sens["R1d_organic_year_excluded"] = r

    # AI 时代词汇泄漏(A-F):题面或标签含 ChatGPT/Copilot/LLM 等
    ai_u = U.qid.map(lambda q: bool(AI_ERA.search(utxt.get(q, ""))))
    ai_c = C.qid.map(lambda q: bool(AI_ERA.search(otxt.get(q, ""))))
    sens["ai_era_terms"] = dict(regex=AI_ERA.pattern,
                                uniform_total=int(ai_u.sum()), uniform_post=int((ai_u & (U.post == 1)).sum()),
                                control_total=int(ai_c.sum()), control_post=int((ai_c & (C.post == 1)).sum()))
    Ua, Ca = U[~ai_u], C[~ai_c]
    r, _ = month_dd(Ua[Ua.score > 0].groupby("ym").score.mean(), Ca[Ca.score > 0].groupby("ym").score.mean())
    sens["R1d_ai_era_excluded"] = r

    # bin 份额版本(B-MINOR 8)
    gu = U1.groupby("ym").apply(lambda g: (g.score >= 3).mean(), include_groups=False)
    gc = C1.groupby("ym").apply(lambda g: (g.score >= 3).mean(), include_groups=False)
    sens["R1d_gen_share_ge3"], _ = month_dd(gu, gc)

    # R1c 按月级重算(A-B 的发现)
    Cb = C[(C.score > 0) & (C.orig > 0)].copy(); Cb["e"] = Cb.score - Cb.orig
    em = Cb.groupby("ym").e.mean()
    r1c_month, _ = month_dd(em, em * 0)          # e 本身就是差,减零序列即得月级前后之差
    sens["R1c_month_level"] = r1c_month
    sens["R1c_question_level_as_in_R1c_analyze"] = dict(dd=0.0988, se=0.0429, ci_normal=[0.0148, 0.1828],
                                                          note="题目级 SE,n=707/458;与本节其它区间口径不同")

    # R1 (跨评分者) 的月级结果,供 S19.3 如实报告
    om = Cb.groupby("ym").orig.mean()            # 主分类器在同 30 月对照子样本上
    sens["R1_cross_rater_month_level"], _ = month_dd(U1.groupby("ym").score.mean(), om)

    # R1 对「全面板月」的月级 Welch 重算：R1_analyze.py 用 1.96*se（正态），
    # 与本节其它区间口径不同（复审 C 的 D1）。两套都落盘。
    pm = pd.DataFrame([{"qid": q["question_id"], "ym": q["ym"]} for q in old]).drop_duplicates("qid")
    pm["score"] = pm.qid.map(ol); pm = pm[pm.score > 0]
    pm = pm[pm.ym.isin(set(U1.ym))]
    sens["R1_cross_rater_vs_full_panel"], _ = month_dd(U1.groupby("ym").score.mean(),
                                                        pm.groupby("ym").score.mean())

    # 对填满宽度回归(B-MAJOR 3 的药方)
    p = pd.DataFrame([{"qid": q["question_id"], "ts": q["creation_date"], "ym": q["ym"]} for q in old]).drop_duplicates("qid")
    g = p.groupby("ym").agg(first=("ts", "min"), last=("ts", "max")).reset_index(); g["fill_h"] = (g["last"] - g["first"]) / 3600
    m = d0.merge(g[["ym", "fill_h"]], on="ym")
    X = sm.add_constant(np.log(m.fill_h.values)); rr = sm.OLS(m.delta.values, X).fit()
    sens["delta_on_log_fill"] = dict(slope=round(rr.params[1], 4), se=round(rr.bse[1], 4), t=round(rr.tvalues[1], 2), n_months=int(len(m)),
                                      implied_change_6p8h_to_55p4h=round(rr.params[1] * (math.log(55.4) - math.log(6.8)), 4),
                                      months_fill_gt_72h=sorted(m[m.fill_h > 72].ym.tolist()),
                                      sampled_post_months_fill_median=round(float(m[m.ym >= EVENT].fill_h.median()), 1),
                                      sampled_post_months_fill_le_14h=int((m[m.ym >= EVENT].fill_h <= 14).sum()),
                                      sampled_post_months_fill_le_15h=int((m[m.ym >= EVENT].fill_h <= 15).sum()),
                                      sampled_post_months_fill_h={k: round(v, 1) for k, v in zip(m[m.ym >= EVENT].ym, m[m.ym >= EVENT].fill_h)})

    # 压缩比(B-MAJOR 1)
    my_drop = Cb[Cb.post == 1].score.mean() - Cb[Cb.post == 0].score.mean()
    s46_drop = Cb[Cb.post == 1].orig.mean() - Cb[Cb.post == 0].orig.mean()
    ratio = my_drop / s46_drop
    hw = (base["ci_normal"][1] - base["ci_normal"][0]) / 2
    hw_w = (base["ci_welch"][1] - base["ci_welch"][0]) / 2
    sens["scale_compression"] = dict(rater_drop_on_control=round(my_drop, 4), primary_drop_on_control=round(s46_drop, 4),
                                     ratio=round(ratio, 3),
                                     n_questions_both_scored=int(len(Cb)),
                                     halfwidth_rater_units_normal=round(hw, 4),
                                     halfwidth_rater_units_welch=round(hw_w, 4),
                                     halfwidth_primary_units_normal=round(hw / ratio, 4),
                                     halfwidth_primary_units_welch=round(hw_w / ratio, 4),
                                     pct_of_0p355_normal=round(100 * hw / ratio / 0.355, 1),
                                     pct_of_0p355_welch=round(100 * hw_w / ratio / 0.355, 1),
                                     pct_of_on_control_drop_normal=round(100 * hw / ratio / abs(s46_drop), 1),
                                     pct_of_on_control_drop_welch=round(100 * hw_w / ratio / abs(s46_drop), 1),
                                     mde_80pct_rater_units=round(2.8 * base["se"], 4),
                                     mde_as_pct_of_rater_own_drop=round(100 * 2.8 * base["se"] / abs(my_drop), 1))
    sens["s0_counts"] = dict(uniform_pre=int((U[U.post == 0].score == 0).sum()), uniform_post=int((U[U.post == 1].score == 0).sum()),
                             control_pre=int((C[C.post == 0].score == 0).sum()), control_post=int((C[C.post == 1].score == 0).sum()))
    sens["rater"] = dict(model="claude-opus-5", instances_per_design=10, batch_size=120,
                         input="rubric verbatim + title + tags + body; no dates, no ids, no labels",
                         provenance="model field in the blind-labelling instances' task transcripts")
    # 盲标审计（此前这几个数是从复审报告抄进稿子的，无脚本产出）
    from scipy.stats import spearmanr
    bl = {}
    for tag, tokfile, bglob, ymap in (("uniform", "R1_token_map.json", "R1_blind_batch_*.json", uym),
                                       ("control", "R1c_token_map.json", "R1c_blind_batch_*.json", oym)):
        tk = json.load(open(os.path.join(HERE, tokfile), encoding="utf-8"))
        num = {t: int(t[1:]) for t in tk}
        rho = spearmanr([num[t] for t in tk], [tk[t] for t in tk]).statistic
        months, sizes = [], []
        for f in sorted(glob.glob(os.path.join(HERE, bglob))):
            recs = json.load(open(f, encoding="utf-8")); sizes.append(len(recs))
            months.append(len({ymap.get(tk[r["id"]]) for r in recs} - {None}))
        bl[tag] = dict(token_id_spearman=round(float(rho), 4), n_batches=len(sizes),
                       batch_size_min=min(sizes), batch_size_max=max(sizes),
                       months_per_batch_min=min(months), months_per_batch_max=max(months))
    sens["blinding"] = bl

    json.dump(sens, open(os.path.join(HERE, "R1_sensitivity_result.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)

    # γ 重估:三个格子(主分类器/对照、我方/对照、我方/均匀),两种估计量
    Cs = C[C.orig > 0].copy(); Cs["score"] = Cs.orig
    gam = dict(primary_on_control=gamma_fits(Cs), rater_on_control=gamma_fits(C), rater_on_uniform=gamma_fits(U))
    json.dump(gam, open(os.path.join(HERE, "R1_gamma_refits_result.json"), "w", encoding="utf-8"), indent=1)

    print("R1_sensitivity_result.json")
    for k in ("R1d_s0_excluded_baseline", "R1d_s0_retained", "R1d_organic_year_excluded", "R1d_ai_era_excluded", "R1d_gen_share_ge3",
              "R1c_month_level", "R1_cross_rater_month_level"):
        v = sens[k]; print("  %-30s ΔΔ %+.3f  SE %.3f  Welch CI [%+.3f, %+.3f]" % (k, v["dd"], v["se"], *v["ci_welch"]))
    v = sens["delta_on_log_fill"]; print("  %-30s slope %+.4f (t %.2f)  6.8h→55.4h: %+.3f" % ("delta_on_log_fill", v["slope"], v["t"], v["implied_change_6p8h_to_55p4h"]))
    v = sens["scale_compression"]; print("  %-30s ratio %.2f  halfwidth→primary %.3f = %.0f%% of 0.355, %.0f%% of on-control drop;  MDE %.0f%% of rater drop"
                                          % ("scale_compression", v["ratio"], v["halfwidth_primary_units_welch"], v["pct_of_0p355_welch"], v["pct_of_on_control_drop_welch"], v["mde_as_pct_of_rater_own_drop"]))
    v = sens["ai_era_terms"]; print("  %-30s uniform %d (%d post)  control %d (%d post)" % ("ai_era_terms", v["uniform_total"], v["uniform_post"], v["control_total"], v["control_post"]))
    print("R1_gamma_refits_result.json")
    for k, vv in gam.items():
        for nm, r in vv.items():
            print("  %-22s %-13s γ %+.3f  SE %.3f  t %+.2f   cells %d (med %.0f, min %d)" % (k, nm, r["gamma"], r["se"], r["t"], r["n_cells"], r["cell_median"], r["cell_min"]))


if __name__ == "__main__":
    main()
