# -*- coding: utf-8 -*-
"""R1c 分析：同分类器内部检验，用来排除「我的盲标实例相对原分类器做压缩」这个混淆。

R1 里的 Δ 是跨分类器相减（我方盲标 − Sonnet 4.6）。常数级偏差在 ΔΔ 里会自己抵消，
但压缩型偏差不会：若我方相对原分类器把高分往下拉、低分往上推，那么在真实替代率高
的前期误差会更负、替代率低的后期误差更浅——足以凭空造出 R1-A 里那个 +0.199。

排除方法：让同一批盲标实例去标「原样本」的题（同 30 个月，各 40 题，原分类器对
这些题已经打过分）。这样能直接算：

  e(m) = mean_我方(m) − mean_Sonnet4.6(m)   ——同一批题、同一批分类器身份、只换评分者

判据（先写死，不因结果调整）：
  R1c-A  e(m) 前后期是否有显著漂移（ΔΔ_e）。
         若 R1 的 ΔΔ（+0.199）主要是压缩伪影，这里应同样显著且同号；
         若这里的 ΔΔ_e 接近 0、不显著，压缩假说被证伪，R1 的漂移就是真的。
  R1c-B  把 R1c-A 的 ΔΔ_e 与 R1-A 的 ΔΔ（+0.199）相减，若 R1 的 ΔΔ 显著大于
         R1c 的 ΔΔ_e，说明「月内位置」这个新维度本身携带额外信号，不能全部
         记在分类器差异头上。
"""
import json, glob, os, math
import numpy as np
import pandas as pd
import csv as _csv

HERE = os.path.dirname(os.path.abspath(__file__))
EVENT = "2022-12"


def load():
    tokmap = json.load(open(os.path.join(HERE, "R1c_token_map.json"), encoding="utf-8"))
    labs = []
    for f in sorted(glob.glob(os.path.join(HERE, "R1c_labels_batch_*.json"))):
        labs += json.load(open(f, encoding="utf-8"))
    lab = pd.DataFrame(labs)
    assert lab.id.is_unique, "R1c 盲标结果里有重复 token"
    lab["question_id"] = lab.id.map(tokmap)
    assert lab.question_id.notna().all(), "有 token 回接不到真实 qid"
    print("R1c 盲标回收 %d 题" % len(lab))

    old_q = []
    for fn in ("so_questions_full.json", "so_questions_ext_py.json"):
        old_q += json.load(open(r"E:\智能体论文\_legB_data\%s" % fn, encoding="utf-8"))
    qmeta = {q["question_id"]: q["ym"] for q in old_q}
    ol = {}
    for fn in ("question_labels.csv", "question_labels_ext_py.csv"):
        for r in _csv.DictReader(open(r"E:\智能体论文\_legB_data\%s" % fn, encoding="utf-8")):
            ol[int(r["question_id"])] = int(r["score"])

    lab["ym"] = lab.question_id.map(qmeta)
    lab["orig_score"] = lab.question_id.map(ol)
    n0 = len(lab)
    lab = lab[lab.ym.notna() & lab.orig_score.notna()]
    print("回接到月份+原分类 %d / %d 题" % (len(lab), n0))
    return lab


def main():
    d = load()
    d = d[(d.score > 0) & (d.orig_score > 0)]           # 同口径：丢 s0
    d["post"] = (d.ym >= EVENT).astype(int)
    d["e"] = d.score - d.orig_score                     # 同题：我方 − Sonnet4.6

    m = d.groupby("ym").agg(e_mean=("e", "mean"), e_sd=("e", "std"), n=("e", "size"),
                             my_mean=("score", "mean"), orig_mean=("orig_score", "mean")).reset_index()
    m["post"] = (m.ym >= EVENT).astype(int)

    print("\n" + "=" * 74)
    print("每月：我方盲标 − 原分类器(Sonnet 4.6)，同一批题")
    print("=" * 74)
    for _, r in m.iterrows():
        print("  %s  post=%d  我方 %.3f  原分类器 %.3f  e=%+.3f  (n=%d)"
              % (r.ym, r.post, r.my_mean, r.orig_mean, r.e_mean, r.n))

    pre, post = d[d.post == 0], d[d.post == 1]
    e_pre, e_post = pre.e.mean(), post.e.mean()
    dd_e = e_post - e_pre
    se_e = math.sqrt(pre.e.var(ddof=1)/len(pre) + post.e.var(ddof=1)/len(post))
    lo, hi = dd_e - 1.96*se_e, dd_e + 1.96*se_e

    print("\n" + "=" * 74)
    print("R1c-A  同分类器内部：我方相对 Sonnet 4.6 的偏差是否前后期漂移")
    print("=" * 74)
    print("  前期 e = %+.3f (n=%d)   后期 e = %+.3f (n=%d)" % (e_pre, len(pre), e_post, len(post)))
    print("  ΔΔ_e（后−前）= %+.3f, SE %.3f, 95%% CI [%+.3f, %+.3f]" % (dd_e, se_e, lo, hi))
    a_pass = lo <= 0 <= hi
    print("  判据 R1c-A：%s —— %s" % (
        "通过(不显著)" if a_pass else "不通过(显著)",
        "我方相对原分类器的偏差不随时间漂移，压缩假说不成立" if a_pass
        else "我方相对原分类器的偏差本身就随时间漂移，需要判断这是压缩还是原分类器自身的问题"))

    R1A_DD, R1A_SE = 0.199, 0.098
    diff = R1A_DD - dd_e
    se_diff = math.sqrt(R1A_SE**2 + se_e**2)
    z = diff / se_diff
    print("\n" + "=" * 74)
    print("R1c-B  R1 的 ΔΔ(+0.199) 是否显著大于本检验测到的分类器内部漂移 ΔΔ_e")
    print("=" * 74)
    print("  R1  ΔΔ  = %+.3f (SE %.3f)" % (R1A_DD, R1A_SE))
    print("  R1c ΔΔ_e = %+.3f (SE %.3f)" % (dd_e, se_e))
    print("  差值 = %+.3f (SE %.3f), z = %.2f" % (diff, se_diff, z))
    b_pass = abs(z) < 1.96
    print("  判据 R1c-B：%s —— %s" % (
        "通过(二者不可区分)" if b_pass else "不通过(R1 的漂移显著更大)",
        "R1 的漂移基本可以用『同一批分类器,换了评分者』本身的噪声解释" if b_pass
        else "R1 的漂移里有一部分不是分类器差异能解释的,来自月内位置本身"))

    print("\n" + "=" * 74)
    print("总判：R1c-A %s / R1c-B %s" % ("过" if a_pass else "不过", "过" if b_pass else "不过"))
    print("=" * 74)

    m.to_csv(os.path.join(HERE, "R1c_month_compare.csv"), index=False, encoding="utf-8-sig")
    json.dump({"e_pre": float(e_pre), "e_post": float(e_post), "dd_e": float(dd_e),
               "dd_e_se": float(se_e), "dd_e_ci": [float(lo), float(hi)],
               "R1_dd": R1A_DD, "R1_dd_se": R1A_SE, "diff": float(diff),
               "diff_se": float(se_diff), "z": float(z),
               "R1c_A": bool(a_pass), "R1c_B": bool(b_pass), "n": int(len(d))},
              open(os.path.join(HERE, "R1c_result.json"), "w", encoding="utf-8"), indent=1)
    print("\n产物：R1c_month_compare.csv  R1c_result.json")


if __name__ == "__main__":
    main()
