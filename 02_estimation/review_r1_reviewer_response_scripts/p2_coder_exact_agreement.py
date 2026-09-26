# -*- coding: utf-8 -*-
u"""P2: agreement between the two coders beyond the reported kappa.

Reports (i) exact five-bin agreement over all 300 questions and (ii) the
coder-coder kappa without the first fifty questions of the shuffled sequence.
Coder A continued past those fifty only after they had been checked against
coder B's scores (main text Section 4.4), so they carry a mild upward selection;
(ii) is the reliability figure without them.

Self-check first: the binary kappa (0.533), raw binary agreement (76.7%) and
weighted kappa (0.609) that the manuscript reports must reproduce from the two
shipped sheets, or the script exits without writing anything.
Reads 03_validation/gold_standard/coding_sheet_A_v2.csv and coding_sheet_B_v2.csv.
"""
import io, json, os
import numpy as np
import pandas as pd

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOLD = os.path.join(PKG, "03_validation", "gold_standard")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "p2_coder_exact_agreement.json")


def kappa_binary(a, b):
    a, b = np.asarray(a) >= 3, np.asarray(b) >= 3
    po = (a == b).mean()
    pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    return (po - pe) / (1 - pe), po


def kappa_qw(a, b, K=5):
    O = np.zeros((K, K))
    for i, j in zip(a, b):
        O[i][j] += 1
    n = O.sum(); rx = O.sum(1); ry = O.sum(0)
    W = np.array([[((i - j) ** 2) / ((K - 1) ** 2) for j in range(K)] for i in range(K)])
    return 1 - (W * O).sum() / (W * np.outer(rx, ry) / n).sum()


A = pd.read_csv(os.path.join(GOLD, "coding_sheet_A_v2.csv"), encoding="utf-8-sig")
B = pd.read_csv(os.path.join(GOLD, "coding_sheet_B_v2.csv"), encoding="utf-8-sig")
m = A[["order", "question_id", "score_0_4"]].merge(
    B[["order", "question_id", "score_0_4"]], on="question_id", suffixes=("_A", "_B"))
assert (m.order_A == m.order_B).all(), "the two sheets do not share the presentation order"
m = m.sort_values("order_A")
sa, sb = m.score_0_4_A.astype(int).to_numpy(), m.score_0_4_B.astype(int).to_numpy()
n = len(m)
kb, po = kappa_binary(sa, sb)
kw = kappa_qw(sa, sb)
exact5 = float((sa == sb).mean())
tail = (m.order_A > 50).to_numpy()
kb_t, _ = kappa_binary(sa[tail], sb[tail])
kw_t = kappa_qw(sa[tail], sb[tail])

print("N = %d" % n)
print("binary kappa   = %.4f   (manuscript 0.533)" % kb)
print("binary raw     = %.4f   (manuscript 0.767)" % po)
print("weighted kappa = %.4f   (manuscript 0.609)" % kw)
assert n == 300
assert round(kb, 3) == 0.533 and round(po, 3) == 0.767 and round(kw, 3) == 0.609, \
    "reported figures do not reproduce; wrong files"
print("self-check passed")
print("exact five-bin agreement, all 300 = %.4f" % exact5)
print("without the first fifty (N = %d): binary kappa %.4f, weighted kappa %.4f" % (tail.sum(), kb_t, kw_t))

out = {
    "note": "Agreement between coders A and B beyond the reported kappa: exact five-bin "
            "agreement over all 300 questions, and kappa without the first fifty questions "
            "of the shuffled sequence (the segment checked before coder A continued).",
    "sources": {"coder_A": "coding_sheet_A_v2.csv", "coder_B": "coding_sheet_B_v2.csv"},
    "n": n,
    "reproduced_from_manuscript": {"binary_kappa": round(kb, 4), "binary_raw_agreement": round(po, 4),
                                   "weighted_kappa": round(kw, 4)},
    "exact_five_bin_agreement_all_300": round(exact5, 4),
    "without_first_fifty": {"n": int(tail.sum()), "binary_kappa": round(kb_t, 4),
                            "weighted_kappa": round(kw_t, 4)},
    "bin_usage_coder_A": {int(k): int(v) for k, v in zip(*np.unique(sa, return_counts=True))},
    "bin_usage_coder_B": {int(k): int(v) for k, v in zip(*np.unique(sb, return_counts=True))},
    "both_use_all_five_bins": bool(len(set(sa.tolist())) == 5 and len(set(sb.tolist())) == 5),
}
io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
print("written " + OUT)
