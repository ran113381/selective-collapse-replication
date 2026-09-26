# -*- coding: utf-8 -*-
"""R2 B 臂(看得见日期的诊断臂):按设计书第二节建批次与指令,只建不派。

事件前 18 个月抽 9、事件后 42 个月抽 9(种子 20260925);每月一个文件,整月 100 题,
字段与原主分类器读过的 q_<ym>.json 完全相同(题号、月份、创建时间、净得票、回答数、是否已解答、标题、标签、正文节选),
文件名 R2v_<ym>.json。指令 = A 臂指令逐字,只改字段说明句与输出键(按 question_id),如实列出字段。
"""
import io, json, os, random, re, sys

sys.stdout.reconfigure(encoding="utf-8")
PKG = r"E:\智能体论文\P9b_OSF_复现包_20260920"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "R2_blind", "armB")
DATA = os.path.join(PKG, "01_panels_and_classification", "data")
EV = 2022 * 12 + 11
recs = []
for fn in ("so_questions_python_2021-2024.json", "so_questions_python_ext_2024-07_2026-05.json"):
    recs += json.load(io.open(os.path.join(DATA, fn), encoding="utf-8"))
by = {}
for r in recs:
    by.setdefault(r["ym"], []).append(r)
ymi = lambda y: int(y[:4]) * 12 + int(y[5:7]) - 1
pre = sorted(m for m in by if ymi(m) < EV)
post = sorted(m for m in by if ymi(m) >= EV)
assert len(pre) == 18 and len(post) == 42
rng = random.Random(20260925)
months = sorted(rng.sample(pre, 9) + rng.sample(post, 9))
FIELDS = ["question_id", "ym", "creation_date", "title", "tags", "score", "answer_count", "is_answered", "body_excerpt"]
for m in months:
    assert len(by[m]) == 100 and all(list(r.keys()) == FIELDS for r in by[m]), m

a = io.open(os.path.join(HERE, "R2_blind", "R2_PROMPT_TEMPLATE.txt"), encoding="utf-8").read()
old_fields = "Each record has: id (an opaque token), title, tags, body."
assert a.count(old_fields) == 1 and a.count('[{"id": "Pxxxx", "score": 0, "label": "VER", "why": "..."}, ...]') == 1
b = a.replace(old_fields, "Each record has: question_id, ym, creation_date, title, tags, score, answer_count, is_answered, body_excerpt.")
b = b.replace('[{"id": "Pxxxx", "score": 0, "label": "VER", "why": "..."}, ...]',
              '[{"question_id": 12345678, "score": 0, "label": "VER", "why": "..."}, ...]')
b = b.replace("every input id appears exactly once", "every input question_id appears exactly once")
b = re.sub(r"\S*R2_blind_batch_NN\.json", os.path.join(OUT, "R2v_MONTH.json").replace("\\", "\\\\"), b)
b = re.sub(r"\S*R2_labels_batch_NN\.json", os.path.join(OUT, "R2v_labels_MONTH.json").replace("\\", "\\\\"), b)
# 除上述四处外逐字不变
diff = [l for l in b.split("\n") if l not in a.split("\n")]
assert len(diff) == 5, diff

os.makedirs(OUT, exist_ok=True)
for m in months:
    io.open(os.path.join(OUT, "R2v_%s.json" % m), "w", encoding="utf-8").write(json.dumps(by[m], ensure_ascii=False, indent=1))
io.open(os.path.join(OUT, "R2v_PROMPT_TEMPLATE.txt"), "w", encoding="utf-8").write(b)
io.open(os.path.join(OUT, "R2v_months.json"), "w", encoding="utf-8").write(
    json.dumps(dict(seed=20260925, pre=[m for m in months if ymi(m) < EV], post=[m for m in months if ymi(m) >= EV]), indent=1))
print("B 臂 18 个月:", months)
print("--- 与 A 臂指令不同的行 ---\n" + "\n".join(diff))
