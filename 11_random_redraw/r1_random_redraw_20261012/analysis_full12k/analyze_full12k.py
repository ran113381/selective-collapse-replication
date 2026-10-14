# -*- coding: utf-8 -*-
"""analyze_full12k.py -- P9b 审稿问题1：全量 12,000 题盲评结果分析（只计算、只描述）。
第0步闸门(sha、全量校验、口径复现)任一不过 -> 打印 GATE FAIL 并退出，不出任何汇总数字。
口径来源(逐行复制，见各函数注释)：
  OLS/二分: E:\\智能体论文\\P9b_OSF_复现包_20260920\\01_panels_and_classification\\run_within_so_llm.py  (OLS [1]、二分 [2])
  PPML    : ...\\02_estimation\\phaseA_composition.py  (ppml_dose; pyfixest.fepois, CRV1 按月)
  NW 对数比: 同上 logratio_nw
用法: D:/python.exe analyze_full12k.py
"""
# 包内副本改动(2026-10-13): 路径改为相对包根; 面板映射(rate_private\panel_map_full12k.json)不随包发布, 改读 derived\labels_by_question_full12k.csv;
# 闸门2 改为核标签文件自身+派生表; 口径函数、闸门3、bootstrap 与输出段未动。
import csv, hashlib, io, json, os, sys
from collections import Counter
import numpy as np
import pandas as pd
import statsmodels.api as sm
import pyfixest as pf

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.dirname(HERE)
WD = os.path.dirname(R)
PKG = os.path.dirname(WD)   # 包内改动: 包根目录(原为硬编码的 E:\ 路径)
LAB = os.path.join(WD, "R3_blind", "set12k")
DT = os.path.join(WD, "derived", "labels_by_question_full12k.csv")   # 包内改动: 原读 rate_private\panel_map_full12k.json(映射不随包发布), 改读按题号派生表
VLOG = os.path.join(R, "subagent_run", "full12k", "all100_verify.log")
PUB = os.path.join(PKG, "07_blind_reclassification", "labels", "question_labels_python_blind.csv")
PUBPANEL = os.path.join(PKG, "07_blind_reclassification", "labels", "within_so_llm_panel_python_blind.csv")
SRC_OLS = os.path.join(PKG, "01_panels_and_classification", "run_within_so_llm.py")
SRC_PPML = os.path.join(PKG, "02_estimation", "phaseA_composition.py")
EVENT = "2022-12"
SEED = 20261013
NBOOT = 2000
K = 5


def sha12(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]


def gate_fail(msg):
    print("GATE FAIL:", msg)
    sys.exit(1)


def ym_to_int(ym):
    y, m = (int(x) for x in str(ym).split("-"))
    return y * 12 + (m - 1)


E_INT = ym_to_int(EVENT)

# ---------------- 第0步 闸门 1: sha ----------------
print("script sha12 (self):", sha12(os.path.abspath(__file__)))
for p, want in ((DT, "dc2f07ad7c85"), (VLOG, "148bcf743f19")):
    got = sha12(p)
    print("sha12 %s = %s (want %s)" % (os.path.relpath(p, R), got, want))
    if got != want: gate_fail("sha mismatch " + p)
print("口径来源脚本 sha12: run_within_so_llm.py=%s  phaseA_composition.py=%s" % (sha12(SRC_OLS), sha12(SRC_PPML)))
print("发表标签 question_labels_python_blind.csv sha12=%s ; 发表月面板 within_so_llm_panel_python_blind.csv sha12=%s" % (sha12(PUB), sha12(PUBPANEL)))

# ---------------- 闸门 2: 全量校验 ----------------
tab = list(csv.DictReader(io.open(DT, encoding="utf-8")))
labels = {}  # id -> row (评分者编号 -> 标签行; 包内无映射, 此处只核标签文件自身, 再与派生表核分布)
nprob = []
for k in range(1, 101):
    lp = os.path.join(LAB, "labels_batch_%03d.json" % k)
    bp = os.path.join(LAB, "blind_batch_%03d.json" % k)
    if not os.path.exists(lp): nprob.append(("missing labels", k)); continue
    try:
        arr = json.load(io.open(lp, encoding="utf-8"))
    except Exception as e:
        nprob.append(("bad json", k, str(e)[:60])); continue
    bin_ids = [r["id"] for r in json.loads(open(bp, "rb").read().decode("utf-8"))]
    out_ids = [r.get("id") for r in arr]
    if len(out_ids) != len(bin_ids): nprob.append(("count", k, len(bin_ids), len(out_ids)))
    if sorted(out_ids) != sorted(bin_ids): nprob.append(("id set", k))
    for r in arr:
        i = r.get("id"); s = r.get("score")
        if not (isinstance(s, int) and not isinstance(s, bool) and 0 <= s <= 4): nprob.append(("bad score", i, s))
        elif r.get("label") != ("GEN" if s >= 3 else "VER"): nprob.append(("label/score", i, s, r.get("label")))
        if i in labels: nprob.append(("duplicate", i))
        labels[i] = r
print("labels files checked 100; total rated ids:", len(labels), "; problems:", len(nprob), nprob[:5])
if nprob or len(labels) != 12000: gate_fail("validation problems %s" % nprob[:5])
rows = [(r["panel"], r["ym"], int(r["question_id"]), int(r["score"]), r["label"]) for r in tab]
if len(rows) != 12000 or len({(p_, q_) for p_, _, q_, _, _ in rows}) != 12000: gate_fail("derived table: rows / unique (panel,question_id)")
if {p_ for p_, _, _, _, _ in rows} != {"panel", "redraw"}: gate_fail("derived table: panel values")
if any(l_ != ("GEN" if s_ >= 3 else "VER") for _, _, _, s_, l_ in rows): gate_fail("derived table: label/score")
cell = Counter((p_, y_) for p_, y_, _, _, _ in rows)
months = sorted({y_ for _, y_, _, _, _ in rows})
print("months:", len(months), months[0], months[-1], "; panel x ym cells:", len(cell), "; cell sizes set:", sorted(set(cell.values())))
if len(months) != 60 or len(cell) != 120 or set(cell.values()) != {100}: gate_fail("panel cell counts")
if Counter(v["score"] for v in labels.values()) != Counter(s_ for _, _, _, s_, _ in rows): gate_fail("score distribution: label files != derived table")
print("GATE 2 PASS: 100 files, 12000 ids once each, 120 cells x 100; label-file score distribution == derived table")

# 面板分数表
old_rows = [r for r in rows if r[0] == "panel"]    # 旧面板(映射中 old)
new_rows = [r for r in rows if r[0] == "redraw"]   # 本轮随机重抽(映射中 new)
pub = {}
for r in csv.DictReader(io.open(PUB, encoding="utf-8")):
    pub[int(r["question_id"])] = (int(r["score"]), r["label"], r["ym"])
if len(pub) != 6000 or {r[2] for r in old_rows} != set(pub): gate_fail("old panel question ids != published label ids")
if any(pub[r[2]][2] != r[1] for r in old_rows): gate_fail("ym mismatch old vs published")
for q, (s, l, y) in pub.items():
    if l != ("GEN" if s >= 3 else "VER"): gate_fail("published label/score mismatch %s" % q)


def make_panel(rows):
    """rows: iterable of (ym, score) -> panel DataFrame 同 aggregate_labels.py 输出结构 (ym,n,GEN,VER,gen_share,s0..s4)。"""
    by = {}
    for ym, s in rows:
        d = by.setdefault(ym, Counter()); d["n"] += 1; d["GEN" if s >= 3 else "VER"] += 1; d["s%d" % s] += 1
    out = []
    for ym in sorted(by):
        d = by[ym]
        out.append({"ym": ym, "n": d["n"], "GEN": d["GEN"], "VER": d["VER"], "gen_share": round(d["GEN"] / d["n"], 4),
                    **{"s%d" % b: d.get("s%d" % b, 0) for b in range(5)}})
    return pd.DataFrame(out)


# ---------------- 口径: 逐行复制自 run_within_so_llm.py / phaseA_composition.py ----------------
def long_panel(w):
    """复制自 phaseA_composition.long_panel；bin = score==b 的题数 s_b(b=1..4)，s0 丢弃；post = ym>=2022-12。"""
    recs = []
    for _, r in w.iterrows():
        t = ym_to_int(r["ym"])
        for b in (1, 2, 3, 4):
            recs.append({"ym": r["ym"], "t": t, "score": b, "count": int(r[f"s{b}"]), "post": int(t >= E_INT)})
    d = pd.DataFrame(recs)
    d["dose"] = d["score"] * d["post"]
    return d


def est_ols(w):
    """复制自 run_within_so_llm.py [1]: log(count) ~ score*post + bin_FE + month_FE, 月聚类; 零格直接 assert 失败(不裁剪)。"""
    d = long_panel(w)
    assert (d["count"] > 0).all(), f"zero in s1-s4 (min={d['count'].min()})"
    d["y"] = np.log(d["count"].astype(float))
    bin_d = pd.get_dummies(d["score"], prefix="b", drop_first=True).astype(float)
    ym_d = pd.get_dummies(d["ym"], prefix="m", drop_first=True).astype(float)
    X = sm.add_constant(pd.concat([d[["dose"]].astype(float), bin_d, ym_d], axis=1))
    res = sm.OLS(d["y"].to_numpy(), X.to_numpy()).fit(cov_type="cluster", cov_kwds={"groups": d["ym"].to_numpy()})
    gi = list(X.columns).index("dose")
    return float(res.params[gi]), float(res.bse[gi]), float(res.pvalues[gi])


def est_bin(w):
    """复制自 run_within_so_llm.py [2]: log(count) ~ gen*post + gen_FE + month_FE, GEN=score>=3, VER=其余(含 s0), 月聚类。"""
    recs2 = []
    for _, r in w.iterrows():
        recs2.append({"ym": r["ym"], "gen": 1, "count": int(r["GEN"])})
        recs2.append({"ym": r["ym"], "gen": 0, "count": int(r["VER"])})
    b2 = pd.DataFrame(recs2)
    b2["s"] = b2["ym"].map(ym_to_int)
    b2["post"] = (b2["s"] >= E_INT).astype(int)
    b2["y"] = np.log(b2["count"].astype(float))
    b2["gp"] = b2["gen"] * b2["post"]
    g_d = pd.get_dummies(b2["gen"], prefix="g", drop_first=True).astype(float)
    m_d = pd.get_dummies(b2["ym"], prefix="m", drop_first=True).astype(float)
    X2 = sm.add_constant(pd.concat([b2[["gp"]].astype(float), g_d, m_d], axis=1))
    res2 = sm.OLS(b2["y"].to_numpy(), X2.to_numpy()).fit(cov_type="cluster", cov_kwds={"groups": b2["ym"].to_numpy()})
    bi = list(X2.columns).index("gp")
    return float(res2.params[bi]), float(res2.bse[bi]), float(res2.pvalues[bi])


def est_ppml(w):
    """复制自 phaseA_composition.ppml_dose: pyfixest.fepois('count ~ dose | score + ym', CRV1 按月)。"""
    d = long_panel(w)
    m = pf.fepois("count ~ dose | score + ym", data=d, vcov={"CRV1": "ym"})
    return float(m.coef().iloc[0]), float(m.se().iloc[0]), float(m.pvalue().iloc[0])


def est_nw(w):
    """复制自 phaseA_composition.logratio_nw: log((s4+.5)/(s1+.5)) ~ post, HAC maxlags=6。"""
    d = w.copy(); d["t"] = d["ym"].map(ym_to_int)
    d["post"] = (d["t"] >= E_INT).astype(int)
    d["lr"] = np.log((d["s4"] + 0.5) / (d["s1"] + 0.5))
    X = sm.add_constant(d[["post"]].astype(float))
    r = sm.OLS(d["lr"].to_numpy(), X.to_numpy()).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    return float(r.params[1]), float(r.bse[1]), float(r.pvalues[1])


# ---------------- 闸门 3: 用发表标签复现 ----------------
wA = make_panel((pub[q][2], pub[q][0]) for q in pub)
wP = pd.read_csv(PUBPANEL)
same = all((wA[c].astype(float).values == wP[c].astype(float).values).all() for c in ["n", "GEN", "VER", "s0", "s1", "s2", "s3", "s4"]) and list(wA.ym) == list(wP.ym)
print("发表标签重建面板 == 包内发表月面板:", same)
if not same: gate_fail("rebuilt published panel != within_so_llm_panel_python_blind.csv")
rep = {"ols": est_ols(wA), "bin": est_bin(wA), "ppml": est_ppml(wA), "nw": est_nw(wA)}
print("复现(发表标签): OLS γ=%.4f SE %.4f p %.4g | bin β=%.4f SE %.4f | PPML γ=%.4f SE %.4f | NW β=%.4f SE %.4f"
      % (rep["ols"][0], rep["ols"][1], rep["ols"][2], rep["bin"][0], rep["bin"][1], rep["ppml"][0], rep["ppml"][1], rep["nw"][0], rep["nw"][1]))
tgt = {"ols": (-0.3038, 0.0379), "bin": (-0.6100, 0.1031), "ppml": (-0.2872, 0.0326), "nw": (-0.8935, 0.1168)}  # 包内日志 run_within_so_llm.log / phaseA_composition.log 原文
for k, (g, s) in tgt.items():
    if round(rep[k][0], 4) != g or round(rep[k][1], 4) != s: gate_fail("reproduction %s: got %.4f/%.4f want %.4f/%.4f" % (k, rep[k][0], rep[k][1], g, s))
assert round(rep["ols"][0], 2) == -0.30 and round(rep["ols"][1], 2) == 0.04 and round(rep["ols"][0], 3) == -0.304
assert round(rep["bin"][0], 2) == -0.61 and round(rep["bin"][1], 2) == 0.10
assert round(rep["ppml"][0], 2) == -0.29 and round(rep["ppml"][1], 2) == 0.03
print("GATE 3 PASS: 复现到正文位数 (OLS -0.30(0.04)/-0.304, bin -0.61(0.10), PPML -0.29(0.03)) 且四位小数与包内日志一致")

# ---------------- 数据: 三列 A/B/C ----------------
rowsA = [(pub[q][2], pub[q][0]) for q in pub]
rowsB = [(r[1], r[3]) for r in old_rows]
rowsC = [(r[1], r[3]) for r in new_rows]
P = {"A": make_panel(rowsA), "B": make_panel(rowsB), "C": make_panel(rowsC)}
for c in P:
    cnt = P[c][["s1", "s2", "s3", "s4"]].values
    print("面板 %s: 月数 %d, n=%d, s1..s4 最小格=%d, 零格数=%d" % (c, len(P[c]), P[c].n.sum(), cnt.min(), int((cnt == 0).sum())))
    if (cnt == 0).any(): gate_fail("zero cell in panel " + c + " (原口径 assert 不允许零格)")

# ---------------- 第1步 一致性 ----------------
def wkappa(a, b, kind):
    n = len(a)
    O = [[0] * K for _ in range(K)]
    for x, y in zip(a, b): O[x][y] += 1
    ra = [sum(O[i]) for i in range(K)]; cb = [sum(O[i][j] for i in range(K)) for j in range(K)]
    w = lambda i, j: abs(i - j) if kind == "linear" else (i - j) ** 2
    num = sum(w(i, j) * O[i][j] for i in range(K) for j in range(K))
    den = sum(w(i, j) * ra[i] * cb[j] / n for i in range(K) for j in range(K))
    return 1 - num / den


def kappa2(a, b):
    n = len(a); po = sum(x == y for x, y in zip(a, b)) / n
    pa = Counter(a); pb = Counter(b)
    pe = sum(pa[k] * pb[k] for k in set(pa) | set(pb)) / n ** 2
    return (po - pe) / (1 - pe)


def agree(pairs):
    a = [x for x, _ in pairs]; b = [y for _, y in pairs]
    ba = [int(x >= 3) for x in a]; bb = [int(y >= 3) for y in b]
    return dict(n=len(pairs), exact=sum(x == y for x, y in pairs) / len(pairs), within1=sum(abs(x - y) <= 1 for x, y in pairs) / len(pairs),
                label=sum(x == y for x, y in zip(ba, bb)) / len(pairs), kappa_lin=wkappa(a, b, "linear"),
                kappa_quad=wkappa(a, b, "quadratic"), kappa_gen=kappa2(ba, bb))


pairs = [(pub[r[2]][0], r[3], r[1]) for r in old_rows]
cons = {"all": agree([(x, y) for x, y, _ in pairs]),
        "pre(<2022-12)": agree([(x, y) for x, y, m in pairs if m < EVENT]),
        "post(>=2022-12)": agree([(x, y) for x, y, m in pairs if m >= EVENT])}
Cm = [[0] * K for _ in range(K)]
for x, y, _ in pairs: Cm[x][y] += 1
with io.open(os.path.join(HERE, "consistency_by_month.csv"), "w", encoding="utf-8", newline="") as f:
    wr = csv.writer(f); wr.writerow(["ym", "n", "label_agree", "exact", "within1"])
    for ym in months:
        p = [(x, y) for x, y, m in pairs if m == ym]
        wr.writerow([ym, len(p), "%.4f" % (sum((x >= 3) == (y >= 3) for x, y in p) / len(p)), "%.4f" % (sum(x == y for x, y in p) / len(p)),
                     "%.4f" % (sum(abs(x - y) <= 1 for x, y in p) / len(p))])

# ---------------- 第2步 逐月 GEN 比例 / 平均分 ----------------
def monthly(w):
    n = w.n.values.astype(float)
    return dict(zip(w.ym, (w.s3 + w.s4) / n)), dict(zip(w.ym, (sum(w["s%d" % b] * b for b in range(5))) / n))


M = {c: monthly(P[c]) for c in P}
with io.open(os.path.join(HERE, "gen_share_by_month.csv"), "w", encoding="utf-8", newline="") as f:
    wr = csv.writer(f); wr.writerow(["ym", "post", "A_gen", "A_mean", "B_gen", "B_mean", "C_gen", "C_mean"])
    for ym in months:
        wr.writerow([ym, int(ym >= EVENT)] + sum([["%.4f" % M[c][0][ym], "%.4f" % M[c][1][ym]] for c in "ABC"], []))
pp = {}
for c in "ABC":
    for j, nm in ((0, "gen"), (1, "mean")):
        pre = np.mean([M[c][j][m] for m in months if m < EVENT]); post = np.mean([M[c][j][m] for m in months if m >= EVENT])
        pp[(c, nm)] = (pre, post, post - pre)
npre = sum(m < EVENT for m in months)

# ---------------- 第3步 重估 γ ----------------
G = {}
for c in "ABC":
    G[c] = {"ols": est_ols(P[c]), "bin": est_bin(P[c]), "ppml": est_ppml(P[c]), "nw": est_nw(P[c])}

# bootstrap: 按月整块重抽，同一组月份同时算 B、C
def month_arrays(w):
    return np.array([ym_to_int(y) >= E_INT for y in w.ym], dtype=float), w[["s0", "s1", "s2", "s3", "s4", "GEN", "VER"]].values.astype(float)


def fast_est(post, cnt):
    """点估计(无聚类)；同一口径的 OLS/二分/Poisson，重抽的各月各自带月固定效应(重复月为独立 FE，点估计与共享 FE 相同)。"""
    Mn = len(post)
    # 4-bin 长表: 行顺序 月×bin
    sc = np.tile(np.arange(1, 5), Mn); mi = np.repeat(np.arange(Mn), 4)
    cnt4 = cnt[:, 1:5].reshape(-1)
    dose = sc * post[mi]
    bins = (sc[:, None] == np.arange(2, 5)[None, :]).astype(float)
    mons = (mi[:, None] == np.arange(1, Mn)[None, :]).astype(float)
    X = np.column_stack([np.ones(len(sc)), dose, bins, mons])
    ols = np.linalg.lstsq(X, np.log(cnt4), rcond=None)[0][1]
    ppm = sm.GLM(cnt4, X, family=sm.families.Poisson()).fit().params[1]
    # 二分: 行 月×(ver,gen)
    gen = np.tile([0, 1], Mn); mi2 = np.repeat(np.arange(Mn), 2)
    cnt2 = cnt[:, [6, 5]].reshape(-1)
    X2 = np.column_stack([np.ones(len(gen)), gen * post[mi2], gen, (mi2[:, None] == np.arange(1, Mn)[None, :]).astype(float)])
    bn = np.linalg.lstsq(X2, np.log(cnt2), rcond=None)[0][1]
    return ols, bn, ppm


postB, cntB = month_arrays(P["B"]); postC, cntC = month_arrays(P["C"])
assert list(P["B"].ym) == list(P["C"].ym)
# 自检：快速估计量 == 原口径点估计
for c, (po, ct) in (("B", (postB, cntB)), ("C", (postC, cntC))):
    f = fast_est(po, ct)
    assert abs(f[0] - G[c]["ols"][0]) < 1e-8 and abs(f[1] - G[c]["bin"][0]) < 1e-8 and abs(f[2] - G[c]["ppml"][0]) < 1e-5, (c, f, G[c])
print("fast_est 自检通过：与原口径点估计一致(OLS/二分 1e-8，PPML 1e-5)")
rng = np.random.default_rng(SEED)
Mn = len(postB)
bs = np.zeros((NBOOT, 6))
for r in range(NBOOT):
    idx = rng.integers(0, Mn, Mn)
    fb = fast_est(postB[idx], cntB[idx]); fc = fast_est(postC[idx], cntC[idx])
    bs[r] = [fb[0], fc[0], fb[1], fc[1], fb[2], fc[2]]
with io.open(os.path.join(HERE, "bootstrap_draws.csv"), "w", encoding="utf-8", newline="") as f:
    wr = csv.writer(f); wr.writerow(["ols_B", "ols_C", "bin_B", "bin_C", "ppml_B", "ppml_C"])
    for row in bs: wr.writerow(["%.6f" % v for v in row])
boot = {}
for j, nm in ((0, "ols"), (2, "bin"), (4, "ppml")):
    dlt = bs[:, j + 1] - bs[:, j]
    pt = G["C"][nm][0] - G["B"][nm][0]
    boot[nm] = dict(point=pt, sd=float(dlt.std(ddof=1)), lo=float(np.percentile(dlt, 2.5)), hi=float(np.percentile(dlt, 97.5)), mean=float(dlt.mean()))

# ---------------- RESULTS ----------------
print("\n=== RESULTS ===")
print("seed=%d nboot=%d; bootstrap 按月整块重抽(60月有放回)，同一组月份同时算 B 与 C；新旧面板 326 题同题号重叠，按月重抽已天然处理(两面板各自按月整块进出，未做按题去重)" % (SEED, NBOOT))
print("口径: bin_b=score==b 的题数(b=1..4, s0 丢弃); GEN=score>=3, VER=其余含 s0; post=ym>=%s (前期%d月/后期%d月); 零格: 原口径 assert count>0(本次三面板零格数均为0); 聚类=月; PPML=pyfixest fepois 'count~dose|score+ym' CRV1 月" % (EVENT, npre, len(months) - npre))
print("复现(发表标签) OLS γ=%.4f(%.4f) p=%.3g | bin β=%.4f(%.4f) | PPML γ=%.4f(%.4f) | NW β=%.4f(%.4f)" % (
    rep["ols"][0], rep["ols"][1], rep["ols"][2], rep["bin"][0], rep["bin"][1], rep["ppml"][0], rep["ppml"][1], rep["nw"][0], rep["nw"][1]))
print("-- 第1步 一致性 (旧面板 6000 题: 本次重评 vs 原发表标签) --")
for k, v in cons.items():
    print("CONS %-16s n=%d exact=%.4f within1=%.4f label=%.4f kappa_lin=%.4f kappa_quad=%.4f kappa_GEN=%.4f" % (
        k, v["n"], v["exact"], v["within1"], v["label"], v["kappa_lin"], v["kappa_quad"], v["kappa_gen"]))
print("CONF5x5 rows=published 0..4, cols=rerun 0..4:")
for i, r in enumerate(Cm): print("   ", i, r)
print("-- 第2步 逐月 GEN 比例与平均分(月度未加权均值; 前期%d月/后期%d月) --" % (npre, len(months) - npre))
for c, nm in (("A", "旧面板·原发表标签"), ("B", "旧面板·本次重评"), ("C", "新面板·本次重评")):
    g = pp[(c, "gen")]; m = pp[(c, "mean")]
    print("GEN %s %-14s 前期=%.4f 后期=%.4f 后-前=%+.4f | 平均分 前期=%.4f 后期=%.4f 后-前=%+.4f" % (c, nm, g[0], g[1], g[2], m[0], m[1], m[2]))
print("-- 第3步 γ (log-count OLS / binary GEN-VER / FE-PPML; 月聚类 SE) --")
for c, nm in (("A", "旧面板·原发表标签"), ("B", "旧面板·本次重评"), ("C", "新面板·本次重评")):
    o, b, p, n = G[c]["ols"], G[c]["bin"], G[c]["ppml"], G[c]["nw"]
    print("GAMMA %s %-14s OLS γ=%+.4f SE %.4f p %.3g | bin β=%+.4f SE %.4f p %.3g | PPML γ=%+.4f SE %.4f p %.3g" % (c, nm, o[0], o[1], o[2], b[0], b[1], b[2], p[0], p[1], p[2]))
    print("S4S1  %s s4-vs-s1 post: exp(3γ_OLS)-1=%+.1f%%  exp(3γ_PPML)-1=%+.1f%%  | NW log((s4+.5)/(s1+.5)) post β=%+.4f SE %.4f p %.3g" % (
        c, 100 * (np.exp(3 * o[0]) - 1), 100 * (np.exp(3 * p[0]) - 1), n[0], n[1], n[2]))
print("-- C - B (bootstrap 95% 百分位区间; 点差=全样本 γ_C-γ_B) --")
for nm in ("ols", "bin", "ppml"):
    b = boot[nm]
    print("DIFF %-5s γ_C-γ_B=%+.4f  boot mean %+.4f sd %.4f  95%% CI [%+.4f, %+.4f]" % (nm, b["point"], b["mean"], b["sd"], b["lo"], b["hi"]))
print("=== END RESULTS ===")
json.dump({"G": {c: {k: list(v) for k, v in G[c].items()} for c in G}, "boot": boot, "cons": cons, "pp": {"%s_%s" % k: v for k, v in pp.items()}},
          io.open(os.path.join(HERE, "result_full12k.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
