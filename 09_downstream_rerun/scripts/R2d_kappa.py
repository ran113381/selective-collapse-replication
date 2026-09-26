# -*- coding: utf-8 -*-
"""R2 下游重估·评分者一致性(表 3 乙栏、§6.1 跨家族比值、S12 标准化版本)在盲评分者为主评分者时的取值。

表 3 乙栏与 S12「标准化版本」的原始脚本不在包内(只有 cross_family_analysis.py 的 3,000 次自助法版本)。
这里按稿件文字重建,并先让原主分类器复现稿件现值,复现了才报盲评分者的数:
  乙栏:对人工共识(230 题两人一致 + 70 题裁决)的二元 κ,在 GLM-5.3 也有分的 299 题上算,
        自助法百分位区间 5,000 次;稿件现值 原主 0.511 [0.412, 0.605]、GLM-4.6 0.525 [0.423, 0.619]、
        GLM-5.3 0.571 [0.476, 0.659],原主在全部 300 题上 0.512;
  标准化:剂量取「分值 × 该评分者分值标准差」,即 γ 乘以标准差;稿件现值 GLM −0.268、原主 −0.421(5,999 题,s1–s4)。
输出 工作文档\\R2d_kappa_result.json
"""
import csv, io, json, os, sys
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
PKG = r"E:\智能体论文\P9b_OSF_复现包_20260920"
GOLD = os.path.join(PKG, "03_validation", "gold_standard")
EV = 2022 * 12 + 11
spec_path = os.path.join(PKG, "05_additional_checks", "cross_family_analysis.py")
src = io.open(spec_path, encoding="utf-8").read()
ns = {"__file__": spec_path}
exec(compile(src[:src.find("def main")], spec_path, "exec"), ns)          # 只取函数:kappa_bin / human_consensus
ns["GOLD"] = GOLD
kappa_bin, human_consensus = ns["kappa_bin"], ns["human_consensus"]


def ymi(y):
    a, b = y.split("-"); return int(a) * 12 + int(b) - 1


orig = pd.read_csv(os.path.join(PKG, "01_panels_and_classification", "data", "question_labels_python_2021-2024.csv")).set_index("question_id").score
blind = pd.read_csv(os.path.join(HERE, "R2_blind", "question_labels_python_blind.csv")).set_index("question_id").score
glm46 = {}
for line in io.open(os.path.join(PKG, "05_additional_checks", "glm_relabel", "labels_glm-4.6.jsonl"), encoding="utf-8"):
    r = json.loads(line); glm46[int(r["question_id"])] = int(r["score"])
glm53g = {}
for line in io.open(os.path.join(PKG, "05_additional_checks", "glm_relabel", "gold_labels_glm-5.3.jsonl"), encoding="utf-8"):
    r = json.loads(line); glm53g[int(r["question_id"])] = int(r["score"])
cons = human_consensus()
assert len(cons) == 300
Q = sorted(cons)
common = [q for q in Q if q in glm53g and q in glm46]
print("金标准 300 题;三评分者共有 %d 题" % len(common))

RATERS = {"orig": lambda q: int(orig[q] >= 3), "blind": lambda q: int(blind[q] >= 3),
          "glm46": lambda q: int(glm46[q] >= 3), "glm53": lambda q: int(glm53g[q] >= 3)}
rng = np.random.default_rng(20260906)
B = 5000
idx = [rng.choice(len(common), len(common), replace=True) for _ in range(B)]
h = np.array([cons[q][1] for q in common])
R = {"N_common": len(common), "kappa_vs_consensus": {}, "diff": {}}
boots = {}
for k, f in RATERS.items():
    a = np.array([f(q) for q in common])
    kk, po = kappa_bin(a, h)
    bs = np.array([kappa_bin(a[i], h[i])[0] for i in idx])
    boots[k] = bs
    R["kappa_vs_consensus"][k] = dict(kappa=round(float(kk), 6), raw=round(float(po), 6),
                                      ci=[round(float(np.percentile(bs, 2.5)), 6), round(float(np.percentile(bs, 97.5)), 6)])
    print("  %-6s κ = %.3f [%.3f, %.3f]  一致 %.1f%%" % (k, kk, *R["kappa_vs_consensus"][k]["ci"], 100 * po))
for a_, b_ in (("glm53", "glm46"), ("glm53", "orig"), ("blind", "orig"), ("glm53", "blind"), ("glm46", "blind")):
    d = boots[a_] - boots[b_]
    pt = R["kappa_vs_consensus"][a_]["kappa"] - R["kappa_vs_consensus"][b_]["kappa"]
    R["diff"]["%s_minus_%s" % (a_, b_)] = [round(pt, 6), round(float(np.percentile(d, 2.5)), 6), round(float(np.percentile(d, 97.5)), 6)]
    print("  %s − %s = %+.3f [%+.3f, %+.3f]" % (a_, b_, pt, *R["diff"]["%s_minus_%s" % (a_, b_)][1:]))
for k in ("orig", "blind"):
    a = np.array([RATERS[k](q) for q in Q]); hh = np.array([cons[q][1] for q in Q])
    R["kappa_vs_consensus"][k]["all300"] = round(float(kappa_bin(a, hh)[0]), 6)
print("  全部 300 题:原主 %.3f,盲 %.3f" % (R["kappa_vs_consensus"]["orig"]["all300"], R["kappa_vs_consensus"]["blind"]["all300"]))

# 自证
ok = (abs(R["kappa_vs_consensus"]["orig"]["kappa"] - 0.511) < 0.0015 and abs(R["kappa_vs_consensus"]["glm46"]["kappa"] - 0.525) < 0.0015
      and abs(R["kappa_vs_consensus"]["glm53"]["kappa"] - 0.571) < 0.0015 and abs(R["kappa_vs_consensus"]["orig"]["all300"] - 0.512) < 0.0015)
R["selfproof_point"] = ok
ci_ok = all(abs(R["kappa_vs_consensus"][k]["ci"][i] - v) <= 0.01 for k, vs in
            (("orig", (0.412, 0.605)), ("glm46", (0.423, 0.619)), ("glm53", (0.476, 0.659))) for i, v in enumerate(vs))
R["selfproof_ci_within_0.01"] = ci_ok
print("自证:点估计 %s;区间(容差 0.01,种子不同) %s" % ("复现" if ok else "!! 未复现", "复现" if ci_ok else "!! 未复现"))

# 跨家族比值与标准化版本(5,999 题,s1–s4 各自剂量)
lab = pd.DataFrame({"question_id": list(glm46)}).assign(glm=lambda d: d.question_id.map(glm46))
lab["orig"] = lab.question_id.map(orig); lab["blind"] = lab.question_id.map(blind)
ym = pd.read_csv(os.path.join(PKG, "01_panels_and_classification", "data", "question_labels_python_2021-2024.csv")).set_index("question_id").ym
lab["ym"] = lab.question_id.map(ym)
assert len(lab) == 5999 and lab.notna().all().all()


def dose(col, binary=False):
    x = lab[lab[col] > 0].copy()
    x["k"] = (x[col] >= 3).astype(int) if binary else x[col]
    c = x.groupby(["ym", "k"]).size().reset_index(name="cnt")
    c["post"] = (c.ym.map(ymi) >= EV).astype(int); c["kp"] = c.k * c.post; c["lc"] = np.log(c.cnt)
    m = smf.ols("lc ~ kp + C(k) + C(ym)", c).fit(cov_type="cluster", cov_kwds={"groups": c["ym"]})
    return float(m.params["kp"]), float(m.bse["kp"]), float(x[col].std(ddof=1))


R["cross_family"] = {}
for col in ("orig", "blind", "glm"):
    g, se, sd = dose(col); gb, seb, _ = dose(col, True)
    R["cross_family"][col] = dict(per_point=[round(g, 6), round(se, 6)], binary=[round(gb, 6), round(seb, 6)],
                                  sd=round(sd, 6), standardized=round(g * sd, 6))
cf = R["cross_family"]
std_ok = abs(cf["glm"]["standardized"] - (-0.268)) < 0.0015 and abs(cf["orig"]["standardized"] - (-0.421)) < 0.0015
R["selfproof_standardized"] = std_ok
for base in ("orig", "blind"):
    R["ratio_glm_over_" + base] = dict(per_point=round(cf["glm"]["per_point"][0] / cf[base]["per_point"][0], 5),
                                       binary=round(cf["glm"]["binary"][0] / cf[base]["binary"][0], 5),
                                       standardized=round(cf["glm"]["standardized"] / cf[base]["standardized"], 5))
print("5,999 题:", json.dumps(cf, ensure_ascii=False))
print("标准化自证(γ×sd 复现 −0.268 / −0.421):", "复现" if std_ok else "!! 未复现")
print("GLM/原主:", R["ratio_glm_over_orig"], " GLM/盲:", R["ratio_glm_over_blind"])
io.open(os.path.join(HERE, "R2d_kappa_result.json"), "w", encoding="utf-8").write(json.dumps(R, indent=1, ensure_ascii=False))
