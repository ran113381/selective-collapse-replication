# -*- coding: utf-8 -*-
"""金标准 κ 计算 v2 —— 全程按 question_id 关联(2026-08-16)。

为什么不能沿用 score_gold.py:它按 `order` 关联,而第二轮问卷重排了呈现顺序,
v2 的 order 与 answer_key 的 order 指向同一题的比例为 0/300 —— 直接跑会全面错配。
本脚本一律用 question_id 做键,对两轮的任意组合都安全。

同时修掉第一轮暴露的两个口径问题:
  1) 人共识用 round((A+B)/2) 落进 Python 银行家舍入 —— (2,3)→2 而 (3,4)→4,
     方向不一致,且恰好把最关键的 2/3 边界平局一律推给 VER。
     改为:混淆矩阵与漂移检验只用 A==B 的无歧义子集,平局数单独报。
  2) 人类量表含 0 档而模型从未打过 0 —— 折 0 进 1 作为预注册次要分析,主结果仍用原始 0-4。

用法:
    py -V:3.13 score_gold_v2.py            # 读本目录的 coding_sheet_A_v2.csv / coding_sheet_B_v2.csv
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CUT = 3          # label = GEN if score >= CUT
K = 5            # 量表档数 0-4


def load_scores(path, col="score_0_4"):
    """-> {question_id: score};容忍 order 列的任何编号方案。"""
    d = {}
    with open(os.path.join(HERE, path), encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            v = (r.get(col) or "").strip()
            if v != "":
                d[int(r["question_id"])] = int(v)
    return d


def load_key():
    m, ym = {}, {}
    with open(os.path.join(HERE, "answer_key_封存勿开.csv"), encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            qid = int(r["question_id"])
            m[qid] = int(r["model_score"])
            ym[qid] = r["ym"]
    return m, ym


def kappa_binary(x, y, cut=CUT):
    ks = sorted(set(x) & set(y))
    a = [int(x[k] >= cut) for k in ks]
    b = [int(y[k] >= cut) for k in ks]
    n = len(ks)
    po = sum(i == j for i, j in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return ((po - pe) / (1 - pe) if pe < 1 else float("nan")), po, n


def kappa_qw(x, y):
    ks = sorted(set(x) & set(y))
    n = len(ks)
    O = [[0] * K for _ in range(K)]
    for k in ks:
        O[x[k]][y[k]] += 1
    rx = [sum(O[i]) for i in range(K)]
    ry = [sum(O[i][j] for i in range(K)) for j in range(K)]
    num = den = 0.0
    for i in range(K):
        for j in range(K):
            w = ((i - j) ** 2) / ((K - 1) ** 2)
            num += w * O[i][j]
            den += w * rx[i] * ry[j] / n
    return (1 - num / den) if den else float("nan")


def within1(x, y):
    ks = sorted(set(x) & set(y))
    return sum(abs(x[k] - y[k]) <= 1 for k in ks) / len(ks)


def collapse0(d):
    """次要分析:人类的 0 折进 1(模型量表实际只用 1-4)。"""
    return {k: (1 if v == 0 else v) for k, v in d.items()}


def report_pair(name, x, y):
    if not (set(x) & set(y)):
        print(f"{name}: [尚无重叠评分]")
        return
    kb, po, n = kappa_binary(x, y)
    print(f"{name}: N={n}  二元κ={kb:+.3f} (一致率{po:.1%})  "
          f"加权κ={kappa_qw(x, y):+.3f}  ±1一致率={within1(x, y):.1%}")


def run(suffix, label):
    fa, fb = f"coding_sheet_A{suffix}.csv", f"coding_sheet_B{suffix}.csv"
    for f in (fa, fb):
        if not os.path.exists(os.path.join(HERE, f)):
            print(f"[缺文件] {f} —— 跳过 {label}")
            return None, None
    A, B = load_scores(fa), load_scores(fb)
    M, YM = load_key()
    if not A or not B:
        print(f"[{label}] A 或 B 尚未填写 (A={len(A)}, B={len(B)})")
        return A or None, B or None

    print("=" * 66)
    print(f"{label}  评分者信度 (question_id 关联)")
    print("=" * 66)
    for nm, x, y in [("人A-人B", A, B), ("人A-模型", A, M), ("人B-模型", B, M)]:
        report_pair(nm, x, y)

    print("\n[次要分析] 人类 0 档折进 1 后:")
    for nm, x, y in [("人A-人B", collapse0(A), collapse0(B)),
                     ("人A-模型", collapse0(A), M), ("人B-模型", collapse0(B), M)]:
        report_pair("  " + nm, x, y)

    # 量表使用形态 —— 第一轮的病灶就出在这里
    print("\n量表使用分布 (0/1/2/3/4):")
    for nm, d in [("人A", A), ("人B", B), ("模型", M)]:
        cnt = [sum(1 for v in d.values() if v == i) for i in range(K)]
        gen = sum(1 for v in d.values() if v >= CUT) / len(d)
        print(f"  {nm}: {cnt}   GEN占比={gen:.1%}  用到{sum(1 for c in cnt if c)}档")

    # 无歧义子集(A==B):替代有偏的 round((A+B)/2) 共识
    both = sorted(set(A) & set(B) & set(M))
    agree = [q for q in both if A[q] == B[q]]
    ties = len(both) - len(agree)
    print(f"\nA==B 无歧义子集: {len(agree)}/{len(both)} ({len(agree)/len(both):.1%})"
          f";分歧 {ties} 题(单独报,不进混淆矩阵)")
    if agree:
        H = {q: A[q] for q in agree}
        kb, po, n = kappa_binary(H, M)
        print(f"  该子集 人类共识-模型: N={n}  二元一致率={po:.1%}  二元κ={kb:+.3f}"
              f"  加权κ={kappa_qw(H, M):+.3f}")
        O = [[0] * K for _ in range(K)]
        for q in agree:
            O[H[q]][M[q]] += 1
        print("  混淆矩阵 (行=人类共识, 列=模型):")
        print("         模型0  模型1  模型2  模型3  模型4")
        for i in range(K):
            print(f"    人{i}: " + "  ".join(f"{O[i][j]:5d}" for j in range(K)))

    # 分时期漂移 —— 按每位编码员分别算,不用共识
    def per(q):
        y = YM[q]
        return "post" if (int(y[:4]) * 12 + int(y[5:7]) - 1) >= 2022 * 12 + 11 else "pre"

    print("\n分时期 人-模型 二元一致率 (漂移检验;两期应相近):")
    for nm, d in [("人A", A), ("人B", B)]:
        for p in ("pre", "post"):
            qs = [q for q in d if q in M and per(q) == p]
            if qs:
                agr = sum(int(d[q] >= CUT) == int(M[q] >= CUT) for q in qs) / len(qs)
                print(f"  {nm}-模型 {p:4s}: N={len(qs):3d}  一致率={agr:.1%}")

    # 有机日期条目敏感性
    org = os.path.join(HERE, "organic_date_items.txt")
    if os.path.exists(org):
        qids = []
        for line in open(org, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#"):
                qids.append(int(line.split(",")[0]))
        if qids:
            A2 = {k: v for k, v in A.items() if k not in qids}
            B2 = {k: v for k, v in B.items() if k not in qids}
            print(f"\n[敏感性] 剔除 {len(qids)} 个含有机日期条目后:")
            report_pair("  人A-人B", A2, B2)
            report_pair("  人A-模型", A2, M)
            report_pair("  人B-模型", B2, M)
    return A, B


def main():
    run("_v2", "第二轮")


if __name__ == "__main__":
    main()
