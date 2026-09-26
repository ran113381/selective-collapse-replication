# -*- coding: utf-8 -*-
"""金标准 κ 计算:人-人 与 人-模型(二元 GEN/VER + 二次加权 0-4)。
用法: python score_gold.py   (需 coding_sheet_A/B.csv 已填完)"""
import csv

def load(path, col):
    d = {}
    for r in csv.DictReader(open(path, encoding="utf-8-sig")):
        v = r[col].strip()
        if v != "":
            d[int(r["order"])] = int(v)
    return d

def kappa_binary(x, y, cut=3):
    ks = sorted(set(x) & set(y))
    a = [int(x[k] >= cut) for k in ks]; b = [int(y[k] >= cut) for k in ks]
    n = len(ks); po = sum(i == j for i, j in zip(a, b)) / n
    pa1 = sum(a) / n; pb1 = sum(b) / n
    pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    return (po - pe) / (1 - pe), po, n

def kappa_qw(x, y, K=5):
    ks = sorted(set(x) & set(y)); n = len(ks)
    O = [[0] * K for _ in range(K)]
    for k in ks:
        O[x[k]][y[k]] += 1
    rx = [sum(O[i]) for i in range(K)]; ry = [sum(O[i][j] for i in range(K)) for j in range(K)]
    num = den = 0.0
    for i in range(K):
        for j in range(K):
            w = ((i - j) ** 2) / ((K - 1) ** 2)
            num += w * O[i][j]
            den += w * rx[i] * ry[j] / n
    return 1 - num / den, n

def confusion(x, y, K=5):
    ks = sorted(set(x) & set(y))
    O = [[0] * K for _ in range(K)]
    for k in ks:
        O[x[k]][y[k]] += 1
    return O

def within1(x, y):
    ks = sorted(set(x) & set(y))
    return sum(abs(x[k] - y[k]) <= 1 for k in ks) / len(ks)

def load_period(path):
    """order -> ym (year-month), for by-period drift check."""
    d = {}
    for r in csv.DictReader(open(path, encoding="utf-8-sig")):
        d[int(r["order"])] = r["ym"]
    return d

A = load("coding_sheet_A.csv", "score_0_4")
B = load("coding_sheet_B.csv", "score_0_4")
M = load("answer_key_封存勿开.csv", "model_score")
YM = load_period("answer_key_封存勿开.csv")

print("=" * 60)
print("金标准评分者信度 (人-人 / 人-模型)")
print("=" * 60)
for name, x, y in [("人A-人B", A, B), ("人A-模型", A, M), ("人B-模型", B, M)]:
    if not (set(x) & set(y)):
        print(f"{name}: [尚无重叠评分，编码完成后再运行]"); continue
    kb, po, n = kappa_binary(x, y)
    kw, _ = kappa_qw(x, y)
    w1 = within1(x, y)
    print(f"{name}: N={n}  二元κ={kb:.3f} (一致率{po:.1%})  加权κ={kw:.3f}  ±1一致率={w1:.1%}")

# 混淆矩阵 (人共识 vs 模型)：审稿人要求
if set(A) & set(B) & set(M):
    ks = sorted(set(A) & set(B) & set(M))
    # 人共识 = A,B 平均四舍五入(仅在 A==B 时无歧义；此处取 round(mean))
    H = {k: round((A[k] + B[k]) / 2) for k in ks}
    print("\n混淆矩阵 (行=人共识 0-4, 列=模型 0-4):")
    O = confusion(H, M)
    print("       模型0  模型1  模型2  模型3  模型4")
    for i in range(5):
        print(f"  人{i}: " + "  ".join(f"{O[i][j]:5d}" for j in range(5)))

    # 分时期一致性漂移检验 (ChatGPT 前/后)：分类器误差是否随处理期系统变化
    def cut(ym): return "post" if (int(ym[:4]) * 12 + int(ym[5:7]) - 1) >= 2022 * 12 + 11 else "pre"
    print("\n分时期 人-模型 二元一致 (漂移检验；两期应相近):")
    for per in ("pre", "post"):
        kk = [k for k in ks if cut(YM[k]) == per]
        agree = sum(int(H[k] >= 3) == int(M[k] >= 3) for k in kk) / len(kk) if kk else float("nan")
        print(f"  {per:4s}: N={len(kk):3d}  二元一致率={agree:.1%}")
    print("  [判读] 两期一致率差异大 => 分类器误差随处理期漂移，需在论文中报告并校正。")
else:
    print("\n[混淆矩阵与分时期漂移检验：需 A/B/模型三者齐备后运行]")
