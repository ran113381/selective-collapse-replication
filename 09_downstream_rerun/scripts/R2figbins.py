# -*- coding: utf-8 -*-
"""R2figbins: bin-dummy (s2, s3, s4 vs s1) estimates under four classifications of the same
6,000 python questions, same specification as p1_14_bin_dummies.py (log-count OLS, score x post
linear dose, month fixed effects, month-clustered SE; bin dummies replace the linear term, s1 is
the reference, linearity Wald test with 2 df).

Classifications: blind (Sonnet 5, blind), earlier (Sonnet 4.6, date-visible),
s46_rerun_blind (Sonnet 4.6 re-run blind), glm46 (GLM-4.6).
Writes R2figbins_result.json with full-precision values. Positive controls (assert, before any
write): blind and earlier deltas equal the stored p1_14_bin_dummies.json of the two arms; the four
linear gammas equal Table 2 to three decimals. Generated 2026-10-05."""
import io, json, os, sys
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.stdout.reconfigure(encoding="utf-8")
# ---- package-relative paths: package root = two levels above this script (scripts -> 09_downstream_rerun -> root) ----
_HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(os.path.dirname(_HERE))
OUTJSON = os.path.join(PKG, "09_downstream_rerun", "results", "R2figbins_result.json")
# ---- /package-relative ----
P = lambda *a: os.path.join(PKG, *a)
Z = 1.959964


def ymi(y):
    a, b = y.split("-"); return int(a) * 12 + int(b) - 1


EVENT = ymi("2022-12")
blind = pd.read_csv(P("07_blind_reclassification", "labels", "question_labels_python_blind.csv"))
earlier = pd.read_csv(P("01_panels_and_classification", "data", "question_labels_python_2021-2024.csv"))
s46 = pd.read_csv(P("07_blind_reclassification", "same_model_sonnet46", "labels", "question_labels_python_blind_s46.csv"))
glm = pd.DataFrame([json.loads(l) for l in io.open(P("05_additional_checks", "glm_relabel", "labels_glm-4.6.jsonl"), encoding="utf-8") if l.strip()])
glm = glm[["question_id", "score"]].drop_duplicates("question_id").merge(blind[["question_id", "ym"]], on="question_id")


def fit(lab):
    lab = lab[lab.score.between(1, 4)]
    nq = int(len(lab))
    c = lab.groupby(["ym", "score"]).size().rename("cnt").reset_index()
    full = pd.MultiIndex.from_product([sorted(lab.ym.unique()), [1, 2, 3, 4]], names=["ym", "score"])
    c = c.set_index(["ym", "score"]).reindex(full, fill_value=0).reset_index()
    assert (c.cnt == 0).sum() == 0
    c["lc"] = np.log(c.cnt); c["post"] = (c.ym.map(ymi) >= EVENT).astype(int)
    c["sxp"] = c.score * c.post
    m = smf.ols("lc ~ sxp + C(score) + C(ym)", c).fit(cov_type="cluster", cov_kwds={"groups": c.ym})
    for b in (2, 3, 4):
        c["d%d" % b] = ((c.score == b) & (c.post == 1)).astype(int)
    s = smf.ols("lc ~ d2 + d3 + d4 + C(score) + C(ym)", c).fit(cov_type="cluster", cov_kwds={"groups": c.ym})
    w = s.wald_test("d3 - 2 * d2 = 0, d4 - 3 * d2 = 0", scalar=True)
    d = {"s%d" % b: {"coef": float(s.params["d%d" % b]), "se": float(s.bse["d%d" % b]), "p": float(s.pvalues["d%d" % b])} for b in (2, 3, 4)}
    d2, d3, d4 = (d["s%d" % b]["coef"] for b in (2, 3, 4))
    out = {"gamma_linear": float(m.params["sxp"]), "gamma_se": float(m.bse["sxp"]), "n_questions": nq,
           "deltas": d,
           "linearity_wald": {"chi2": float(w.statistic), "df": 2, "p": float(w.pvalue)},
           "monotone": bool(d2 >= d3 >= d4 and d2 <= 0),
           "ci95": {k: [v["coef"] - Z * v["se"], v["coef"] + Z * v["se"]] for k, v in d.items()}}
    return out


res = {}
for name, lab in (("blind", blind), ("earlier", earlier), ("s46_rerun_blind", s46), ("glm46", glm)):
    res[name] = fit(lab)
    r = res[name]
    print("%-16s n %d gamma %+.4f | d2 %+.3f (%.3f) d3 %+.3f (%.3f) d4 %+.3f (%.3f) | linearity chi2 %.3f p %.4f | monotone %s"
          % (name, r["n_questions"], r["gamma_linear"], r["deltas"]["s2"]["coef"], r["deltas"]["s2"]["se"], r["deltas"]["s3"]["coef"],
             r["deltas"]["s3"]["se"], r["deltas"]["s4"]["coef"], r["deltas"]["s4"]["se"], r["linearity_wald"]["chi2"], r["linearity_wald"]["p"], r["monotone"]))

# ---- positive controls: read the stored p1_14 files of the two arms, compare ----
ST = {"blind": json.load(open(P("09_downstream_rerun", "blind", "outputs", "02_estimation", "review_r1_reviewer_response_scripts", "p1_14_bin_dummies.json"), encoding="utf-8"))["python"],
      "earlier": json.load(open(P("09_downstream_rerun", "orig", "outputs", "02_estimation", "review_r1_reviewer_response_scripts", "p1_14_bin_dummies.json"), encoding="utf-8"))["python"]}
ctl = {}
maxdiff = 0.0
for arm in ("blind", "earlier"):
    mine = [res[arm]["deltas"]["s%d" % b]["coef"] for b in (2, 3, 4)]
    stored = [ST[arm]["deltas"]["s%d" % b]["coef"] for b in (2, 3, 4)]
    assert [round(x, 3) for x in mine] == [round(x, 3) for x in stored], (arm, mine, stored)
    maxdiff = max(maxdiff, max(abs(a - b) for a, b in zip(mine, stored)))
    ctl[arm + "_deltas_match_p1_14"] = True
assert [round(res["blind"]["deltas"]["s%d" % b]["coef"], 3) for b in (2, 3, 4)] == [-0.213, -0.495, -0.919]
assert [round(res["earlier"]["deltas"]["s%d" % b]["coef"], 3) for b in (2, 3, 4)] == [-0.258, -0.630, -1.261]
for k, want in (("blind", -0.304), ("earlier", -0.416), ("s46_rerun_blind", -0.346), ("glm46", -0.227)):
    assert round(res[k]["gamma_linear"], 3) == want, (k, res[k]["gamma_linear"])
ctl["gammas_match_table2"] = True
print("positive controls OK; max |delta - stored p1_14 delta| = %.3e" % maxdiff)

out = {"_note": "R2figbins.py, 2026-10-05. Log-count OLS on month x bin counts (python, 6,000 questions, bins s1-s4), "
                "linear dose score x post vs bin dummies (s1 reference), month fixed effects, month-clustered SE, "
                "linearity Wald test on d3 = 2*d2, d4 = 3*d2 (2 df). ci95 = coef +/- 1.959964 x se. monotone = d2 >= d3 >= d4 and d2 <= 0. "
                "Classifications: blind = Sonnet 5 blind; earlier = Sonnet 4.6 date-visible; s46_rerun_blind = Sonnet 4.6 blind re-run; glm46 = GLM-4.6.",
       **res, "controls": ctl}
with open(OUTJSON, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("wrote", OUTJSON)
