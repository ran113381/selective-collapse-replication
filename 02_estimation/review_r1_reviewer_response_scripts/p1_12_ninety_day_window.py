# -*- coding: utf-8 -*-
u"""P1-12：Table 9 / SI S9 的「再丢面板最后 90 天」是多余的，重算。

现状：稿件对重复关闭率用两道限制——(a) 只计发帖后 90 天内的关闭（对的，必需，
否则 2021 年的题有五年暴露、2026 年的只有几个月）；(b) 再丢掉面板最后 90 天，
N 从 6,000 降到 5,640。

(b) 是多余的：关闭状态 2026-09-06 回抓，面板止于 2026-05，最后一个月的题到回抓时
也已有 ≥90 天可观测寿命，(a) 对它们照样成立。丢掉 360 道题不换来任何东西。

本脚本先按现行口径复现已发表的四行，证明管线对；再去掉 (b) 重算。

自证：S1 复现口径必须给出 N=5,640 与已发表的四对百分比（容差 0.05pp）。
"""
import io, json, os, sys
import numpy as np
import pandas as pd
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8")

DATA = r"E:\智能体论文\_legB_data"
REP = r"E:\智能体论文\P9_修订_20260703\replication_additions"
HERE = os.path.dirname(os.path.abspath(__file__))

lab = pd.read_csv(os.path.join(DATA, "question_labels.csv"))
cm = pd.read_csv(os.path.join(REP, "closure_meta.csv"))
own = pd.read_csv(os.path.join(REP, "asker_owner.csv")).drop_duplicates(
    "question_id")[["question_id", "q_creation"]]

# 创建时间两个来源：原口径用 asker_owner.csv 的 q_creation（39 条缺失，那 39 条
# 就此被连带丢出样本）；JSON 的 creation_date 则 6,000 条齐全。先核两者一致。
created = {}
for fn in ("so_questions_full.json", "so_questions_ext_py.json"):
    for q in json.load(io.open(os.path.join(DATA, fn), encoding="utf-8")):
        created[q["question_id"]] = q["creation_date"]
lab["created_json"] = lab.question_id.map(created)
assert lab.created_json.notna().all(), "JSON 有题缺创建时间"

d = lab.merge(cm[["question_id", "closed_date", "closed_reason"]], on="question_id", how="left")
d = d.merge(own, on="question_id", how="left")
d = d[d.score.between(1, 4)].copy()
d["post"] = (d.ym >= "2022-12").astype(int)
DAY = 86400.0


def mi_of(y):
    a, b = y.split("-")
    return int(a) * 12 + int(b) - 1


d["mi"] = d.ym.map(mi_of)
both = d[d.q_creation.notna()]
disagree = int((both.q_creation != both.created_json).sum())
print("两个创建时间源在共有的 %d 条上不一致 %d 条" % (len(both), disagree))
print("q_creation 缺失 %d 条（JSON 侧齐全，可救回）" % int(d.q_creation.isna().sum()))

REFETCH = float(cm.closed_date.max())
d["age_at_refetch"] = (REFETCH - d.created_json) / DAY
print("回抓时点(由最后一次关闭推定) = %s" % pd.to_datetime(REFETCH, unit="s").date())
print("面板最后一月 = %s；该月题目在回抓时的最小寿命 = %.0f 天 → 90 天暴露窗对它们照样成立"
      % (d.ym.max(), d[d.ym == d.ym.max()].age_at_refetch.min()))


def mark(df, tcol):
    df = df.copy()
    df["dup_within_90"] = (df.closed_date.notna() & (df.closed_reason == "Duplicate")
                           & ((df.closed_date - df[tcol]) / DAY <= 90))
    return df


def table(df, tag):
    rows = []
    for b in (1, 2, 3, 4):
        g = df[df.score == b]
        out = {"bin": "s%d" % b}
        for per, nm in ((0, "pre"), (1, "post")):
            gg = g[g.post == per]
            n, k = len(gg), int(gg.dup_within_90.sum())
            out["%s_n" % nm], out["%s_pct" % nm] = n, 100.0 * k / n if n else np.nan
        p1, n1 = out["pre_pct"] / 100, out["pre_n"]
        p2, n2 = out["post_pct"] / 100, out["post_n"]
        diff = 100 * (p2 - p1)
        seD = 100 * np.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
        out["diff"], out["lo"], out["hi"] = diff, diff - 1.96 * seD, diff + 1.96 * seD
        rows.append(out)
    print("\n%s  (N = %d)" % (tag, len(df)))
    for r in rows:
        print("  %s  pre %5.2f%% (N=%4d)   post %5.2f%% (N=%4d)   diff %+5.2f [%+.2f, %+.2f]"
              % (r["bin"], r["pre_pct"], r["pre_n"], r["post_pct"], r["post_n"],
                 r["diff"], r["lo"], r["hi"]))
    return rows


# ---- 现行口径 ----
# 实际切法（读 s17_length_conditioned.py:33 得知）：按**月索引**丢最后
# ceil(90/30)=3 个月，且创建时间取自 asker_owner.csv，那 39 条缺失被连带丢出。
cur = mark(d[(d.mi <= d.mi.max() - 3) & d.q_creation.notna()], "q_creation")
rows_cur = table(cur, "现行口径（丢最后 3 个月 + 丢 39 条缺创建时间的）")

# ---- 自证 ----
PUB = [(3.69, 271, 2.12, 945), (4.31, 394, 2.48, 1090),
       (4.69, 661, 4.08, 1300), (11.83, 465, 10.12, 514)]
fail = []
if len(cur) != 5640:
    fail.append("S1 N 不符：应 5640，实得 %d" % len(cur))
for r, (a, an, b_, bn) in zip(rows_cur, PUB):
    if abs(r["pre_pct"] - a) > 0.05 or abs(r["post_pct"] - b_) > 0.05:
        fail.append("S1 %s 百分比不复现：应 %.2f/%.2f 实得 %.2f/%.2f"
                    % (r["bin"], a, b_, r["pre_pct"], r["post_pct"]))
    if r["pre_n"] != an or r["post_n"] != bn:
        fail.append("S1 %s N 不复现：应 %d/%d 实得 %d/%d"
                    % (r["bin"], an, bn, r["pre_n"], r["post_n"]))
print("\n自证：" + ("复现通过" if not fail else "失败 %d 条" % len(fail)))
for x in fail:
    print("  !! " + x)
if fail:
    sys.exit(2)

# ---- 建议口径：不丢月份，并用 JSON 创建时间救回那 39 条 ----
rows_new = table(mark(d, "created_json"),
                 "建议口径（保留全部月份，JSON 创建时间救回 39 条）")

# 定性结论是否变号
qual = []
for r in rows_new:
    if r["lo"] <= 0 <= r["hi"]:
        pass
    else:
        qual.append("%s 区间不再覆盖零：[%+.2f, %+.2f]" % (r["bin"], r["lo"], r["hi"]))
    if r["diff"] > 0:
        qual.append("%s 差值转正（低档向 s4 靠拢，与相贴标签预测同向）" % r["bin"])
print("\n定性结论变化：" + ("无（每个区间仍覆盖零、低档仍下行）" if not qual else ""))
for x in qual:
    print("  ** " + x)

out = {
    "note": "P1-12：去掉多余的「丢面板最后 90 天」。90 天暴露窗保留。",
    "refetch_date": str(pd.to_datetime(REFETCH, unit="s").date()),
    "min_age_last_month_days": round(float(d[d.ym == d.ym.max()].age_at_refetch.min()), 1),
    "current_spec": {"n": int(len(cur)), "rows": rows_cur},
    "proposed_spec": {"n": int(len(d)), "rows": rows_new},
    "qualitative_change": qual or "none",
}
p = os.path.join(HERE, "p1_12_ninety_day_window.json")
with io.open(p, "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1, default=float)
print("\n已存 %s" % os.path.basename(p))
