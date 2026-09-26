# -*- coding: utf-8 -*-
"""R2 稿件用数的汇总:输出 工作文档\\R2_numbers_result.json

稿件里本轮的数分散在盲标签镜像的各脚本输出里,其中一部分脚本只打印不存 JSON
(answer_side_test、fixed_window_answer、phaseA_answer_window、check_cap_sensitivity、
s17_bound_both_samples、phaseA_composition、run_within_so_llm)。本脚本:
  1 收盲臂镜像里各脚本的输出 JSON(原样);
  2 收上述只打印脚本的日志行(原样字符串);
  3 收 S19 盲臂的 R1 结果 JSON;
  4 按写明的公式算稿件里由产物推导的数(比值、占比、百分数换算等),不引入任何新估计。
不收 R2d_compare.json / R2d_r1_compare.json(逐叶差异表,不是稿件用数)。
脚本带写作时本机的绝对路径,与包内其他脚本相同。
"""
import glob, io, json, math, os, re, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(HERE, "R2_downstream", "blind")
R = {"blind_json": {}, "blind_logs": {}, "blind_r1": {}, "derived": {}}
for f in sorted(glob.glob(os.path.join(B, "02_estimation", "*.json")) + glob.glob(os.path.join(B, "02_estimation", "review_r1", "*.json"))
                + glob.glob(os.path.join(B, "02_estimation", "review_r1_reviewer_response_scripts", "*.json"))
                + glob.glob(os.path.join(B, "05_additional_checks", "glm_relabel", "cross_family_*.json"))):
    R["blind_json"][os.path.relpath(f, B)] = json.load(io.open(f, encoding="utf-8"))
for n in ("answer_side_test", "fixed_window_answer", "phaseA_answer_window", "check_cap_sensitivity",
          "s17_bound_both_samples", "phaseA_composition", "run_within_so_llm", "gold_score_adjudication"):
    txt = io.open(os.path.join(B, "logs", n + ".log"), encoding="utf-8").read().split("--- stderr ---")[0]
    R["blind_logs"][n] = [l.strip() for l in txt.splitlines() if re.search(r"\d", l) and "written" not in l and "写入" not in l]
for f in sorted(glob.glob(os.path.join(B, "06", "*_result.json"))):
    R["blind_r1"][os.path.basename(f)] = json.load(io.open(f, encoding="utf-8"))

# ---- 推导数(每项给出公式与来源) ----
bj = R["blind_json"]
s17 = bj["02_estimation\\s17_length_conditioned.json"]
bs = bj["02_estimation\\bin_stability_test.json"]
more = json.load(io.open(os.path.join(HERE, "R2d_more_result.json"), encoding="utf-8"))
kap = json.load(io.open(os.path.join(HERE, "R2d_kappa_result.json"), encoding="utf-8"))
mem = bj["02_estimation\\memorization_check.json"]
d = R["derived"]
# (a) S17 长度削弱。中位长度取自盲臂 bin_stability_test 日志 D 段(逐行断言);平均 log 变化 × s17 的前期长度系数
#     = 示踪量损失;除以「长题 s4 参照 − 接收档长题前期」= 失去的分辨率比例;s2 的回答示踪上界按封闭示踪比例放松。
bsl = io.open(os.path.join(B, "logs", "bin_stability_test.log"), encoding="utf-8").read()
med = {}
for b in (1, 2, 3, 4):
    m = re.search(r"^\s*s\s+%d\s+(\d+)\s+(\d+)\s" % b, bsl.split("=== D.")[1], re.M)
    med[b] = (int(m.group(1)), int(m.group(2)))
dlog = sum(math.log(c / a) for a, c in med.values()) / 4
coef = lambda v: abs(v["coef"] if isinstance(v, dict) else v[0])
cd, ca = coef(s17["pre_len_effect_dup"]), coef(s17["pre_len_effect_answer_count"])
ref = s17["ref_long_s4_pre"]
gap_dup = ref["dup"] - s17["s1_long_dup"]["pre"]
gap_ans = ref["answers"] - s17["s1_long_answer_count"]["pre"]
d["s17"] = dict(median_len=med, mean_log_change=round(dlog, 3), closure_loss=round(cd * dlog, 4), closure_gap=round(gap_dup, 3),
                closure_retained=round(1 - cd * dlog / gap_dup, 3), answer_loss=round(ca * dlog, 4), answer_gap=round(gap_ans, 3),
                answer_retained=round(1 - ca * dlog / gap_ans, 3))
s2 = bs["migration_bound_answers"]["s2"]["max_share_of_gain_explained"]
d["s17"]["s2_answer_bound"] = round(s2, 4)
d["s17"]["s2_answer_bound_if_blunted_like_closure"] = round(s2 / d["s17"]["closure_retained"], 4)
assert round(100 * s2) == 12 and round(100 * s2 / d["s17"]["closure_retained"]) == 14
assert abs(d["s17"]["closure_retained"] - 7 / 8) < 0.01 and abs(d["s17"]["answer_retained"] - 19 / 20) < 0.01
# (b) 记忆化:gap 区间下限 与 点估计 各占盲评分者降幅之比;人工降幅占盲评分者降幅之比
lo = mem["gap"]["change"] - 1.96 * mem["gap"]["se"]
d["memorisation"] = dict(gap_lower=round(lo, 3), share_at_lower=round(abs(lo) / abs(mem["model"]["diff"]), 3),
                         share_at_point=round(abs(mem["gap"]["change"]) / abs(mem["model"]["diff"]), 3),
                         human_over_blind=round(mem["human"]["diff"] / mem["model"]["diff"], 3))
assert abs(d["memorisation"]["share_at_lower"] - 0.5) < 0.02 and abs(d["memorisation"]["share_at_point"] - 0.2) < 0.02
assert abs(d["memorisation"]["human_over_blind"] - 0.8) < 0.02
# (c) κ 与比值;S19 评分者对盲分类在同题上的 γ 之比
kg = R["blind_r1"]["R1_gamma_refits_result.json"]
d["kappa_ratios"] = dict(glm_over_blind=kap["ratio_glm_over_blind"], glm_over_orig=kap["ratio_glm_over_orig"])
d["s19_rater_over_blind_gamma"] = dict(
    ols=round(kg["rater_on_control"]["logcount_ols"]["gamma"] / kg["primary_on_control"]["logcount_ols"]["gamma"], 3),
    ppml=round(kg["rater_on_control"]["fe_poisson"]["gamma"] / kg["primary_on_control"]["fe_poisson"]["gamma"], 3))
# (d) 稿件用的是源值的换算形式(百分比、取整、四位小数),源文件里没有原样。一律由源值程序化换算,不手敲。
import pandas as pd
fw = [l for l in R["blind_logs"]["fixed_window_answer"] if "within 30d:" in l and "->" in l]
s1_30 = [float(x) for x in re.findall(r"(\d\.\d+)", next(l for l in fw if l.startswith("s1")))]
s4_30 = [float(x) for x in re.findall(r"(\d\.\d+)", next(l for l in fw if l.startswith("s4")))]
av = bj["02_estimation\\absolute_volume.json"]["absolute_by_bin_python"]
lab_b = pd.read_csv(os.path.join(B, "data", "question_labels.csv")).set_index("question_id").score
lab_o = pd.read_csv(os.path.join(HERE, "R2_downstream", "orig", "data", "question_labels.csv")).set_index("question_id").score.reindex(lab_b.index)
glm = {}
for line in io.open(r"E:\智能体论文\P9b_OSF_复现包_20260920\05_additional_checks\glm_relabel\labels_glm-4.6.jsonl", encoding="utf-8"):
    r = json.loads(line); glm[int(r["question_id"])] = int(r["score"])
b5999 = lab_b[lab_b.index.isin(list(glm))]
v2 = json.load(io.open(os.path.join(HERE, "R2v_result.json"), encoding="utf-8"))
pt = bj["02_estimation\\review_r1\\p1_parallel_trends_sensitivity.json"]["pre_linear_trend_per_month"]["estimate"]
d["converted"] = dict(
    fixed_window_30d_s1_pct=[round(100 * x, 1) for x in s1_30], fixed_window_30d_s4_pct=[round(100 * x, 1) for x in s4_30],
    gen_share_blind_on_5999_pct=round(100 * float((b5999 >= 3).mean()), 1),
    blind_vs_orig_within1_pct=round(100 * float(((lab_b - lab_o).abs() <= 1).mean()), 1),
    kappa_blind_raw_299_pct=round(100 * kap["kappa_vs_consensus"]["blind"]["raw"], 1),
    armB_agreement_pct=[round(100 * v2["agreement"]["exact"], 1), round(100 * v2["agreement"]["binary"], 1)],
    python_volume_pre_post_rounded={b: [int(round(av[b]["pre_abs"])), int(round(av[b]["post_abs"]))] for b in ("s1", "s2", "s3", "s4")},
    closure_bin_interaction_4dp=round(bs["interaction"]["coef"] if isinstance(bs["interaction"], dict) else bs["interaction"][0], 4),
    closure_bin_interaction_se_4dp=round(bs["interaction"]["se"], 4),
    pre_trend_per_month_4dp=round(pt, 4))
# 第三轮效标(表 4 / S13):解出率的百分数形式、p 值的两位有效数字、样本事件前占比;
# S1.3 两位编码员 300 题五档完全一致率。全部由全精度源值一次换算(R2c_result 已存 6 位)。
c3 = json.load(io.open(os.path.join(HERE, "R2c_result.json"), encoding="utf-8"))
crit = json.load(io.open(os.path.join(HERE, "R2_criterion", "criterion_sample_v3.json"), encoding="utf-8"))
_g = r"E:\智能体论文\P9b_OSF_复现包_20260920\03_validation\gold_standard"
import csv
_sa = {int(r["order"]): r["score_0_4"].strip() for r in csv.DictReader(io.open(os.path.join(_g, "coding_sheet_A_v2.csv"), encoding="utf-8-sig"))}
_sb = {int(r["order"]): r["score_0_4"].strip() for r in csv.DictReader(io.open(os.path.join(_g, "coding_sheet_B_v2.csv"), encoding="utf-8-sig"))}
_both = [o for o in _sa if _sa[o] and _sb.get(o)]
assert len(_both) == 300
p2 = lambda p: float("%.2g" % p)
tg = c3["pooled"]["tiers"]
d["converted"].update(
    criterion_common_solve_pct={t: [round(100 * c3["common_subset"][t]["s%d" % b], 1) for b in (1, 2, 3, 4)] for t in tg},
    criterion_full_solve_pct={t: [round(100 * c3[t]["solve_by_bin"]["s%d" % b], 1) for b in (1, 2, 3, 4)] for t in tg},
    criterion_spearman_p_2sig={t: dict(common=p2(c3["common_subset_metrics"][t]["spearman"][1]), full=p2(c3[t]["spearman_solved"][1])) for t in tg},
    criterion_pooled_p_2sig=dict(all=p2(c3["pooled"]["slope"][2]), pre=p2(c3["pooled"]["period_pre"][2]), post=p2(c3["pooled"]["period_post"][2])),
    criterion_pre_share_pct=round(100 * sum(s["ym"] < "2022-12" for s in crit) / len(crit), 1),
    coder_exact_agreement_300_pct=round(100 * sum(_sa[o] == _sb[o] for o in _both) / len(_both), 1))
assert d["converted"]["criterion_pre_share_pct"] == 32.2 and d["converted"]["coder_exact_agreement_300_pct"] == 38.0
# S5 表注:主行区间的自助抽样次数,取自 score_adjudication.py 源码(脚本内常量,非估计)
_sa_src = io.open(os.path.join(_g, "score_adjudication.py"), encoding="utf-8").read()
_m = re.findall(r"for _ in range\((\d+)\):\s*\n\s*ii = rng\.choice", _sa_src)
assert len(_m) == 1, _m
d["converted"]["gold_adjudication_bootstrap_draws"] = "{:,}".format(int(_m[0]))
print(json.dumps(d, ensure_ascii=False, default=str))
io.open(os.path.join(HERE, "R2_numbers_result.json"), "w", encoding="utf-8").write(json.dumps(R, indent=1, ensure_ascii=False, default=str))
