# -*- coding: utf-8 -*-
"""C-1 — the asker-composition rival explanation.

The referee's strongest counter-argument: month fixed effects absorb a
platform-wide LEVEL shock but not a COMPOSITIONAL one. The tech-sector
contraction and the shrinking junior-developer pipeline accelerated in late
2022, contemporaneously with ChatGPT. If fewer novices entered the platform,
and machine-answerable questions are disproportionately novice questions --
a correlation the paper's own cited Xue et al. (2026) reports, finding effects
concentrated in "less-experienced-user topics" -- then the identical monotone
gradient appears with no AI-substitution behaviour whatsoever.

Every validity check in the paper survives this rival unchanged: the four
answerers' monotone solve rates, cross-family agreement, and the moderators'
duplicate-closure gradient are all equally consistent with "fewer novices".
The criterion tests prove the rubric measures machine-answerability; they
cannot separate the two stories, because novice questions ARE the
machine-answerable ones.

Design:
  * Re-fetches owner for all 6,000 python question ids via /2.3/questions/{ids}
    (100/batch, ~60 calls), then account creation_date for the unique owners
    via /2.3/users/{ids} (100/batch). RESUMABLE: appends to CSV, skips done ids.
  * MEASUREMENT CAVEAT, enforced here: owner.reputation is a CURRENT snapshot,
    contaminated by post-treatment accumulation, and is NOT used as a control.
    The pre-determined variable is account age AT THE MOMENT OF POSTING,
    = question.creation_date - user.creation_date, which is fixed at the time
    the question is asked and cannot be moved by the treatment.
  * Reports:
      (a) owner resolution rate, and whether non-resolution is non-random
          across bins and across pre/post (chi-square), per the paper's own
          discipline on the GLM-5.3 attrition;
      (b) whether the asker pool actually shifted: tenure distribution
          pre vs post;
      (c) whether tenure and substitutability are related at all -- if they
          are not, the rival is dead on arrival;
      (d) SHIFT-SHARE DECOMPOSITION of the fall in mean substitutability into
          a WITHIN-stratum component (same-tenure askers ask fewer
          machine-answerable questions) and a BETWEEN-stratum component
          (the tenure mix changed). The rival explanation IS the between term;
      (e) the paper's own dose-response re-estimated WITHIN each tenure
          stratum, and pooled with a triple interaction s x post x stratum
          under month-x-stratum fixed effects, which absorb exactly the
          compositional shock the rival posits.

Run (needs network):  python asker_tenure.py
Nothing here mutates the manuscript.
"""
import os, sys, json, csv, time, math
import urllib.request, urllib.parse
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
import warnings
warnings.simplefilter("ignore")

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

DATA = r"E:\智能体论文\_legB_data"
HERE = os.path.dirname(os.path.abspath(__file__))
Q_CSV = os.path.join(HERE, "asker_owner.csv")     # question_id -> owner
U_CSV = os.path.join(HERE, "asker_users.csv")     # user_id -> account creation
OUT_JSON = os.path.join(HERE, "asker_tenure.json")

Q_API = "https://api.stackexchange.com/2.3/questions/{ids}"
U_API = "https://api.stackexchange.com/2.3/users/{ids}"
KEY = os.environ.get("STACK_API_KEY")
PAGESIZE = 100
SLEEP = 0.25
EVENT_YM = "2022-12"


def ym_int(y):
    a, b = y.split("-")
    return int(a) * 12 + int(b) - 1


EVENT = ym_int(EVENT_YM)


def api_get(url, params, tries=5):
    for k in range(tries):
        q = urllib.parse.urlencode(params)
        try:
            with urllib.request.urlopen(f"{url}?{q}", timeout=60) as r:
                d = json.loads(r.read().decode("utf-8"))
        except Exception as e:
            time.sleep(2 * (k + 1))
            continue
        if d.get("backoff"):
            time.sleep(int(d["backoff"]) + 1)
        if "error_id" in d:
            time.sleep(3 * (k + 1))
            continue
        return d
    return None


def chunks(xs, n):
    for i in range(0, len(xs), n):
        yield xs[i:i + n]


# ---------------------------------------------------------------- fetch: owners
def fetch_owners(ids):
    done = set()
    if os.path.exists(Q_CSV):
        done = set(pd.read_csv(Q_CSV)["question_id"].astype(int))
    todo = [i for i in ids if i not in done]
    print(f"[owners] have {len(done)}, need {len(todo)}")
    if not todo:
        return
    new = not os.path.exists(Q_CSV)
    f = open(Q_CSV, "a", newline="", encoding="utf-8")
    w = csv.writer(f)
    if new:
        w.writerow(["question_id", "q_creation", "owner_user_id", "owner_type", "owner_rep_snapshot"])
    for bi, batch in enumerate(chunks(todo, PAGESIZE)):
        p = {"site": "stackoverflow", "pagesize": PAGESIZE}
        if KEY:
            p["key"] = KEY
        d = api_get(Q_API.format(ids=";".join(map(str, batch))), p)
        if d is None:
            print(f"  [batch {bi}] FAILED, stopping (rerun to resume)")
            break
        got = set()
        for it in d.get("items", []):
            o = it.get("owner") or {}
            w.writerow([it["question_id"], it.get("creation_date"),
                        o.get("user_id", ""), o.get("user_type", ""),
                        o.get("reputation", "")])
            got.add(it["question_id"])
        for q in batch:                      # deleted questions return nothing
            if q not in got:
                w.writerow([q, "", "", "gone", ""])
        f.flush()
        if (bi + 1) % 10 == 0:
            print(f"  [owners] batch {bi+1}, quota_remaining={d.get('quota_remaining')}")
        time.sleep(SLEEP)
    f.close()


# ----------------------------------------------------------------- fetch: users
def fetch_users(uids):
    done = set()
    if os.path.exists(U_CSV):
        done = set(pd.read_csv(U_CSV)["user_id"].astype(int))
    todo = [u for u in uids if u not in done]
    print(f"[users] have {len(done)}, need {len(todo)}")
    if not todo:
        return
    new = not os.path.exists(U_CSV)
    f = open(U_CSV, "a", newline="", encoding="utf-8")
    w = csv.writer(f)
    if new:
        w.writerow(["user_id", "u_creation"])
    for bi, batch in enumerate(chunks(todo, PAGESIZE)):
        p = {"site": "stackoverflow", "pagesize": PAGESIZE}
        if KEY:
            p["key"] = KEY
        d = api_get(U_API.format(ids=";".join(map(str, batch))), p)
        if d is None:
            print(f"  [batch {bi}] FAILED, stopping (rerun to resume)")
            break
        got = set()
        for it in d.get("items", []):
            w.writerow([it["user_id"], it.get("creation_date")])
            got.add(it["user_id"])
        for u in batch:
            if u not in got:
                w.writerow([u, ""])
        f.flush()
        if (bi + 1) % 10 == 0:
            print(f"  [users] batch {bi+1}, quota_remaining={d.get('quota_remaining')}")
        time.sleep(SLEEP)
    f.close()


# ------------------------------------------------------------------------- main
def main():
    lab = pd.read_csv(os.path.join(DATA, "question_labels.csv"))
    lab = lab.rename(columns={"score": "s"})
    lab["question_id"] = lab["question_id"].astype(int)
    print(f"labels: N={len(lab)}, months {lab['ym'].min()}..{lab['ym'].max()}, "
          f"s in {sorted(lab['s'].unique())}")

    fetch_owners(lab["question_id"].tolist())
    own = pd.read_csv(Q_CSV)
    own["question_id"] = own["question_id"].astype(int)
    own = own.drop_duplicates("question_id")

    uids = sorted({int(u) for u in own["owner_user_id"].dropna() if str(u).strip() != ""})
    fetch_users(uids)
    usr = pd.read_csv(U_CSV).drop_duplicates("user_id")

    df = lab.merge(own, on="question_id", how="left")
    df = df.merge(usr, left_on="owner_user_id", right_on="user_id", how="left")
    df["mi"] = df["ym"].map(ym_int)
    df["post"] = (df["mi"] >= EVENT).astype(int)

    res = {}

    # ---- (a) resolution rate + non-random-attrition test -----------------
    df["resolved"] = df["u_creation"].notna() & df["q_creation"].notna()
    rr = df["resolved"].mean()
    print(f"\n=== (a) owner resolution ===\nresolved {df['resolved'].sum()}/{len(df)} = {rr:.1%}")
    ct = pd.crosstab(df["s"], df["resolved"])
    ct2 = pd.crosstab(df["post"], df["resolved"])
    p_bin = stats.chi2_contingency(ct)[1] if ct.shape[1] > 1 else float("nan")
    p_per = stats.chi2_contingency(ct2)[1] if ct2.shape[1] > 1 else float("nan")
    rate = lambda t: (t[True] / t.sum(axis=1)).round(4).to_dict() if True in t.columns else "all resolved"
    print(f"  by bin:    {rate(ct)}  chi2 p={p_bin:.4f}")
    print(f"  by period: {rate(ct2)}  chi2 p={p_per:.4f}")
    res["resolution"] = {"rate": rr, "p_by_bin": p_bin, "p_by_period": p_per,
                         "by_bin": (ct[True] / ct.sum(axis=1)).round(4).to_dict()}

    d = df[df["resolved"]].copy()
    d["tenure_days"] = (d["q_creation"] - d["u_creation"]) / 86400.0
    d = d[d["tenure_days"] >= 0]
    print(f"  usable after tenure>=0: {len(d)}")

    # ---- (b) did the asker pool actually shift? --------------------------
    pre, pst = d[d["post"] == 0], d[d["post"] == 1]
    print(f"\n=== (b) asker tenure, pre vs post ===")
    print(f"  pre  N={len(pre):5d}  mean={pre['tenure_days'].mean():7.1f}d  median={pre['tenure_days'].median():7.1f}d")
    print(f"  post N={len(pst):5d}  mean={pst['tenure_days'].mean():7.1f}d  median={pst['tenure_days'].median():7.1f}d")
    u_stat, p_mw = stats.mannwhitneyu(pre["tenure_days"], pst["tenure_days"])
    print(f"  Mann-Whitney p={p_mw:.3g}")
    newbie_pre = (pre["tenure_days"] < 365).mean()
    newbie_pst = (pst["tenure_days"] < 365).mean()
    print(f"  share of askers with <1y account: {newbie_pre:.1%} -> {newbie_pst:.1%}")
    res["pool_shift"] = {"mean_pre": pre["tenure_days"].mean(), "mean_post": pst["tenure_days"].mean(),
                         "median_pre": pre["tenure_days"].median(), "median_post": pst["tenure_days"].median(),
                         "p_mannwhitney": p_mw,
                         "newbie_share_pre": newbie_pre, "newbie_share_post": newbie_pst}

    # ---- (c) is tenure related to substitutability at all? ---------------
    rho, p_rho = stats.spearmanr(d["tenure_days"], d["s"])
    print(f"\n=== (c) tenure vs substitutability ===\n  Spearman rho={rho:+.4f}, p={p_rho:.3g}")
    res["tenure_vs_s"] = {"spearman_rho": rho, "p": p_rho}

    # tenure strata: terciles of the PRE-period distribution (fixed cut points,
    # so the strata do not move with the treatment)
    q1, q2 = pre["tenure_days"].quantile([1/3, 2/3]).values
    d["g"] = np.where(d["tenure_days"] <= q1, "young",
             np.where(d["tenure_days"] <= q2, "mid", "old"))
    print(f"  pre-period tercile cuts: {q1:.0f}d, {q2:.0f}d")
    print("  mean s by stratum x period:")
    piv = d.pivot_table(index="g", columns="post", values="s", aggfunc="mean")
    print(piv.round(3).to_string())

    # ---- (d) shift-share decomposition of the fall in mean s -------------
    print(f"\n=== (d) shift-share decomposition of the mean-s decline ===")
    g_order = ["young", "mid", "old"]
    pre, pst = d[d["post"] == 0], d[d["post"] == 1]      # re-slice now that g exists
    w_pre = pre.groupby("g").size().reindex(g_order).fillna(0)
    w_pre = w_pre / w_pre.sum()
    w_pst = pst.groupby("g").size().reindex(g_order).fillna(0)
    w_pst = w_pst / w_pst.sum()
    s_pre = d[d["post"] == 0].groupby("g")["s"].mean().reindex(g_order)
    s_pst = d[d["post"] == 1].groupby("g")["s"].mean().reindex(g_order)
    total = (w_pst * s_pst).sum() - (w_pre * s_pre).sum()
    within = (((w_pre + w_pst) / 2) * (s_pst - s_pre)).sum()
    between = ((w_pst - w_pre) * ((s_pre + s_pst) / 2)).sum()
    print(f"  stratum shares pre : {w_pre.round(4).to_dict()}")
    print(f"  stratum shares post: {w_pst.round(4).to_dict()}")
    print(f"  mean s pre : {s_pre.round(4).to_dict()}")
    print(f"  mean s post: {s_pst.round(4).to_dict()}")
    print(f"  TOTAL   change in mean s : {total:+.4f}")
    print(f"  WITHIN  (same-tenure askers ask fewer machine-answerable Qs): {within:+.4f}  ({within/total*100:5.1f}%)")
    print(f"  BETWEEN (the tenure mix changed = the rival explanation)   : {between:+.4f}  ({between/total*100:5.1f}%)")
    res["decomposition"] = {"total": total, "within": within, "between": between,
                            "within_share": within / total, "between_share": between / total,
                            "w_pre": w_pre.round(5).to_dict(), "w_post": w_pst.round(5).to_dict(),
                            "s_pre": s_pre.round(5).to_dict(), "s_post": s_pst.round(5).to_dict(),
                            "cuts_days": [float(q1), float(q2)]}

    # ---- (e) dose-response within tenure strata --------------------------
    print(f"\n=== (e) the paper's dose-response, within tenure strata ===")
    d4 = d[d["s"].between(1, 4)].copy()          # paper drops s0
    res["stratified_gamma"] = {}

    def dose(panel, label):
        panel = panel[panel["n"] > 0].copy()
        panel["logn"] = np.log(panel["n"])
        panel["sxpost"] = panel["s"] * panel["post"]
        m = smf.ols("logn ~ sxpost + C(s) + C(ym)", data=panel).fit(
            cov_type="cluster", cov_kwds={"groups": panel["ym"]})
        g, se, p = m.params["sxpost"], m.bse["sxpost"], m.pvalues["sxpost"]
        cells = len(panel)
        print(f"  {label:22s} gamma={g:+.4f} (SE {se:.4f})  p={p:.3g}   "
              f"cells={cells}  s4/s1 diff={math.exp(3*g)-1:+.1%}")
        return {"gamma": g, "se": se, "p": p, "cells": cells,
                "s4_vs_s1": math.exp(3 * g) - 1}

    full = d4.groupby(["ym", "s"]).size().rename("n").reset_index()
    full["post"] = full["ym"].map(ym_int) >= EVENT
    full["post"] = full["post"].astype(int)
    res["stratified_gamma"]["all_resolved"] = dose(full, "all resolved askers")

    for g_ in g_order:
        sub = d4[d4["g"] == g_]
        pan = sub.groupby(["ym", "s"]).size().rename("n").reset_index()
        pan["post"] = (pan["ym"].map(ym_int) >= EVENT).astype(int)
        res["stratified_gamma"][g_] = dose(pan, f"tenure = {g_}")

    # pooled with stratum-x-month FE: absorbs exactly the compositional shock
    print(f"\n=== (e2) pooled, stratum-x-month FE (absorbs the rival's shock) ===")
    pan = d4.groupby(["ym", "s", "g"]).size().rename("n").reset_index()
    idx = pd.MultiIndex.from_product([sorted(d4["ym"].unique()), [1, 2, 3, 4], g_order],
                                     names=["ym", "s", "g"])
    pan = pan.set_index(["ym", "s", "g"]).reindex(idx, fill_value=0).reset_index()
    pan["post"] = (pan["ym"].map(ym_int) >= EVENT).astype(int)
    pan["sxpost"] = pan["s"] * pan["post"]
    pan["gm"] = pan["g"] + "_" + pan["ym"]
    zero = (pan["n"] == 0).mean()
    print(f"  cells={len(pan)}, zero cells={zero:.1%} -> Poisson (PPML), log-OLS would drop them")
    mp = smf.poisson("n ~ sxpost + C(s):C(g) + C(gm)", data=pan).fit(
        disp=0, cov_type="cluster", cov_kwds={"groups": pan["ym"]})
    g_, se_, p_ = mp.params["sxpost"], mp.bse["sxpost"], mp.pvalues["sxpost"]
    print(f"  PPML gamma (stratum-x-month FE) = {g_:+.4f} (SE {se_:.4f}), p={p_:.3g}")
    res["pooled_ppml_stratum_month_fe"] = {"gamma": g_, "se": se_, "p": p_, "zero_share": zero}

    # benchmark: same PPML without the stratum-x-month FE
    pan["sxpost"] = pan["s"] * pan["post"]
    mb = smf.poisson("n ~ sxpost + C(s) + C(ym)", data=pan).fit(
        disp=0, cov_type="cluster", cov_kwds={"groups": pan["ym"]})
    print(f"  PPML gamma (plain month FE, same cells) = {mb.params['sxpost']:+.4f} "
          f"(SE {mb.bse['sxpost']:.4f}), p={mb.pvalues['sxpost']:.3g}")
    res["pooled_ppml_plain"] = {"gamma": mb.params["sxpost"], "se": mb.bse["sxpost"],
                                "p": mb.pvalues["sxpost"]}

    json.dump(res, open(OUT_JSON, "w", encoding="utf-8"), indent=2, default=float)
    print(f"\nwritten: {OUT_JSON}")


if __name__ == "__main__":
    main()
