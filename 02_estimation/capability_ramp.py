# -*- coding: utf-8 -*-
"""Phase 1.3 — capability ramp: the dose slope by post-window.

The substitutability labels come from a 2026-era classifier; the treatment
date is ChatGPT (2022-12). If 2026 labels partly encode capability that did
not exist in Dec 2022, the dose gradient should be weak in the months when
only GPT-3.5 existed (2022-12..2023-02, before GPT-4 on 2023-03-14) and grow
as the capability frontier advances. This script makes that ramp explicit:

  (a) windowed DiD: the manuscript's spec, log(count_{s,m}) on s x post with
      bin and month FE, month-clustered SE, with the POST sample restricted to
      one window at a time (the full pre-period is always kept);
  (b) monthly event-study coefficients gamma_k (reference k = -1, 2022-11),
      averaged within post-year buckets with SEs from the coefficient
      covariance (so Fig 3A can carry year-bucket annotations);
  (c) the same windows in the ABSOLUTE-volume domain (from Phase 1.2's
      N_t x p_hat series): the volume-weighted s4-vs-s1 survival ratio per
      window, which shows why the equal-weight exp(3*gamma)-1 (-71%) exceeds
      the volume-weighted differential (-61.5%): the differential is
      concentrated in later, lower-volume months.

Pass criteria (must reproduce the session's scratch numbers):
  python full window   gamma = -0.416
  python GPT-3.5-only  gamma = -0.203

Run:  python capability_ramp.py
"""
import os, sys, json, warnings
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

warnings.simplefilter("ignore")
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

DATA = r"E:\智能体论文\_legB_data"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_JSON = os.path.join(HERE, "capability_ramp.json")
OUT_ES = os.path.join(HERE, "capability_ramp_eventstudy.csv")

PANELS = {"python": "within_so_llm_panel.csv",
          "javascript": "within_so_llm_panel_js.csv",
          "java": "within_so_llm_panel_java.csv"}


def ymi(y):
    a, b = y.split("-")
    return int(a) * 12 + int(b) - 1


EVENT = ymi("2022-12")
GPT4 = ymi("2023-03")  # GPT-4 released 2023-03-14; first full month after = 2023-04

WINDOWS = [
    ("full 2022-12..2026-05",           ymi("2022-12"), ymi("2026-05")),
    ("GPT-3.5 only 2022-12..2023-02",   ymi("2022-12"), ymi("2023-02")),
    ("first 6m 2022-12..2023-05",       ymi("2022-12"), ymi("2023-05")),
    ("y1 2022-12..2023-11",             ymi("2022-12"), ymi("2023-11")),
    ("y2 2023-12..2024-11",             ymi("2023-12"), ymi("2024-11")),
    ("y3 2024-12..2025-11",             ymi("2024-12"), ymi("2025-11")),
    ("y4 2025-12..2026-05",             ymi("2025-12"), ymi("2026-05")),
]
YEAR_BUCKETS = {"y1": (ymi("2022-12"), ymi("2023-11")), "y2": (ymi("2023-12"), ymi("2024-11")),
                "y3": (ymi("2024-12"), ymi("2025-11")), "y4": (ymi("2025-12"), ymi("2026-05"))}


def long_panel(fn):
    w = pd.read_csv(os.path.join(DATA, fn))
    d = w.melt(id_vars=["ym"], value_vars=["s1", "s2", "s3", "s4"], var_name="bin", value_name="cnt")
    d["s"] = d["bin"].str[1].astype(int)
    d["t"] = d["ym"].map(ymi)
    d["lc"] = np.log(d["cnt"])
    return d


def windowed(d):
    out = []
    for name, lo, hi in WINDOWS:
        sub = d[(d.t < EVENT) | ((d.t >= lo) & (d.t <= hi))].copy()
        sub["post"] = (sub.t >= EVENT).astype(int)
        sub["sxp"] = sub.s * sub.post
        m = smf.ols("lc ~ sxp + C(bin) + C(ym)", sub).fit(cov_type="cluster", cov_kwds={"groups": sub["ym"]})
        g, se, p = m.params["sxp"], m.bse["sxp"], m.pvalues["sxp"]
        out.append({"window": name, "post_months": int(sub.post.sum() // 4), "gamma": float(g),
                    "se": float(se), "p": float(p), "s4_vs_s1": float(np.exp(3 * g) - 1)})
    return out


def event_study(d):
    """gamma_k for every month k != 2022-11 (point estimates only, matching the
    manuscript's within_so_llm_eventstudy.csv), then year-bucket means expressed
    RELATIVE TO THE MEAN OF THE PRE-PERIOD LEADS, so the bucket numbers do not
    depend on which single month is the omitted reference.

    No SEs here by design: a month-specific s x 1[m=k] regressor lives inside a
    single month cluster, and the OLS normal equations zero that cluster's score,
    so month-clustered SEs are identically 0 (degenerate). Inference for the
    ramp comes from the windowed DiD in (a), whose s x post regressor spans
    many clusters."""
    d = d.copy()
    months = sorted(d.t.unique())
    ref = ymi("2022-11")
    cols = []
    for k in months:
        if k == ref:
            continue
        c = f"k{k}"
        d[c] = (d.t == k).astype(int) * d.s
        cols.append(c)
    formula = "lc ~ " + " + ".join(cols) + " + C(bin) + C(ym)"
    m = smf.ols(formula, d).fit()
    es = pd.DataFrame({"t": [int(c[1:]) for c in cols],
                       "gamma_k": [m.params[c] for c in cols]})
    es["ym"] = es.t.map(lambda t: f"{t // 12:04d}-{t % 12 + 1:02d}")
    es["rel_month"] = es.t - EVENT
    pre_cols = [c for c in cols if int(c[1:]) < ref]
    pre_mean = float(np.mean([m.params[c] for c in pre_cols]))
    buckets = {"pre_leads_mean_vs_ref": {"months": len(pre_cols), "mean_gamma_k": pre_mean}}
    for name, (lo, hi) in YEAR_BUCKETS.items():
        sel = [c for c in cols if lo <= int(c[1:]) <= hi]
        if not sel:
            continue
        mean = float(np.mean([m.params[c] for c in sel]))
        buckets[name] = {"months": len(sel), "mean_gamma_k_vs_ref": mean,
                         "mean_gamma_k_vs_pre_mean": mean - pre_mean}
    return es, buckets


def absolute_by_window(tag):
    fn = os.path.join(HERE, f"absolute_volume_series_{tag}.csv")
    if not os.path.exists(fn):
        return None
    s = pd.read_csv(fn)
    s["t"] = s.ym.map(ymi)
    pre = s[s.t < EVENT]
    out = []
    for name, lo, hi in WINDOWS:
        w = s[(s.t >= lo) & (s.t <= hi)]
        surv = {b: w[f"Nhat_s{b}"].mean() / pre[f"Nhat_s{b}"].mean() for b in (1, 4)}
        out.append({"window": name, "s1_change": float(surv[1] - 1), "s4_change": float(surv[4] - 1),
                    "s4_vs_s1_volume_weighted": float(surv[4] / surv[1] - 1),
                    "platform_change": float(w.total.mean() / pre.total.mean() - 1)})
    return out


def main():
    results = {}
    for lang, fn in PANELS.items():
        d = long_panel(fn)
        print(f"\n== {lang} ==")
        print("  (a) windowed DiD")
        win = windowed(d)
        for r in win:
            print(f"    {r['window']:32s} post_m={r['post_months']:2d}  γ={r['gamma']:+.3f} (SE {r['se']:.3f}) "
                  f"p={r['p']:.4f}  s4-vs-s1={r['s4_vs_s1']:+.0%}")
        es, buckets = event_study(d)
        es["lang"] = lang
        print("  (b) event-study year-bucket means of γ_k (point estimates; inference is in (a))")
        pm = buckets["pre_leads_mean_vs_ref"]
        print(f"    pre-leads mean vs ref 2022-11: {pm['mean_gamma_k']:+.3f} ({pm['months']} months)")
        for k, v in buckets.items():
            if k == "pre_leads_mean_vs_ref":
                continue
            print(f"    {k:4s} months={v['months']:2d}  mean γ_k vs ref={v['mean_gamma_k_vs_ref']:+.3f}  "
                  f"vs pre-mean={v['mean_gamma_k_vs_pre_mean']:+.3f}")
        ab = absolute_by_window(lang)
        if ab:
            print("  (c) absolute-volume domain (from 1.2): s4-vs-s1 volume-weighted differential by window")
            for r in ab:
                print(f"    {r['window']:32s} platform={r['platform_change']:+.0%}  s1={r['s1_change']:+.0%}  "
                      f"s4={r['s4_change']:+.0%}  s4-vs-s1(vol-wt)={r['s4_vs_s1_volume_weighted']:+.0%}")
        results[lang] = {"windowed": win, "event_study_year_buckets": buckets, "absolute_by_window": ab}
        if lang == "python":
            es_all = es
        else:
            es_all = pd.concat([es_all, es])

    es_all.to_csv(OUT_ES, index=False)
    json.dump(results, open(OUT_JSON, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    # pass criteria
    py = {r["window"]: r["gamma"] for r in results["python"]["windowed"]}
    ok_full = abs(py["full 2022-12..2026-05"] - (-0.416)) < 0.002
    ok_35 = abs(py["GPT-3.5 only 2022-12..2023-02"] - (-0.203)) < 0.002
    ref = pd.read_csv(os.path.join(DATA, "within_so_llm_eventstudy.csv"))
    mine = es_all[es_all.lang == "python"][["rel_month", "gamma_k"]].rename(columns={"rel_month": "k", "gamma_k": "mine"})
    cmp = ref.merge(mine, on="k", how="outer")
    maxdiff = float((cmp.gamma_k - cmp.mine).abs().max())
    ok_es = (len(cmp) == 59) and cmp.mine.notna().all() and maxdiff < 1e-8
    print(f"\nPASS full=-0.416: {ok_full} ({py['full 2022-12..2026-05']:+.4f});  "
          f"PASS GPT-3.5=-0.203: {ok_35} ({py['GPT-3.5 only 2022-12..2023-02']:+.4f});  "
          f"PASS event-study == manuscript csv (59 pts): {ok_es} (max|diff|={maxdiff:.1e})")
    results["_pass"] = {"full": ok_full, "gpt35": ok_35, "eventstudy_matches_manuscript": bool(ok_es)}
    json.dump(results, open(OUT_JSON, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"written: {OUT_JSON}\n         {OUT_ES}")


if __name__ == "__main__":
    main()
