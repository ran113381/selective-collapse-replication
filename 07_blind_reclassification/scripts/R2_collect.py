# -*- coding: utf-8 -*-
"""R2 A 臂:收标签、逐批核验、全齐后合并成题级标签表与月度面板(与原 aggregate_labels.py 同格式)。

逐批核验:文件存在;条数 = 批内题数;编号集合与批次完全相同、无重复;score ∈ {0..4};
label 与 score 一致(>=3 为 GEN)。任何一批不合格就只报告、不合并。
合并产物(工作文档\\R2_blind\\):
  question_labels_python_blind.csv   question_id, ym, score, label
  within_so_llm_panel_python_blind.csv  ym, n, GEN, VER, gen_share, s0..s4
"""
import csv, glob, io, json, os, sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "R2_blind")
tok = json.load(io.open(os.path.join(D, "R2_token_map.json"), encoding="utf-8"))
ymm = json.load(io.open(os.path.join(D, "R2_ym_map.json"), encoding="utf-8"))
ok_batches, bad, missing = [], [], []
rows = []
for i in range(1, 51):
    bf = os.path.join(D, "R2_blind_batch_%02d.json" % i)
    lf = os.path.join(D, "R2_labels_batch_%02d.json" % i)
    ids = [r["id"] for r in json.load(io.open(bf, encoding="utf-8"))]
    if not os.path.exists(lf):
        missing.append(i); continue
    try:
        lab = json.load(io.open(lf, encoding="utf-8"))
    except Exception as e:
        bad.append((i, "JSON 读不了:%s" % e)); continue
    got = [str(r.get("id")) for r in lab]
    probs = []
    if len(lab) != len(ids): probs.append("条数 %d≠%d" % (len(lab), len(ids)))
    if sorted(got) != sorted(ids): probs.append("编号集合不符(缺 %d、多 %d)" % (len(set(ids) - set(got)), len(set(got) - set(ids))))
    if len(set(got)) != len(got): probs.append("有重复编号")
    for r in lab:
        s = r.get("score")
        if not isinstance(s, int) or not 0 <= s <= 4:
            probs.append("非法分值 %r" % (s,)); break
        if r.get("label") != ("GEN" if s >= 3 else "VER"):
            probs.append("label 与 score 不一致"); break
    if probs:
        bad.append((i, "; ".join(probs))); continue
    ok_batches.append(i)
    for r in lab:
        q = tok[r["id"]]
        rows.append(dict(question_id=q, ym=ymm[str(q)], score=r["score"], label=r["label"]))

print("合格 %d 批;缺 %d 批 %s;不合格 %d 批" % (len(ok_batches), len(missing), missing, len(bad)))
for i, p in bad:
    print("  !! 批 %02d:%s" % (i, p))
if missing or bad:
    raise SystemExit(0)

assert len(rows) == 6000 and len({r["question_id"] for r in rows}) == 6000
rows.sort(key=lambda r: (r["ym"], r["question_id"]))
with io.open(os.path.join(D, "question_labels_python_blind.csv"), "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["question_id", "ym", "score", "label"]); w.writeheader(); w.writerows(rows)
by = defaultdict(lambda: defaultdict(int))
for r in rows:
    by[r["ym"]]["n"] += 1; by[r["ym"]][r["label"]] += 1; by[r["ym"]]["s%d" % r["score"]] += 1
with io.open(os.path.join(D, "within_so_llm_panel_python_blind.csv"), "w", encoding="utf-8", newline="") as f:
    cols = ["ym", "n", "GEN", "VER", "gen_share"] + ["s%d" % i for i in range(5)]
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
    for ym in sorted(by):
        d = by[ym]
        w.writerow(dict(ym=ym, n=d["n"], GEN=d["GEN"], VER=d["VER"], gen_share=round(d["GEN"] / d["n"], 4),
                        **{"s%d" % i: d.get("s%d" % i, 0) for i in range(5)}))
assert len(by) == 60 and all(by[m]["n"] == 100 for m in by)
print("全部 50 批合格,已合并 6,000 题与 60 个月面板")
