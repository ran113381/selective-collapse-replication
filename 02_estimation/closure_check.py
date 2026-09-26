# -*- coding: utf-8 -*-
"""Phase 1.1 — closure-rate check (mechanical-composition falsifier).

This addresses what would otherwise be the most damaging alternative
explanation left open: the SE API returns only
NON-DELETED questions, and after the platform-wide ~80% volume collapse,
average moderator/community scrutiny per surviving question rises. If simple,
duplicate, "already-answered-by-search" (i.e. exactly the s4/generative-type)
questions get closed/deleted disproportionately more in the post period —
via close-as-duplicate, low-quality-post review, or Staging Ground (rolled
out 2024) pre-publication filtering — then part or all of the s4-vs-s1 dose
gradient could be a MEASUREMENT artifact of differential survivorship, not a
demand-side substitution effect.

Design:
  * Pulls closed_date / closed_reason / score / answer_count for all 6,000
    python question ids in question_labels.csv via /2.3/questions/{ids}
    (100/batch, ~60 calls; well within the unauthenticated 300/day quota).
  * RESUMABLE (like fetch_first_answers.py): appends to closure_meta.csv,
    skips ids already fetched.
  * Reports:
      (a) closure rate by substitutability bin x period (pre/post, and by
          year), to see whether s4's closure rate rises differentially
          post-ChatGPT (esp. from 2024, when Staging Ground shipped);
      (b) the main dose-response re-estimated EXCLUDING closed questions,
          with month sample sizes now free to vary (not fixed at 100) —
          both log-count OLS and (where cell counts allow) a Poisson/PPML
          fixed-total-free specification;
      (c) the 2024-cutoff split (pre- vs post-Staging-Ground) on both (a)
          and (b).

Run (needs network):  python closure_check.py
Then this script itself prints (a)-(c); nothing here mutates the manuscript.
"""
import os, sys, json, csv, time
import urllib.request, urllib.parse
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import warnings
warnings.simplefilter("ignore")

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

DATA = r"E:\智能体论文\_legB_data"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_CSV = os.path.join(HERE, "closure_meta.csv")
OUT_JSON = os.path.join(HERE, "closure_check.json")

API = "https://api.stackexchange.com/2.3/questions/{ids}"
# built via /2.3/filter/create?include=question.closed_date;question.closed_reason&base=default
# (base=none returns an empty {} body for this endpoint — an SE API quirk verified
# empirically; base=default + the two extra fields works and default already carries
# answer_count/score/creation_date/question_id).
FILTER = "!*M*dC)MfMUxnKjPG"
KEY = os.environ.get("STACK_API_KEY")
PAGESIZE = 100
SLEEP = 0.2
EVENT_YM = "2022-12"
STAGING_GROUND_YM = "2024-01"  # rollout began 2024; treated as the split point


def ym_int(y):
    a, b = y.split("-")
    return int(a) * 12 + int(b) - 1


EVENT = ym_int(EVENT_YM)
SPLIT2024 = ym_int(STAGING_GROUND_YM)


def load_targets():
    df = pd.read_csv(os.path.join(DATA, "question_labels.csv"))
    return df  # question_id, ym, score, label, title


def already_done():
    done = set()
    if os.path.exists(OUT_CSV):
        for r in csv.DictReader(open(OUT_CSV, encoding="utf-8")):
            done.add(int(r["question_id"]))
    return done


def call(ids):
    params = {"site": "stackoverflow", "pagesize": PAGESIZE, "filter": FILTER, "page": 1}
    if KEY:
        params["key"] = KEY
    out = {}
    page = 1
    stop = False
    while True:
        params["page"] = page
        url = API.format(ids=";".join(map(str, ids))) + "?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=60) as resp:
            data = json.load(resp)
        for q in data.get("items", []):
            out[q["question_id"]] = {
                "closed_date": q.get("closed_date", ""),
                "closed_reason": q.get("closed_reason", ""),
                "score": q.get("score", ""),
                "answer_count": q.get("answer_count", ""),
            }
        if data.get("backoff"):
            time.sleep(data["backoff"] + 1)
        if data.get("quota_remaining", 1) <= 5:
            print(f"[quota] near exhaustion (remaining {data.get('quota_remaining')}), stopping politely.")
            stop = True
            break
        if data.get("has_more"):
            page += 1
            time.sleep(SLEEP)
        else:
            break
    return out, stop


def fetch_all():
    targets = load_targets()
    ids_all = targets["question_id"].astype(int).tolist()
    done = already_done()
    todo = [q for q in ids_all if q not in done]
    print(f"targets={len(ids_all):,}  already done={len(done):,}  to fetch={len(todo):,}"
          f"  (key={'yes' if KEY else 'no — 300/day quota'})")
    new = not os.path.exists(OUT_CSV)
    f = open(OUT_CSV, "a", newline="", encoding="utf-8")
    w = csv.writer(f)
    if new:
        w.writerow(["question_id", "closed_date", "closed_reason", "score", "answer_count"])
    stop = False
    for i in range(0, len(todo), PAGESIZE):
        if stop:
            break
        batch = todo[i:i + PAGESIZE]
        try:
            res, stop = call(batch)
        except Exception as e:
            print(f"[error] batch {i//PAGESIZE}: {e}; sleeping 5s and retrying once")
            time.sleep(5)
            try:
                res, stop = call(batch)
            except Exception as e2:
                print(f"[error] retry failed: {e2}; stopping, run again to resume")
                break
        for qid in batch:
            r = res.get(qid, {})
            w.writerow([qid, r.get("closed_date", ""), r.get("closed_reason", ""),
                        r.get("score", ""), r.get("answer_count", "")])
        f.flush()
        print(f"  batch {i//PAGESIZE + 1}/{(len(todo)+PAGESIZE-1)//PAGESIZE} written "
              f"({i+len(batch)}/{len(todo)})", flush=True)
        time.sleep(SLEEP)
    f.close()
    print("fetch done (resumable — re-run to continue if quota/backoff stopped it).")


def analyze():
    labels = load_targets()
    meta = pd.read_csv(OUT_CSV)
    df = labels.merge(meta, on="question_id", how="left")
    missing = df["closed_date"].isna().sum() + (df["answer_count"].isna()).sum()
    print(f"\nmerged rows={len(df)}  rows missing meta={df['closed_reason'].isna().sum()}")
    df["closed"] = df["closed_date"].notna() & (df["closed_date"].astype(str) != "")
    df["t"] = df["ym"].map(ym_int)
    df["post"] = (df["t"] >= EVENT).astype(int)
    df["period2024"] = np.where(df["t"] >= SPLIT2024, "2024+", "pre2024")
    # column name clash on merge: labels.score is the 0-4 substitutability bin,
    # meta.score is the SO net vote score — pandas suffixes them _x/_y.
    df = df.rename(columns={"score_x": "s", "score_y": "so_score"})
    if "s" not in df.columns:
        cols = df.columns.tolist()
        raise SystemExit(f"column layout unexpected (expected score_x/score_y from merge): {cols}")

    results = {}

    # (a) closure rate by bin x period
    print("\n=== (a) closure rate by substitutability bin x period ===")
    tab = df.groupby(["s", "post"])["closed"].agg(["mean", "count"]).reset_index()
    print(tab.to_string(index=False))
    results["closure_rate_by_bin_post"] = tab.to_dict("records")

    print("\n=== (a2) closure rate by bin x year-window (pre / y1(2022-12..2023-11) / y2(2023-12..2024-11) / y3+(2024-12..)) ===")
    def bucket(t):
        if t < EVENT: return "pre"
        if t < EVENT + 12: return "y1_2023"
        if t < EVENT + 24: return "y2_2024"
        return "y3plus_2025-26"
    df["ybucket"] = df["t"].map(bucket)
    tab2 = df.groupby(["s", "ybucket"])["closed"].agg(["mean", "count"]).reset_index()
    print(tab2.to_string(index=False))
    results["closure_rate_by_bin_yearbucket"] = tab2.to_dict("records")

    print("\n=== (c) closure rate pre-2024 vs 2024+ (Staging Ground split), by bin ===")
    tab3 = df.groupby(["s", "period2024"])["closed"].agg(["mean", "count"]).reset_index()
    print(tab3.to_string(index=False))
    results["closure_rate_by_bin_2024split"] = tab3.to_dict("records")

    # differential closure test: does post x s predict closed?
    m_cl = smf.logit("closed ~ s * post", df.astype({"closed": int})).fit(disp=0)
    print("\n=== differential closure logit: closed ~ s*post ===")
    print(m_cl.summary().tables[1])
    results["closure_logit_coef_s_x_post"] = float(m_cl.params.get("s:post", np.nan))
    results["closure_logit_p_s_x_post"] = float(m_cl.pvalues.get("s:post", np.nan))

    # (b) re-estimate dose-response EXCLUDING closed questions
    # NB: the manuscript's spec drops bin s0 as "near-empty" (Methods) — s ranges
    # 1..4 there. question_labels.csv still carries a handful of s0 rows (25 of
    # 6000), so we must drop them here too or the "closed-included" reference
    # number will not reproduce the manuscript's headline -0.42 for python.
    n_s0 = (df["s"] == 0).sum()
    print(f"\n[note] dropping {n_s0} s=0 rows to match manuscript spec (s in 1..4) before regression")
    df = df[df["s"] > 0].copy()

    print("\n=== (b) dose-response re-estimated excluding closed questions (month size now free) ===")
    kept = df[~df["closed"]].copy()
    counts = kept.groupby(["ym", "s"]).size().reset_index(name="cnt")
    counts["t"] = counts["ym"].map(ym_int)
    counts["post"] = (counts["t"] >= EVENT).astype(int)
    counts["sxpost"] = counts["s"] * counts["post"]
    counts["lc"] = np.log(counts["cnt"].replace(0, np.nan))
    n_zero = counts["cnt"].eq(0).sum()
    print(f"  bin-months with zero count after exclusion: {n_zero} (dropped from log spec)")
    m_ols = smf.ols("lc ~ sxpost + C(s) + C(ym)", counts.dropna(subset=["lc"])).fit(
        cov_type="cluster", cov_kwds={"groups": counts.dropna(subset=["lc"])["ym"]})
    g, se, p = m_ols.params["sxpost"], m_ols.bse["sxpost"], m_ols.pvalues["sxpost"]
    print(f"  OLS log-count (closed excluded): γ={g:+.4f} (SE {se:.4f}) p={p:.4g}  "
          f"s4-vs-s1={np.exp(3*g)-1:+.1%}")
    results["gamma_excl_closed_ols"] = {"gamma": float(g), "se": float(se), "p": float(p)}

    try:
        import statsmodels.api as sm
        counts["ym_c"] = counts["ym"].astype("category")
        counts["s_c"] = counts["s"].astype("category")
        m_pois = smf.glm("cnt ~ sxpost + C(s) + C(ym)", counts,
                          family=sm.families.Poisson()).fit(
            cov_type="cluster", cov_kwds={"groups": counts["ym"]})
        g2, se2, p2 = m_pois.params["sxpost"], m_pois.bse["sxpost"], m_pois.pvalues["sxpost"]
        print(f"  Poisson/PPML (closed excluded, zeros included): γ={g2:+.4f} (SE {se2:.4f}) p={p2:.4g}")
        results["gamma_excl_closed_poisson"] = {"gamma": float(g2), "se": float(se2), "p": float(p2)}
    except Exception as e:
        print(f"  [Poisson skipped] {e}")

    # for comparison: original (closed included) on this same merged sample
    counts_all = df.groupby(["ym", "s"]).size().reset_index(name="cnt")
    counts_all["t"] = counts_all["ym"].map(ym_int)
    counts_all["post"] = (counts_all["t"] >= EVENT).astype(int)
    counts_all["sxpost"] = counts_all["s"] * counts_all["post"]
    counts_all["lc"] = np.log(counts_all["cnt"].replace(0, np.nan))
    m_all = smf.ols("lc ~ sxpost + C(s) + C(ym)", counts_all.dropna(subset=["lc"])).fit(
        cov_type="cluster", cov_kwds={"groups": counts_all.dropna(subset=["lc"])["ym"]})
    ga, sea, pa = m_all.params["sxpost"], m_all.bse["sxpost"], m_all.pvalues["sxpost"]
    print(f"\n  [reference] OLS log-count (closed INCLUDED, same merged sample): γ={ga:+.4f} (SE {sea:.4f}) p={pa:.4g}")
    results["gamma_incl_closed_ols_reference"] = {"gamma": float(ga), "se": float(sea), "p": float(pa)}

    # (c) re-estimate split at 2024
    print("\n=== (c) dose-response excluding closed, split pre-2024 / 2024+ ===")
    for label, sub in [("pre-2024 post-period only", kept[(kept.t >= EVENT) & (kept.t < SPLIT2024)]),
                        ("2024+ post-period only", kept[kept.t >= SPLIT2024])]:
        d = pd.concat([kept[kept.t < EVENT], sub])
        c = d.groupby(["ym", "s"]).size().reset_index(name="cnt")
        c["t"] = c["ym"].map(ym_int)
        c["post"] = (c["t"] >= EVENT).astype(int)
        c["sxpost"] = c["s"] * c["post"]
        c["lc"] = np.log(c["cnt"].replace(0, np.nan))
        if c["post"].sum() == 0:
            print(f"  {label}: no post months in window, skipped")
            continue
        mm = smf.ols("lc ~ sxpost + C(s) + C(ym)", c.dropna(subset=["lc"])).fit(
            cov_type="cluster", cov_kwds={"groups": c.dropna(subset=["lc"])["ym"]})
        gg, sse, pp = mm.params["sxpost"], mm.bse["sxpost"], mm.pvalues["sxpost"]
        print(f"  {label:28s} γ={gg:+.4f} (SE {sse:.4f}) p={pp:.4g}  n_post_months={c[c.post==1]['ym'].nunique()}")
        results[f"gamma_excl_closed_{label.replace(' ', '_')}"] = {"gamma": float(gg), "se": float(sse), "p": float(pp)}

    overall_closure = df["closed"].mean()
    print(f"\noverall closure rate in sample: {overall_closure:.1%}")
    results["overall_closure_rate"] = float(overall_closure)

    json.dump(results, open(OUT_JSON, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"\nwritten: {OUT_JSON}")


if __name__ == "__main__":
    if "--analyze-only" not in sys.argv:
        fetch_all()
    if os.path.exists(OUT_CSV):
        analyze()
    else:
        print("no closure_meta.csv yet; fetch must have failed immediately.")
