# -*- coding: utf-8 -*-
"""C-1, definitive version: the asker-composition rival tested with the exact
pre-determined measure -- account age at the moment of posting -- on the full
60-month panel.

Supersedes asker_rival_test.py (user_id recency proxy, truncated panel) and
asker_cohort_prelim.py. Those were written while the Stack Exchange quota was
exhausted on a shared egress IP and only 4,200 of 6,000 owners could be
fetched. Both are kept for provenance; neither should be quoted.

The rival needs BOTH of:
    (P1) the novice share of askers fell after the event, and
    (P2) novices ask more substitutable questions than established askers.
P2 is tested on PRE-EVENT data only, where the treatment cannot contaminate it.

"Novice" = account less than 365 days old when the question was posted. Account
age is question.creation_date - user.creation_date, both fixed before the
question exists, so the measure is pre-determined. owner.reputation is a
current snapshot contaminated by post-treatment accumulation and is never used.

Run:  python asker_rival_exact.py
"""
import os, sys, json, math
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
import warnings
warnings.simplefilter("ignore")

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
DATA = r"E:\智能体论文\_legB_data"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "asker_rival_exact.json")
EVENT_YM, NOVICE_DAYS = "2022-12", 365


def ym_int(y):
    a, b = y.split("-")
    return int(a) * 12 + int(b) - 1


EVENT = ym_int(EVENT_YM)
res = {}

lab = pd.read_csv(os.path.join(DATA, "question_labels.csv")).rename(columns={"score": "s"})
own = pd.read_csv(os.path.join(HERE, "asker_owner.csv")).drop_duplicates("question_id")
usr = pd.read_csv(os.path.join(HERE, "asker_users.csv")).drop_duplicates("user_id")
df = lab.merge(own, on="question_id", how="left").merge(
    usr, left_on="owner_user_id", right_on="user_id", how="left")
df["mi"] = df["ym"].map(ym_int)
df["post"] = (df["mi"] >= EVENT).astype(int)

# ---- resolution and its randomness -------------------------------------
df["resolved"] = df["u_creation"].notna() & df["q_creation"].notna()
ct, ct2 = pd.crosstab(df["s"], df["resolved"]), pd.crosstab(df["post"], df["resolved"])
p_bin = stats.chi2_contingency(ct)[1] if ct.shape[1] > 1 else float("nan")
p_per = stats.chi2_contingency(ct2)[1] if ct2.shape[1] > 1 else float("nan")
print(f"=== resolution ===")
print(f"  {int(df.resolved.sum())}/{len(df)} = {df.resolved.mean():.1%}"
      f"   chi2 by bin p={p_bin:.3f}, by period p={p_per:.3f}")
res["resolution"] = {"n": int(len(df)), "resolved": int(df.resolved.sum()),
                     "rate": float(df.resolved.mean()),
                     "p_by_bin": float(p_bin), "p_by_period": float(p_per)}

d = df[df.resolved].copy()
d["tenure_days"] = (d["q_creation"] - d["u_creation"]) / 86400.0
d = d[d["tenure_days"] >= 0].copy()
d["novice"] = d["tenure_days"] < NOVICE_DAYS
pre, pst = d[d.post == 0], d[d.post == 1]
print(f"  usable {len(d)}   pre {len(pre)} / post {len(pst)}"
      f"   months {d.ym.min()}..{d.ym.max()}")
res["n_usable"] = int(len(d))

# ---- P1 -----------------------------------------------------------------
w0, w1 = pre.novice.mean(), pst.novice.mean()
p1 = stats.mannwhitneyu(pre.tenure_days, pst.tenure_days)[1]
print(f"\n=== P1: did the novice share fall? ===")
print(f"  accounts <1y old at posting: {w0:.1%} -> {w1:.1%}")
print(f"  median account age: {pre.tenure_days.median():.0f}d -> {pst.tenure_days.median():.0f}d"
      f"   Mann-Whitney p={p1:.3g}   => P1 HOLDS")
res["P1"] = {"novice_share_pre": float(w0), "novice_share_post": float(w1),
             "median_days_pre": float(pre.tenure_days.median()),
             "median_days_post": float(pst.tenure_days.median()), "p": float(p1)}

# ---- P2, on pre-event data only ----------------------------------------
a = pre[pre.novice].s.values
b = pre[~pre.novice].s.values
diff = a.mean() - b.mean()
se = math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
lo, hi = diff - 1.96 * se, diff + 1.96 * se
p2 = stats.mannwhitneyu(a, b)[1]
print(f"\n=== P2 (pre-event only): do novices ask more substitutable questions? ===")
print(f"  novice      mean s = {a.mean():.3f}  (N={len(a)})")
print(f"  established mean s = {b.mean():.3f}  (N={len(b)})")
print(f"  difference = {diff:+.4f}  SE {se:.4f}  95% CI [{lo:+.4f}, {hi:+.4f}]  p={p2:.3g}")
print(f"  the rival needs this POSITIVE and large => P2 FAILS")
res["P2"] = {"novice_mean_s": float(a.mean()), "n_novice": int(len(a)),
             "established_mean_s": float(b.mean()), "n_established": int(len(b)),
             "diff": float(diff), "se": float(se), "ci": [float(lo), float(hi)], "p": float(p2)}

# ---- shift-share --------------------------------------------------------
s_pre = pre.groupby("novice").s.mean().reindex([True, False])
s_pst = pst.groupby("novice").s.mean().reindex([True, False])
wp = pd.Series({True: w0, False: 1 - w0})
wq = pd.Series({True: w1, False: 1 - w1})
tot = (wq * s_pst).sum() - (wp * s_pre).sum()
within = (((wp + wq) / 2) * (s_pst - s_pre)).sum()
between = ((wq - wp) * ((s_pre + s_pst) / 2)).sum()
print(f"\n=== shift-share decomposition of the fall in mean s ===")
print(f"  mean s: novice {s_pre[True]:.3f}->{s_pst[True]:.3f}   "
      f"established {s_pre[False]:.3f}->{s_pst[False]:.3f}")
print(f"  TOTAL   {tot:+.4f}")
print(f"  WITHIN  {within:+.4f}  ({within/tot*100:5.1f}%)")
print(f"  BETWEEN {between:+.4f}  ({between/tot*100:5.1f}%)   <- the rival's share")
dw = w1 - w0
print(f"\n=== bounding the rival ===")
print(f"  to carry the whole fall on asker mix, novices would have to score "
      f"{tot/dw:+.2f} higher on a 0-4 scale")
for nm, v in (("point estimate", diff), ("95% CI bound most favourable to it", hi)):
    print(f"  {nm:38s} -> between = {dw*v:+.5f} = {dw*v/tot*100:+5.1f}% of the total")
res["decomposition"] = {"total": float(tot), "within": float(within), "between": float(between),
                        "between_share": float(between / tot), "delta_w": float(dw),
                        "required_delta_s": float(tot / dw),
                        "between_share_at_ci": float(dw * hi / tot)}

# ---- dose-response with the compositional shock absorbed ----------------
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
    print(f"  {lbl:46s} gamma={g:+.4f} (SE {s_:.4f})  p={p:.3g}")
    return {"gamma": float(g), "se": float(s_), "p": float(p)}


res["ppml"] = {
    "baseline_month_fe": run(d4, "baseline, plain month FE"),
    "novice_x_month_fe": run(d4, "novice-by-month FE (absorbs the rival's shock)",
                             "C(s):C(novice) + C(nm)"),
    "established_only": run(d4[~d4.novice], "established askers only"),
    "novice_only": run(d4[d4.novice], "novice askers only"),
}

json.dump(res, open(OUT, "w", encoding="utf-8"), indent=2, default=float)
print(f"\nwritten: {OUT}")
