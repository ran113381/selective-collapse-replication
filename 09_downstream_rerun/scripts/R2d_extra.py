# -*- coding: utf-8 -*-
"""R2 下游重估·补充:稿件里有一批 python 数,出处不在 R2d_downstream.py 跑过的包内脚本里。本脚本把它们补齐,
在原标签臂与盲标签臂上各算一遍,原标签臂逐项对稿件现值自证(容差见各处),自证不过的项在结果里标 reproduced=False,
其盲臂数不得进稿,须先查明出处。

出处清单(来源 → 本脚本的做法):
  1 p1_12_ninety_day_window.py、p1_parallel_trends_sensitivity.py(replication_additions\\review_r1,**不在 OSF 包里**)
      → 复制进两套镜像跑;盲臂把脚本内嵌的原标签自证常数换成盲臂自己的上游值。
  2 memorization_check.py(包内)读 gold_sample.json 的 model_score = 原分类器分
      → 镜像内建 03_validation\\gold_standard,盲臂把 model_score 换成盲标签(300 题都在面板内,断言)。
  3 R1_phaseB_recompute.py 的 A(关闭原因分档)、B(24 种排列)、E(量加权 s4 对 s1)→ 同一算法,两臂各算。
  4 表 2 注的窗口等同检验(F = 1.10 等),包内与 review_r1 均无脚本,只在 PNAS 版 SI 正文里
      → 按稿件文字重建规格,原标签臂须复现 1.10/.36、0.187/.081、0.229/.15 才算规格找对。
  5 图 2 的份额指数(159/130/91/53)、各档跌幅、表 5 末 12 个月跌幅 → 由面板与量重构序列直接算。
输出 工作文档\\R2d_extra_result.json;日志 R2_downstream\\<arm>\\logs\\*.log
"""
import importlib.util, io, itertools, json, math, os, shutil, subprocess, sys
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("r2d", os.path.join(HERE, "R2d_downstream.py"))
r2d = importlib.util.module_from_spec(spec); sys.argv, _argv = ["x", "none"], sys.argv; spec.loader.exec_module(r2d); sys.argv = _argv
PKG, REPADD, ROOT, BL = r2d.PKG, r2d.REPADD, r2d.ROOT, r2d.BL
GOLD_SRC = os.path.join(PKG, "03_validation", "gold_standard")
EV = 2022 * 12 + 11


def ymi(y):
    a, b = y.split("-"); return int(a) * 12 + int(b) - 1


def run(base, rel, cwd=None):
    fp = os.path.join(base, rel)
    env = dict(os.environ, PYTHONIOENCODING="utf-8"); env.pop("STACK_API_KEY", None)
    r = subprocess.run([sys.executable, fp], cwd=cwd or os.path.dirname(fp), env=env, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=3600)
    name = os.path.splitext(os.path.basename(fp))[0]
    io.open(os.path.join(base, "logs", name + ".log"), "w", encoding="utf-8").write(r.stdout + "\n--- stderr ---\n" + r.stderr)
    return r.returncode


def setup_extra(arm):
    base = os.path.join(ROOT, arm)
    rv = os.path.join(base, "02_estimation", "review_r1")
    ramp = json.load(io.open(os.path.join(base, "02_estimation", "capability_ramp.json"), encoding="utf-8"))
    win = {r["window"]: r["gamma"] for r in ramp["python"]["windowed"]}
    for f in ("p1_12_ninety_day_window.py", "p1_parallel_trends_sensitivity.py"):
        t = io.open(os.path.join(REPADD, "review_r1", f), encoding="utf-8").read()
        t = r2d.patch(t, base)
        if arm == "blind":
            if f.startswith("p1_12"):
                old = "if fail:\n    sys.exit(2)\n"
                assert t.count(old) == 1
                t = t.replace(old, "# [R2d 盲臂] 原标签发表值自证在 orig 臂执行,盲臂不拦\n")
            else:
                old1 = 'TAB4 = {"sxY1": -0.313, "sxY2": -0.499}'
                old2 = "if abs(gamma_hat - (-0.416)) > 0.01:"
                assert t.count(old1) == 1 and t.count(old2) == 1
                t = t.replace(old1, 'TAB4 = {"sxY1": %.4f, "sxY2": %.4f}  # [R2d 盲臂] 取自盲臂 capability_ramp.json' % (
                    win["y1 2022-12..2023-11"], win["y2 2023-12..2024-11"]))
                t = t.replace(old2, "if abs(gamma_hat - (%.4f)) > 0.01:  # [R2d 盲臂] 盲臂头条" % win["full 2022-12..2026-05"])
        io.open(os.path.join(rv, f), "w", encoding="utf-8").write(t)
    # 记忆化检验:镜像内的金标准目录
    g = os.path.join(base, "03_validation", "gold_standard")
    os.makedirs(g, exist_ok=True)
    for f in ("coding_sheet_A_v2.csv", "coding_sheet_B_v2.csv", "裁决记录表.csv"):
        shutil.copy2(os.path.join(GOLD_SRC, f), g)
    gold = json.load(io.open(os.path.join(GOLD_SRC, "gold_sample.json"), encoding="utf-8"))
    lab = pd.read_csv(os.path.join(base, "data", "question_labels.csv")).set_index("question_id")
    assert all(int(x["question_id"]) in lab.index for x in gold) and len(gold) == 300
    if arm == "orig":   # 自证:金标准里的 model_score 就是原主分类器的面板标签
        assert all(int(x["model_score"]) == int(lab.loc[int(x["question_id"]), "score"]) for x in gold)
    else:
        for x in gold:
            x["model_score"] = int(lab.loc[int(x["question_id"]), "score"])
            x["model_label"] = str(lab.loc[int(x["question_id"]), "label"])
    json.dump(gold, io.open(os.path.join(g, "gold_sample.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    rc = {}
    for f in ("p1_12_ninety_day_window.py", "p1_parallel_trends_sensitivity.py"):
        rc[f] = run(base, os.path.join("02_estimation", "review_r1", f))
    rc["memorization_check.py"] = run(base, os.path.join("02_estimation", "memorization_check.py"))
    return rc


def panel(base):
    w = pd.read_csv(os.path.join(base, "data", "within_so_llm_panel.csv"))
    rec = [{"ym": r.ym, "t": ymi(r.ym), "s": b, "cnt": int(r["s%d" % b])} for _, r in w.iterrows() for b in (1, 2, 3, 4)]
    L = pd.DataFrame(rec); L["post"] = (L.t >= EV).astype(int); L["lc"] = np.log(L.cnt.clip(lower=1))
    return w, L


def stats_arm(base):
    out = {}
    lab = pd.read_csv(os.path.join(base, "data", "question_labels.csv"))
    clo = pd.read_csv(os.path.join(base, "02_estimation", "closure_meta.csv")).rename(columns={"score": "so_score"})
    # ---- 3A 关闭原因分档(全样本,不设 90 天窗)
    d = lab.merge(clo, on="question_id"); d = d[d.score.between(1, 4)].copy()
    dup = (d.closed_reason == "Duplicate"); cf = d.closed_reason.isin(["Needs details or clarity", "Needs more focus"])
    dr = {b: 100 * dup[d.score == b].mean() for b in (1, 2, 3, 4)}; cr = {b: 100 * cf[d.score == b].mean() for b in (1, 2, 3, 4)}
    rho, prho = stats.spearmanr(d.score, dup.astype(int))
    top = {b: d[d.score == b].closed_reason.value_counts().index[0] for b in (1, 2, 3, 4)}
    out["closure_reasons"] = dict(N=len(d), dup_pct=[round(dr[b], 2) for b in (1, 2, 3, 4)],
                                  cf_pct=[round(cr[b], 2) for b in (1, 2, 3, 4)], spearman=[round(float(rho), 4), float(prho)],
                                  fold_dup=round(dr[4] / dr[1], 2), fold_cf=round(cr[4] / cr[1], 2),
                                  base_ratio=round(dr[1] / cr[1], 2), pp_dup=round(dr[4] - dr[1], 2), pp_cf=round(cr[4] - cr[1], 2),
                                  dup_most_common_every_bin=all(v == "Duplicate" for v in top.values()))
    # ---- 3B 24 种排列
    w, L = panel(base)
    bins = pd.get_dummies(L.s, prefix="b", drop_first=True).astype(float); mo = pd.get_dummies(L.ym, prefix="m", drop_first=True).astype(float)

    def g_of(mp):
        dose = (L.s.map(mp) * L.post).rename("dose").astype(float)
        return float(sm.OLS(L.lc.to_numpy(), sm.add_constant(pd.concat([dose, bins, mo], axis=1)).to_numpy()).fit().params[1])
    gs = {p: g_of(dict(zip([1, 2, 3, 4], p))) for p in itertools.permutations([1, 2, 3, 4])}
    obs = gs[(1, 2, 3, 4)]
    rng = np.random.default_rng(7)
    draws = np.array([gs[tuple(rng.permutation([1, 2, 3, 4]))] for _ in range(2000)])
    out["permutation"] = dict(observed=round(obs, 4), rank_of_24=sorted(gs.values()).index(obs) + 1,
                              p_2000=round(float((np.sum(draws <= obs) + 1) / 2001), 4))
    # ---- 4 窗口等同检验(按稿件文字重建:所有后期斜率同一模型、以整个前期为参照)
    yrs = [("Y1", "2022-12", "2023-11"), ("Y2", "2023-12", "2024-11"), ("Y3", "2024-12", "2025-11"), ("Y4", "2025-12", "2026-05")]
    for k, lo, hi in yrs:
        L["sx" + k] = L.s * ((L.t >= ymi(lo)) & (L.t <= ymi(hi))).astype(int)
    m = smf.ols("lc ~ sxY1 + sxY2 + sxY3 + sxY4 + C(s) + C(ym)", L).fit(cov_type="cluster", cov_kwds={"groups": L.ym})
    ft = m.f_test("sxY1 = sxY2, sxY2 = sxY3, sxY3 = sxY4")
    tt = m.t_test("sxY2 - sxY1 = 0")
    L["sxG"] = L.s * ((L.t >= ymi("2022-12")) & (L.t <= ymi("2023-02"))).astype(int)
    L["sxR"] = L.s * (L.t >= ymi("2023-03")).astype(int)
    m2 = smf.ols("lc ~ sxG + sxR + C(s) + C(ym)", L).fit(cov_type="cluster", cov_kwds={"groups": L.ym})
    t2 = m2.t_test("sxR - sxG = 0")
    out["window_tests"] = dict(years={k: [round(float(m.params["sx" + k]), 4), round(float(m.bse["sx" + k]), 4)] for k, _, _ in yrs},
                               F=round(float(np.squeeze(ft.fvalue)), 3), F_p=round(float(ft.pvalue), 4), F_df=[int(ft.df_num), int(ft.df_denom)],
                               y2_minus_y1=[round(float(np.squeeze(tt.effect)), 4), round(float(np.squeeze(tt.sd)), 4), round(float(tt.pvalue), 4)],
                               gpt35=[round(float(m2.params["sxG"]), 4), round(float(m2.bse["sxG"]), 4)],
                               rest=[round(float(m2.params["sxR"]), 4), round(float(m2.bse["sxR"]), 4)],
                               rest_minus_gpt35=[round(float(np.squeeze(t2.effect)), 4), round(float(np.squeeze(t2.sd)), 4), round(float(t2.pvalue), 4)])
    # ---- 5 份额指数与量
    pre, post = w[w.ym.map(ymi) < EV], w[w.ym.map(ymi) >= EV]
    out["share_index_post_over_pre"] = [round(100 * post["s%d" % b].mean() / pre["s%d" % b].mean(), 1) for b in (1, 2, 3, 4)]
    out["s0_share"] = [round(float(pre.s0.mean()), 2), round(float(post.s0.mean()), 2)]
    av = pd.read_csv(os.path.join(base, "02_estimation", "absolute_volume_series_python.csv")); av["t"] = av.ym.map(ymi)
    pa, po = av[av.t < EV], av[av.t >= EV]; l12 = av[av.t > av.t.max() - 12]
    ch = {b: 100 * (po["Nhat_s%d" % b].mean() / pa["Nhat_s%d" % b].mean() - 1) for b in (1, 2, 3, 4)}
    c12 = {b: 100 * (l12["Nhat_s%d" % b].mean() / pa["Nhat_s%d" % b].mean() - 1) for b in (1, 2, 3, 4)}
    out["volume"] = dict(pre_per_month=[round(float(pa["Nhat_s%d" % b].mean()), 1) for b in (1, 2, 3, 4)],
                         post_per_month=[round(float(po["Nhat_s%d" % b].mean()), 1) for b in (1, 2, 3, 4)],
                         change_pct=[round(ch[b], 1) for b in (1, 2, 3, 4)], final12_pct=[round(c12[b], 1) for b in (1, 2, 3, 4)],
                         vol_weighted_s4_vs_s1=round(100 * ((1 + ch[4] / 100) / (1 + ch[1] / 100) - 1), 1),
                         bins_sum_over_total=round(float((av[["Nhat_s%d" % b for b in (1, 2, 3, 4)]].sum(axis=1) / av.total).mean()), 3))
    return out


def selfproof(o):
    """原标签臂须复现的稿件现值。返回 {项: (是否复现, 实得)}。"""
    c = o["closure_reasons"]; wt = o["window_tests"]; v = o["volume"]
    chk = {
        "closure dup 2.6/3.2/4.5/11.3": ([round(x, 1) for x in c["dup_pct"]] == [2.6, 3.2, 4.5, 11.3], c["dup_pct"]),
        "closure cf 0.5..2.6": ([round(c["cf_pct"][0], 1), round(c["cf_pct"][3], 1)] == [0.5, 2.6], c["cf_pct"]),
        "closure rho .115 p 3.5e-19": (round(c["spearman"][0], 3) == 0.115 and 3.4e-19 < c["spearman"][1] < 3.6e-19, c["spearman"]),
        "closure 4.3/4.8-fold, 8.7/2.1 pp": ((round(c["fold_dup"], 1), round(c["fold_cf"], 1), round(c["pp_dup"], 1), round(c["pp_cf"], 1)) == (4.3, 4.8, 8.7, 2.1),
                                            (c["fold_dup"], c["fold_cf"], c["pp_dup"], c["pp_cf"])),
        "permutation rank 1/24": (o["permutation"]["rank_of_24"] == 1, o["permutation"]),
        "F 1.10 p .36": (abs(wt["F"] - 1.10) < 0.006 and abs(wt["F_p"] - 0.36) < 0.006, (wt["F"], wt["F_p"])),
        "y2-y1 0.187 p .081": (abs(abs(wt["y2_minus_y1"][0]) - 0.187) < 0.0006 and abs(wt["y2_minus_y1"][2] - 0.081) < 0.0006, wt["y2_minus_y1"]),
        "gpt35 vs rest 0.229 p .15": (abs(abs(wt["rest_minus_gpt35"][0]) - 0.229) < 0.0006 and abs(wt["rest_minus_gpt35"][2] - 0.15) < 0.006, wt["rest_minus_gpt35"]),
        "share index 159/130/91/53": ([round(x) for x in o["share_index_post_over_pre"]] == [159, 130, 91, 53], o["share_index_post_over_pre"]),
        "volume -63.6/-71.1/-76.7/-86.0": (v["change_pct"] == [-63.6, -71.1, -76.7, -86.0], v["change_pct"]),
        "final12 -95.5/-95.9/-97.5/-98.7": (v["final12_pct"] == [-95.5, -95.9, -97.5, -98.7], v["final12_pct"]),
        "vol-weighted -61.5": (v["vol_weighted_s4_vs_s1"] == -61.5, v["vol_weighted_s4_vs_s1"]),
    }
    return {k: dict(reproduced=bool(a), got=b) for k, (a, b) in chk.items()}


if __name__ == "__main__":
    R = {}
    for arm in ("orig", "blind"):
        R[arm] = {"script_rc": setup_extra(arm), "stats": stats_arm(os.path.join(ROOT, arm))}
        print("[%s] 补充脚本返回码:" % arm, R[arm]["script_rc"])
    R["orig_selfproof"] = selfproof(R["orig"]["stats"])
    for k, v in R["orig_selfproof"].items():
        print("自证 %-34s %s  %s" % (k, "OK" if v["reproduced"] else "!! 未复现", v["got"]))
    for k in R["blind"]["stats"]:
        print("\n[%s]\n  原 %s\n  盲 %s" % (k, R["orig"]["stats"][k], R["blind"]["stats"][k]))
    io.open(os.path.join(HERE, "R2d_extra_result.json"), "w", encoding="utf-8").write(json.dumps(R, indent=1, ensure_ascii=False, default=str))
