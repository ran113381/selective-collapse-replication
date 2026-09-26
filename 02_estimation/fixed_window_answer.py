# -*- coding: utf-8 -*-
"""Phase B — the CLEAN answer-margin test with a fixed post-publication window.

Consumes first_answer.csv (from fetch_first_answers.py) and re-runs the answer
margin dose-DiD with the outcome redefined as "answered within W days of
publication" for W in {30, 90}, plus first-answer latency. This removes the
scrape-date-snapshot / cohort-age confound that downgraded the A2 result: every
question is observed over the same fixed post-publication risk window, so young
post-ChatGPT cohorts are no longer mechanically under-counted.

Decision gate (Gate C of the review blueprint):
  * if score*post on answered-within-30d is negative and significant, the
    answer-margin (supply-side lemons) result is RESTORED to a signed finding;
  * if not, it stays exploratory and the paper's supply-side claim rests on the
    ban + the RCT voluntary arm, exactly as the current text already states.

Run after fetch_first_answers.py has produced first_answer.csv.
"""
import os, json, csv
import numpy as np, pandas as pd
import statsmodels.api as sm

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = r"E:\智能体论文\_legB_data"
FA = os.path.join(HERE, "first_answer.csv")
EVENT = 2022 * 12 + 11
DAY = 86400
FILES = ["so_questions_full.json", "so_questions_ext_py.json"]
LAB = ["question_labels.csv", "question_labels_ext_py.csv"]


def main():
    if not os.path.exists(FA):
        raise SystemExit("first_answer.csv not found — run fetch_first_answers.py first (needs network).")
    fa = {int(r["question_id"]): r for r in csv.DictReader(open(FA, encoding="utf-8"))}
    labels = {}
    for fn in LAB:
        for r in csv.DictReader(open(os.path.join(DATA, fn), encoding="utf-8")):
            labels[int(r["question_id"])] = int(r["score"])

    rows = []
    for fn in FILES:
        for q in json.load(open(os.path.join(DATA, fn), encoding="utf-8")):
            qid = int(q["question_id"]); s = labels.get(qid)
            if s is None or s == 0 or qid not in fa:
                continue
            cd = int(q["creation_date"])
            cm = pd.to_datetime(cd, unit="s").to_period("M")
            t = cm.year * 12 + (cm.month - 1)
            fad = fa[qid]["first_answer_date"]
            lat = (int(fad) - cd) / DAY if fad else np.inf
            rows.append({"score": s, "t": t, "ym": q["ym"],
                         "a30": int(lat <= 30), "a90": int(lat <= 90),
                         "lat": lat if np.isfinite(lat) else np.nan})
    d = pd.DataFrame(rows)
    d["post"] = (d.t >= EVENT).astype(int); d["dose"] = d.score * d.post
    print(f"N with fetched answers = {len(d):,}")

    def did(dep):
        bins = pd.get_dummies(d.score, prefix="b", drop_first=True).astype(float)
        mo = pd.get_dummies(d.ym, prefix="m", drop_first=True).astype(float)
        X = sm.add_constant(pd.concat([d[["dose"]].astype(float).reset_index(drop=True),
                                       bins.reset_index(drop=True), mo.reset_index(drop=True)], axis=1))
        r = sm.OLS(d[dep].astype(float).to_numpy(), X.to_numpy()).fit(
            cov_type="cluster", cov_kwds={"groups": d.ym.to_numpy()})
        i = list(X.columns).index("dose")
        return r.params[i], r.bse[i], r.pvalues[i]

    print("\nFIXED-WINDOW answer margin (clean; identification within-month across bins):")
    for dep, lbl in (("a30", "answered within 30d"), ("a90", "answered within 90d")):
        g, se, p = did(dep)
        for sc in (1, 4):
            pre = d[(d.score == sc) & (d.post == 0)][dep].mean()
            post = d[(d.score == sc) & (d.post == 1)][dep].mean()
            print(f"    s{sc} {lbl}: {pre:.3f} -> {post:.3f}")
        verdict = "RESTORED (signed)" if (g < 0 and p < 0.05) else "stays exploratory"
        print(f"  {lbl}: score*post = {g:+.4f} (se {se:.4f}, p={p:.4g})  ->  {verdict}\n")

    # latency (Cox-style read via mean, plus a simple regression on log-latency for answered)
    ans = d[np.isfinite(d.lat)]
    print(f"first-answer latency among answered (N={len(ans):,}): "
          f"pre median {ans[ans.post==0].lat.median():.1f}d, post {ans[ans.post==1].lat.median():.1f}d")


if __name__ == "__main__":
    main()
