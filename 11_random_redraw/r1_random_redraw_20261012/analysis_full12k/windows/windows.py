# -*- coding: utf-8 -*-
"""[包内副本: 删稿件 sha 断言、路径改相对包根、删窗口内重抽区间; 估计量与闸门未动]
windows.py -- P9b 问题1 写回前补算: 按时段/按月估计在三列面板(A/B/C)上各算一遍。只算、只描述。
A=旧面板·原发表标签  B=旧面板·本次重评  C=随机面板·本次重评。面板构造/标签/映射 = analyze_full12k.py 的闸门+面板段(原样 exec，不重写)。
各估计量口径移植自(OSF 复现包)：
  02_estimation/capability_ramp.py (windowed / event_study), review_r1_reviewer_response_scripts/p0_6_pretrends.py,
  p0_6_ref_sensitivity.py, p0_3_placebo_overlap.py, p1_parallel_trends_sensitivity.py;
  01_panels_and_classification/run_within_so_llm.py (前期领先项线性斜率); 09_downstream_rerun/scripts/R2d_extra.py §4 (窗口等同检验)。
原脚本读面板文件，这里改读 P[c]（同结构的月×bin计数面板）；先用 A 复现盲臂日志里的数字，复现不到的项跳过。
用法: D:/python.exe windows.py
"""
import csv, hashlib, io, json, os, sys, warnings
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

warnings.simplefilter("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
AN = os.path.dirname(HERE)
SRC = os.path.join(AN, "analyze_full12k.py")
MARK = "# ---------------- 第1步 一致性"
txt = io.open(SRC, encoding="utf-8").read()
assert hashlib.sha256(open(SRC, "rb").read()).hexdigest()[:12] == "87e222d0c7c9", "analyze_full12k.py sha mismatch"
assert MARK in txt
prefix = txt[:txt.index(MARK)]
G0 = {"__file__": SRC, "__name__": "analyze_prefix"}
exec(compile(prefix, SRC, "exec"), G0)   # 闸门1-3 + 三列面板 P（原样）
P = G0["P"]
ym_to_int = G0["ym_to_int"]
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
PKG = G0["PKG"]   # 包内改动: 包根目录(由 analyze_full12k.py 前段给出)
BLOUT = os.path.join(PKG, "09_downstream_rerun", "blind", "outputs", "within_so_llm_eventstudy.csv")
SRCS = [os.path.join(PKG, "02_estimation", "capability_ramp.py"),
        os.path.join(PKG, "02_estimation", "review_r1_reviewer_response_scripts", "p0_6_pretrends.py"),
        os.path.join(PKG, "02_estimation", "review_r1_reviewer_response_scripts", "p0_6_ref_sensitivity.py"),
        os.path.join(PKG, "02_estimation", "review_r1_reviewer_response_scripts", "p0_3_placebo_overlap.py"),
        os.path.join(PKG, "02_estimation", "review_r1_reviewer_response_scripts", "p1_parallel_trends_sensitivity.py"),
        os.path.join(PKG, "01_panels_and_classification", "run_within_so_llm.py"),
        os.path.join(PKG, "09_downstream_rerun", "scripts", "R2d_extra.py")]
print("原脚本 sha12:")
for s in SRCS:
    print("  %s  %s" % (hashlib.sha256(open(s, "rb").read()).hexdigest()[:12], os.path.relpath(s, PKG)))

EVENT = ym_to_int("2022-12"); REF = ym_to_int("2022-11")
def ymi(y): return ym_to_int(y)
def lab(t): return "%04d-%02d" % (t // 12, t % 12 + 1)


def Lof(w):
    d = w.melt(id_vars=["ym"], value_vars=["s1", "s2", "s3", "s4"], var_name="bin", value_name="cnt")
    d["s"] = d["bin"].str[1].astype(int)
    d["t"] = d["ym"].map(ymi)
    d["lc"] = np.log(d["cnt"].clip(lower=1))
    return d

LL = {c: Lof(P[c]) for c in "ABC"}

# ---------------- 估计量(移植) ----------------
POSTW = [("GPT-3.5 only (2022-12..2023-02)", "2022-12", "2023-02"), ("First 6 months (..2023-05)", "2022-12", "2023-05"),
         ("Year 1 (2022-12..2023-11)", "2022-12", "2023-11"), ("Year 2 (2023-12..2024-11)", "2023-12", "2024-11"),
         ("Year 3 (2024-12..2025-11)", "2024-12", "2025-11"), ("Year 4 (2025-12..2026-05)", "2025-12", "2026-05"),
         ("Full post (2022-12..2026-05)", "2022-12", "2026-05")]

def est_post_windows(d):
    out = []
    for name, lo, hi in POSTW:
        lo_, hi_ = ymi(lo), ymi(hi)
        sub = d[(d.t < EVENT) | ((d.t >= lo_) & (d.t <= hi_))].copy()
        sub["post"] = (sub.t >= EVENT).astype(int); sub["sxp"] = sub.s * sub.post
        m = smf.ols("lc ~ sxp + C(bin) + C(ym)", sub).fit(cov_type="cluster", cov_kwds={"groups": sub["ym"]})
        out.append((name, float(m.params["sxp"]), float(m.bse["sxp"]), float(m.pvalues["sxp"])))
    return out

PRE_WINDOWS = [("W1", "sxW1", ymi("2021-06"), ymi("2021-11")), ("W2", "sxW2", ymi("2021-12"), ymi("2022-05")),
               ("W3", "sxW3", ymi("2022-06"), ymi("2022-10"))]

def est_pre_windows(d):
    """p0_6_pretrends [2][3]: 单月参照 2022-11 的三窗口 + 联合 Wald。"""
    pre = d[d.t <= REF].copy()
    for _, col, lo, hi in PRE_WINDOWS:
        pre[col] = pre.s * ((pre.t >= lo) & (pre.t <= hi)).astype(int)
    cols = [c for _, c, _, _ in PRE_WINDOWS]
    m = smf.ols("lc ~ " + " + ".join(cols) + " + C(bin) + C(ym)", pre).fit(cov_type="cluster", cov_kwds={"groups": pre["ym"]})
    beta = np.array([m.params[c] for c in cols]); V = m.cov_params().loc[cols, cols].to_numpy()
    wald = float(beta @ np.linalg.inv(V) @ beta)
    return beta, np.sqrt(np.diag(V)), wald, float(stats.chi2.sf(wald, 3))

def est_ref_variant(d, ref_ts):
    """p0_6_ref_sensitivity.fit_pre_windows: 参照月集合 ref_ts 排出窗口。"""
    pre = d[d.t <= REF].copy()
    wins = [("W1", ymi("2021-06"), ymi("2021-11")), ("W2", ymi("2021-12"), ymi("2022-05")), ("W3", ymi("2022-06"), ymi("2022-10"))]
    act = []
    for n, lo, hi in wins:
        mi = sorted(t for t in pre.t.unique() if lo <= t <= hi and t not in ref_ts)
        if mi: act.append((n, mi))
    for n, mi in act: pre["sx_" + n] = pre.s * pre.t.isin(mi).astype(int)
    cols = ["sx_" + n for n, _ in act]
    m = smf.ols("lc ~ " + " + ".join(cols) + " + C(bin) + C(ym)", pre).fit(cov_type="cluster", cov_kwds={"groups": pre["ym"]})
    beta = np.array([m.params[c] for c in cols]); V = m.cov_params().loc[cols, cols].to_numpy()
    wald = float(beta @ np.linalg.inv(V) @ beta); df = len(beta)
    return dict(names=[n for n, _ in act], nmon=[len(mi) for _, mi in act], beta=beta, se=np.sqrt(np.diag(V)), wald=wald, df=df, p=float(stats.chi2.sf(wald, df)))

def est_v3(d):
    pre = d[d.t <= REF].copy()
    for n, lo, hi in (("W1", ymi("2021-06"), ymi("2021-11")), ("W2", ymi("2021-12"), ymi("2022-05")), ("W3", ymi("2022-06"), ymi("2022-11"))):
        pre["sx_" + n] = pre.s * ((pre.t >= lo) & (pre.t <= hi)).astype(int)
    m = smf.ols("lc ~ sx_W2 + sx_W3 + C(bin) + C(ym)", pre).fit(cov_type="cluster", cov_kwds={"groups": pre["ym"]})
    b = np.array([m.params["sx_W2"], m.params["sx_W3"]]); V = m.cov_params().loc[["sx_W2", "sx_W3"], ["sx_W2", "sx_W3"]].to_numpy()
    w = float(b @ np.linalg.inv(V) @ b)
    return b, np.sqrt(np.diag(V)), w, float(stats.chi2.sf(w, 2))

def ref_zscore(w):
    ww = w.copy(); ww["n4"] = ww.s1 + ww.s2 + ww.s3 + ww.s4
    ww["mean_s"] = (ww.s1 + 2 * ww.s2 + 3 * ww.s3 + 4 * ww.s4) / ww.n4
    nov = ww[ww.ym == "2022-11"].mean_s.iloc[0]
    near = ww[(ww.ym >= "2022-05") & (ww.ym <= "2022-10")].mean_s
    return float(nov), float(near.mean()), float(near.std()), float((nov - near.mean()) / near.std())

def est_eventstudy(d):
    """capability_ramp.event_study (参照 2022-11)."""
    dd = d.copy(); months = sorted(dd.t.unique()); cols = []
    for k in months:
        if k == REF: continue
        c = "k%d" % k; dd[c] = (dd.t == k).astype(int) * dd.s; cols.append(c)
    m = smf.ols("lc ~ " + " + ".join(cols) + " + C(bin) + C(ym)", dd).fit()
    return pd.DataFrame({"t": [int(c[1:]) for c in cols], "gamma_k": [m.params[c] for c in cols]}).assign(k=lambda x: x.t - EVENT)

def lead_slope(es):
    """run_within_so_llm [3] (lstsq 斜率) + check_detrend_ci (OLS SE)."""
    pre = es[es.k <= -2]
    X = np.column_stack([np.ones(len(pre)), pre.k.values.astype(float)]); y = pre.gamma_k.values
    b = np.linalg.lstsq(X, y, rcond=None)[0]; r = y - X @ b
    V = (r @ r) / (len(pre) - 2) * np.linalg.inv(X.T @ X)
    return float(b[1]), float(np.sqrt(V[1, 1])), float(b[1] / np.sqrt(V[1, 1])), len(pre)

def est_p1(d):
    """p1_parallel_trends_sensitivity: 前三后四窗口同一回归 → 前期线性趋势 + 断点。"""
    W7 = [("sxW1", "2021-06", "2021-11", "pre"), ("sxW2", "2021-12", "2022-05", "pre"), ("sxW3", "2022-06", "2022-10", "pre"),
          ("sxY1", "2022-12", "2023-11", "post"), ("sxY2", "2023-12", "2024-11", "post"), ("sxY3", "2024-12", "2025-11", "post"), ("sxY4", "2025-12", "2026-05", "post")]
    c = d.copy()
    for col, lo, hi, _ in W7: c[col] = c.s * ((c.t >= ymi(lo)) & (c.t <= ymi(hi))).astype(int)
    cols = [w[0] for w in W7]
    m = smf.ols("lc ~ " + " + ".join(cols) + " + C(bin) + C(ym)", c).fit(cov_type="cluster", cov_kwds={"groups": c["ym"]})
    beta = np.array([m.params[k] for k in cols]); V = m.cov_params().loc[cols, cols].to_numpy()
    NMO = {col: ymi(hi) - ymi(lo) + 1 for col, lo, hi, _ in W7}
    TAU = {col: float(np.mean([t - REF for t in range(ymi(lo), ymi(hi) + 1)])) for col, lo, hi, _ in W7}
    PRE = [w[0] for w in W7 if w[3] == "pre"]; POST = [w[0] for w in W7 if w[3] == "post"]
    n_pre = sum(NMO[k] for k in PRE) + 1; n_post = sum(NMO[k] for k in POST)
    c_pre = np.array([NMO[k] / n_pre if k in PRE else 0.0 for k in cols]); c_post = np.array([NMO[k] / n_post if k in POST else 0.0 for k in cols])
    ce = c_post - c_pre
    gh, gse = float(ce @ beta), float(np.sqrt(ce @ V @ ce))
    X = np.column_stack([np.ones(3), [TAU[k] for k in PRE]]); Vi = np.linalg.inv(V[:3, :3]); XtVX = X.T @ Vi @ X
    coef = np.linalg.solve(XtVX, X.T @ Vi @ beta[:3]); Vc = np.linalg.inv(XtVX)
    tr, trse = float(coef[1]), float(np.sqrt(Vc[1, 1])); trp = float(2 * (1 - stats.norm.cdf(abs(tr / trse))))
    lever = sum(NMO[k] * TAU[k] for k in POST) / n_post - sum(NMO[k] * TAU[k] for k in PRE) / n_pre
    crit = stats.norm.ppf(0.975)
    dz = gh / lever; di = (gh + crit * gse) / lever
    return dict(trend=tr, trend_se=trse, trend_p=trp, gamma=gh, gamma_se=gse, lever=float(lever), delta_zero=float(dz), delta_insig=float(di),
                mbar_zero=float(abs(dz) / abs(tr)), mbar_insig=float(abs(di) / abs(tr)), beta=beta, se=np.sqrt(np.diag(V)))

def est_placebo(d, W):
    ts = sorted(d.t.unique()); cands = [t for t in ts if t - W >= ts[0] and t + W - 1 <= ts[-1]]
    gs = {}
    for ev in cands:
        dd = d[(d.t >= ev - W) & (d.t < ev + W)].copy()
        dd["dz"] = dd.s * (dd.t >= ev).astype(int)
        bb = pd.get_dummies(dd.s, prefix="b", drop_first=True).astype(float)
        mm = pd.get_dummies(dd.ym, prefix="m", drop_first=True).astype(float)
        X = sm.add_constant(pd.concat([dd[["dz"]].astype(float), bb, mm], axis=1))
        gs[ev] = sm.OLS(dd.lc.values, X.values).fit().params[list(X.columns).index("dz")]
    tg = gs[EVENT]; ranked = sorted(gs.items(), key=lambda kv: kv[1])
    rank = [i for i, (ev, _) in enumerate(ranked) if ev == EVENT][0] + 1
    pre_c = [ev for ev in cands if ev < EVENT]
    return dict(W=W, n=len(cands), rank=rank, pct=100.0 * rank / len(cands), gamma=float(tg), n_pre=len(pre_c),
                n_pre_more_neg=sum(gs[ev] < tg for ev in pre_c), n_clean=sum(1 for ev in pre_c if ev + W - 1 < EVENT), gs=gs)

def est_wintests(d):
    """R2d_extra §4。"""
    L = d.copy()
    yrs = [("Y1", "2022-12", "2023-11"), ("Y2", "2023-12", "2024-11"), ("Y3", "2024-12", "2025-11"), ("Y4", "2025-12", "2026-05")]
    for k, lo, hi in yrs: L["sx" + k] = L.s * ((L.t >= ymi(lo)) & (L.t <= ymi(hi))).astype(int)
    m = smf.ols("lc ~ sxY1 + sxY2 + sxY3 + sxY4 + C(s) + C(ym)", L).fit(cov_type="cluster", cov_kwds={"groups": L.ym})
    ft = m.f_test("sxY1 = sxY2, sxY2 = sxY3, sxY3 = sxY4"); tt = m.t_test("sxY2 - sxY1 = 0")
    L["sxG"] = L.s * ((L.t >= ymi("2022-12")) & (L.t <= ymi("2023-02"))).astype(int)
    L["sxR"] = L.s * (L.t >= ymi("2023-03")).astype(int)
    m2 = smf.ols("lc ~ sxG + sxR + C(s) + C(ym)", L).fit(cov_type="cluster", cov_kwds={"groups": L.ym})
    t2 = m2.t_test("sxR - sxG = 0")
    return dict(F=float(np.squeeze(ft.fvalue)), Fp=float(ft.pvalue), y2y1=float(np.squeeze(tt.effect)), y2y1se=float(np.squeeze(tt.sd)), y2y1p=float(tt.pvalue),
                rg=float(np.squeeze(t2.effect)), rgse=float(np.squeeze(t2.sd)), rgp=float(t2.pvalue))

# ---------------- 复现闸门: A vs 盲臂日志 ----------------
print("\n=== 复现(A=发表标签面板) vs 盲臂日志 / 稿件 ===")
rp = {}
chk = {}
def ok(name, cond, got):
    chk[name] = bool(cond); print("  [%s] %s : %s" % ("PASS" if cond else "FAIL", name, got))

A = LL["A"]
t3 = est_post_windows(A)
T3_WANT = [(-0.000, 0.048), (-0.113, 0.073), (-0.193, 0.058), (-0.387, 0.047), (-0.343, 0.047), (-0.281, 0.050), (-0.304, 0.038)]
ok("T3 post windows 7 rows (3 dec)", all(round(g, 3) == wg and round(s, 3) == ws for (n, g, s, p), (wg, ws) in zip(t3, T3_WANT)),
   [(round(g, 3), round(s, 3)) for n, g, s, p in t3])
bw, sw, Wd, pw = est_pre_windows(A)
ok("pre 3 windows beta/SE 4dp", [round(x, 4) for x in bw] == [-0.0973, -0.1773, -0.1223] and [round(x, 4) for x in sw] == [0.0504, 0.0596, 0.0216], ([round(x, 4) for x in bw], [round(x, 4) for x in sw]))
ok("pre joint Wald 44.523 (p~1.2e-9)", round(Wd, 3) == 44.523 and 1.1e-9 < pw < 1.3e-9, (round(Wd, 3), pw))
v1 = est_ref_variant(A, {ymi("2022-09"), ymi("2022-10"), ymi("2022-11")}); v2 = est_ref_variant(A, {ymi("2022-%02d" % m) for m in range(6, 12)})
ok("V1 W=3.34 p=.3425", round(v1["wald"], 2) == 3.34 and round(v1["p"], 4) == 0.3425, (round(v1["wald"], 2), round(v1["p"], 4)))
ok("V2 W=1.43 p=.4888", round(v2["wald"], 2) == 1.43 and round(v2["p"], 4) == 0.4888, (round(v2["wald"], 2), round(v2["p"], 4)))
b3, s3, w3, p3 = est_v3(A)
ok("V3 W2/W3 vs W1", [round(x, 4) for x in b3] == [-0.0799, -0.0046] and [round(x, 4) for x in s3] == [0.0772, 0.0578] and round(w3, 2) == 1.43 and round(p3, 4) == 0.4888, ([round(x, 4) for x in b3], [round(x, 4) for x in s3], round(w3, 2), round(p3, 4)))
zz = ref_zscore(P["A"])
ok("2022-11 z=2.13 (2.723 vs 2.559 SD .077)", round(zz[0], 3) == 2.723 and round(zz[1], 3) == 2.559 and round(zz[2], 3) == 0.077 and round(zz[3], 2) == 2.13, [round(x, 3) for x in zz])
ES = {c: est_eventstudy(LL[c]) for c in "ABC"}
bl = pd.read_csv(BLOUT).merge(ES["A"][["k", "gamma_k"]], on="k", suffixes=("_ref", "_mine"), how="outer")
md = float((bl.gamma_k_ref - bl.gamma_k_mine).abs().max())
ok("event study A == 盲臂 within_so_llm_eventstudy.csv (59 pts)", len(bl) == 59 and bl.gamma_k_mine.notna().all() and md < 1e-8, "max|diff|=%.2e" % md)
ls = lead_slope(ES["A"])
ok("lead slope -0.00307 (SE .0052)", round(ls[0], 5) == -0.00307 and round(ls[1], 4) == 0.0052, (round(ls[0], 5), round(ls[1], 4), ls[3]))
p1 = est_p1(A)
ok("p1 trend -0.00084 SE .00439 p .848", round(p1["trend"], 5) == -0.00084 and round(p1["trend_se"], 5) == 0.00439 and round(p1["trend_p"], 3) == 0.848, (round(p1["trend"], 5), round(p1["trend_se"], 5), round(p1["trend_p"], 3)))
ok("p1 breakdown -0.01013 / -0.00794, lever 30.0", round(p1["delta_zero"], 5) == -0.01013 and round(p1["delta_insig"], 5) == -0.00794 and round(p1["lever"], 1) == 30.0, (round(p1["delta_zero"], 5), round(p1["delta_insig"], 5), round(p1["lever"], 1)))
pl9, pl12 = est_placebo(A, 9), est_placebo(A, 12)
ok("placebo ±9: 13/43, -0.1450, 0/9, clean 1", (pl9["rank"], pl9["n"], round(pl9["gamma"], 4), pl9["n_pre_more_neg"], pl9["n_pre"], pl9["n_clean"]) == (13, 43, -0.1450, 0, 9, 1), (pl9["rank"], pl9["n"], round(pl9["gamma"], 4), pl9["n_pre_more_neg"], pl9["n_pre"], pl9["n_clean"]))
ok("placebo ±12: 13/37, -0.1788, 0/6", (pl12["rank"], pl12["n"], round(pl12["gamma"], 4), pl12["n_pre_more_neg"], pl12["n_pre"]) == (13, 37, -0.1788, 0, 6), (pl12["rank"], pl12["n"], round(pl12["gamma"], 4), pl12["n_pre_more_neg"], pl12["n_pre"]))
wt = est_wintests(A)
ok("win tests F=3.666 p=.0172; y2-y1 -0.1936 p .0019; rest-gpt35 -0.3269 SE .0435", (round(wt["F"], 3), round(wt["Fp"], 4), round(wt["y2y1"], 4), round(wt["y2y1p"], 4), round(wt["rg"], 4), round(wt["rgse"], 4)) == (3.666, 0.0172, -0.1936, 0.0019, -0.3269, 0.0435),
   (round(wt["F"], 3), round(wt["Fp"], 4), round(wt["y2y1"], 4), round(wt["y2y1p"], 4), round(wt["rg"], 4), round(wt["rgse"], 4)))
# 稿件所报位数: 对 A 复现不到的项单列
GATE = {"t3": chk["T3 post windows 7 rows (3 dec)"], "pre": chk["pre 3 windows beta/SE 4dp"] and chk["pre joint Wald 44.523 (p~1.2e-9)"],
        "ref": chk["V1 W=3.34 p=.3425"] and chk["V2 W=1.43 p=.4888"] and chk["V3 W2/W3 vs W1"],
        "z": chk["2022-11 z=2.13 (2.723 vs 2.559 SD .077)"], "es": chk["event study A == 盲臂 within_so_llm_eventstudy.csv (59 pts)"],
        "lead": chk["lead slope -0.00307 (SE .0052)"], "p1": chk["p1 trend -0.00084 SE .00439 p .848"] and chk["p1 breakdown -0.01013 / -0.00794, lever 30.0"],
        "pl9": chk["placebo ±9: 13/43, -0.1450, 0/9, clean 1"], "pl12": chk["placebo ±12: 13/37, -0.1788, 0/6"], "wt": chk["win tests F=3.666 p=.0172; y2-y1 -0.1936 p .0019; rest-gpt35 -0.3269 SE .0435"]}
print("GATE flags:", GATE)
UNREPRO = [k for k, v in GATE.items() if not v]

# ---------------- 三列计算 ----------------
res = {c: {} for c in "ABC"}
for c in "ABC":
    d = LL[c]; r = res[c]
    r["t3"] = est_post_windows(d)
    r["pre"] = est_pre_windows(d)
    r["v1"] = est_ref_variant(d, {ymi("2022-09"), ymi("2022-10"), ymi("2022-11")})
    r["v2"] = est_ref_variant(d, {ymi("2022-%02d" % m) for m in range(6, 12)})
    r["v3"] = est_v3(d)
    r["z"] = ref_zscore(P[c])
    r["lead"] = lead_slope(ES[c])
    r["p1"] = est_p1(d)
    r["pl9"] = est_placebo(d, 9); r["pl12"] = est_placebo(d, 12)
    r["wt"] = est_wintests(d)

# ---------------- bootstrap: 按月整块重抽，同一组月份同时算 B 和 C ----------------
SEED = 20261013; NBOOT = 2000

def month_cnt(w):
    return {ymi(r.ym): np.array([r.s1, r.s2, r.s3, r.s4], float) for r in w.itertuples()}
MC = {c: month_cnt(P[c]) for c in "ABC"}

def fast_coef(copies, nreg):
    """copies: list of (cnt[4], flags[nreg]); 回归 log cnt ~ Σ_j b*flag_j + bin FE(2..4) + 每个月份副本一个 FE。返回前 nreg 个系数。"""
    M = len(copies)
    b = np.tile(np.arange(1, 5), M); mi = np.repeat(np.arange(M), 4)
    y = np.log(np.maximum(np.concatenate([c[0] for c in copies]), 1.0))
    F = np.repeat(np.array([c[1] for c in copies], float), 4, axis=0)
    X = np.column_stack([b[:, None] * F, np.ones(4 * M), (b[:, None] == np.arange(2, 5)[None, :]).astype(float),
                         (mi[:, None] == np.arange(1, M)[None, :]).astype(float)])
    return np.linalg.lstsq(X, y, rcond=None)[0][:nreg]

def post_copies(mc, lo, hi, idx=None):
    pre = [(mc[t], [0.0]) for t in sorted(mc) if t < EVENT]
    wm = [t for t in sorted(mc) if lo <= t <= hi]
    sel = wm if idx is None else [wm[i] for i in idx]
    return pre + [(mc[t], [1.0]) for t in sel], len(wm)

def pre_copies(mc, j, idx=None):
    """V0 三窗口: 样本 = t<=REF; 窗口 j 的月份(可重抽)，其余月份固定。flags=[W1,W2,W3]。"""
    out = []; wm = [t for t in sorted(mc) if PRE_WINDOWS[j][2] <= t <= PRE_WINDOWS[j][3]]
    for t in sorted(mc):
        if t > REF: continue
        f = [1.0 if (PRE_WINDOWS[i][2] <= t <= PRE_WINDOWS[i][3]) else 0.0 for i in range(3)]
        if t in wm and idx is not None: continue
        out.append((mc[t], f))
    if idx is not None:
        for i in idx:
            t = wm[i]; out.append((mc[t], [1.0 if (PRE_WINDOWS[q][2] <= t <= PRE_WINDOWS[q][3]) else 0.0 for q in range(3)]))
    return out, len(wm)

# 自检: fast_coef 点估计 == smf 点估计
for c in "BC":
    for (name, lo, hi), row in zip(POSTW, res[c]["t3"]):
        cp, _ = post_copies(MC[c], ymi(lo), ymi(hi))
        assert abs(fast_coef(cp, 1)[0] - row[1]) < 1e-8, (c, name, fast_coef(cp, 1)[0], row[1])
    for j in range(3):
        cp, _ = pre_copies(MC[c], j)
        assert abs(fast_coef(cp, 3)[j] - res[c]["pre"][0][j]) < 1e-8, (c, j)
print("fast_coef 自检通过: 与 smf 点估计一致(后期 7 窗口 + 前期 3 窗口, B/C)")

def ci_str(dif, pt):
    # 包内改动: 删去按窗口内月份重抽的 B-C 区间(已作废), 只留点差
    return "%+.4f (点差, 无区间)" % pt

# ---------------- 逐月路径 ----------------
esdf = pd.DataFrame({"k": ES["A"].k.values, "ym": ES["A"].t.map(lab).values, "A": ES["A"].gamma_k.values, "B": ES["B"].gamma_k.values, "C": ES["C"].gamma_k.values})
esdf["B_minus_C"] = esdf.B - esdf.C; esdf["A_minus_C"] = esdf.A - esdf.C
esdf.to_csv(os.path.join(HERE, "event_study_paths.csv"), index=False, encoding="utf-8", float_format="%.6f")
def pathstat(col):
    x = esdf[col]; i = x.abs().idxmax()
    return x.mean(), x.abs().max(), esdf.ym[i], esdf.k[i]
pBC, pAC = pathstat("B_minus_C"), pathstat("A_minus_C")
rBC = float(np.corrcoef(esdf.B, esdf.C)[0, 1]); rAC = float(np.corrcoef(esdf.A, esdf.C)[0, 1])
# 额外(同表): A-B
pAB = float(np.corrcoef(esdf.A, esdf.B)[0, 1])

# ---------------- RESULTS ----------------
def f3(g, s=None, p=None):
    t = "%+.3f" % g
    if s is not None: t += " (%.3f)" % s
    if p is not None: t += " p=%.3g" % p
    return t
L = []
def line(item, ms, a, b, c, d): L.append("%s | %s | %s | %s | %s | %s" % (item, ms, a, b, c, d))
MSL = {"t3": 285, "pre": 271, "lead": 271, "p1": 273, "pl": 436, "plt": 478, "wt": 297}
for i, (name, lo, hi) in enumerate(POSTW):
    want = T3_WANT[i]
    ms = "L%d: %+.3f (%.3f)" % (287 + i, want[0], want[1])
    ra, rb, rc = res["A"]["t3"][i], res["B"]["t3"][i], res["C"]["t3"][i]
    line("Table3/Fig9 python γ [%s]" % name, ms, f3(ra[1], ra[2], ra[3]), f3(rb[1], rb[2], rb[3]), f3(rc[1], rc[2], rc[3]),
         "B-C " + ci_str(None, rb[1] - rc[1]) + "; 95%%CI B [%+.3f,%+.3f] C [%+.3f,%+.3f] A [%+.3f,%+.3f]" % (
             rb[1] - 1.96 * rb[2], rb[1] + 1.96 * rb[2], rc[1] - 1.96 * rc[2], rc[1] + 1.96 * rc[2], ra[1] - 1.96 * ra[2], ra[1] + 1.96 * ra[2]))
for j, (n, col, lo, hi) in enumerate(PRE_WINDOWS):
    rr = {c: res[c]["pre"] for c in "ABC"}
    line("§5.4/6.2 前期窗口 %s 斜率(单月参照2022-11) %s..%s" % (n, lab(lo), lab(hi)), "L226/271: 三窗口各5-6月,无逐窗口数",
         "%+.4f (SE %.4f)" % (rr["A"][0][j], rr["A"][1][j]), "%+.4f (SE %.4f)" % (rr["B"][0][j], rr["B"][1][j]), "%+.4f (SE %.4f)" % (rr["C"][0][j], rr["C"][1][j]),
         "B-C " + ci_str(None, rr["B"][0][j] - rr["C"][0][j]))
line("§6.2 前期三窗口联合 Wald χ²(3), 单月参照", "L271: χ²(3)=44.5, p<.001", "%.3f p=%.3g" % (res["A"]["pre"][2], res["A"]["pre"][3]), "%.3f p=%.3g" % (res["B"]["pre"][2], res["B"]["pre"][3]),
     "%.3f p=%.3g" % (res["C"]["pre"][2], res["C"]["pre"][3]), "B-C Wald 点差 %+.3f (未做bootstrap)" % (res["B"]["pre"][2] - res["C"]["pre"][2]))
for key, tag, ms in (("v1", "三月均值参照(2022-09..11)", "L271: p=.34"), ("v2", "六月均值参照(2022-06..11)", "L271: p=.49")):
    f = lambda c: "χ²(%d)=%.3f p=%.4f; β=%s" % (res[c][key]["df"], res[c][key]["wald"], res[c][key]["p"], ",".join("%+.4f" % x for x in res[c][key]["beta"]))
    line("§6.2 前期联合检验, " + tag, ms, f("A"), f("B"), f("C"), "B-C χ²点差 %+.3f" % (res["B"][key]["wald"] - res["C"][key]["wald"]))
f = lambda c: "χ²(2)=%.3f p=%.4f; W2-W1=%+.4f W3-W1=%+.4f" % (res[c]["v3"][2], res[c]["v3"][3], res[c]["v3"][0][0], res[c]["v3"][0][1])
line("§6.2 前期窗口互比(V3, 无参照月)", "稿件未报(盲臂日志 p0_6_ref_sensitivity: p=.4888)", f("A"), f("B"), f("C"), "—")
f = lambda c: "%.3f vs %.3f(SD %.3f) z=%.2f" % (res[c]["z"][0], res[c]["z"][1], res[c]["z"][2], res[c]["z"][3])
line("§6.2 2022-11 mean score(s1-s4) vs 前6月", "L271: 2.72 vs 2.56, 2.13 SD", f("A"), f("B"), f("C"), "—")
f = lambda c: "%+.5f/月 (SE %.4f, t=%+.2f, %d个lead)" % res[c]["lead"]
line("§6.2 月度前期领先项线性斜率(k<=-2)", "L271: -0.003/月", f("A"), f("B"), f("C"), "B-C %+.5f" % (res["B"]["lead"][0] - res["C"]["lead"][0]))
f = lambda c: "%+.5f/月 (SE %.5f, p=%.3f)" % (res[c]["p1"]["trend"], res[c]["p1"]["trend_se"], res[c]["p1"]["trend_p"])
line("§6.2 联合估计的前期剂量斜率", "L273: -0.0008/月 (SE 0.0044)", f("A"), f("B"), f("C"), "B-C %+.5f" % (res["B"]["p1"]["trend"] - res["C"]["p1"]["trend"]))
f = lambda c: "致不显著 %+.5f/月; 抹掉点估计 %+.5f/月; 杠杆 %.1f月; Mbar %.1f/%.1f" % (res[c]["p1"]["delta_insig"], res[c]["p1"]["delta_zero"], res[c]["p1"]["lever"], res[c]["p1"]["mbar_insig"], res[c]["p1"]["mbar_zero"])
line("§6.2 差异趋势断点值", "L273: -0.0079 / -0.0101", f("A"), f("B"), f("C"), "—")
f = lambda c: "F(3,59)=%.3f p=%.4f; Y2-Y1=%+.4f(SE %.4f,p=%.4f); (3月后其余)-(GPT3.5)=%+.4f(SE %.4f,p=%.2g)" % (
    res[c]["wt"]["F"], res[c]["wt"]["Fp"], res[c]["wt"]["y2y1"], res[c]["wt"]["y2y1se"], res[c]["wt"]["y2y1p"], res[c]["wt"]["rg"], res[c]["wt"]["rgse"], res[c]["wt"]["rgp"])
line("§6.2 窗口等同检验(年份 F; Y2-Y1; 其余-GPT3.5窗口)", "L297: F=3.67 p=.017; Y2-Y1 0.194 p=.002; 0.327 p<.001 (本行 Y2-Y1 为带符号差)", f("A"), f("B"), f("C"), "—")
for key, W in (("pl9", 9), ("pl12", 12)):
    f = lambda c: "γ_true=%+.4f 排第%d/%d (%.1f百分位); 事件前候选更负 %d/%d" % (res[c][key]["gamma"], res[c][key]["rank"], res[c][key]["n"], res[c][key]["pct"], res[c][key]["n_pre_more_neg"], res[c][key]["n_pre"])
    ms = "L436/478: 13th of 43 (30th pct), γ=-0.145; 更负于全部9个事件前候选" if W == 9 else "L478: ±12 窗口 13 of 37; 无事件前候选更负"
    line("Table7 匹配窗口安慰剂 ±%d月" % W, ms, f("A"), f("B"), f("C"), "B-C γ_true点差 %+.4f" % (res["B"][key]["gamma"] - res["C"][key]["gamma"]))
line("Fig8A 逐月事件研究路径 (k=-1参照, 59点) B-C", "L220/276: 仅点估计图", "—", "—", "—", "B-C 逐月差: 均值 %+.4f, 最大|差| %.4f (月 %s, k=%d); Pearson r(B,C)=%.4f" % (pBC[0], pBC[1], pBC[2], pBC[3], rBC))
line("Fig8A 逐月事件研究路径 A-C", "同上", "—", "—", "—", "A-C 逐月差: 均值 %+.4f, 最大|差| %.4f (月 %s, k=%d); Pearson r(A,C)=%.4f; (附)r(A,B)=%.4f" % (pAC[0], pAC[1], pAC[2], pAC[3], rAC, pAB))

print("\n=== RESULTS ===")
print("包内版: 已删去 B-C 的窗口内月份重抽 bootstrap 区间(作废); B-C 列只给点差; A/B/C 各列括号内为月聚类 SE, 末列 95%CI 为 ±1.96SE")
print("未复现(A 对盲臂日志/稿件)的项: %s" % (UNREPRO if UNREPRO else "无"))
print("项目 | 稿件值及稿件行号 | A | B | C | B–C 点差及各列95%CI")
for l in L: print(l)
print("=== END RESULTS ===")

# ---------------- 输出文件 ----------------
pd.DataFrame([{"cutoff": lab(ev), "is_pre": ev < EVENT, "A": res["A"]["pl9"]["gs"][ev], "B": res["B"]["pl9"]["gs"][ev], "C": res["C"]["pl9"]["gs"][ev]} for ev in sorted(res["A"]["pl9"]["gs"])]).to_csv(
    os.path.join(HERE, "placebo_w9_candidates.csv"), index=False, float_format="%.6f")
with io.open(os.path.join(HERE, "windows_table.md"), "w", encoding="utf-8") as fh:
    fh.write("# windows_table (只描述; windows.py 生成)\n\n注: 三列 A=旧面板·原发表标签, B=旧面板·本次重评, C=随机面板·本次重评。B-C 列只给点差(原按窗口内月份重抽的区间已作废, 本包不含); 末列 95%%CI 为 ±1.96SE。未复现项: %s\n\n" % (UNREPRO if UNREPRO else "无"))
    fh.write("| 项目 | 稿件值及稿件行号 | A | B | C | B–C 点差及各列95%CI |\n|---|---|---|---|---|---|\n")
    for l in L: fh.write("| " + l.replace(" | ", " | ") + " |\n")
json.dump({"unrepro": UNREPRO, "gate": GATE}, io.open(os.path.join(HERE, "windows_gate.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
