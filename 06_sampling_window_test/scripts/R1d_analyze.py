# -*- coding: utf-8 -*-
"""R1d — 单一评分者、双抽样设计的最终检验。

R1c 揭出一个问题：即使窗口不变，我方盲标 vs Sonnet 4.6 的差值本身就随时间漂移
（+0.099，显著），R1 的总漂移（+0.199）统计上与这个纯评分者效应区分不开。这说明
跨分类器比较（R1 用我方 vs 用 Sonnet 4.6）洗不干净。

本检验把 Sonnet 4.6 整个移出画面。R1 和 R1c 都是**我方同一批盲标实例**打的分：
  R1   —— 我方评分，整月均匀抽样（30 月 × 40 题）
  R1c  —— 我方评分，原始「每月最早」窗口的子样本（同 30 月 × 40 题）
两边评分者完全相同，唯一变量是抽样规则。这是单一评分者、双抽样设计的组内比较，
干净地隔离窗口效应，不再依赖跨分类器差值。

判据（先写死）：
  R1d-A  Δ'(m) = 我方在均匀样本的月均分 − 我方在原窗口样本的月均分。
         Δ' 前后期之差的 95% 区间是否含 0。
         不含 0 → 月内窗口位置本身确实携带独立于评分者的信号，R1 的方向成立。
         含 0 → 窗口效应在单一评分者下测不出来，R1 的信号主要是跨分类器噪声。
"""
import json, glob, os, math
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
EVENT = "2022-12"


def my_scores(raw_file, token_file, label_glob):
    raw = pd.DataFrame(json.load(open(os.path.join(HERE, raw_file), encoding="utf-8")))
    tokmap = json.load(open(os.path.join(HERE, token_file), encoding="utf-8"))
    labs = []
    for f in sorted(glob.glob(os.path.join(HERE, label_glob))):
        labs += json.load(open(f, encoding="utf-8"))
    lab = pd.DataFrame(labs)
    assert lab.id.is_unique
    lab["question_id"] = lab.id.map(tokmap)
    assert lab.question_id.notna().all()
    d = raw.merge(lab[["question_id", "score"]], on="question_id", how="inner")
    return d


def main():
    uni = my_scores("R1_uniform_raw.json", "R1_token_map.json", "R1_labels_batch_*.json")
    orig = my_scores(
        json.dumps.__module__ and "R1c_uniform_raw_placeholder", "x", "x"
    ) if False else None
    # R1c 的原始抓取文件叫法不同：R1c 直接复用 _legB_data 的题，token_map 已含 qid 映射，
    # 不需要单独的 raw 文件——重建一个等价的 raw frame。
    tokmap = json.load(open(os.path.join(HERE, "R1c_token_map.json"), encoding="utf-8"))
    old_q = []
    for fn in ("so_questions_full.json", "so_questions_ext_py.json"):
        old_q += json.load(open(r"E:\智能体论文\_legB_data\%s" % fn, encoding="utf-8"))
    qmeta = {q["question_id"]: q["ym"] for q in old_q}
    labs = []
    for f in sorted(glob.glob(os.path.join(HERE, "R1c_labels_batch_*.json"))):
        labs += json.load(open(f, encoding="utf-8"))
    labc = pd.DataFrame(labs)
    assert labc.id.is_unique
    labc["question_id"] = labc.id.map(tokmap)
    labc["ym"] = labc.question_id.map(qmeta)
    orig = labc[labc.ym.notna()][["question_id", "ym", "score"]].copy()

    uni = uni[uni.score > 0][["question_id", "ym", "score"]].copy()
    orig = orig[orig.score > 0].copy()

    months = sorted(set(uni.ym) & set(orig.ym))
    uni = uni[uni.ym.isin(months)]; orig = orig[orig.ym.isin(months)]
    print("对比月份 %d 个；均匀样本 n=%d，原窗口样本 n=%d（均为我方盲标）"
          % (len(months), len(uni), len(orig)))

    um = uni.groupby("ym").score.agg(["mean", "count", "std"]).rename(
        columns={"mean": "u_mean", "count": "u_n", "std": "u_sd"})
    om = orig.groupby("ym").score.agg(["mean", "count", "std"]).rename(
        columns={"mean": "o_mean", "count": "o_n", "std": "o_sd"})
    d = um.join(om).reset_index()
    d["post"] = (d.ym >= EVENT).astype(int)
    d["delta"] = d.u_mean - d.o_mean

    print("\n" + "=" * 74)
    print("每月：我方在均匀样本 / 我方在原窗口样本，同一批评分者")
    print("=" * 74)
    for _, r in d.iterrows():
        print("  %s  post=%d  均匀 %.3f(n=%2d)  原窗口 %.3f(n=%2d)  Δ' %+.3f"
              % (r.ym, r.post, r.u_mean, r.u_n, r.o_mean, r.o_n, r.delta))

    pre, post = d[d.post == 0], d[d.post == 1]
    dd = post.delta.mean() - pre.delta.mean()
    se = math.sqrt(post.delta.var(ddof=1)/len(post) + pre.delta.var(ddof=1)/len(pre))
    lo, hi = dd - 1.96*se, dd + 1.96*se

    print("\n" + "=" * 74)
    print("R1d-A  单一评分者、双抽样设计：Δ' 是否前后期漂移")
    print("=" * 74)
    print("  前期 Δ' = %+.3f   后期 Δ' = %+.3f" % (pre.delta.mean(), post.delta.mean()))
    print("  ΔΔ'（后−前）= %+.3f, SE %.3f, 95%% CI [%+.3f, %+.3f]" % (dd, se, lo, hi))
    a_pass = lo <= 0 <= hi
    print("  判据 R1d-A：%s" % ("通过(区间含0)——窗口效应在单一评分者下测不出来" if a_pass
          else "不通过(区间不含0)——单一评分者下窗口效应依然显著，R1的信号是真的"))

    d.to_csv(os.path.join(HERE, "R1d_month_compare.csv"), index=False, encoding="utf-8-sig")
    json.dump({"delta_pre": float(pre.delta.mean()), "delta_post": float(post.delta.mean()),
               "dd": float(dd), "dd_se": float(se), "dd_ci": [float(lo), float(hi)],
               "R1d_A": bool(a_pass), "n_uniform": int(len(uni)), "n_orig": int(len(orig))},
              open(os.path.join(HERE, "R1d_result.json"), "w", encoding="utf-8"), indent=1)
    print("\n产物：R1d_month_compare.csv  R1d_result.json")


if __name__ == "__main__":
    main()
