# -*- coding: utf-8 -*-
"""Phase A2 — answer-margin under cohort-age restriction (immediate mitigation).

The concern: "is_answered as of scrape" mechanically understates answers for
young cohorts, and post-ChatGPT cohorts are younger -> the differential could be
an accrual artifact. Immediate mitigation (no re-fetch): each source file carries
its own scrape snapshot; restrict to questions that were >= AGE_MIN months old at
scrape, so accrual is (near) complete, and re-run the dose-DiD on is_answered.

The clean fixed-window (30/90-day first-answer) version needs API re-fetch of
answer timestamps -> Phase B. This script answers: does the answer-margin result
SURVIVE removing the young-cohort bias? If yes, it stands (with the fixed-window
as confirmation to follow); if no, it is downgraded to exploratory.
"""
import os, json
import numpy as np, pandas as pd
import statsmodels.api as sm

DATA = (r"C:\Users\<user>\AppData\Local\Temp\claude\E-------\77fae8c6-f490-4ed9-96cb-fd023fd3807e"
        r"\scratchpad\P9\P9_验证经济学_迁移包_20260629\P9_code\legB\data")
EVENT = 2022 * 12 + 11  # 2022-12
FILES = ["so_questions_full.json", "so_questions_ext_py.json"]
LAB = ["question_labels.csv", "question_labels_ext_py.csv"]


def ym_int(ym):
    y, m = ym.split("-"); return int(y) * 12 + (int(m) - 1)


# load labels
labels = {}
for fn in LAB:
    df = pd.read_csv(os.path.join(DATA, fn))
    for _, r in df.iterrows():
        labels[int(r["question_id"])] = int(r["score"])

# load questions, tag each with its file's proxy scrape month = max creation in file
rows = []
for fn in FILES:
    qs = json.load(open(os.path.join(DATA, fn), encoding="utf-8"))
    cds = [q["creation_date"] for q in qs]
    scrape_month = pd.Timestamp(pd.to_datetime(max(cds), unit="s")).to_period("M")
    scrape_int = scrape_month.year * 12 + (scrape_month.month - 1)
    for q in qs:
        s = labels.get(q["question_id"])
        if s is None or s == 0:
            continue
        cm = pd.to_datetime(q["creation_date"], unit="s").to_period("M")
        cint = cm.year * 12 + (cm.month - 1)
        rows.append({"qid": q["question_id"], "t": cint, "ym": q["ym"], "score": s,
                     "is_answered": int(bool(q.get("is_answered"))),
                     "answer_count": int(q.get("answer_count") or 0),
                     "age": scrape_int - cint, "scrape": scrape_int})
d = pd.DataFrame(rows)
d["post"] = (d["t"] >= EVENT).astype(int)
d["dose"] = d["score"] * d["post"]
print(f"N total = {len(d):,};  age range {d.age.min()}..{d.age.max()} months")


def dose_did(dat, dep):
    bins = pd.get_dummies(dat["score"], prefix="b", drop_first=True).astype(float)
    mo = pd.get_dummies(dat["ym"], prefix="m", drop_first=True).astype(float)
    X = sm.add_constant(pd.concat([dat[["dose"]].astype(float).reset_index(drop=True),
                                   bins.reset_index(drop=True), mo.reset_index(drop=True)], axis=1))
    r = sm.OLS(dat[dep].astype(float).to_numpy(), X.to_numpy()).fit(
        cov_type="cluster", cov_kwds={"groups": dat["ym"].to_numpy()})
    i = list(X.columns).index("dose")
    return r.params[i], r.bse[i], r.pvalues[i], len(dat)


print("\n" + "=" * 70)
print("A2 — answer-margin dose-DiD (is_answered) under cohort-age restriction")
print("=" * 70)
for amin in (0, 6, 12, 18):
    sub = d[d.age >= amin]
    g, se, p, n = dose_did(sub, "is_answered")
    # s1/s4 pre-post answered rates on this subsample
    def rate(sc, po):
        x = sub[(sub.score == sc) & (sub.post == po)]
        return x.is_answered.mean() if len(x) else np.nan
    print(f"\n[age>={amin:>2}mo]  N={n:,}")
    print(f"  score*post = {g:+.4f} (se {se:.4f}, p={p:.4g})")
    print(f"  s1 answered {rate(1,0):.3f}->{rate(1,1):.3f}   "
          f"s4 answered {rate(4,0):.3f}->{rate(4,1):.3f}")

print("\n" + "=" * 70)
print("A2 — same on answer_count (mean answers), age>=12")
print("=" * 70)
sub = d[d.age >= 12]
g, se, p, n = dose_did(sub, "answer_count")
print(f"  score*post = {g:+.4f} (se {se:.4f}, p={p:.4g}), N={n:,}")

# also: verdict
sub12 = d[d.age >= 12]
g12, se12, p12, _ = dose_did(sub12, "is_answered")
verdict = "SURVIVES" if (g12 > 0 and p12 < 0.10) else "DOES NOT clearly survive"
print(f"\nVERDICT (age>=12, is_answered): score*post={g12:+.4f} p={p12:.4g} -> {verdict}")
print("DONE")
