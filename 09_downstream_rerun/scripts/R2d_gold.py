# -*- coding: utf-8 -*-
"""R2 下游重估·金标准敏感性(SI S5 / S1.3):包内 score_adjudication.py 读 answer_key_封存勿开.csv 的 model_score
(= 原主分类器分)。两套镜像的 03_validation\\gold_standard 里各放一份脚本与输入,盲臂把 answer_key 与
gold_sample 的 model_score 换成盲标签(300 题都在面板内,断言),其余文件逐字节相同;两臂各跑一遍,
另用 cross_family_analysis.py 同一个 3,000 次自助法函数补 300 题 κ 的区间(稿件 S5 主行的口径)。
输出 R2_downstream\\<arm>\\logs\\gold_score_adjudication.log 与 工作文档\\R2d_gold_result.json
"""
import csv, io, json, os, shutil, subprocess, sys
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
PKG = r"E:\智能体论文\P9b_OSF_复现包_20260920"
SRC = os.path.join(PKG, "03_validation", "gold_standard")
ROOT = os.path.join(HERE, "R2_downstream")
FILES = ["score_adjudication.py", "coding_sheet_A_v2.csv", "coding_sheet_B_v2.csv", "gold_sample_v2_order.json",
         "裁决记录表.csv", "answer_key_封存勿开.csv", "organic_date_items.txt"]
ns = {"__file__": "x"}
src = io.open(os.path.join(PKG, "05_additional_checks", "cross_family_analysis.py"), encoding="utf-8").read()
exec(compile(src[:src.find("def main")], "cfa", "exec"), ns); ns["GOLD"] = SRC
R = {}
for arm in ("orig", "blind"):
    g = os.path.join(ROOT, arm, "03_validation", "gold_standard")
    os.makedirs(g, exist_ok=True)
    for f in FILES:
        shutil.copy2(os.path.join(SRC, f), g)
    lab = pd.read_csv(os.path.join(ROOT, arm, "data", "question_labels.csv")).set_index("question_id").score
    ak = os.path.join(g, "answer_key_封存勿开.csv")
    rows = list(csv.DictReader(io.open(ak, encoding="utf-8-sig")))
    assert len(rows) == 300 and all(int(r["question_id"]) in lab.index for r in rows)
    if arm == "orig":
        assert all(int(r["model_score"]) == int(lab[int(r["question_id"])]) for r in rows), "answer_key 与原标签不一致"
    else:
        for r in rows:
            r["model_score"] = str(int(lab[int(r["question_id"])]))
            if "model_label" in r:
                r["model_label"] = "GEN" if int(r["model_score"]) >= 3 else "VER"
        with io.open(ak, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, os.path.join(g, "score_adjudication.py")], cwd=g, env=env, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    io.open(os.path.join(ROOT, arm, "logs", "gold_score_adjudication.log"), "w", encoding="utf-8").write(r.stdout + "\n--- stderr ---\n" + r.stderr)
    cons = ns["human_consensus"]()
    Q = sorted(cons)
    a = np.array([int(lab[q] >= 3) for q in Q]); h = np.array([cons[q][1] for q in Q])
    k, po = ns["kappa_bin"](a, h)
    R[arm] = dict(rc=r.returncode, kappa300=round(float(k), 4), raw=round(float(po), 4),
                  ci_3000=[round(x, 3) for x in ns["boot_ci"](a, h)])
    print("[%s] rc=%d  κ300 %.3f %s  一致 %.1f%%" % (arm, r.returncode, k, R[arm]["ci_3000"], 100 * po))
R["selfproof_ci"] = R["orig"]["ci_3000"] == [0.413, 0.607]
print("自证 原 κ300 区间 = [0.413, 0.607]:", R["selfproof_ci"])
io.open(os.path.join(HERE, "R2d_gold_result.json"), "w", encoding="utf-8").write(json.dumps(R, indent=1, ensure_ascii=False))


# ---- 补:S5 里包内脚本不产出的三行(中点共识 4 题剔除、两位编码员各自对主评分者的前后一致率),两臂同算,原臂自证
from scipy import stats as _st
Cs = {int(r["order"]): int(r["score_0_4"]) for r in csv.DictReader(io.open(os.path.join(SRC, "coding_sheet_A_v2.csv"), encoding="utf-8-sig")) if r["score_0_4"].strip()}
Bs = {int(r["order"]): int(r["score_0_4"]) for r in csv.DictReader(io.open(os.path.join(SRC, "coding_sheet_B_v2.csv"), encoding="utf-8-sig")) if r["score_0_4"].strip()}
qid = {s["order_v2"]: s["question_id"] for s in json.load(io.open(os.path.join(SRC, "gold_sample_v2_order.json"), encoding="utf-8"))}
adj = {int(r["order"]): int(r["consensus_0_4"]) for r in csv.DictReader(io.open(os.path.join(SRC, "裁决记录表.csv"), encoding="utf-8-sig")) if r["consensus_0_4"].strip()}
mid = {qid[o] for o, v in adj.items() if 2 * v == Cs[o] + Bs[o]}
ymq = {int(r["question_id"]): r["ym"] for r in json.load(io.open(os.path.join(SRC, "gold_sample.json"), encoding="utf-8"))}
cons = ns["human_consensus"]()
Q = sorted(cons)
for arm in ("orig", "blind"):
    lab = pd.read_csv(os.path.join(ROOT, arm, "data", "question_labels.csv")).set_index("question_id").score
    keep = [q for q in Q if q not in mid]
    a = np.array([int(lab[q] >= 3) for q in keep]); h = np.array([cons[q][1] for q in keep])
    R[arm]["kappa_excl_midpoint"] = [round(float(ns["kappa_bin"](a, h)[0]), 4), len(keep)]
    for nm, S in (("A", Cs), ("B", Bs)):
        ag = {qid[o]: int(S[o] >= 3) == int(lab[qid[o]] >= 3) for o in S}
        pre = [v for q, v in ag.items() if ymq[q] < "2022-12"]; post = [v for q, v in ag.items() if ymq[q] >= "2022-12"]
        p = _st.fisher_exact([[sum(pre), len(pre) - sum(pre)], [sum(post), len(post) - sum(post)]])[1]
        R[arm]["drift_coder_" + nm] = [round(100 * np.mean(pre), 1), round(100 * np.mean(post), 1), round(float(p), 3)]
    print("[%s] 中点 %d 题剔除 κ=%.3f (N=%d);编码员 A 前后 %s;B %s" % (arm, len(mid), *R[arm]["kappa_excl_midpoint"], R[arm]["drift_coder_A"], R[arm]["drift_coder_B"]))
R["midpoint_items"] = sorted(mid)
R["selfproof_extra"] = (len(mid) == 4 and round(R["orig"]["kappa_excl_midpoint"][0], 3) == 0.526
                        and R["orig"]["drift_coder_A"][:2] == [80.0, 71.0] and R["orig"]["drift_coder_B"][:2] == [75.6, 72.9])
print("自证(中点 0.526、A 80.0/71.0、B 75.6/72.9):", R["selfproof_extra"])
io.open(os.path.join(HERE, "R2d_gold_result.json"), "w", encoding="utf-8").write(json.dumps(R, indent=1, ensure_ascii=False))
