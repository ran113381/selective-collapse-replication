# -*- coding: utf-8 -*-
"""Bin composition, not the mean, compared across the two sampling designs (S19.3).

gamma is identified from the relative sizes of the bins, not from the mean. A
sampling rule that pulled both tails toward the middle would leave the mean
unchanged and still move log(s4/s1). The earlier S19 comparisons tested only the
mean and the generative share, which are not the quantity gamma depends on.

This script repeats the design comparison, with the same raters on both designs, on:
  - log(s4/s1): the direct counterpart of the paper's headline contrast
  - each of the four bin shares
Criterion as in R1d: whether the Welch 95% interval of the difference covers zero.
"""
import io, json, glob, math, os
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
LEGB = r"E:\智能体论文\_legB_data"
EVENT = "2022-12"


def load(tokfile, labglob, ym_of):
    tok = json.load(open(os.path.join(HERE, tokfile), encoding="utf-8"))
    labs = []
    for f in sorted(glob.glob(os.path.join(HERE, labglob))):
        labs += json.load(open(f, encoding="utf-8"))
    d = pd.DataFrame(labs)
    d["qid"] = d.id.map(tok)
    d["ym"] = d.qid.map(ym_of)
    return d[d.ym.notna() & (d.score > 0)].copy()


def month_dd(a, b, label):
    """a、b 是按月的序列；返回两者之差的前后期变化与 Welch 区间。"""
    d = (a - b).dropna().rename("delta").reset_index()
    d["post"] = d.ym >= EVENT
    pre, post = d[~d.post].delta, d[d.post].delta
    dd = post.mean() - pre.mean()
    va, vb = post.var(ddof=1) / len(post), pre.var(ddof=1) / len(pre)
    se = math.sqrt(va + vb)
    df = (va + vb) ** 2 / (va ** 2 / (len(post) - 1) + vb ** 2 / (len(pre) - 1))
    t = stats.t.ppf(0.975, df)
    out = dict(dd=round(dd, 4), se=round(se, 4), welch_df=round(df, 1),
               ci_welch=[round(dd - t * se, 4), round(dd + t * se, 4)],
               n_pre_months=int(len(pre)), n_post_months=int(len(post)))
    out["covers_zero"] = bool(out["ci_welch"][0] <= 0 <= out["ci_welch"][1])
    print("  %-26s ΔΔ' %+.4f  SE %.4f  Welch CI [%+.4f, %+.4f]  含0=%s"
          % (label, out["dd"], out["se"], out["ci_welch"][0], out["ci_welch"][1], out["covers_zero"]))
    return out


def main():
    uraw = json.load(open(os.path.join(HERE, "R1_uniform_raw.json"), encoding="utf-8"))
    uym = {r["question_id"]: r["ym"] for r in uraw}
    old = []
    for fn in ("so_questions_full.json", "so_questions_ext_py.json"):
        old += json.load(open(os.path.join(LEGB, fn), encoding="utf-8"))
    oym = {q["question_id"]: q["ym"] for q in old}

    U = load("R1_token_map.json", "R1_labels_batch_*.json", uym)
    C = load("R1c_token_map.json", "R1c_labels_batch_*.json", oym)
    months = sorted(set(U.ym) & set(C.ym))
    U, C = U[U.ym.isin(months)], C[C.ym.isin(months)]
    print("同一批评分者，两套设计；%d 个月，均匀 n=%d，原窗口 n=%d\n" % (len(months), len(U), len(C)))

    res = {"note": "B-M8：设计间比较改用 bin 构成。同一批评分者，只变抽样规则。",
           "n_months": len(months), "n_uniform": int(len(U)), "n_control": int(len(C))}

    # ---- log(s4/s1)：头条对比的直接对应物 ----
    def logratio(d):
        g = d.groupby("ym").score
        s4 = g.apply(lambda x: (x == 4).sum())
        s1 = g.apply(lambda x: (x == 1).sum())
        # 月内某档为 0 时 log 不可用，按 Haldane 修正各加 0.5
        return (s4 + 0.5).apply(math.log) - (s1 + 0.5).apply(math.log)

    print("[1] log(s4/s1)，Haldane 修正 +0.5")
    res["log_s4_s1"] = month_dd(logratio(U), logratio(C), "log(s4/s1)")

    # ---- 四个 bin 各自的份额 ----
    print("\n[2] 各 bin 份额")
    res["bin_shares"] = {}
    for b in (1, 2, 3, 4):
        su = U.groupby("ym").score.apply(lambda x, b=b: (x == b).mean())
        scn = C.groupby("ym").score.apply(lambda x, b=b: (x == b).mean())
        res["bin_shares"]["s%d" % b] = month_dd(su, scn, "s%d share" % b)

    # ---- 参照：均值与 GEN 份额（S19 已报，放这里便于并列看）----
    print("\n[3] 参照（S19 已报）")
    res["mean_reference"] = month_dd(U.groupby("ym").score.mean(),
                                     C.groupby("ym").score.mean(), "mean")
    res["gen_share_reference"] = month_dd(
        U.groupby("ym").score.apply(lambda x: (x >= 3).mean()),
        C.groupby("ym").score.apply(lambda x: (x >= 3).mean()), "GEN share")

    allc = [res["log_s4_s1"]] + list(res["bin_shares"].values()) + \
           [res["mean_reference"], res["gen_share_reference"]]
    res["all_cover_zero"] = all(x["covers_zero"] for x in allc)
    print("\n全部 %d 个规格的区间都含 0: %s" % (len(allc), res["all_cover_zero"]))

    json.dump(res, open(os.path.join(HERE, "R1_composition_result.json"), "w",
                        encoding="utf-8"), indent=1, ensure_ascii=False)
    print("产物：R1_composition_result.json")


if __name__ == "__main__":
    main()
