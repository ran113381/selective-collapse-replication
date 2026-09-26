# -*- coding: utf-8 -*-
"""方案乙 裁决后分析(预登记于 2026-08-23,先于裁决数据存在——分析计划不随结果改动)。

输入: 裁决记录表.csv(consensus_0_4 已填)。
预登记的分析(全部执行,不挑报):
  A. 裁决前口径(已定,不变): κ_AB 二元 0.533 / 加权 0.609 / ρ 0.661 如实报为评分者间信度。
  B. 共识金标准构建: 230 题二元一致(共识=两人共同侧;序数共识仅在 A==B 时定义)
     + 70 题裁决共识。"无法达成"题剔除并报数。
  C. 主检验: 共识 vs 模型 二元 κ(N=300−无法达成数)。
  D. 次要: 共识 vs 模型 加权 κ,仅在序数共识有定义的子集(A==B 的 114 题 + 70 裁决题)。
  E. 敏感性: (i) 仅 230 未裁决题 vs 仅 70 裁决题分别报;
     (ii) 剔除 4 个有机日期条目; (iii) 分时期漂移(pre/post 2022-12, Fisher)。
  F. 描述: 裁决落点(偏A/偏B/两者之外)——事后描述,不作检验。
用法: py -V:3.13 score_adjudication.py
"""
import csv
import json
import os

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))

A = {int(r["order"]): int(r["score_0_4"])
     for r in csv.DictReader(open(os.path.join(HERE, "coding_sheet_A_v2.csv"),
                                  encoding="utf-8-sig")) if r["score_0_4"].strip()}
B = {int(r["order"]): int(r["score_0_4"])
     for r in csv.DictReader(open(os.path.join(HERE, "coding_sheet_B_v2.csv"),
                                  encoding="utf-8-sig")) if r["score_0_4"].strip()}
M = {int(r["question_id"]): int(r["model_score"])
     for r in csv.DictReader(open(os.path.join(HERE, "answer_key_封存勿开.csv"),
                                  encoding="utf-8-sig"))}
gv2 = json.load(open(os.path.join(HERE, "gold_sample_v2_order.json"), encoding="utf-8"))
qid = {s["order_v2"]: s["question_id"] for s in gv2}
ym = {s["order_v2"]: s["ym"] for s in gv2}

adj, failed = {}, []
for r in csv.DictReader(open(os.path.join(HERE, "裁决记录表.csv"), encoding="utf-8-sig")):
    o = int(r["order"])
    v = r["consensus_0_4"].strip()
    if v == "":
        note = list(r.values())[-1]
        (failed if "无法" in str(note) else failed).append(o)
    else:
        adj[o] = int(v)
missing = [o for o in range(1, 301) if (A[o] >= 3) != (B[o] >= 3) and o not in adj and o not in failed]
if missing:
    print(f"[警告] {len(missing)} 道裁决题既无共识分也未标'无法达成': {missing[:10]}")
    failed += missing

# 共识二元标签
cons_bin = {}
for o in range(1, 301):
    if (A[o] >= 3) == (B[o] >= 3):
        cons_bin[o] = int(A[o] >= 3)
    elif o in adj:
        cons_bin[o] = int(adj[o] >= 3)
# 序数共识: A==B 或 已裁决
cons_ord = {o: A[o] for o in range(1, 301) if A[o] == B[o]}
cons_ord.update(adj)

def kbin_dict(d):
    ks = sorted(d)
    a = np.array([d[o] for o in ks])
    b = np.array([int(M[qid[o]] >= 3) for o in ks])
    po = (a == b).mean(); p1, p2 = a.mean(), b.mean()
    pe = p1 * p2 + (1 - p1) * (1 - p2)
    return (po - pe) / (1 - pe), po, len(ks)

def kqw_pairs(pairs, K=5):
    n = len(pairs); O = np.zeros((K, K))
    for i, j in pairs: O[i][j] += 1
    rx = O.sum(1); ry = O.sum(0); num = den = 0.0
    for i in range(K):
        for j in range(K):
            w = ((i - j) ** 2) / ((K - 1) ** 2)
            num += w * O[i][j]; den += w * rx[i] * ry[j] / n
    return 1 - num / den

print("=" * 66)
print("方案乙 裁决后分析(预登记口径)")
print("=" * 66)
print(f"裁决题回收: {len(adj)}/70   无法达成: {len(failed)} {failed if failed else ''}")
print()
print("A. 裁决前信度(不变,如实报): κ_AB 二元 0.533 [0.439,0.627] / 加权 0.609 [0.535,0.677] / ρ 0.661")
print()
k, po, n = kbin_dict(cons_bin)
print(f"C. 主检验 共识vs模型 二元: κ={k:+.3f}  一致率={po:.1%}  N={n}")
rng = np.random.default_rng(20260824)
ks_ = sorted(cons_bin); arr = np.array([[cons_bin[o], int(M[qid[o]] >= 3)] for o in ks_])
boots = []
for _ in range(3000):
    ii = rng.choice(len(arr), len(arr), replace=True)
    a, b = arr[ii, 0], arr[ii, 1]
    po_ = (a == b).mean(); p1, p2 = a.mean(), b.mean()
    pe = p1 * p2 + (1 - p1) * (1 - p2)
    boots.append((po_ - pe) / (1 - pe))
print(f"   bootstrap 95% CI [{np.percentile(boots,2.5):+.3f}, {np.percentile(boots,97.5):+.3f}]")
print()
pairs = [(cons_ord[o], M[qid[o]]) for o in sorted(cons_ord)]
print(f"D. 共识vs模型 加权κ(序数共识子集 N={len(pairs)}): {kqw_pairs(pairs):+.3f}")
print()
agreed = {o: v for o, v in cons_bin.items() if (A[o] >= 3) == (B[o] >= 3)}
adjud = {o: v for o, v in cons_bin.items() if o in adj}
k1, p1_, n1 = kbin_dict(agreed); k2, p2_, n2 = kbin_dict(adjud)
print(f"E-i. 未裁决230题: κ={k1:+.3f} 一致率={p1_:.1%} N={n1}   裁决70题: κ={k2:+.3f} 一致率={p2_:.1%} N={n2}")
ORG = [38, 194, 297, 84]  # r1 order;换算为 v2 order
r1_to_qid = {s["order"]: s["question_id"] for s in
             json.load(open(os.path.join(HERE, "gold_sample.json"), encoding="utf-8"))}
org_qids = {r1_to_qid[o] for o in ORG}
sub = {o: v for o, v in cons_bin.items() if qid[o] not in org_qids}
k3, p3_, n3 = kbin_dict(sub)
print(f"E-ii. 剔除有机日期4题: κ={k3:+.3f} N={n3}")
pre = [o for o in cons_bin if int(ym[o][:4]) * 12 + int(ym[o][5:7]) - 1 < 2022 * 12 + 11]
post = [o for o in cons_bin if o not in pre]
cp = sum(cons_bin[o] == int(M[qid[o]] >= 3) for o in pre)
cq = sum(cons_bin[o] == int(M[qid[o]] >= 3) for o in post)
_, pv = stats.fisher_exact([[cp, len(pre) - cp], [cq, len(post) - cq]])
print(f"E-iii. 漂移: pre {cp}/{len(pre)}={cp/len(pre):.1%}  post {cq}/{len(post)}={cq/len(post):.1%}  Fisher p={pv:.3f}")
print()
toA = sum(1 for o in adj if (adj[o] >= 3) == (A[o] >= 3))
toB = sum(1 for o in adj if (adj[o] >= 3) == (B[o] >= 3))
print(f"F. 裁决落点(描述): 与A同侧 {toA}  与B同侧 {toB}  (共{len(adj)})")
