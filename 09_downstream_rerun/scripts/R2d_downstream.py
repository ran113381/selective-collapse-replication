# -*- coding: utf-8 -*-
"""R2 下游重估:把包内所有读 python 分类器标签的检验,在「原标签」与「盲标签」两套镜像上各跑一遍。

两套镜像只差三个文件(question_labels.csv / question_labels_ext_py.csv / within_so_llm_panel.csv),
其余缓存(closure_meta、asker_owner/users、edit_meta、first_answer、platform_monthly_totals、题目正文)
逐字节相同。within_so_llm_eventstudy.csv 在两边都由 run_within_so_llm.py 重新生成(盲臂先删掉旧文件,
读到旧的就会报错而不是静默用错)。

自证:原标签臂的每个输出 JSON 与 P9_修订_20260703\\replication_additions 下当年的同名产物逐叶比对;
原标签臂重生成的事件研究 CSV 须与 _legB_data 里的逐点相等。自证不过的脚本,其盲臂结果不得进稿。
不联网:三个带抓取的脚本只以 --analyze-only 或缓存齐全方式运行(运行前断言缓存在),且环境里去掉 STACK_API_KEY。

用法:python R2d_downstream.py build | run orig | run blind | compare
输出:工作文档\\R2_downstream\\{orig,blind}\\...;logs\\*.log;R2d_compare.json
"""
import glob, io, json, math, os, re, shutil, subprocess, sys

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HERE = os.path.dirname(os.path.abspath(__file__))
PKG = r"E:\智能体论文\P9b_OSF_复现包_20260920"
LEGB = r"E:\智能体论文\_legB_data"
REPADD = r"E:\智能体论文\P9_修订_20260703\replication_additions"
BL = os.path.join(HERE, "R2_blind")
ROOT = os.path.join(HERE, "R2_downstream")

RUNS = [  # (名字, 相对镜像根的路径, 参数)
    ("run_within_so_llm", r"01_panels_and_classification\run_within_so_llm.py", ["--panel", "within_so_llm_panel.csv"]),
    ("phaseA_composition", r"02_estimation\phaseA_composition.py", []),
    ("phaseA_answer_window", r"02_estimation\phaseA_answer_window.py", []),
    ("answer_side_test", r"02_estimation\answer_side_test.py", []),
    ("fixed_window_answer", r"02_estimation\fixed_window_answer.py", []),
    ("closure_check", r"02_estimation\closure_check.py", ["--analyze-only"]),
    ("absolute_volume", r"02_estimation\absolute_volume.py", ["--analyze-only"]),
    ("capability_ramp", r"02_estimation\capability_ramp.py", []),
    ("asker_tenure", r"02_estimation\asker_tenure.py", []),
    ("asker_cohort_prelim", r"02_estimation\asker_cohort_prelim.py", []),
    ("asker_rival_test", r"02_estimation\asker_rival_test.py", []),
    ("asker_rival_exact", r"02_estimation\asker_rival_exact.py", []),
    ("bin_stability_test", r"02_estimation\bin_stability_test.py", []),
    ("edit_exposure_check", r"02_estimation\edit_exposure_check.py", []),
    ("s17_length_conditioned", r"02_estimation\s17_length_conditioned.py", []),
    ("s17_bound_both_samples", r"02_estimation\s17_bound_both_samples.py", []),
    ("p0_2_staging_ground", r"02_estimation\review_r1_reviewer_response_scripts\p0_2_staging_ground.py", []),
    ("p0_3_placebo_overlap", r"02_estimation\review_r1_reviewer_response_scripts\p0_3_placebo_overlap.py", []),
    ("p0_6_pretrends", r"02_estimation\review_r1_reviewer_response_scripts\p0_6_pretrends.py", []),
    ("p0_6_ref_sensitivity", r"02_estimation\review_r1_reviewer_response_scripts\p0_6_ref_sensitivity.py", []),
    ("p1_14_bin_dummies", r"02_estimation\review_r1_reviewer_response_scripts\p1_14_bin_dummies.py", []),
    ("check_cap_sensitivity", r"02_estimation\review_r1_reviewer_response_scripts\check_cap_sensitivity.py", []),
    ("check_detrend_ci", r"02_estimation\review_r1_reviewer_response_scripts\check_detrend_ci.py", []),
    ("cross_family_analysis", r"05_additional_checks\cross_family_analysis.py", ["--model", "glm-4.6"]),
]
CACHES = ["closure_meta.csv", "asker_owner.csv", "asker_users.csv", "edit_meta.csv", "first_answer.csv",
          "platform_monthly_totals.csv"]
FRESH = ["capability_ramp_eventstudy.csv", "absolute_volume_series_python.csv", "absolute_volume_series_java.csv",
         "absolute_volume_series_javascript.csv"]


def patch(text, base):
    data, est = os.path.join(base, "data"), os.path.join(base, "02_estimation")
    text = re.sub(r'DATA\s*=\s*\(r"C:\\Users[^)]*\)', lambda m: 'DATA = r"%s"' % data, text)
    text = re.sub(r'DATA\s*=\s*r"C:\\Users[^"]*"', lambda m: 'DATA = r"%s"' % data, text)
    text = text.replace(r"E:\智能体论文\_legB_data", data)
    text = text.replace(r"E:\智能体论文\P9_修订_20260703\replication_additions", est)
    text = text.replace(r'r"E:\智能体论文\P9_金标准_20260704"', 'r"%s"' % os.path.join(PKG, "03_validation", "gold_standard"))
    text = re.sub(r'^DATA = os\.path\.join\(HERE, "data"\)', lambda m: 'DATA = r"%s"' % data, text, flags=re.M)
    for lit in re.findall(r'r"([A-Z]:\\[^"]*)"', text):     # 自检:剩下的绝对路径只能指向镜像内或包内(只读)
        assert lit.startswith(base) or lit.startswith(os.path.join(PKG, "03_validation")), "未改写的绝对路径: " + lit
    return text


def build():
    import pandas as pd
    for arm in ("orig", "blind"):
        base = os.path.join(ROOT, arm)
        assert base.startswith(os.path.join(HERE, "R2_downstream"))
        if os.path.exists(base):
            shutil.rmtree(base)
        data = os.path.join(base, "data")
        shutil.copytree(LEGB, data)
        if arm == "blind":
            b = pd.read_csv(os.path.join(BL, "question_labels_python_blind.csv")).set_index("question_id")
            for fn in ("question_labels.csv", "question_labels_ext_py.csv"):
                q = pd.read_csv(os.path.join(data, fn))
                assert set(q.question_id) <= set(b.index), fn + " 有题不在盲标签里"
                assert (q.ym.values == b.loc[q.question_id, "ym"].values).all(), fn + " 月份对不上"
                q["score"] = b.loc[q.question_id, "score"].values
                q["label"] = b.loc[q.question_id, "label"].values
                q.to_csv(os.path.join(data, fn), index=False, encoding="utf-8")
            p = pd.read_csv(os.path.join(BL, "within_so_llm_panel_python_blind.csv"))
            o = pd.read_csv(os.path.join(LEGB, "within_so_llm_panel.csv"))
            assert list(p.columns) == list(o.columns) and list(p.ym) == list(o.ym)
            q = pd.read_csv(os.path.join(data, "question_labels.csv"))      # 自证:面板 = 题级标签的月×分值计数
            ct = q.groupby(["ym", "score"]).size().unstack(fill_value=0)
            for s in range(5):
                assert (ct.reindex(p.ym)[s].values == p["s%d" % s].values).all(), "面板与题级标签不一致 s%d" % s
            assert (q.assign(g=q.score >= 3).groupby("ym").g.sum().reindex(p.ym).values == p.GEN.values).all()
            p.to_csv(os.path.join(data, "within_so_llm_panel.csv"), index=False)
            os.remove(os.path.join(data, "within_so_llm_eventstudy.csv"))
        est = os.path.join(base, "02_estimation")
        rv = os.path.join(est, "review_r1_reviewer_response_scripts")
        os.makedirs(rv); os.makedirs(os.path.join(est, "review_r1"))
        src_est = os.path.join(PKG, "02_estimation")
        for f in os.listdir(src_est):
            if os.path.isfile(os.path.join(src_est, f)) and not f.endswith(".json") and f not in FRESH:
                shutil.copy2(os.path.join(src_est, f), est)
        shutil.copy2(os.path.join(src_est, "legB_first_answer.csv"), os.path.join(est, "first_answer.csv"))
        src_rv = os.path.join(src_est, "review_r1_reviewer_response_scripts")
        for f in os.listdir(src_rv):
            if f.endswith(".py"):
                shutil.copy2(os.path.join(src_rv, f), rv)
        c01 = os.path.join(base, "01_panels_and_classification"); os.makedirs(os.path.join(c01, "data"))
        shutil.copy2(os.path.join(PKG, "01_panels_and_classification", "run_within_so_llm.py"), c01)
        shutil.copy2(os.path.join(data, "question_labels.csv"), os.path.join(c01, "data", "question_labels_python_2021-2024.csv"))
        c05 = os.path.join(base, "05_additional_checks"); os.makedirs(c05)
        shutil.copy2(os.path.join(PKG, "05_additional_checks", "cross_family_analysis.py"), c05)
        shutil.copytree(os.path.join(PKG, "05_additional_checks", "glm_relabel"), os.path.join(c05, "glm_relabel"))
        for f in glob.glob(os.path.join(c05, "glm_relabel", "cross_family_*.json")):
            os.remove(f)                                   # 输出须新生成
        for name, rel, _ in RUNS:
            fp = os.path.join(base, rel)
            t = io.open(fp, encoding="utf-8").read()
            io.open(fp, "w", encoding="utf-8").write(patch(t, base))
        for c in CACHES:
            assert os.path.exists(os.path.join(est, c)), "缺缓存 " + c
        if arm == "blind":
            patch_blind(base)
        print("[%s] 镜像已建: %s" % (arm, base))


# 盲臂专用:两个脚本内嵌「复现原标签发表值」的断言/门槛,原标签臂照旧执行(那是自证),
# 盲臂里改为不拦——否则脚本在盲标签上必然停在自证处、出不了数。每处替换都断言命中恰好一次。
BLIND_PATCH = [
    (r"02_estimation\s17_bound_both_samples.py",
     'assert t["n"] == 5640, t["n"]\n'
     'assert round(100 * t["s1_close_hi"], 1) == 15.7 and round(100 * t["s2_close_hi"], 1) == 13.1\n'
     'assert round(100 * t["s1_ans_hi"], 1) == 2.4 and round(100 * t["s2_ans_hi"], 1) == 2.0\n'
     'assert round(100 * t["s1_ans_share"]) == 6 and round(100 * t["s2_ans_share"]) == 9\n'
     'assert u["n"] == 5930, u["n"]\n',
     "# [R2d 盲臂] 原标签数值自证在 orig 臂执行,盲臂不拦\n"),
    (r"02_estimation\review_r1_reviewer_response_scripts\p1_14_bin_dummies.py",
     'PUBLISHED = {"python": -0.416,',
     'PUBLISHED = {"python": -0.304,  # [R2d 盲臂] 盲标签头条(R2_analyze_result.json)\n             '),
]


def patch_blind(base):
    for rel, old, new in BLIND_PATCH:
        fp = os.path.join(base, rel)
        t = io.open(fp, encoding="utf-8").read()
        assert t.count(old) == 1, "盲臂补丁未命中: " + rel
        io.open(fp, "w", encoding="utf-8").write(t.replace(old, new))


def run(arm):
    base = os.path.join(ROOT, arm)
    logs = os.path.join(base, "logs"); os.makedirs(logs, exist_ok=True)
    env = dict(os.environ, PYTHONIOENCODING="utf-8"); env.pop("STACK_API_KEY", None)
    for c in CACHES:
        assert os.path.exists(os.path.join(base, "02_estimation", c)), "缺缓存 " + c
    for name, rel, args in RUNS:
        fp = os.path.join(base, rel)
        try:
            r = subprocess.run([sys.executable, fp] + args, cwd=os.path.dirname(fp), env=env,
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=3600)
            out, rc = r.stdout + "\n--- stderr ---\n" + r.stderr, r.returncode
        except subprocess.TimeoutExpired:
            out, rc = "TIMEOUT", -9
        io.open(os.path.join(logs, name + ".log"), "w", encoding="utf-8").write(out)
        print("[%s] %-24s rc=%d" % (arm, name, rc), flush=True)


def flat(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from flat(v, p + "/" + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from flat(v, p + "[%d]" % i)
    else:
        yield p, o


def num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def diff(a, b, tol=1e-9):
    fa, fb = dict(flat(a)), dict(flat(b))
    keys = sorted(set(fa) | set(fb))
    out = []
    for k in keys:
        x, y = fa.get(k), fb.get(k)
        if num(x) and num(y):
            if not (math.isclose(x, y, rel_tol=tol, abs_tol=tol) or (math.isnan(x) and math.isnan(y))):
                out.append((k, x, y))
        elif x != y:
            out.append((k, x, y))
    return len(keys), out


def outputs(base):
    fs = glob.glob(os.path.join(base, "02_estimation", "*.json")) + glob.glob(os.path.join(base, "02_estimation", "review_r1", "*.json")) \
        + glob.glob(os.path.join(base, "02_estimation", "review_r1_reviewer_response_scripts", "*.json")) \
        + glob.glob(os.path.join(base, "05_additional_checks", "glm_relabel", "cross_family_*.json"))
    return {os.path.relpath(f, base): f for f in fs}


def compare():
    import pandas as pd
    R = {"selfproof": {}, "blind_vs_orig": {}}
    o, b = outputs(os.path.join(ROOT, "orig")), outputs(os.path.join(ROOT, "blind"))
    # 自证 1:事件研究 CSV
    es = pd.read_csv(os.path.join(ROOT, "orig", "data", "within_so_llm_eventstudy.csv")).merge(
        pd.read_csv(os.path.join(LEGB, "within_so_llm_eventstudy.csv")), on="k")
    R["selfproof"]["eventstudy_csv"] = dict(n=len(es), maxdiff=float((es.gamma_k_x - es.gamma_k_y).abs().max()))
    # 自证 2:原标签臂 JSON 对当年产物
    for rel, f in sorted(o.items()):
        nm = os.path.basename(f)
        cands = [os.path.join(REPADD, nm), os.path.join(REPADD, "review_r1", nm),
                 os.path.join(PKG, "02_estimation", nm), os.path.join(PKG, "02_estimation", "review_r1_reviewer_response_scripts", nm),
                 os.path.join(PKG, "05_additional_checks", "glm_relabel", nm)]
        ref = next((c for c in cands if os.path.exists(c)), None)
        if ref is None:
            R["selfproof"][rel] = "无当年产物可比"; continue
        n, d = diff(json.load(io.open(ref, encoding="utf-8")), json.load(io.open(f, encoding="utf-8")))
        R["selfproof"][rel] = dict(ref=ref, leaves=n, differ=len(d), first=[list(x) for x in d[:8]])
    for rel in sorted(set(o) | set(b)):
        if rel not in o or rel not in b:
            R["blind_vs_orig"][rel] = "只在一边: " + ("orig" if rel in o else "blind"); continue
        n, d = diff(json.load(io.open(o[rel], encoding="utf-8")), json.load(io.open(b[rel], encoding="utf-8")))
        R["blind_vs_orig"][rel] = dict(leaves=n, differ=len(d), rows=[list(x) for x in d])
    io.open(os.path.join(HERE, "R2d_compare.json"), "w", encoding="utf-8").write(json.dumps(R, indent=1, ensure_ascii=False, default=str))
    print("事件研究 CSV 自证: n=%d max|diff|=%.2e" % (R["selfproof"]["eventstudy_csv"]["n"], R["selfproof"]["eventstudy_csv"]["maxdiff"]))
    for rel, v in R["selfproof"].items():
        if rel == "eventstudy_csv": continue
        print("自证 %-60s %s" % (rel, v if isinstance(v, str) else "叶 %d 不等 %d" % (v["leaves"], v["differ"])))
    for rel, v in R["blind_vs_orig"].items():
        print("盲/原 %-60s %s" % (rel, v if isinstance(v, str) else "叶 %d 变 %d" % (v["leaves"], v["differ"])))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "build": build()
    elif cmd == "run": run(sys.argv[2])
    elif cmd == "compare": compare()
