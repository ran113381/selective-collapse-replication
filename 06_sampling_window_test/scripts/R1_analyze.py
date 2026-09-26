# -*- coding: utf-8 -*-
"""R1 分析：整月均匀抽样 vs 每月最早 100 题。判据在看数据之前写死。

问的问题不是「均匀样本的水平和原样本一样吗」——两者水平本就不必相同，
月内不同时段的提问人群不同。问的是 **差值随时间漂不漂**：

    Δ(m) = mean_uniform(m) − mean_first100(m)

γ 由前后期的**构成变化**识别。若 Δ(m) 在前后期之间不变，抽样规则只造成一个
被 bin 固定效应吸收掉的水平差，动不了 γ。若 Δ(m) 前后期不同，差多少就是污染多少。

判据（先写死）：
  R1-A  Δ 的前后期之差，若 |ΔΔ| 的 95% 区间含 0 → 抽样规则不驱动结果。
  R1-B  均匀样本自身的前后期替代率落差，应与原样本的 2.72→2.36（−0.36）同号；
        若同号且量级相当 → 头条在真随机样本上复现。
  R1-C  在均匀样本上重估剂量反应 γ，符号与显著性应与 −0.42 一致。
  R1-D  三条里任何一条不过，如实报，不改判据。
"""
import json, glob, os, math
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
EVENT = "2022-12"


def load():
    raw = pd.DataFrame(json.load(open(os.path.join(HERE, "R1_uniform_raw.json"), encoding="utf-8")))
    tokmap = json.load(open(os.path.join(HERE, "R1_token_map.json"), encoding="utf-8"))
    qid_of = {k: v for k, v in tokmap.items()}

    labs = []
    for f in sorted(glob.glob(os.path.join(HERE, "R1_labels_batch_*.json"))):
        labs += json.load(open(f, encoding="utf-8"))
    lab = pd.DataFrame(labs)
    assert lab.id.is_unique, "盲标结果里有重复 token"
    lab["question_id"] = lab.id.map(qid_of)
    assert lab.question_id.notna().all(), "有 token 回接不到真实 qid"

    new = raw.merge(lab[["question_id", "score", "label"]], on="question_id", how="inner")
    print("均匀样本回接成功 %d / %d 题" % (len(new), len(raw)))

    old_q = []
    for fn in ("so_questions_full.json", "so_questions_ext_py.json"):
        old_q += json.load(open(r"E:\智能体论文\_legB_data\%s" % fn, encoding="utf-8"))
    ol = {}
    import csv as _csv
    for fn in ("question_labels.csv", "question_labels_ext_py.csv"):
        for r in _csv.DictReader(open(r"E:\智能体论文\_legB_data\%s" % fn, encoding="utf-8")):
            ol[int(r["question_id"])] = int(r["score"])
    old = pd.DataFrame([{"question_id": q["question_id"], "ym": q["ym"],
                         "score": ol.get(q["question_id"])} for q in old_q])
    old = old.drop_duplicates("question_id")
    old = old[old.score.notna() & (old.score > 0)]      # 与主面板同口径：丢 s0
    return new, old


def main():
    new, old = load()
    new = new[new.score > 0]                            # 同口径
    months = sorted(set(new.ym) & set(old.ym))
    new = new[new.ym.isin(months)]; old = old[old.ym.isin(months)]
    print("对比月份 %d 个；均匀 n=%d，原样本 n=%d" % (len(months), len(new), len(old)))

    nm = new.groupby("ym").score.agg(["mean", "count", "std"]).rename(
        columns={"mean": "u_mean", "count": "u_n", "std": "u_sd"})
    om = old.groupby("ym").score.agg(["mean", "count", "std"]).rename(
        columns={"mean": "o_mean", "count": "o_n", "std": "o_sd"})
    d = nm.join(om).reset_index()
    d["post"] = (d.ym >= EVENT).astype(int)
    d["delta"] = d.u_mean - d.o_mean
    d["se_delta"] = np.sqrt(d.u_sd**2 / d.u_n + d.o_sd**2 / d.o_n)

    print("\n" + "=" * 70)
    print("每月：均匀样本均分 / 原样本均分 / 差值")
    print("=" * 70)
    for _, r in d.iterrows():
        print("  %s  post=%d   uniform %.3f (n=%3d)   first100 %.3f (n=%3d)   Δ %+.3f"
              % (r.ym, r.post, r.u_mean, r.u_n, r.o_mean, r.o_n, r.delta))

    pre, post = d[d.post == 0], d[d.post == 1]

    # ---- R1-A：Δ 有没有前后期漂移 ----
    dd = post.delta.mean() - pre.delta.mean()
    se = math.sqrt(post.delta.var(ddof=1) / len(post) + pre.delta.var(ddof=1) / len(pre))
    lo, hi = dd - 1.96 * se, dd + 1.96 * se
    print("\n" + "=" * 70)
    print("R1-A  抽样规则造成的偏倚是否随时间漂移")
    print("=" * 70)
    print("  前期 Δ = %+.3f   后期 Δ = %+.3f" % (pre.delta.mean(), post.delta.mean()))
    print("  ΔΔ（后−前）= %+.3f, SE %.3f, 95%% CI [%+.3f, %+.3f]" % (dd, se, lo, hi))
    a_pass = lo <= 0 <= hi
    print("  判据 R1-A：%s —— %s" % ("通过" if a_pass else "不通过",
          "区间含 0，抽样规则不驱动前后期落差" if a_pass else "区间不含 0，存在时变污染，需量化后写进稿"))

    # ---- R1-B：均匀样本自身的前后期落差 ----
    up, uo = new[new.ym >= EVENT].score, new[new.ym < EVENT].score
    op_, oo = old[old.ym >= EVENT].score, old[old.ym < EVENT].score
    du = up.mean() - uo.mean()
    do = op_.mean() - oo.mean()
    seu = math.sqrt(up.var(ddof=1)/len(up) + uo.var(ddof=1)/len(uo))
    print("\n" + "=" * 70)
    print("R1-B  头条落差在真随机样本上是否复现")
    print("=" * 70)
    print("  原样本   前 %.3f → 后 %.3f   落差 %+.3f" % (oo.mean(), op_.mean(), do))
    print("  均匀样本 前 %.3f → 后 %.3f   落差 %+.3f  (SE %.3f, 95%% CI [%+.3f, %+.3f])"
          % (uo.mean(), up.mean(), du, seu, du-1.96*seu, du+1.96*seu))
    b_pass = (du < 0) and (do < 0) and (du - 1.96*seu < 0)
    print("  判据 R1-B：%s" % ("通过——同号且显著" if b_pass else "不通过"))

    # ---- R1-C：在均匀样本上重估 γ ----
    print("\n" + "=" * 70)
    print("R1-C  在均匀样本上重估剂量反应 γ")
    print("=" * 70)
    cell = (new.groupby(["score", "ym"]).size().rename("n").reset_index())
    cell["post"] = (cell.ym >= EVENT).astype(int)
    cell = cell[cell.n > 0]
    X = pd.get_dummies(cell.score.astype(int).astype(str), prefix="s", drop_first=True)
    T = pd.get_dummies(cell.ym, prefix="m", drop_first=True)
    import numpy.linalg as la
    D = pd.concat([pd.Series(1.0, index=cell.index, name="const"),
                   pd.Series(cell.score * cell.post, name="s_x_post").astype(float),
                   X.astype(float), T.astype(float)], axis=1)
    y = np.log(cell.n.values.astype(float))
    Dm = D.values.astype(float)
    beta, *_ = la.lstsq(Dm, y, rcond=None)
    resid = y - Dm @ beta
    # 月聚类稳健
    XtX_inv = la.pinv(Dm.T @ Dm)
    meat = np.zeros((Dm.shape[1], Dm.shape[1]))
    for m in cell.ym.unique():
        idx = (cell.ym == m).values
        Xg, ug = Dm[idx], resid[idx]
        s = Xg.T @ ug
        meat += np.outer(s, s)
    G = cell.ym.nunique()
    V = XtX_inv @ meat @ XtX_inv * (G / (G - 1.0))
    j = list(D.columns).index("s_x_post")
    g_hat, g_se = beta[j], math.sqrt(V[j, j])
    t = g_hat / g_se
    print("  γ(均匀样本) = %+.3f  (SE %.3f, t = %.2f, %d 个月聚类)" % (g_hat, g_se, t, G))
    print("  主稿 γ(最早100) = −0.42")
    c_pass = (g_hat < 0) and (abs(t) > 1.96)
    print("  判据 R1-C：%s" % ("通过——同号且显著" if c_pass else "不通过（符号或显著性未复现）"))

    print("\n" + "=" * 70)
    print("总判：R1-A %s / R1-B %s / R1-C %s"
          % ("过" if a_pass else "不过", "过" if b_pass else "不过", "过" if c_pass else "不过"))
    print("=" * 70)

    d.to_csv(os.path.join(HERE, "R1_month_compare.csv"), index=False, encoding="utf-8-sig")
    json.dump({"delta_pre": float(pre.delta.mean()), "delta_post": float(post.delta.mean()),
               "dd": float(dd), "dd_se": float(se), "dd_ci": [float(lo), float(hi)],
               "uniform_prepost_drop": float(du), "orig_prepost_drop": float(do),
               "gamma_uniform": float(g_hat), "gamma_uniform_se": float(g_se),
               "n_uniform": int(len(new)), "n_orig": int(len(old)), "months": len(months),
               "R1_A": bool(a_pass), "R1_B": bool(b_pass), "R1_C": bool(c_pass)},
              open(os.path.join(HERE, "R1_result.json"), "w", encoding="utf-8"), indent=1)
    print("\n产物：R1_month_compare.csv  R1_result.json")


if __name__ == "__main__":
    main()
