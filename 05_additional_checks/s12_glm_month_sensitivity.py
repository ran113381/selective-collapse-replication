# -*- coding: utf-8 -*-
"""Section 4.5 sensitivity: dropping the one month with unparseable GLM-4.6
output from the independent-family (GLM-4.6) dose-response re-estimation.

Reproduces, from files shipped in this package only, the two numbers Section
4.5 of the manuscript reports: the independent-family classifier's
dose-response estimate per point (Table 2: -0.227) and its value after
dropping 2022-06, the one month for which the earlier GLM-4.6 relabelling run
returned no parseable score for any of that month's 6,000-question sample
(-0.226; well inside one standard error of the first). It also reproduces the
same pair on the binary (generative-vs-verification) contrast, unaffected by
the drop.

PKG is derived from this script's own location (parent of 05_additional_checks),
so the package can be moved or run from anywhere without editing this file.

Run:  python s12_glm_month_sensitivity.py
"""
import io
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

PKG = str(Path(__file__).resolve().parents[1])
EV = 2022 * 12 + 11


def pj(*p):
    return os.path.join(PKG, *p)


def ymi(y):
    a, b = y.split("-")
    return int(a) * 12 + (int(b) - 1)


def dose(df, col, binary=False, drop=None):
    x = df[df[col] > 0].copy()
    if drop:
        x = x[x.ym != drop]
    x["k"] = (x[col] >= 3).astype(int) if binary else x[col]
    c = x.groupby(["ym", "k"]).size().reset_index(name="cnt")
    c["post"] = (c.ym.map(ymi) >= EV).astype(int)
    c["kp"] = c.k * c.post
    c["lc"] = np.log(c.cnt)
    mm = smf.ols("lc ~ kp + C(k) + C(ym)", c).fit(
        cov_type="cluster", cov_kwds={"groups": c["ym"]})
    return float(mm.params["kp"]), float(mm.bse["kp"])


if __name__ == "__main__":
    lab = pd.read_csv(pj("01_panels_and_classification", "data",
                          "question_labels_python_2021-2024.csv"))
    assert len(lab) == 6000 and lab.question_id.nunique() == 6000

    glm = {}
    with io.open(pj("05_additional_checks", "glm_relabel",
                     "labels_glm-4.6.jsonl"), encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            glm[int(r["question_id"])] = int(r["score"])
    assert len(glm) == 5999

    g = lab.copy()
    g["glm"] = g.question_id.map(glm)
    g = g.dropna(subset=["glm"]).copy()
    g["glm"] = g.glm.astype(int)
    assert len(g) == 5999

    miss = lab[~lab.question_id.isin(glm)].ym.tolist()
    assert miss == ["2022-06"], miss

    gl_pp, gl_pp_se = dose(g, "glm")
    gl_pp_d, _ = dose(g, "glm", drop="2022-06")
    gl_b, gl_b_se = dose(g, "glm", True)
    gl_b_d, _ = dose(g, "glm", True, "2022-06")

    print("independent-family (GLM-4.6) dose-response, per point:")
    print("  full sample      : %.3f (SE %.3f)" % (gl_pp, gl_pp_se))
    print("  2022-06 dropped  : %.3f" % gl_pp_d)
    print("  (Section 4.5: 'moves the GLM-labelled estimate from -0.227 to -0.226')")
    print("binary (generative vs verification) contrast:")
    print("  full sample      : %.3f (SE %.3f)" % (gl_b, gl_b_se))
    print("  2022-06 dropped  : %.3f" % gl_b_d)

    assert round(gl_pp, 3) == -0.227 and round(gl_pp_se, 3) == 0.036
    assert round(gl_pp_d, 3) == -0.226
    assert round(gl_b, 3) == -0.410
    assert round(gl_b_d, 3) == -0.410
    print("\nAll assertions passed: reproduces Section 4.5's -0.227 -> -0.226 sensitivity.")
