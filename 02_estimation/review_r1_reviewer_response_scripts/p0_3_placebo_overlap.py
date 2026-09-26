# -*- coding: utf-8 -*-
u"""Placebo cutoffs: for each of the 43 candidate cutoffs, the window start and end
and the number of months it overlaps the treated period.

Both window widths are computed, +-9 and +-12 months. The pre-period has 18 months
and a +-9 window is 18 months wide, so at most one pre-period candidate has a
window lying entirely before the treatment date.

Usage: python p0_3_placebo_overlap.py
"""
import io, json, os, sys
import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.stdout.reconfigure(encoding="utf-8")

DATA = r"E:\智能体论文\_legB_data"
HERE = os.path.dirname(os.path.abspath(__file__))
EVENT = 2022 * 12 + 11  # 2022-12


def ym_int(ym):
    y, m = ym.split("-")
    return int(y) * 12 + (int(m) - 1)


def lab(t):
    return "%04d-%02d" % (t // 12, t % 12 + 1)


wpy = pd.read_csv(os.path.join(DATA, "within_so_llm_panel.csv"))
d = []
for _, r in wpy.iterrows():
    for b in (1, 2, 3, 4):
        d.append({"ym": r["ym"], "t": ym_int(r["ym"]), "score": b, "count": int(r["s%d" % b])})
d = pd.DataFrame(d)
d["y"] = np.log(d["count"].clip(lower=1))
ts = sorted(d.t.unique())


def run(W):
    cands = [t for t in ts if t - W >= ts[0] and t + W - 1 <= ts[-1]]
    gs = {}
    for ev in cands:
        dd = d[(d.t >= ev - W) & (d.t < ev + W)].copy()
        dd["dz"] = dd.score * (dd.t >= ev).astype(int)
        bb = pd.get_dummies(dd.score, prefix="b", drop_first=True).astype(float)
        mm = pd.get_dummies(dd.ym, prefix="m", drop_first=True).astype(float)
        X = sm.add_constant(pd.concat([dd[["dz"]].astype(float), bb, mm], axis=1))
        gs[ev] = sm.OLS(dd.y.values, X.values).fit().params[list(X.columns).index("dz")]

    true_g = gs[EVENT]
    ranked = sorted(gs.items(), key=lambda kv: kv[1])  # 最负排最前
    rank_of_true = [i for i, (ev, _) in enumerate(ranked) if ev == EVENT][0] + 1
    pct = 100.0 * rank_of_true / len(cands)

    rows = []
    pre_clean = 0
    for ev in cands:
        lo, hi = ev - W, ev + W - 1
        overlap = sum(1 for t in range(lo, hi + 1) if t >= EVENT)
        is_pre = ev < EVENT
        clean = is_pre and overlap == 0
        if clean:
            pre_clean += 1
        rows.append({"cutoff": lab(ev), "window_lo": lab(lo), "window_hi": lab(hi),
                     "is_pre_event": is_pre, "months_overlapping_treatment": overlap,
                     "clean_placebo": clean, "gamma": float(gs[ev]),
                     "more_negative_than_true": bool(gs[ev] < true_g)})

    n_pre = sum(1 for ev in cands if ev < EVENT)
    print("\n±%d 月窗口：候选 %d 个，事件前候选 %d 个，其中窗口整段不碰处理期的 %d 个"
          % (W, len(cands), n_pre, pre_clean))
    print("  真实事件 gamma=%.4f，在 %d 个候选里排第 %d（第 %.1f 百分位，越靠前越负）"
          % (true_g, len(cands), rank_of_true, pct))
    n_more_neg_pre = sum(1 for ev in cands if ev < EVENT and gs[ev] < true_g)
    print("  事件前候选中比真实事件更负的：%d/%d" % (n_more_neg_pre, n_pre))

    df = pd.DataFrame(rows)
    out_csv = os.path.join(HERE, f"placebo_overlap_w{W}.csv")
    df.to_csv(out_csv, index=False)
    print("  写入 %s" % out_csv)
    return {"window": W, "n_candidates": len(cands), "n_pre_event": n_pre,
            "n_clean_placebo": pre_clean, "true_gamma": float(true_g),
            "rank_of_true": rank_of_true, "percentile": pct,
            "n_pre_more_negative_than_true": n_more_neg_pre}


print("=" * 78)
print("P0-3：安慰剂窗口 vs 处理期重叠核验（±9 与 ±12）")
print("=" * 78)
summary = {"w9": run(9), "w12": run(12)}

op = os.path.join(HERE, "p0_3_placebo_overlap_summary.json")
json.dump(summary, io.open(op, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print("\n写入 %s" % op)
print("\n稿件现文本核对：")
print("  §7.1 写 'nine placebo cutoffs precede it'                      -> 实际事件前候选 %d 个（±9）"
      % summary["w9"]["n_pre_event"])
print("  §7.1 写 'more negative than every one of the nine placebo'     -> 整段不碰处理期的只有 %d 个（±9）"
      % summary["w9"]["n_clean_placebo"])
print("  ±12 版本：事件前候选 %d 个，整段干净的 %d 个"
      % (summary["w12"]["n_pre_event"], summary["w12"]["n_clean_placebo"]))
