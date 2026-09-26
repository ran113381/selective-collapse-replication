# -*- coding: utf-8 -*-
"""Does a substitutability bin mean the same thing before and after? (S17)

The relabelling rival: askers may draft or
polish questions with ChatGPT before posting. A polished question carries more
context and less ambiguity, so the rubric scores it LOWER on substitutability.
The observed compositional shift would then follow from a change in how
questions are WRITTEN, with no change in which questions are ASKED. Date-blind
classification does not help (the classifier correctly scores changed text),
month fixed effects do not help (this is a compositional shock), and the volume
reconstruction does not help (N_t x p_hat inherits the platform-wide fall).

The rival makes a sharp, falsifiable prediction. Under migration, the
post-period low bins are contaminated with questions that "really" belong in
s4, and s4 questions are duplicate-closed at 11.3% against 2.6% for s1.
Therefore:

    RIVAL  => duplicate-closure rates RISE in the low bins after the event,
              and the closure-by-bin gradient FLATTENS.
    EXIT   => the bin-to-closure mapping is STABLE; an s4 question after the
              event is the same kind of object as an s4 question before it.

Exposure confound, handled here: closure status was re-fetched in 2026-09, so a
2021 question has had five years to be closed and a 2026 question a few months.
Raw closure rates therefore fall mechanically over time. We equalise exposure by
counting only closures that occurred within a fixed WINDOW days of the
question's creation, using closed_date and the creation timestamps recovered for
the asker analysis, and dropping the final WINDOW days of the panel, which
cannot have a full window.

Run:  python bin_stability_test.py
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
OUT = os.path.join(HERE, "bin_stability_test.json")
EVENT_YM, WINDOW = "2022-12", 90


def ym_int(y):
    a, b = y.split("-")
    return int(a) * 12 + int(b) - 1


EVENT = ym_int(EVENT_YM)
res = {"window_days": WINDOW}

lab = pd.read_csv(os.path.join(DATA, "question_labels.csv")).rename(columns={"score": "s"})
clo = pd.read_csv(os.path.join(HERE, "closure_meta.csv")).rename(columns={"score": "so_score"})
own = pd.read_csv(os.path.join(HERE, "asker_owner.csv")).drop_duplicates("question_id")[
    ["question_id", "q_creation"]]
d = lab.merge(clo, on="question_id", how="left").merge(own, on="question_id", how="left")
d["mi"] = d["ym"].map(ym_int)
d["post"] = (d["mi"] >= EVENT).astype(int)

# exposure-equalised duplicate closure
d["days_to_close"] = (d["closed_date"] - d["q_creation"]) / 86400.0
d["dup"] = ((d["closed_reason"] == "Duplicate") & (d["days_to_close"] <= WINDOW)).astype(int)
d["any_close"] = ((d["closed_reason"].notna()) & (d["days_to_close"] <= WINDOW)).astype(int)

last_mi = d["mi"].max()
cut = last_mi - math.ceil(WINDOW / 30.0)          # drop months without a full window
full = d[(d["mi"] <= cut) & d["q_creation"].notna() & d["s"].between(1, 4)].copy()
print(f"N={len(d)}  usable after exposure trim (<= {cut - EVENT} months post) = {len(full)}")
print(f"  dropped: {int(d['q_creation'].isna().sum())} without creation date, "
      f"{int((d['mi'] > cut).sum())} inside the final {WINDOW}-day window")
res["n_usable"] = int(len(full))

# ---- A. the decisive table: closure rate by bin x period ---------------
print(f"\n=== A. duplicate closure within {WINDOW} days, by bin x period ===")
print(f"{'bin':>4} {'pre rate':>10} {'n':>6} {'post rate':>10} {'n':>6} {'diff':>9} {'95% CI':>20}")
tab = {}
for b in (1, 2, 3, 4):
    a_ = full[(full.s == b) & (full.post == 0)]["dup"]
    c_ = full[(full.s == b) & (full.post == 1)]["dup"]
    p0, p1 = a_.mean(), c_.mean()
    se = math.sqrt(p0 * (1 - p0) / len(a_) + p1 * (1 - p1) / len(c_))
    diff = p1 - p0
    lo, hi = diff - 1.96 * se, diff + 1.96 * se
    print(f"s{b:>3} {p0:9.2%} {len(a_):6d} {p1:9.2%} {len(c_):6d} {diff:+8.2%}   "
          f"[{lo:+.2%}, {hi:+.2%}]")
    tab[f"s{b}"] = {"pre": float(p0), "n_pre": int(len(a_)), "post": float(p1),
                    "n_post": int(len(c_)), "diff": float(diff), "ci": [float(lo), float(hi)]}
res["closure_by_bin"] = tab
print("  RIVAL predicts the low bins rise; EXIT predicts all four flat.")

# ---- B. does the gradient flatten? -------------------------------------
print(f"\n=== B. does the closure-by-bin gradient flatten after the event? ===")
for lbl, sub in (("pre ", full[full.post == 0]), ("post", full[full.post == 1])):
    rho, p = stats.spearmanr(sub["s"], sub["dup"])
    m = smf.ols("dup ~ s", data=sub).fit(cov_type="HC1")
    print(f"  {lbl}: Spearman rho={rho:+.4f} (p={p:.2g})   LPM slope={m.params['s']:+.5f} "
          f"(SE {m.bse['s']:.5f})")
    res.setdefault("gradient", {})[lbl.strip()] = {
        "rho": float(rho), "p": float(p),
        "lpm_slope": float(m.params["s"]), "lpm_se": float(m.bse["s"])}
m = smf.ols("dup ~ s * post", data=full).fit(cov_type="HC1")
print(f"  interaction s x post = {m.params['s:post']:+.5f} (SE {m.bse['s:post']:.5f}), "
      f"p = {m.pvalues['s:post']:.3f}")
res["interaction"] = {"coef": float(m.params["s:post"]), "se": float(m.bse["s:post"]),
                      "p": float(m.pvalues["s:post"])}

# ---- C. how big would the rival's contamination have to be? ------------
print(f"\n=== C. what the rival requires, quantified ===")
sh_pre = full[full.post == 0].s.value_counts(normalize=True).sort_index()
sh_pst = full[full.post == 1].s.value_counts(normalize=True).sort_index()
print("  bin shares:", {f"s{b}": f"{sh_pre[b]:.3f}->{sh_pst[b]:.3f}" for b in (1, 2, 3, 4)})
r_pre = {b: full[(full.s == b) & (full.post == 0)]["dup"].mean() for b in (1, 2, 3, 4)}
gain = {b: max(sh_pst[b] - sh_pre[b], 0.0) for b in (1, 2, 3, 4)}
loss = {b: max(sh_pre[b] - sh_pst[b], 0.0) for b in (1, 2, 3, 4)}
tot_loss = sum(loss.values())
donor_rate = (sum(loss[b] * r_pre[b] for b in (1, 2, 3, 4)) / tot_loss) if tot_loss else float("nan")
print(f"  donor bins (those that lost share) had a pre-event duplicate rate of {donor_rate:.2%}")
for b in (1, 2, 3, 4):
    if gain[b] <= 0:
        continue
    pred = (sh_pre[b] * r_pre[b] + gain[b] * donor_rate) / sh_pst[b]
    obs = full[(full.s == b) & (full.post == 1)]["dup"].mean()
    print(f"  s{b}: under pure migration the post rate would be {pred:.2%}; "
          f"observed {obs:.2%}  ({'consistent' if abs(obs-pred)<0.01 else 'NOT consistent'})")
    res.setdefault("migration_prediction", {})[f"s{b}"] = {
        "predicted": float(pred), "observed": float(obs), "share_gain": float(gain[b])}

# ---- D. did questions get longer within bin? ---------------------------
print(f"\n=== D. question length within bin (right-censored at ~1400 chars) ===")
txt = {}
for f in ("so_questions_full.json", "so_questions_ext_py.json"):
    p_ = os.path.join(DATA, f)
    if os.path.exists(p_):
        for q in json.load(open(p_, encoding="utf-8")):
            txt[q["question_id"]] = len(q.get("title") or "") + len(q.get("body_excerpt") or "")
full["nchar"] = full["question_id"].map(txt)
have = full[full["nchar"].notna()]
print(f"  text available for {len(have)}/{len(full)}")
print(f"{'bin':>4} {'pre median':>11} {'post median':>12} {'MW p':>10}")
for b in (1, 2, 3, 4):
    a_ = have[(have.s == b) & (have.post == 0)]["nchar"]
    c_ = have[(have.s == b) & (have.post == 1)]["nchar"]
    p = stats.mannwhitneyu(a_, c_)[1] if len(a_) and len(c_) else float("nan")
    print(f"s{b:>3} {a_.median():11.0f} {c_.median():12.0f} {p:10.3g}")
    res.setdefault("length", {})[f"s{b}"] = {"pre_median": float(a_.median()),
                                             "post_median": float(c_.median()), "p": float(p)}
print("  RIVAL predicts within-bin length rises (more context pasted in).")

# ---- E. platform-native outcomes within bin ----------------------------
print(f"\n=== E. answers and votes within bin (platform-native, no classifier) ===")
print(f"{'bin':>4} {'ans pre':>8} {'ans post':>9} {'score pre':>10} {'score post':>11}")
for b in (1, 2, 3, 4):
    a_ = full[(full.s == b) & (full.post == 0)]
    c_ = full[(full.s == b) & (full.post == 1)]
    print(f"s{b:>3} {a_.answer_count.mean():8.2f} {c_.answer_count.mean():9.2f} "
          f"{a_.so_score.mean():10.2f} {c_.so_score.mean():11.2f}")
    res.setdefault("native", {})[f"s{b}"] = {
        "ans_pre": float(a_.answer_count.mean()), "ans_post": float(c_.answer_count.mean()),
        "score_pre": float(a_.so_score.mean()), "score_post": float(c_.so_score.mean())}

json.dump(res, open(OUT, "w", encoding="utf-8"), indent=2, default=float)
print(f"\nwritten: {OUT}")

# ---- F. bound the migrated fraction, allowing a common level shift -----
print(f"\n=== F. how much migration is compatible with the closure data? ===")
# s4 lost share, so under the rival it is a donor and is NOT contaminated;
# its pre->post change therefore estimates the common level shift in moderation.
delta = tab["s4"]["post"] - tab["s4"]["pre"]
print(f"  common moderation shift, estimated from the uncontaminated donor s4: {delta:+.2%}")
for b in (1, 2):
    r_pre = tab[f"s{b}"]["pre"]
    obs = tab[f"s{b}"]["post"]
    n = tab[f"s{b}"]["n_post"]
    se = math.sqrt(obs * (1 - obs) / n)
    denom = donor_rate - r_pre
    f_hat = (obs - (r_pre + delta)) / denom
    f_hi = (obs + 1.96 * se - (r_pre + delta)) / denom
    need = gain[b] / sh_pst[b]
    print(f"  s{b}: migrated fraction f = {f_hat:+.1%}  (95% upper bound {f_hi:+.1%});"
          f"  pure migration would need f = {need:.1%}")
    print(f"       => migration can account for at most {max(f_hi,0)/need*100:.0f}% "
          f"of s{b}'s share gain")
    res.setdefault("migration_bound", {})[f"s{b}"] = {
        "f_hat": float(f_hat), "f_upper95": float(f_hi), "f_required": float(need),
        "max_share_of_gain_explained": float(max(f_hi, 0) / need)}

# ---- G. an outcome that never touches the classifier -------------------
print(f"\n=== G. does the answers-per-question gradient survive? ===")
ma = smf.ols("answer_count ~ s * post", data=full).fit(cov_type="HC1")
print(f"  s slope pre  = {ma.params['s']:+.4f} (SE {ma.bse['s']:.4f})")
print(f"  s x post     = {ma.params['s:post']:+.4f} (SE {ma.bse['s:post']:.4f}), "
      f"p = {ma.pvalues['s:post']:.3f}")
res["answers_gradient"] = {"s": float(ma.params["s"]), "s_se": float(ma.bse["s"]),
                           "interaction": float(ma.params["s:post"]),
                           "interaction_se": float(ma.bse["s:post"]),
                           "interaction_p": float(ma.pvalues["s:post"])}
json.dump(res, open(OUT, "w", encoding="utf-8"), indent=2, default=float)
print(f"\nrewritten: {OUT}")

# ---- H. the same bound from a much higher-powered outcome --------------
# Duplicate closure is a rare event, so F's interval is wide. Answers per
# question is not rare and its bin gradient is steep (0.90 -> 1.61), so the
# same migration logic bounds f far more tightly. Exposure differs by calendar
# time but not by bin, so the s4-estimated level shift absorbs it.
print(f"\n=== H. migration bound from answers per question (higher power) ===")
a_pre = {b: full[(full.s == b) & (full.post == 0)]["answer_count"] for b in (1, 2, 3, 4)}
a_pst = {b: full[(full.s == b) & (full.post == 1)]["answer_count"] for b in (1, 2, 3, 4)}
a_donor = sum(loss[b] * a_pre[b].mean() for b in (1, 2, 3, 4)) / tot_loss
d_ans = a_pst[4].mean() - a_pre[4].mean()
print(f"  donor bins' pre-event mean answers = {a_donor:.3f}; "
      f"common shift from s4 = {d_ans:+.3f}")
for b in (1, 2):
    obs, n = a_pst[b].mean(), len(a_pst[b])
    se = a_pst[b].std(ddof=1) / math.sqrt(n)
    denom = a_donor - a_pre[b].mean()
    f_hat = (obs - (a_pre[b].mean() + d_ans)) / denom
    f_hi = (obs + 1.96 * se - (a_pre[b].mean() + d_ans)) / denom
    need = gain[b] / sh_pst[b]
    print(f"  s{b}: f = {f_hat:+.1%}  (95% upper bound {f_hi:+.1%});  "
          f"pure migration needs {need:.1%}")
    print(f"       => migration explains at most {max(f_hi,0)/need*100:.0f}% of s{b}'s share gain")
    res.setdefault("migration_bound_answers", {})[f"s{b}"] = {
        "f_hat": float(f_hat), "f_upper95": float(f_hi), "f_required": float(need),
        "max_share_of_gain_explained": float(max(f_hi, 0) / need)}
json.dump(res, open(OUT, "w", encoding="utf-8"), indent=2, default=float)
print(f"\nrewritten: {OUT}")
