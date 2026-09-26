# -*- coding: utf-8 -*-
"""Phase 1.4(b) — criterion validity across ANSWERER capability tiers.

The paper's criterion test (N=320) used Sonnet 5 as the blind answerer. One
concern is that 2026-era capability defines the labels; the
cheapest honest check is whether the rubric's ORDERING of machine-answerability
holds when the answerer is weaker (Haiku 4.5) or from another family (GLM).
Same 320 questions, same judge protocol (Opus 5, blind, graded reference
quality), same metrics as analyze_criterion_v2.py.

Reads, per tier, judgment_out_*.json in the tier's directory (the paper's own
Sonnet 5 tier is read from criterion_results_v2.csv). Writes
weak_tier_results.json + a per-tier per-question CSV.

Usage:  python weak_tier_analysis.py
"""
import json, os, glob, csv
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf

HERE = os.path.dirname(os.path.abspath(__file__))
sample = {int(r["qid"]): r for r in json.load(open(os.path.join(HERE, "criterion_sample_v2.json"), encoding="utf-8"))}

TIERS = [("Sonnet 5 (paper)", None), ("Haiku 4.5", "batches_haiku45"),
         ("GLM-4.6", "batches_glmflash"), ("GLM-5.3", "batches_glm53")]

# The GLM-5.3 tier is short 36 of 320 answers (the account balance ran out), and
# that attrition is NOT random: missing rates fall monotonically in
# substitutability — s1 20.0%, s2 11.2%, s3 8.8%, s4 5.0% (chi2 = 9.77, p = .021).
# Dropping those items only from the GLM-5.3 tier would inflate its s1 solve rate
# and FLATTEN its measured gradient. So every tier is also reported on the common
# subset of questions all four tiers answered, where the attrition applies equally
# to all of them and cannot drive a between-tier difference.


def load_tier(name, d):
    if d is None:
        df = pd.read_csv(os.path.join(HERE, "criterion_results_v2.csv"))
        df = df.rename(columns={"sub": "s", "ref_quality": "reference_quality"})
        df["qid"] = df["qid"].astype(int)
        return df[["qid", "s", "reference_quality", "answerable", "adequacy"]]
    rows = {}
    # plain batches first, then any *_swapfix file, so corrected re-judgments overwrite
    files = sorted(glob.glob(os.path.join(HERE, d, "judgment_out_*.json")), key=lambda p: ("swapfix" in p, p))
    for f in files:
        for j in json.load(open(f, encoding="utf-8")):
            q = sample.get(int(j["qid"]))
            if not q:
                continue
            rows[int(j["qid"])] = {"qid": int(j["qid"]), "s": int(q["sub_score"]), "reference_quality": q["reference_quality"],
                                   "answerable": int(j["answerable"]), "adequacy": float(j["adequacy"])}
    return pd.DataFrame(list(rows.values()))


def metrics(df):
    df = df.dropna(subset=["answerable"]).copy()
    df["gen"] = (df.s >= 3).astype(int)
    out = {"N": int(len(df))}
    out["solve_by_bin"] = {f"s{b}": float(df[df.s == b].answerable.mean()) for b in (1, 2, 3, 4)}
    out["n_by_bin"] = {f"s{b}": int((df.s == b).sum()) for b in (1, 2, 3, 4)}
    out["adequacy_by_bin"] = {f"s{b}": float(df[df.s == b].adequacy.mean()) for b in (1, 2, 3, 4)}
    r, p = stats.spearmanr(df.s, df.answerable); out["spearman_solved"] = [float(r), float(p)]
    r2, p2 = stats.spearmanr(df.s, df.adequacy); out["spearman_adequacy"] = [float(r2), float(p2)]
    g, v = df[df.gen == 1].answerable, df[df.gen == 0].answerable
    tab = [[int(g.sum()), int(len(g) - g.sum())], [int(v.sum()), int(len(v) - v.sum())]]
    orr, pf = stats.fisher_exact(tab)
    out["gen_vs_ver"] = {"gen_rate": float(g.mean()), "ver_rate": float(v.mean()), "OR": float(orr), "fisher_p": float(pf)}
    e4, e1 = df[df.s == 4].answerable, df[df.s == 1].answerable
    _, pe = stats.fisher_exact([[int(e4.sum()), int(len(e4) - e4.sum())], [int(e1.sum()), int(len(e1) - e1.sum())]])
    out["endpoints_s4_vs_s1"] = {"s4": float(e4.mean()), "s1": float(e1.mean()), "fisher_p": float(pe)}
    try:
        m = smf.logit("answerable ~ s", df).fit(disp=0)
        out["logit_or_per_point"] = [float(np.exp(m.params["s"])), float(m.pvalues["s"])]
    except Exception as e:
        out["logit_or_per_point"] = [None, str(e)]
    strong = df[df.reference_quality.isin(["accepted", "top_voted"])]
    if len(strong) > 10:
        rs, ps = stats.spearmanr(strong.s, strong.answerable)
        out["strong_ref_subset"] = {"N": int(len(strong)), "spearman": [float(rs), float(ps)],
                                    "gen_rate": float(strong[strong.gen == 1].answerable.mean()),
                                    "ver_rate": float(strong[strong.gen == 0].answerable.mean())}
    none = df[df.reference_quality == "none"]
    if len(none) > 10:
        rn, pn = stats.spearmanr(none.s, none.answerable)
        out["no_ref_subset"] = {"N": int(len(none)), "spearman": [float(rn), float(pn)]}
    return out


def report(name, m):
    sb = m["solve_by_bin"]; ab = m["adequacy_by_bin"]
    print(f"\n== {name} (N={m['N']}) ==")
    print(f"  solve by bin s1..s4: {sb['s1']:.3f} / {sb['s2']:.3f} / {sb['s3']:.3f} / {sb['s4']:.3f}   n={list(m['n_by_bin'].values())}")
    print(f"  adequacy by bin:     {ab['s1']:.2f} / {ab['s2']:.2f} / {ab['s3']:.2f} / {ab['s4']:.2f}")
    print(f"  Spearman(s, solved) ρ={m['spearman_solved'][0]:+.3f} p={m['spearman_solved'][1]:.2e};  "
          f"(s, adequacy) ρ={m['spearman_adequacy'][0]:+.3f} p={m['spearman_adequacy'][1]:.2e}")
    gv = m["gen_vs_ver"]
    print(f"  GEN vs VER: {gv['gen_rate']:.3f} vs {gv['ver_rate']:.3f}  OR={gv['OR']:.2f}  Fisher p={gv['fisher_p']:.2e}")
    ep = m["endpoints_s4_vs_s1"]
    print(f"  s4 vs s1: {ep['s4']:.3f} vs {ep['s1']:.3f}  Fisher p={ep['fisher_p']:.2e};  logit OR/pt={m['logit_or_per_point'][0]}")


def main():
    res, frames = {}, []
    for name, d in TIERS:
        try:
            df = load_tier(name, d)
        except Exception as e:
            print(f"[{name}] skipped: {e}"); continue
        if len(df) == 0:
            print(f"[{name}] no judgments yet"); continue
        m = metrics(df); res[name] = m
        df["tier"] = name; frames.append(df)
        sb = m["solve_by_bin"]
        print(f"\n== {name} (N={m['N']}) ==")
        print(f"  solve by bin s1..s4: {sb['s1']:.3f} / {sb['s2']:.3f} / {sb['s3']:.3f} / {sb['s4']:.3f}   n={list(m['n_by_bin'].values())}")
        ab = m["adequacy_by_bin"]
        print(f"  adequacy by bin:     {ab['s1']:.2f} / {ab['s2']:.2f} / {ab['s3']:.2f} / {ab['s4']:.2f}")
        print(f"  Spearman(s, solved) ρ={m['spearman_solved'][0]:+.3f} p={m['spearman_solved'][1]:.2e};  "
              f"(s, adequacy) ρ={m['spearman_adequacy'][0]:+.3f} p={m['spearman_adequacy'][1]:.2e}")
        gv = m["gen_vs_ver"]
        print(f"  GEN vs VER: {gv['gen_rate']:.3f} vs {gv['ver_rate']:.3f}  OR={gv['OR']:.2f}  Fisher p={gv['fisher_p']:.2e}")
        ep = m["endpoints_s4_vs_s1"]
        print(f"  s4 vs s1: {ep['s4']:.3f} vs {ep['s1']:.3f}  Fisher p={ep['fisher_p']:.2e};  logit OR/pt={m['logit_or_per_point'][0]}")
        if "strong_ref_subset" in m:
            s_ = m["strong_ref_subset"]; print(f"  strong-ref (N={s_['N']}): ρ={s_['spearman'][0]:+.3f} p={s_['spearman'][1]:.2e}; GEN {s_['gen_rate']:.3f} vs VER {s_['ver_rate']:.3f}")
        if "no_ref_subset" in m:
            n_ = m["no_ref_subset"]; print(f"  no-ref (N={n_['N']}): ρ={n_['spearman'][0]:+.3f} p={n_['spearman'][1]:.2e}")
    # cross-tier: is the ORDERING invariant? per-question agreement between tiers
    if len(frames) >= 2:
        wide = pd.concat(frames).pivot_table(index=["qid", "s"], columns="tier", values="answerable").reset_index()
        tiers = [t for t in wide.columns if t not in ("qid", "s")]
        print("\n== cross-tier ==")
        for i in range(len(tiers)):
            for j in range(i + 1, len(tiers)):
                a, b = wide[tiers[i]], wide[tiers[j]]
                ok = a.notna() & b.notna()
                agree = float((a[ok] == b[ok]).mean())
                print(f"  {tiers[i]} vs {tiers[j]}: per-question agreement {agree:.3f} (N={int(ok.sum())})")
        res["_cross_tier_wide_csv"] = "weak_tier_per_question.csv"
        wide.to_csv(os.path.join(HERE, "weak_tier_per_question.csv"), index=False)

        # --- common-subset re-run: identical questions for every tier ---
        allf = pd.concat(frames)
        common = set.intersection(*[set(f.qid) for f in frames])
        print(f"\n{'='*66}\nCOMMON SUBSET — every tier on the same {len(common)} questions\n{'='*66}")
        res["_common_subset_N"] = len(common)
        res["common_subset"] = {}
        for name, _ in TIERS:
            sub = allf[(allf.tier == name) & (allf.qid.isin(common))]
            if len(sub) == 0:
                continue
            mm = metrics(sub); res["common_subset"][name] = mm
            report(name, mm)
    json.dump(res, open(os.path.join(HERE, "weak_tier_results.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("\nwritten: weak_tier_results.json")


if __name__ == "__main__":
    main()
