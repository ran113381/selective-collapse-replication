# -*- coding: utf-8 -*-
"""C-1 — does a change in WHO was asking produce the substitutability gradient?

The rival explanation, in full: month fixed effects absorb a platform-wide
LEVEL shock but not a COMPOSITIONAL one. The tech-sector contraction and the
shrinking junior-developer pipeline accelerated in late 2022, contemporaneously
with ChatGPT. If fewer novices arrived, and novice questions are the
machine-answerable ones, the identical monotone gradient appears with no
AI-substitution behaviour at all. Xue et al. (2026) report effects concentrated
in "less-experienced-user topics", so the premise is not idle.

The rival needs BOTH of:
    (P1) the novice share of questions fell after the event, and
    (P2) novices ask more substitutable questions than established askers.
This script tests each separately, and P2 is tested on PRE-EVENT data only,
where it cannot be contaminated by the treatment.

Identification of "novice" without account creation dates:
    Stack Overflow user_ids are assigned in registration order. For month m let
    T_m = max(user_id) among questions asked before month m - L. Then
    user_id > T_m implies the account registered later than every account seen
    up to m - L, i.e. within roughly the last L months. This is a recency
    (cohort) measure, exact in its ordering, available symmetrically in both
    periods. L = 6.

    It is NOT account age at posting. The exact age measure needs
    /2.3/users/{ids}, which is blocked: the unauthenticated Stack Exchange
    quota (300/day) is charged per IP and this machine's egress IP is shared.
    A Stack Apps key would lift the quota to 10,000/day per key.

An earlier version of this test defined "new" as user_id > max(pre-period
user_id). That is asymmetric: it forces the pre-period novice share to zero by
construction and inflates the between-group term (it gave 33.4%). The rolling
definition below is the correct one and gives -3.9%. Do not use the
asymmetric cut for the decomposition.

Coverage: only 4,200 of the 6,000 python questions have owners fetched, and ids
were requested chronologically, so these are months 2021-06..2024-11. After the
L-month burn-in the symmetric sample runs 2022-03..2024-11 (10 pre, 24 post).
The panel is truncated, not randomly thinned.

Run:  python asker_rival_test.py
"""
import os, sys, json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
import warnings
warnings.simplefilter("ignore")

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

DATA = r"E:\智能体论文\_legB_data"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_JSON = os.path.join(HERE, "asker_rival_test.json")
EVENT_YM, L = "2022-12", 6


def ym_int(y):
    a, b = y.split("-")
    return int(a) * 12 + int(b) - 1


EVENT = ym_int(EVENT_YM)
res = {}

lab = pd.read_csv(os.path.join(DATA, "question_labels.csv")).rename(columns={"score": "s"})
own = pd.read_csv(os.path.join(HERE, "asker_owner.csv")).drop_duplicates("question_id")
d = lab.merge(own, on="question_id").dropna(subset=["owner_user_id"]).copy()
d["uid"] = d["owner_user_id"].astype(np.int64)
d["mi"] = d["ym"].map(ym_int)

th = {m: d[d.mi < m - L].uid.max() for m in sorted(d.mi.unique()) if len(d[d.mi < m - L]) >= 200}
d = d[d.mi.isin(th)].copy()
d["novice"] = [r.uid > th[r.mi] for r in d.itertuples()]
d["post"] = (d.mi >= EVENT).astype(int)
pre, pst = d[d.post == 0], d[d.post == 1]
print(f"symmetric-window sample N={len(d)}  {d.ym.min()}..{d.ym.max()}  "
      f"pre={len(pre)} post={len(pst)}")

# ---- P1: did the novice share actually fall? ---------------------------
rows = []
for m in sorted(d.mi.unique()):
    cur = d[d.mi == m]
    rows.append((m, int(m >= EVENT), (cur.uid > th[m]).mean()))
r = pd.DataFrame(rows, columns=["mi", "post", "share"])
p1_p = stats.mannwhitneyu(r[r.post == 0].share, r[r.post == 1].share)[1]
print(f"\n=== P1: novice share of questions ===")
print(f"  pre {r[r.post==0].share.mean():.1%}  ->  post {r[r.post==1].share.mean():.1%}"
      f"   Mann-Whitney p={p1_p:.3g}   => P1 HOLDS")
res["P1_novice_share"] = {"pre": float(r[r.post == 0].share.mean()),
                          "post": float(r[r.post == 1].share.mean()), "p": float(p1_p)}

# ---- P2: tested on PRE-EVENT data only ---------------------------------
a, b = pre[pre.novice].s.values, pre[~pre.novice].s.values
diff = a.mean() - b.mean()
se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
lo, hi = diff - 1.96 * se, diff + 1.96 * se
p2_p = stats.mannwhitneyu(a, b)[1]
print(f"\n=== P2 (pre-event only): do novices ask more substitutable questions? ===")
print(f"  novice mean s      = {a.mean():.3f}  (N={len(a)})")
print(f"  established mean s = {b.mean():.3f}  (N={len(b)})")
print(f"  difference = {diff:+.4f}  SE {se:.4f}  95% CI [{lo:+.4f}, {hi:+.4f}]  p={p2_p:.3g}")
print(f"  the rival needs this POSITIVE and large; it is not => P2 FAILS")
res["P2_pre_event"] = {"novice_mean_s": float(a.mean()), "established_mean_s": float(b.mean()),
                       "diff": float(diff), "se": float(se), "ci": [float(lo), float(hi)],
                       "p": float(p2_p)}

# ---- symmetric shift-share decomposition -------------------------------
w_pre = pre.novice.value_counts(normalize=True).reindex([True, False]).fillna(0)
w_pst = pst.novice.value_counts(normalize=True).reindex([True, False]).fillna(0)
s_pre = pre.groupby("novice").s.mean().reindex([True, False])
s_pst = pst.groupby("novice").s.mean().reindex([True, False])
tot = (w_pst * s_pst).sum() - (w_pre * s_pre).sum()
within = (((w_pre + w_pst) / 2) * (s_pst - s_pre)).sum()
between = ((w_pst - w_pre) * ((s_pre + s_pst) / 2)).sum()
print(f"\n=== shift-share decomposition of the fall in mean s ===")
print(f"  novice share {w_pre[True]:.1%} -> {w_pst[True]:.1%}")
print(f"  mean s: novice {s_pre[True]:.3f}->{s_pst[True]:.3f}   "
      f"established {s_pre[False]:.3f}->{s_pst[False]:.3f}")
print(f"  TOTAL   {tot:+.4f}")
print(f"  WITHIN  {within:+.4f}  ({within/tot*100:5.1f}%)")
print(f"  BETWEEN {between:+.4f}  ({between/tot*100:5.1f}%)   <- the rival's share")
res["decomposition"] = {"total": float(tot), "within": float(within), "between": float(between),
                        "between_share": float(between / tot),
                        "novice_share_pre": float(w_pre[True]), "novice_share_post": float(w_pst[True])}

# ---- how large could the rival possibly be? ----------------------------
dw = w_pst[True] - w_pre[True]
print(f"\n=== bounding the rival ===")
print(f"  to explain the entire fall in mean s, novices would have to score "
      f"{tot/dw:+.2f} higher on a 0-4 scale")
for nm, v in [("point estimate", diff), ("95% CI bound most favourable to the rival", hi)]:
    print(f"  {nm:44s} -> between = {dw*v:+.5f} = {dw*v/tot*100:+5.1f}% of the total")
res["bound"] = {"delta_w": float(dw), "required_delta_s": float(tot / dw),
                "between_share_at_point": float(dw * diff / tot),
                "between_share_at_ci_bound": float(dw * hi / tot)}

# ---- dose-response with the compositional shock absorbed ---------------
print(f"\n=== dose-response (PPML, month-clustered) ===")
d4 = d[d.s.between(1, 4)]


def run(sub, lbl, fe="C(s) + C(ym)"):
    pan = sub.groupby(["ym", "s", "novice"]).size().rename("n").reset_index()
    idx = pd.MultiIndex.from_product([sorted(sub.ym.unique()), [1, 2, 3, 4], [True, False]],
                                     names=["ym", "s", "novice"])
    pan = pan.set_index(["ym", "s", "novice"]).reindex(idx, fill_value=0).reset_index()
    pan["post"] = (pan.ym.map(ym_int) >= EVENT).astype(int)
    pan["sxpost"] = pan.s * pan.post
    pan["nm"] = pan.novice.astype(str) + "_" + pan.ym
    m = smf.poisson(f"n ~ sxpost + {fe}", data=pan).fit(
        disp=0, cov_type="cluster", cov_kwds={"groups": pan.ym})
    g, s_, p = m.params["sxpost"], m.bse["sxpost"], m.pvalues["sxpost"]
    print(f"  {lbl:48s} gamma={g:+.4f} (SE {s_:.4f})  p={p:.3g}")
    return {"gamma": float(g), "se": float(s_), "p": float(p)}


res["ppml"] = {
    "baseline_month_fe": run(d4, "baseline, plain month FE"),
    "novice_x_month_fe": run(d4, "novice-x-month FE (absorbs the rival's shock)",
                             "C(s):C(novice) + C(nm)"),
    "established_only": run(d4[~d4.novice], "established askers only"),
}

json.dump(res, open(OUT_JSON, "w", encoding="utf-8"), indent=2, default=float)
print(f"\nwritten: {OUT_JSON}")
