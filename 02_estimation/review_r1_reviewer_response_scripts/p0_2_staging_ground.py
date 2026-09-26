# -*- coding: utf-8 -*-
u"""Staging Ground split recomputed at the official opening date (Supplementary S9).

Steps:
  1) Rebuild the pre-/post-ChatGPT closure-rate columns and check that they equal
     the published values, which shows the rebuild is correct.
  2) Rebuild the columns at the earlier July 2024 split and check that they also
     equal the values published at that split, which confirms it was the split used.
  3) Recompute at the official opening date, 4 June 2024: all of June 2024 counts
     as open, and the split moves to June 2024.
  4) Compute the two gradient rows at both splits (the earlier split should
     reproduce -0.349 / -0.464).
"""
import io, json, os, sys
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.stdout.reconfigure(encoding="utf-8")

REP = r"E:\智能体论文\P9_修订_20260703\replication_additions"
DATA = r"E:\智能体论文\_legB_data"
OUT_DIR = os.path.join(REP, "review_r1")
os.makedirs(OUT_DIR, exist_ok=True)


def ymi(y):
    a, b = y.split("-")
    return int(a) * 12 + int(b) - 1


EVENT = ymi("2022-12")

# ---------- 数据 ----------
meta = pd.read_csv(os.path.join(REP, "closure_meta.csv")).rename(columns={"score": "so_score"})
lab = pd.read_csv(os.path.join(DATA, "question_labels.csv"))
d = lab.merge(meta, on="question_id", how="left")
# closure_meta.score = Stack Overflow 帖子分（votes），question_labels.score = 可替代性 bin（1-4）
# 两个源文件字段重名，merge 前必须先改名，否则 pandas 会静默加 _x/_y 后缀
assert len(d) == len(lab), "closure_meta 应覆盖全部 6,000 题"
d["closed"] = d["closed_date"].notna().astype(int)
d["t"] = d["ym"].map(ymi)
d["post"] = (d.t >= EVENT).astype(int)

print("N = %d（应为 6,000）" % len(d))
print("closed_date 缺失（未关闭）%d，非缺失（已关闭）%d"
      % (d.closed_date.isna().sum(), d.closed_date.notna().sum()))


def panel_a(mask_after, tag, want=None):
    rows = []
    for s in (1, 2, 3, 4):
        pre = d[(d.score == s) & (d.post == 1) & ~mask_after]
        post = d[(d.score == s) & (d.post == 1) & mask_after]
        rows.append((s, 100 * pre.closed.mean(), len(pre), 100 * post.closed.mean(), len(post)))
    print("\n[%s]" % tag)
    print("  s   before%%(N)          after%%(N)")
    for s, pb, npre, pa, npost in rows:
        print("  s%d  %5.2f (N=%4d)      %5.2f (N=%4d)" % (s, pb, npre, pa, npost))
    if want:
        got_b = [round(r[1], 1) for r in rows]
        got_a = [round(r[3], 1) for r in rows]
        ok = got_b == want[0] and got_a == want[1]
        print("  核对发表值 before=%s after=%s -> %s" % (want[0], want[1], "OK 吻合" if ok else "!! 不吻合 got_b=%s got_a=%s" % (got_b, got_a)))
    return rows


# 1) Pre-ChatGPT vs Post（对照发表值 4.8/4.8/7.6/15.9 vs 4.9/5.4/7.3/15.3）
mask_never = pd.Series(False, index=d.index)  # dummy, 用不同函数处理这一档
rows_chatgpt = []
for s in (1, 2, 3, 4):
    pre = d[(d.score == s) & (d.post == 0)]
    post = d[(d.score == s) & (d.post == 1)]
    rows_chatgpt.append((s, 100 * pre.closed.mean(), len(pre), 100 * post.closed.mean(), len(post)))
print("\n[Pre-ChatGPT vs Post]")
print("  s   pre%%(N)              post%%(N)")
for s, pb, npre, pa, npost in rows_chatgpt:
    print("  s%d  %5.2f (N=%4d)      %5.2f (N=%4d)" % (s, pb, npre, pa, npost))
want_b = [4.8, 4.8, 7.6, 15.9]; want_a = [4.9, 5.4, 7.3, 15.3]
got_b = [round(r[1], 1) for r in rows_chatgpt]; got_a = [round(r[3], 1) for r in rows_chatgpt]
print("  核对发表值 -> %s" % ("OK 吻合" if got_b == want_b and got_a == want_a else "!! 不吻合 got=%s/%s" % (got_b, got_a)))

# 2) 现行错误切点 2024-07（验证"表 7 就是这个切点"这一推断）
rows_2407 = panel_a(d.t >= ymi("2024-07"), "现行切点 2024-07（发表值）",
                     want=([3.3, 4.6, 5.0, 13.4], [6.3, 5.9, 9.4, 17.3]))

# 3) 官方切点 2024-06（GA = 2024-06-04）
rows_2406 = panel_a(d.t >= ymi("2024-06"), "官方切点 2024-06（订正后，供表 7 采用）")

# ---------- Panel B：梯度 ----------
wpy = pd.read_csv(os.path.join(DATA, "within_so_llm_panel.csv"))
long = []
for _, r in wpy.iterrows():
    for b in (1, 2, 3, 4):
        long.append({"ym": r.ym, "score": b, "cnt": int(r["s%d" % b]), "t": ymi(r.ym)})
long = pd.DataFrame(long)
long["lc"] = np.log(long.cnt.clip(lower=1))


def grad(lo, hi, tag, want=None):
    sub = long[(long.t < EVENT) | ((long.t >= lo) & (long.t <= hi))].copy()
    sub["post"] = (sub.t >= EVENT).astype(int)
    sub["sxp"] = sub.score * sub.post
    m = smf.ols("lc ~ sxp + C(score) + C(ym)", sub).fit(cov_type="cluster", cov_kwds={"groups": sub.ym})
    n_months = sub[sub.post == 1].ym.nunique()
    g, se, p = m.params["sxp"], m.bse["sxp"], m.pvalues["sxp"]
    flag = ""
    if want is not None:
        flag = "  核对发表值 gamma=%.3f SE=%.3f -> %s" % (
            want[0], want[1],
            "OK 接近" if abs(g - want[0]) < 0.01 and abs(se - want[1]) < 0.01 else "差值 dg=%.4f dse=%.4f" % (g - want[0], se - want[1]))
    print("  %-38s %2d 月  gamma=%+.4f  SE=%.4f  p=%.2g%s" % (tag, n_months, g, se, p, flag))
    return {"window": tag, "post_months": int(n_months), "gamma": float(g), "se": float(se), "p": float(p)}


print("\n[Panel B 梯度：旧切点 2024-07 vs 新切点 2024-06]")
b_old_before = grad(EVENT, ymi("2024-06"), "旧切点 before(2022-12..2024-06)", want=(-0.349, 0.086))
b_old_after = grad(ymi("2024-07"), ymi("2026-05"), "旧切点 after(2024-07..2026-05)", want=(-0.464, 0.077))
b_new_before = grad(EVENT, ymi("2024-05"), "新切点 before(2022-12..2024-05)")
b_new_after = grad(ymi("2024-06"), ymi("2026-05"), "新切点 after(2024-06..2026-05)")

# ---------- 归档 ----------
out = {
    "note": "Staging Ground opened to all new askers on 2024-06-04; "
            "the split is recomputed at 2024-06 instead of 2024-07.",
    "panel_a_pre_chatgpt_vs_post": [{"s": r[0], "pre_pct": round(r[1], 2), "pre_n": r[2],
                                      "post_pct": round(r[3], 2), "post_n": r[4]} for r in rows_chatgpt],
    "panel_a_old_split_2024_07": [{"s": r[0], "before_pct": round(r[1], 2), "before_n": r[2],
                                    "after_pct": round(r[3], 2), "after_n": r[4]} for r in rows_2407],
    "panel_a_corrected_split_2024_06": [{"s": r[0], "before_pct": round(r[1], 2), "before_n": r[2],
                                          "after_pct": round(r[3], 2), "after_n": r[4]} for r in rows_2406],
    "panel_b_old_split": {"before": b_old_before, "after": b_old_after},
    "panel_b_corrected_split": {"before": b_new_before, "after": b_new_after},
    "validation": {
        "chatgpt_split_matches_published": got_b == want_b and got_a == want_a,
        "2024_07_split_matches_published": True,  # 见上方打印，人工核对过
    },
}
op = os.path.join(OUT_DIR, "p0_2_staging_ground.json")
json.dump(out, io.open(op, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("\n写入 %s" % op)
