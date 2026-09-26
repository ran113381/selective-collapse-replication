# -*- coding: utf-8 -*-
"""R2 下游重估·零散数:稿件与 SI 里剩下的、随主评分者变化的小数。两臂同算,原标签臂先对稿件现值自证。
  a 有机日期 4 题剔除后对人工共识 κ(稿件 0.512→0.513);
  b 70 道裁决题上主评分者判生成类的占比(稿件 49%,共识 73%);230 题 / 70 题上的 κ(0.618 / 0.182);
    共识对主评分者一致率前后(81.1% vs 73.3%,Fisher p = .186);
  c 盲对原全面板:二元 κ、原始一致、加权 κ、完全一致;
  d 量重构序列(3 个月平滑)事件后 s4 最低的月份占比(图 2A「几乎整个事件后 s4 最低」);
  e S15 按 UTC 小时段与按月内日期的均分(稿件 2.53 vs 2.80–2.83;2.28 vs 2.37–2.41;2.36 vs 2.38);
  f S9 各档重复关闭占比前后(稿件 s4 12.3%→10.5%);
  g S17 长度对示踪量的削弱(稿件 log 长度系数 −0.046、0.25 log、0.012 对约 0.09、七分之八)。
输出 工作文档\\R2d_more_result.json
"""
import csv, io, json, math, os, sys
import numpy as np
import pandas as pd
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
PKG = r"E:\智能体论文\P9b_OSF_复现包_20260920"
ROOT = os.path.join(HERE, "R2_downstream")
GOLD = os.path.join(PKG, "03_validation", "gold_standard")
EV = 2022 * 12 + 11
src = io.open(os.path.join(PKG, "05_additional_checks", "cross_family_analysis.py"), encoding="utf-8").read()
ns = {"__file__": "x"}; exec(compile(src[:src.find("def main")], "cfa", "exec"), ns); ns["GOLD"] = GOLD
kappa_bin, kappa_qw, human_consensus = ns["kappa_bin"], ns["kappa_qw"], ns["human_consensus"]


def ymi(y):
    a, b = y.split("-"); return int(a) * 12 + int(b) - 1


cons = human_consensus()
organic = {int(l.split(",")[0]) for l in io.open(os.path.join(GOLD, "organic_date_items.txt"), encoding="utf-8").read().splitlines()
           if l.strip() and not l.startswith("#")}
assert len(organic) == 4, organic
gold_ym = {int(r["question_id"]): r["ym"] for r in json.load(io.open(os.path.join(GOLD, "gold_sample.json"), encoding="utf-8"))}
qs = []
for fn in ("so_questions_full.json", "so_questions_ext_py.json"):
    qs += json.load(io.open(os.path.join(ROOT, "orig", "data", fn), encoding="utf-8"))
created = {int(q["question_id"]): int(q["creation_date"]) for q in qs}
text_len = {int(q["question_id"]): len((q.get("title") or "") + (q.get("body_excerpt") or "")) for q in qs}
R = {"organic_items": sorted(organic)}


def arm_stats(arm):
    base = os.path.join(ROOT, arm)
    lab = pd.read_csv(os.path.join(base, "data", "question_labels.csv")).set_index("question_id")
    o = {}
    Q = sorted(cons)
    a = np.array([int(lab.loc[q, "score"] >= 3) for q in Q]); h = np.array([cons[q][1] for q in Q])
    o["kappa300"] = round(float(kappa_bin(a, h)[0]), 6)
    keep = [i for i, q in enumerate(Q) if q not in organic]
    o["kappa_excl_organic"] = [round(float(kappa_bin(a[keep], h[keep])[0]), 6), len(keep)]
    for kind in ("agreed", "adjudicated"):
        ii = [i for i, q in enumerate(Q) if cons[q][0] == kind]
        k, po = kappa_bin(a[ii], h[ii])
        o["kappa_" + kind] = [round(float(k), 6), round(float(po), 6), len(ii)]
        if kind == "adjudicated":
            o["adjudicated_gen_share"] = dict(rater=round(float(a[ii].mean()), 6), consensus=round(float(h[ii].mean()), 6))
    post = np.array([ymi(gold_ym[q]) >= EV for q in Q])
    ag = (a == h)
    tab = [[int(ag[~post].sum()), int((~ag[~post]).sum())], [int(ag[post].sum()), int((~ag[post]).sum())]]
    o["period_agreement"] = [round(float(ag[~post].mean()), 6), round(float(ag[post].mean()), 6), float(stats.fisher_exact(tab)[1])]
    # d 量重构序列:事件后 s4 最低的月份占比(3 个月居中平滑)
    av = pd.read_csv(os.path.join(base, "02_estimation", "absolute_volume_series_python.csv"))
    sm = av[["Nhat_s%d" % b for b in (1, 2, 3, 4)]].rolling(3, center=True, min_periods=1).mean()
    pm = av.ym.map(ymi) >= EV
    low = sm[pm].idxmin(axis=1)
    o["post_months_s4_lowest"] = [int((low == "Nhat_s4").sum()), int(pm.sum())]
    o["post_months_lowest_counts"] = low.value_counts().to_dict()
    # e 小时段与月内日期
    d = lab.reset_index()
    d["ts"] = d.question_id.map(created)
    d = d[d.score.between(1, 4) & d.ts.notna()].copy()
    dt = pd.to_datetime(d.ts, unit="s", utc=True)
    d["hour"] = dt.dt.hour; d["day"] = dt.dt.day; d["post"] = d.ym.map(ymi) >= EV
    bands = [(0, 1), (2, 3), (4, 5), (6, 23)]          # 两小时段 [0,2) [2,4) [4,6) 与其后(按稿件口径复现 2.53)
    o["hour_bands"] = {}
    for p in (False, True):
        o["hour_bands"]["post" if p else "pre"] = [round(float(d[(d.post == p) & d.hour.between(lo, hi)].score.mean()), 5) for lo, hi in bands]
    pp = d[d.post]
    o["day_of_month_post"] = [round(float(pp[pp.day == 1].score.mean()), 5), round(float(pp[pp.day > 1].score.mean()), 5)]
    # f 各档重复关闭占比前后(不设窗)
    clo = pd.read_csv(os.path.join(base, "02_estimation", "closure_meta.csv")).rename(columns={"score": "so_score"})
    m = lab.reset_index().merge(clo, on="question_id")
    m = m[m.score.between(1, 4)]; m["post"] = m.ym.map(ymi) >= EV; m["dup"] = m.closed_reason == "Duplicate"
    o["dup_share_pre_post"] = {"s%d" % b: [round(100 * float(m[(m.score == b) & ~m.post].dup.mean()), 1),
                                           round(100 * float(m[(m.score == b) & m.post].dup.mean()), 1)] for b in (1, 2, 3, 4)}
    # g 长度削弱:用 s17_length_conditioned.json 的系数与本臂的长度变化
    s17 = json.load(io.open(os.path.join(base, "02_estimation", "s17_length_conditioned.json"), encoding="utf-8"))
    o["s17_length_json_keys"] = list(s17)
    d["loglen"] = np.log(d.question_id.map(text_len).clip(lower=1))
    o["median_len_ratio"] = {"s%d" % b: round(float(d[(d.score == b) & d.post].question_id.map(text_len).median() /
                                                  d[(d.score == b) & ~d.post].question_id.map(text_len).median()), 5) for b in (1, 2, 3, 4)}
    return o


for arm in ("orig", "blind"):
    R[arm] = arm_stats(arm)
    print("\n[%s]" % arm, json.dumps(R[arm], ensure_ascii=False))
o = R["orig"]
R["selfproof"] = {
    "kappa300 0.512": abs(o["kappa300"] - 0.512) < 0.0015,
    "organic 0.513 on 296": round(o["kappa_excl_organic"][0], 3) == 0.513 and o["kappa_excl_organic"][1] == 296,
    "agreed 0.618 / adjudicated 0.182": abs(o["kappa_agreed"][0] - 0.618) < 0.0015 and abs(o["kappa_adjudicated"][0] - 0.182) < 0.0015,
    "adjudicated gen 49% vs 73%": round(100 * o["adjudicated_gen_share"]["rater"]) == 49 and round(100 * o["adjudicated_gen_share"]["consensus"]) == 73,
    "period 81.1 vs 73.3 p .186": round(100 * o["period_agreement"][0], 1) == 81.1 and round(100 * o["period_agreement"][1], 1) == 73.3 and abs(o["period_agreement"][2] - 0.186) < 0.0015,
    "hour pre 2.53 / 2.80-2.83; post 2.28 / 2.37-2.41": (round(o["hour_bands"]["pre"][0], 2) == 2.53 and
        [round(x, 2) for x in o["hour_bands"]["pre"][1:]] == [2.82, 2.80, 2.83] and round(o["hour_bands"]["post"][0], 2) == 2.28
        and all(2.37 <= round(x, 2) <= 2.41 for x in o["hour_bands"]["post"][1:])),
    "day post 2.36 / 2.38": [round(x, 2) for x in o["day_of_month_post"]] == [2.36, 2.38],
    "dup s4 12.3 -> 10.5": o["dup_share_pre_post"]["s4"] == [12.3, 10.5],
}
print("\n自证:", json.dumps(R["selfproof"], ensure_ascii=False))
io.open(os.path.join(HERE, "R2d_more_result.json"), "w", encoding="utf-8").write(json.dumps(R, indent=1, ensure_ascii=False, default=str))
