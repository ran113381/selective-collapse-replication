# -*- coding: utf-8 -*-
"""Section 7.5 of the manuscript: the relabelling bound on both samples.

`bin_stability_test.py` computes the bound on 5,640 questions: it drops the 45
questions whose creation timestamp was not recovered and the panel's final three
months. The ninety-day closure window does not require the second drop, since
every question satisfies it. This script computes the same bound on that sample
and on the 5,930 questions that keep the final three months, so that both can be
reported.

It first reproduces every figure this section prints for the 5,640-question sample and
stops if any differs; only then does it print the 5,930-question figures.
Reads only files in this package. Run from this directory.
"""
import math
import os
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
EV = 2022 * 12 + 11                      # December 2022


def ymi(y):
    a, b = y.split("-")
    return int(a) * 12 + int(b) - 1


lab = pd.read_csv(os.path.join(PKG, "01_panels_and_classification", "data",
                               "question_labels_python_2021-2024.csv"))
assert len(lab) == 6000 and lab.question_id.nunique() == 6000
clo = pd.read_csv(os.path.join(HERE, "closure_meta.csv")).rename(columns={"score": "so_score"})
own = pd.read_csv(os.path.join(HERE, "asker_owner.csv")).drop_duplicates("question_id")[["question_id", "q_creation"]]

dd = lab.rename(columns={"score": "s"}).merge(clo, on="question_id", how="left").merge(own, on="question_id", how="left")
dd["mi"] = dd.ym.map(ymi)
dd["post"] = (dd.mi >= EV).astype(int)
dd["dtc"] = (dd.closed_date - dd.q_creation) / 86400.0
dd["dup"] = ((dd.closed_reason == "Duplicate") & (dd.dtc <= 90)).astype(int)
assert int(dd.q_creation.isna().sum()) == 45


def bound(full):
    """Migrant fraction implied by each tracer, with s4 as the common-shift counterfactual."""
    tab = {}
    for b in (1, 2, 3, 4):
        a_ = full[(full.s == b) & (full.post == 0)]["dup"]
        c_ = full[(full.s == b) & (full.post == 1)]["dup"]
        tab[b] = dict(pre=a_.mean(), post=c_.mean(), n_post=len(c_))
    sh0 = full[full.post == 0].s.value_counts(normalize=True).sort_index()
    sh1 = full[full.post == 1].s.value_counts(normalize=True).sort_index()
    gain = {b: max(sh1[b] - sh0[b], 0.0) for b in (1, 2, 3, 4)}
    loss = {b: max(sh0[b] - sh1[b], 0.0) for b in (1, 2, 3, 4)}
    tl = sum(loss.values())
    donor = sum(loss[b] * tab[b]["pre"] for b in (1, 2, 3, 4)) / tl
    delta = tab[4]["post"] - tab[4]["pre"]
    out = dict(n=len(full), donor_dup=donor)
    for b in (1, 2):
        obs = tab[b]["post"]
        se = math.sqrt(obs * (1 - obs) / tab[b]["n_post"])
        den = donor - tab[b]["pre"]
        out["s%d_need" % b] = gain[b] / sh1[b]
        out["s%d_close_hi" % b] = (obs + 1.96 * se - (tab[b]["pre"] + delta)) / den
    apre = {b: full[(full.s == b) & (full.post == 0)].answer_count for b in (1, 2, 3, 4)}
    apst = {b: full[(full.s == b) & (full.post == 1)].answer_count for b in (1, 2, 3, 4)}
    adon = sum(loss[b] * apre[b].mean() for b in (1, 2, 3, 4)) / tl
    dans = apst[4].mean() - apre[4].mean()
    for b in (1, 2):
        obs = apst[b].mean()
        se = apst[b].std(ddof=1) / math.sqrt(len(apst[b]))
        den = adon - apre[b].mean()
        hi = (obs + 1.96 * se - (apre[b].mean() + dans)) / den
        out["s%d_ans_hi" % b] = hi
        out["s%d_ans_share" % b] = max(hi, 0.0) / out["s%d_need" % b]
    return out


base = dd[dd.q_creation.notna() & dd.s.between(1, 4)]
trim = base[base.mi <= dd.mi.max() - math.ceil(90 / 30.0)]
t, u = bound(trim), bound(base)

# ---- the 5,640-question figures printed in the manuscript (Section 7.5) must reproduce first ----
assert t["n"] == 5640, t["n"]
assert round(100 * t["s1_close_hi"], 1) == 15.7 and round(100 * t["s2_close_hi"], 1) == 13.1
assert round(100 * t["s1_ans_hi"], 1) == 2.4 and round(100 * t["s2_ans_hi"], 1) == 2.0
assert round(100 * t["s1_ans_share"]) == 6 and round(100 * t["s2_ans_share"]) == 9
assert u["n"] == 5930, u["n"]

for label, r in (("final three months dropped", t), ("final three months kept", u)):
    print("Sample of %s (%s) questions" % (format(r["n"], ","), label))
    print("  closure tracer, 95%% upper bound on migrant fraction: s1 %.1f%%, s2 %.1f%%"
          % (100 * r["s1_close_hi"], 100 * r["s2_close_hi"]))
    print("  answer tracer,  95%% upper bound on migrant fraction: s1 %.1f%%, s2 %.1f%%"
          % (100 * r["s1_ans_hi"], 100 * r["s2_ans_hi"]))
    print("  share of the gain the answer tracer leaves to relabelling: s1 %.0f%%, s2 %.0f%%"
          % (100 * r["s1_ans_share"], 100 * r["s2_ans_share"]))
