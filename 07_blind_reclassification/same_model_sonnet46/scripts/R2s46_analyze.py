# -*- coding: utf-8 -*-
"""Sonnet 4.6 同模型盲跑(设计书第 13 条(二)、第 15 条):收标签、合并,跑预设三项,不增不减。

① 对原分类(同一模型、看得见日期):逐题精确一致率、二元一致率与二元 κ;
   d = 原分 − 盲分,E[d|事件前]、E[d|事件后] 与差(口径同 B 臂 R2v_analyze.py:题级 d~post 按月聚类正态区间,
   月均值 Welch 区间),另报二元版本。
② 对 Sonnet 5 盲标签(A 臂)的二元 κ。
③ 在本臂标签上重估头条(对数计数 OLS、固定总量 FE-PPML;估计量取包内 phaseA_composition.py)与对人工共识的二元 κ。
另报每批写出模型与重派次数(取自 R2s46_verify_result.json)。

自证(任一不过即退出不出数):原标签 OLS γ = −0.416;原标签对共识 κ = 0.512;
同一管线在 Sonnet 5 盲标签上复现 R2_analyze_result.json 的 OLS、PPML 与对共识 κ;本臂输入批与 A 臂输入批逐批编号相同。
只读 A 臂与包内文件;产物只写本目录的新文件。
"""
import csv, io, json, os, sys
from collections import defaultdict
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
WD = os.path.dirname(HERE)
A = os.path.join(WD, "R2_blind")
PKG = r"E:\智能体论文\P9b_OSF_复现包_20260920"
DATA = os.path.join(PKG, "01_panels_and_classification", "data")
GS = os.path.join(PKG, "03_validation", "gold_standard")

src = io.open(os.path.join(PKG, "02_estimation", "phaseA_composition.py"), encoding="utf-8").read()
ns = {}
exec(compile(src[:src.find('print("=" * 74)')], "phaseA_composition.py", "exec"), ns)
EVENT, ym_int, ols_dose, ppml_dose = ns["EVENT"], ns["ym_int"], ns["ols_dose"], ns["ppml_dose"]
assert EVENT == ym_int("2022-12")

# ---------------------------------------------------------------- 收标签
tok = json.load(io.open(os.path.join(A, "R2_token_map.json"), encoding="utf-8"))
ymm = json.load(io.open(os.path.join(A, "R2_ym_map.json"), encoding="utf-8"))
rows = []
for i in range(1, 51):
    ids = [r["id"] for r in json.load(io.open(os.path.join(HERE, "input", "R2_blind_batch_%02d.json" % i), encoding="utf-8"))]
    ids_a = [r["id"] for r in json.load(io.open(os.path.join(A, "R2_blind_batch_%02d.json" % i), encoding="utf-8"))]
    assert ids == ids_a, i
    lab = json.load(io.open(os.path.join(HERE, "R2_labels_batch_%02d.json" % i), encoding="utf-8"))
    got = [str(r["id"]) for r in lab]
    assert len(lab) == len(ids) and sorted(got) == sorted(ids) and len(set(got)) == len(got), i
    for r in lab:
        s = r["score"]
        assert isinstance(s, int) and 0 <= s <= 4 and r["label"] == ("GEN" if s >= 3 else "VER"), (i, r)
        q = tok[r["id"]]
        rows.append(dict(question_id=q, ym=ymm[str(q)], score=s, label=r["label"]))
assert len(rows) == 6000 and len({r["question_id"] for r in rows}) == 6000
rows.sort(key=lambda r: (r["ym"], r["question_id"]))
with io.open(os.path.join(HERE, "question_labels_python_blind_s46.csv"), "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["question_id", "ym", "score", "label"]); w.writeheader(); w.writerows(rows)
by = defaultdict(lambda: defaultdict(int))
for r in rows:
    by[r["ym"]]["n"] += 1; by[r["ym"]][r["label"]] += 1; by[r["ym"]]["s%d" % r["score"]] += 1
cols = ["ym", "n", "GEN", "VER", "gen_share"] + ["s%d" % i for i in range(5)]
with io.open(os.path.join(HERE, "within_so_llm_panel_python_blind_s46.csv"), "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
    for ym in sorted(by):
        d = by[ym]
        w.writerow(dict(ym=ym, n=d["n"], GEN=d["GEN"], VER=d["VER"], gen_share=round(d["GEN"] / d["n"], 4),
                        **{"s%d" % i: d.get("s%d" % i, 0) for i in range(5)}))
assert len(by) == 60 and all(by[m]["n"] == 100 for m in by)


# ---------------------------------------------------------------- 估计与 κ
def long_panel(w):
    recs = []
    for _, r in w.iterrows():
        t = ym_int(r["ym"])
        for b in (1, 2, 3, 4):
            recs.append({"ym": r["ym"], "t": t, "score": b, "count": int(r["s%d" % b]), "post": int(t >= EVENT)})
    d = pd.DataFrame(recs); d["dose"] = d["score"] * d["post"]
    return d


def headline(w):
    d = long_panel(w)
    f = lambda t: dict(coef=round(float(t[0]), 4), se=round(float(t[1]), 4), p=float(t[2]),
                       ci=[round(float(t[0] - 1.96 * t[1]), 4), round(float(t[0] + 1.96 * t[1]), 4)])
    return dict(ols=f(ols_dose(d)), ppml=f(ppml_dose(d)), zero_cells=int((d["count"] == 0).sum()))


def kbin(a, b):
    a, b = np.asarray(a) >= 3, np.asarray(b) >= 3
    po = (a == b).mean(); pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    return dict(kappa=round(float((po - pe) / (1 - pe)), 4), agree=round(float(po), 4), n=int(len(a)))


def load_scores(path):
    return {int(r["question_id"]): int(r["score"]) for r in csv.DictReader(io.open(path, encoding="utf-8"))}


s46 = {int(r["question_id"]): int(r["score"]) for r in rows}
s5 = load_scores(os.path.join(A, "question_labels_python_blind.csv"))
orig = {}
for fn in ("question_labels_python_2021-2024.csv", "question_labels_python_ext_2024-07_2026-05.csv"):
    orig.update(load_scores(os.path.join(DATA, fn)))
assert set(s46) == set(s5) and set(s46) <= set(orig)

Aa = {int(r["order"]): int(r["score_0_4"]) for r in csv.DictReader(io.open(os.path.join(GS, "coding_sheet_A_v2.csv"), encoding="utf-8-sig"))}
Bb = {int(r["order"]): int(r["score_0_4"]) for r in csv.DictReader(io.open(os.path.join(GS, "coding_sheet_B_v2.csv"), encoding="utf-8-sig"))}
adj = {int(r["order"]): int(r["consensus_0_4"]) for r in csv.DictReader(io.open(os.path.join(GS, "裁决记录表.csv"), encoding="utf-8-sig"))}
q_of = {s["order_v2"]: int(s["question_id"]) for s in json.load(io.open(os.path.join(GS, "gold_sample_v2_order.json"), encoding="utf-8"))}
cons = {q_of[o]: (int(Aa[o] >= 3) * 3 if (Aa[o] >= 3) == (Bb[o] >= 3) else (3 if adj[o] >= 3 else 0)) for o in range(1, 301)}
ks = sorted(cons)

# ---------------------------------------------------------------- 自证
w0 = pd.read_csv(os.path.join(DATA, "within_so_llm_panel_python.csv"))
H0 = headline(w0)
assert round(H0["ols"]["coef"], 3) == -0.416, H0["ols"]
k0 = kbin([orig[q] for q in ks], [cons[q] for q in ks])
assert round(k0["kappa"], 3) == 0.512, k0
RA = json.load(io.open(os.path.join(WD, "R2_analyze_result.json"), encoding="utf-8"))
H5 = headline(pd.read_csv(os.path.join(A, "within_so_llm_panel_python_blind.csv")))
for k in ("ols", "ppml"):
    assert H5[k]["coef"] == RA["blind"][k]["coef"] and H5[k]["se"] == RA["blind"][k]["se"], (k, H5[k], RA["blind"][k])
k5 = kbin([s5[q] for q in ks], [cons[q] for q in ks])
assert k5["kappa"] == RA["kappa"]["blind_vs_consensus"][0], (k5, RA["kappa"]["blind_vs_consensus"])
print("自证通过:原标签 γ %+.4f、κ %.3f;Sonnet 5 盲标签复现 A 臂 OLS %+.4f、PPML %+.4f、κ %.4f"
      % (H0["ols"]["coef"], k0["kappa"], H5["ols"]["coef"], H5["ppml"]["coef"], k5["kappa"]))

# ---------------------------------------------------------------- ① 对原分类
qs = sorted(s46)
ym_of = {int(r["question_id"]): r["ym"] for r in rows}
g = np.array([ym_of[q] for q in qs])
post = np.array([int(ym_int(m) >= EVENT) for m in g], float)
months_pre = sorted({m for m in g if ym_int(m) < EVENT}); months_post = sorted({m for m in g if ym_int(m) >= EVENT})
d_score = np.array([orig[q] - s46[q] for q in qs], float)
d_bin = np.array([int(orig[q] >= 3) - int(s46[q] >= 3) for q in qs], float)


def did(v):
    f = sm.OLS(v, sm.add_constant(post)).fit(cov_type="cluster", cov_kwds={"groups": g})
    b, se = f.params[1], f.bse[1]
    a = [v[g == m].mean() for m in months_pre]; c = [v[g == m].mean() for m in months_post]
    t = stats.ttest_ind(c, a, equal_var=False)
    va, vc = np.var(a, ddof=1) / len(a), np.var(c, ddof=1) / len(c)
    dfw = (va + vc) ** 2 / (va ** 2 / (len(a) - 1) + vc ** 2 / (len(c) - 1))
    hw = stats.t.ppf(0.975, dfw) * np.sqrt(va + vc)
    return dict(mean_pre=round(float(v[post == 0].mean()), 4), mean_post=round(float(v[post == 1].mean()), 4),
                diff=round(float(b), 4), se_cluster=round(float(se), 4), p_cluster=float(f.pvalues[1]),
                ci_normal=[round(float(b - 1.96 * se), 4), round(float(b + 1.96 * se), 4)],
                ci_welch=[round(float(np.mean(c) - np.mean(a) - hw), 4), round(float(np.mean(c) - np.mean(a) + hw), 4)],
                p_welch=float(t.pvalue), n=int(len(v)), months_pre=len(months_pre), months_post=len(months_post))


R = dict(note="设计书第 13 条(二)预设三项;d = 原分(看得见日期) − Sonnet 4.6 盲分")
R["self_check"] = dict(original_ols=H0["ols"]["coef"], original_kappa_consensus=k0["kappa"],
                       sonnet5_blind_ols=H5["ols"]["coef"], sonnet5_blind_ppml=H5["ppml"]["coef"],
                       sonnet5_blind_kappa_consensus=k5["kappa"])
R["s46_vs_original"] = dict(exact_agree=round(float(np.mean(d_score == 0)), 4),
                            kbin=kbin([s46[q] for q in qs], [orig[q] for q in qs]),
                            d_score=did(d_score), d_binary=did(d_bin))
# ---------------------------------------------------------------- ② 对 Sonnet 5 盲标签
R["s46_vs_sonnet5_blind"] = dict(kbin=kbin([s46[q] for q in qs], [s5[q] for q in qs]))
# ---------------------------------------------------------------- ③ 头条与对共识 κ
w46 = pd.read_csv(os.path.join(HERE, "within_so_llm_panel_python_blind_s46.csv"))
R["headline_s46"] = headline(w46)
R["headline_reference"] = dict(original=H0, sonnet5_blind=H5)
R["kappa_vs_consensus"] = dict(s46=kbin([s46[q] for q in ks], [cons[q] for q in ks]), original=k0, sonnet5_blind=k5)
tot = w46[["s%d" % i for i in range(5)]].sum()
R["s46_bin_counts"] = {k: int(v) for k, v in tot.items()}
# ---------------------------------------------------------------- 每批写出模型与重派次数
V = json.load(io.open(os.path.join(HERE, "R2s46_verify_result.json"), encoding="utf-8"))
R["batches"] = {nn: dict(writer_model=b["last_writer_model"], all_models=b["last_writer_all_models"],
                         reruns=b["n_sessions"] - 1, accept=b["accept"]) for nn, b in V["batches"].items()}
R["batches_summary"] = dict(n_accept=V["n_accept"], writer_models=sorted({b["last_writer_model"] for b in V["batches"].values()}),
                            reruns={nn: b["n_sessions"] - 1 for nn, b in V["batches"].items() if b["n_sessions"] > 1})

io.open(os.path.join(HERE, "R2s46_analyze_result.json"), "w", encoding="utf-8").write(json.dumps(R, indent=1, ensure_ascii=False))

o = R["s46_vs_original"]
print("① 对原分类:精确一致 %.1f%%;二元 κ %.4f(一致 %.1f%%,N=%d)"
      % (100 * o["exact_agree"], o["kbin"]["kappa"], 100 * o["kbin"]["agree"], o["kbin"]["n"]))
for k in ("d_score", "d_binary"):
    s = o[k]
    print("   %-8s 事件前 %+.4f 事件后 %+.4f 差 %+.4f 正态 [%+.4f, %+.4f] p=%.3g  Welch [%+.4f, %+.4f] p=%.3g  (%d+%d 月)"
          % (k, s["mean_pre"], s["mean_post"], s["diff"], *s["ci_normal"], s["p_cluster"], *s["ci_welch"], s["p_welch"],
             s["months_pre"], s["months_post"]))
k = R["s46_vs_sonnet5_blind"]["kbin"]
print("② 对 Sonnet 5 盲标签:二元 κ %.4f(一致 %.1f%%,N=%d)" % (k["kappa"], 100 * k["agree"], k["n"]))
for m in ("ols", "ppml"):
    h = R["headline_s46"][m]
    print("③ %-4s γ %+.4f (SE %.4f, p=%.3g, CI [%+.4f, %+.4f])" % (m, h["coef"], h["se"], h["p"], *h["ci"]))
k = R["kappa_vs_consensus"]["s46"]
print("③ 对人工共识:二元 κ %.4f(一致 %.1f%%,N=%d)" % (k["kappa"], 100 * k["agree"], k["n"]))
print("零格 %d;分档 %s" % (R["headline_s46"]["zero_cells"], R["s46_bin_counts"]))
print("批次:接受 %d/50;写出模型 %s;重派 %s" % (R["batches_summary"]["n_accept"], R["batches_summary"]["writer_models"],
                                          R["batches_summary"]["reruns"]))
