# -*- coding: utf-8 -*-
"""C-1 preliminary — the asker-composition rival, tested without further API calls.

The blocking problem: the unauthenticated Stack Exchange quota (300/day) is
charged per IP, and this machine's egress IP is shared, so /users/{ids} is
unavailable and account creation dates cannot be fetched. Account age at
posting therefore cannot be computed yet.

What CAN be done exactly, with zero further API calls:

  Stack Overflow user_ids are assigned in registration order. Therefore, with
  T = max(user_id) among askers observed BEFORE the event month,

        user_id <= T  =>  that account registered before the event.

  This is exact, not an approximation: the user holding id T asked a question
  before the event, so they registered before the event, and every smaller id
  registered no later than they did.

  Restricting to askers with user_id <= T holds the asker population fixed at
  a set of accounts that all existed before ChatGPT. Inside that subsample the
  rival explanation -- "the inflow of novices dried up" -- cannot operate,
  because no post-event registrant is in it. If the dose-response survives
  there, the compositional-inflow story cannot be what produces it.

  Residual objection this does NOT answer (stated, not hidden): the subsample
  selects on accounts that were still active after the event, so it trades an
  inflow-composition concern for a survivor-composition one. The full test
  (account age at posting, all askers) needs the users endpoint.

Coverage caveat: only 4,200 of the 6,000 python questions have owners fetched,
and because ids were requested in chronological order these are months
2021-06..2024-11 -- the full 18-month pre-period plus 24 post months. The
panel is truncated, not randomly thinned, so the estimates below correspond to
the paper's Year-1-plus-Year-2 window, not to its full-panel headline.

Run:  python asker_cohort_prelim.py
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
OUT_JSON = os.path.join(HERE, "asker_cohort_prelim.json")
EVENT_YM = "2022-12"


def ym_int(y):
    a, b = y.split("-")
    return int(a) * 12 + int(b) - 1


EVENT = ym_int(EVENT_YM)
res = {}

lab = pd.read_csv(os.path.join(DATA, "question_labels.csv")).rename(columns={"score": "s"})
own = pd.read_csv(os.path.join(HERE, "asker_owner.csv")).drop_duplicates("question_id")
df = lab.merge(own, on="question_id", how="inner")
df["mi"] = df["ym"].map(ym_int)
df["post"] = (df["mi"] >= EVENT).astype(int)

print(f"merged N={len(df)}  months {df.ym.min()}..{df.ym.max()}  "
      f"pre={int((df.post==0).sum())} post={int((df.post==1).sum())}")

# ---- (a) resolution and whether it is non-random ------------------------
df["has_owner"] = df["owner_user_id"].notna()
ct = pd.crosstab(df["s"], df["has_owner"])
p_bin = stats.chi2_contingency(ct)[1] if ct.shape[1] > 1 else float("nan")
ct2 = pd.crosstab(df["post"], df["has_owner"])
p_per = stats.chi2_contingency(ct2)[1] if ct2.shape[1] > 1 else float("nan")
print(f"\n=== (a) owner resolution ===")
print(f"  resolved {int(df.has_owner.sum())}/{len(df)} = {df.has_owner.mean():.1%}")
if ct.shape[1] > 1:
    print(f"  by bin:    {(ct[True]/ct.sum(axis=1)).round(4).to_dict()}   chi2 p={p_bin:.4f}")
    print(f"  by period: {(ct2[True]/ct2.sum(axis=1)).round(4).to_dict()}   chi2 p={p_per:.4f}")
res["resolution"] = {"rate": float(df.has_owner.mean()), "p_by_bin": float(p_bin),
                     "p_by_period": float(p_per), "n": int(len(df))}

d = df[df["has_owner"]].copy()
d["uid"] = d["owner_user_id"].astype(np.int64)

# ---- (b) did the asker pool actually shift? ----------------------------
T = int(d.loc[d["post"] == 0, "uid"].max())
d["pre_registered"] = d["uid"] <= T
share_pre = d.loc[d.post == 0, "pre_registered"].mean()
share_post = d.loc[d.post == 1, "pre_registered"].mean()
print(f"\n=== (b) did the asker pool shift? ===")
print(f"  threshold T = max pre-period user_id = {T}")
print(f"  share of questions from pre-ChatGPT-registered accounts:")
print(f"    pre  {share_pre:.1%}   (100% by construction)")
print(f"    post {share_post:.1%}  -> {1-share_post:.1%} of post questions come from NEW accounts")
uid_pre, uid_post = d.loc[d.post == 0, "uid"], d.loc[d.post == 1, "uid"]
print(f"  median user_id: pre {uid_pre.median():,.0f} -> post {uid_post.median():,.0f}"
      f"  (higher = registered later)")
print(f"  Mann-Whitney p = {stats.mannwhitneyu(uid_pre, uid_post)[1]:.3g}")
res["pool_shift"] = {"T": T, "post_share_pre_registered": float(share_post),
                     "post_share_new_accounts": float(1 - share_post),
                     "median_uid_pre": float(uid_pre.median()),
                     "median_uid_post": float(uid_post.median())}

# ---- (c) is registration recency related to substitutability? ----------
rho, p_rho = stats.spearmanr(d["uid"], d["s"])
print(f"\n=== (c) registration recency vs substitutability ===")
print(f"  Spearman rho(user_id, s) = {rho:+.4f}, p = {p_rho:.3g}")
print(f"  mean s by whether the account is new (post-period questions only):")
pp = d[d.post == 1]
print(f"    pre-registered accounts : {pp[pp.pre_registered]['s'].mean():.3f}  (N={int(pp.pre_registered.sum())})")
print(f"    new accounts            : {pp[~pp.pre_registered]['s'].mean():.3f}  (N={int((~pp.pre_registered).sum())})")
res["recency_vs_s"] = {"spearman_rho": float(rho), "p": float(p_rho),
                       "mean_s_post_preReg": float(pp[pp.pre_registered]["s"].mean()),
                       "mean_s_post_new": float(pp[~pp.pre_registered]["s"].mean())}

# ---- (d) shift-share decomposition of the mean-s decline ---------------
# groups: pre-registered cohort terciles (fixed by the PRE-period id
# distribution, so the cut points cannot move with the treatment) + "new".
q1, q2 = d.loc[d.post == 0, "uid"].quantile([1/3, 2/3]).values
def grp(u):
    if u > T:   return "new"
    if u <= q1: return "cohort_old"
    if u <= q2: return "cohort_mid"
    return "cohort_recent"
d["g"] = d["uid"].map(grp)
order = ["cohort_old", "cohort_mid", "cohort_recent", "new"]

w_pre = d[d.post == 0].groupby("g").size().reindex(order).fillna(0); w_pre /= w_pre.sum()
w_pst = d[d.post == 1].groupby("g").size().reindex(order).fillna(0); w_pst /= w_pst.sum()
s_pre = d[d.post == 0].groupby("g")["s"].mean().reindex(order)
s_pst = d[d.post == 1].groupby("g")["s"].mean().reindex(order)
s_mid = ((s_pre.fillna(s_pst) + s_pst.fillna(s_pre)) / 2)
total = (w_pst * s_pst.fillna(0)).sum() - (w_pre * s_pre.fillna(0)).sum()
within = (((w_pre + w_pst) / 2) * (s_pst - s_pre).fillna(0)).sum()
between = ((w_pst - w_pre) * s_mid).sum()
print(f"\n=== (d) shift-share decomposition of the fall in mean s ===")
print(f"  cohort cuts (pre-period id terciles): {q1:,.0f} / {q2:,.0f} / T={T:,}")
print(f"  shares  pre : {w_pre.round(4).to_dict()}")
print(f"  shares  post: {w_pst.round(4).to_dict()}")
print(f"  mean s  pre : {s_pre.round(3).to_dict()}")
print(f"  mean s  post: {s_pst.round(3).to_dict()}")
print(f"  TOTAL change in mean s                     : {total:+.4f}")
print(f"  WITHIN  (same cohort asks less substitutable): {within:+.4f}  ({within/total*100:5.1f}%)")
print(f"  BETWEEN (the cohort mix changed = the rival) : {between:+.4f}  ({between/total*100:5.1f}%)")
res["decomposition"] = {"total": float(total), "within": float(within), "between": float(between),
                        "within_share": float(within/total), "between_share": float(between/total),
                        "cuts": [float(q1), float(q2), float(T)],
                        "w_pre": w_pre.round(5).to_dict(), "w_post": w_pst.round(5).to_dict(),
                        "s_pre": s_pre.round(4).to_dict(), "s_post": s_pst.round(4).to_dict()}

# ---- (e) the paper's dose-response, on a fixed pre-registered population
print(f"\n=== (e) dose-response (paper's spec) on subsamples ===")
d4 = d[d["s"].between(1, 4)].copy()

def dose(sub, label):
    pan = sub.groupby(["ym", "s"]).size().rename("n").reset_index()
    idx = pd.MultiIndex.from_product([sorted(sub["ym"].unique()), [1, 2, 3, 4]], names=["ym", "s"])
    pan = pan.set_index(["ym", "s"]).reindex(idx, fill_value=0).reset_index()
    pan["post"] = (pan["ym"].map(ym_int) >= EVENT).astype(int)
    pan["sxpost"] = pan["s"] * pan["post"]
    zero = float((pan["n"] == 0).mean())
    ols = pan[pan["n"] > 0].copy(); ols["logn"] = np.log(ols["n"])
    mo = smf.ols("logn ~ sxpost + C(s) + C(ym)", data=ols).fit(
        cov_type="cluster", cov_kwds={"groups": ols["ym"]})
    mp = smf.poisson("n ~ sxpost + C(s) + C(ym)", data=pan).fit(
        disp=0, cov_type="cluster", cov_kwds={"groups": pan["ym"]})
    print(f"  {label:34s} N={len(sub):5d}  zeros={zero:5.1%}")
    print(f"      log-OLS gamma={mo.params['sxpost']:+.4f} (SE {mo.bse['sxpost']:.4f}) "
          f"p={mo.pvalues['sxpost']:.3g}   s4/s1={math.exp(3*mo.params['sxpost'])-1:+.1%}")
    print(f"      PPML    gamma={mp.params['sxpost']:+.4f} (SE {mp.bse['sxpost']:.4f}) "
          f"p={mp.pvalues['sxpost']:.3g}")
    return {"n": int(len(sub)), "zero_share": zero,
            "ols_gamma": float(mo.params["sxpost"]), "ols_se": float(mo.bse["sxpost"]),
            "ols_p": float(mo.pvalues["sxpost"]),
            "ppml_gamma": float(mp.params["sxpost"]), "ppml_se": float(mp.bse["sxpost"]),
            "ppml_p": float(mp.pvalues["sxpost"])}

res["dose"] = {}
res["dose"]["all_with_owner"] = dose(d4, "all askers (truncated panel)")
res["dose"]["pre_registered_only"] = dose(d4[d4["pre_registered"]],
                                          "pre-ChatGPT-registered accounts ONLY")
for g_ in ["cohort_old", "cohort_mid", "cohort_recent"]:
    res["dose"][g_] = dose(d4[d4["g"] == g_], f"  of which {g_}")

# ---- (e2) pooled PPML with cohort-x-month FE ---------------------------
print(f"\n=== (e2) pooled PPML with cohort-x-month FE (absorbs the rival's shock) ===")
sub = d4[d4["pre_registered"]]
pan = sub.groupby(["ym", "s", "g"]).size().rename("n").reset_index()
idx = pd.MultiIndex.from_product([sorted(sub["ym"].unique()), [1, 2, 3, 4],
                                  ["cohort_old", "cohort_mid", "cohort_recent"]],
                                 names=["ym", "s", "g"])
pan = pan.set_index(["ym", "s", "g"]).reindex(idx, fill_value=0).reset_index()
pan["post"] = (pan["ym"].map(ym_int) >= EVENT).astype(int)
pan["sxpost"] = pan["s"] * pan["post"]
pan["gm"] = pan["g"] + "_" + pan["ym"]
print(f"  cells={len(pan)}, zero cells={(pan['n']==0).mean():.1%}")
m1 = smf.poisson("n ~ sxpost + C(s):C(g) + C(gm)", data=pan).fit(
    disp=0, cov_type="cluster", cov_kwds={"groups": pan["ym"]})
print(f"  PPML gamma, cohort-x-month FE = {m1.params['sxpost']:+.4f} "
      f"(SE {m1.bse['sxpost']:.4f}), p = {m1.pvalues['sxpost']:.3g}")
m2 = smf.poisson("n ~ sxpost + C(s) + C(ym)", data=pan).fit(
    disp=0, cov_type="cluster", cov_kwds={"groups": pan["ym"]})
print(f"  PPML gamma, plain month FE (same cells) = {m2.params['sxpost']:+.4f} "
      f"(SE {m2.bse['sxpost']:.4f}), p = {m2.pvalues['sxpost']:.3g}")
res["pooled"] = {"cohort_month_fe": {"gamma": float(m1.params["sxpost"]), "se": float(m1.bse["sxpost"]),
                                     "p": float(m1.pvalues["sxpost"])},
                 "plain_month_fe": {"gamma": float(m2.params["sxpost"]), "se": float(m2.bse["sxpost"]),
                                    "p": float(m2.pvalues["sxpost"])}}

json.dump(res, open(OUT_JSON, "w", encoding="utf-8"), indent=2, default=float)
print(f"\nwritten: {OUT_JSON}")
