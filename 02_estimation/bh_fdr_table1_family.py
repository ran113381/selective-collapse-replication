# -*- coding: utf-8 -*-
"""Benjamini-Hochberg FDR across the confirmatory family reported in Section 7.2
and Table 7 of the manuscript.

The family is the six estimates of Table 2 of the manuscript: the three language
dose-responses (log-count OLS), the python binary contrast, and the python
fixed-total FE-PPML and Newey-West share-ratio estimators. The p values are the
ones printed in Table 2. Where the table prints a bound (< .001)
the bound is used; BH q values are monotone in p, so each q printed below is an
upper bound on the exact one.

(The BH block inside phaseA_composition.py is an earlier family: three PPML
estimates and the answer-margin snapshot. It is not the one Section 7.2 reports.)

Run:  python bh_fdr_table1_family.py
"""
P = {
    "python, log-count OLS": 1e-3,
    "javascript, log-count OLS": 1e-3,
    "java, log-count OLS": 0.019,
    "python, binary generative vs verification": 1e-3,
    "python, fixed-total FE-PPML": 1e-3,
    "python, Newey-West log(s4/s1)": 1e-3,
}


def bh(pvals):
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    q = [0.0] * m
    prev = 1.0
    for rank in range(m - 1, -1, -1):
        i = order[rank]
        prev = min(prev, pvals[i] * m / (rank + 1))
        q[i] = prev
    return q


if __name__ == "__main__":
    names = list(P)
    q = bh([P[k] for k in names])
    for k, v in zip(names, q):
        print("%-45s p <= %-8.2g q <= %.3g" % (k, P[k], v))
    print("largest q: %.3f" % max(q))
