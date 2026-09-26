# -*- coding: utf-8 -*-
"""R2 A 臂:python 面板 6,000 题盲批次 + 指令文本。按设计书第一节,硬闸全过才写盘。

输出目录 工作文档\\R2_blind\\ :
  R2_blind_batch_01..50.json   评分者看的批次(只有 id/title/tags/body)
  R2_token_map.json            编号 -> 题号(评分者不可见)
  R2_ym_map.json               题号 -> 月份(仅供闸门与分析)
  R2_PROMPT_TEMPLATE.txt       指令模板(NN 处替换批号)
  R2_build_result.json         闸门读数
"""
import hashlib, io, json, os, random, re, sys
from collections import Counter
from scipy.stats import spearmanr

sys.stdout.reconfigure(encoding="utf-8")
PKG = r"E:\智能体论文\P9b_OSF_复现包_20260920"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "R2_blind")
DATA = os.path.join(PKG, "01_panels_and_classification", "data")
SEED_TOK, SEED_ORDER = 20260923, 20260924
NB, BS = 50, 120
fails = []

recs = []
for fn in ("so_questions_python_2021-2024.json", "so_questions_python_ext_2024-07_2026-05.json"):
    recs += json.load(io.open(os.path.join(DATA, fn), encoding="utf-8"))
qids = [int(r["question_id"]) for r in recs]
if len(recs) != 6000 or len(set(qids)) != 6000:
    fails.append("面板不是 6,000 个不同题号:%d / %d" % (len(recs), len(set(qids))))
mc = Counter(r["ym"] for r in recs)
if len(mc) != 60 or set(mc.values()) != {100}:
    fails.append("不是 60 个月 × 100 题")
# 与标签表的题号一致
import csv
lab = set()
for fn in ("question_labels_python_2021-2024.csv", "question_labels_python_ext_2024-07_2026-05.csv"):
    lab |= {int(r["question_id"]) for r in csv.DictReader(io.open(os.path.join(DATA, fn), encoding="utf-8"))}
if lab != set(qids):
    fails.append("批次题号与标签表题号不一致")

# ---- 编号:打乱的号池,按题号顺序发放 ----
pool = ["P%04d" % i for i in range(1, 6001)]
random.Random(SEED_TOK).shuffle(pool)
by_q = {int(r["question_id"]): r for r in recs}
sq = sorted(by_q)
tok = {pool[i]: sq[i] for i in range(6000)}
rho = spearmanr([int(t[1:]) for t in tok], [tok[t] for t in tok]).statistic
if abs(rho) >= 0.05:
    fails.append("编号与题号秩相关 %.3f ≥ 0.05" % rho)
q2t = {q: t for t, q in tok.items()}

# ---- 分批:另一种子打乱,切 50 × 120 ----
order = sq[:]
random.Random(SEED_ORDER).shuffle(order)
batches = [order[i * BS:(i + 1) * BS] for i in range(NB)]
KEYS = ["id", "title", "tags", "body"]
out_batches, months_per = [], []
for b in batches:
    rows = []
    for q in b:
        r = by_q[q]
        rows.append({"id": q2t[q], "title": r["title"], "tags": r["tags"], "body": r["body_excerpt"]})
    out_batches.append(rows)
    months_per.append(len({by_q[q]["ym"] for q in b}))
if min(months_per) < 40:
    fails.append("有批次只覆盖 %d 个月(<40)" % min(months_per))
flat = [q for b in batches for q in b]
if len(flat) != 6000 or len(set(flat)) != 6000:
    fails.append("分批后不是 6,000 题各一次")
own_id_in_text = 0
for rows, b in zip(out_batches, batches):
    for row, q in zip(rows, b):
        if list(row.keys()) != KEYS:
            fails.append("字段不在白名单:%s" % list(row.keys())); break
        blob = json.dumps(row, ensure_ascii=False)
        if str(q) in blob:
            own_id_in_text += 1

# ---- 指令:S19 的 PROMPT.md 原文,只替换路径与编号前缀 ----
pm = io.open(os.path.join(PKG, "06_sampling_window_test", "PROMPT.md"), encoding="utf-8").read()
m = re.search(r"```\n(.*?)\n```", pm, re.S)
tmpl = m.group(1)
old_in = [l for l in tmpl.split("\n") if l.strip().endswith("R1_blind_batch_01.json")]
old_out = [l for l in tmpl.split("\n") if l.strip().endswith("R1_labels_batch_01.json")]
if len(old_in) != 1 or len(old_out) != 1 or tmpl.count('"Qxxxx"') != 1:
    fails.append("S19 指令模板的三个替换位没有各命中一次")
else:
    tmpl = tmpl.replace(old_in[0], os.path.join(OUT, "R2_blind_batch_NN.json"))
    tmpl = tmpl.replace(old_out[0], os.path.join(OUT, "R2_labels_batch_NN.json"))
    tmpl = tmpl.replace('"Qxxxx"', '"Pxxxx"')
# 防泄漏:指令里不得出现假设、方向、时期、既有取值
FORBID = [r"hypothes", r"predict", r"declin", r"\bdrop", r"\bfall", r"increase", r"ChatGPT", r"treatment",
          r"\bevent\b", r"pre-period", r"post-period", r"gamma", r"γ", r"\b20\d\d-\d\d\b", r"0\.4\d", r"GLM",
          r"Sonnet 4\.6", r"original label", r"archive"]
leak = [f for f in FORBID if re.search(f, tmpl, re.I)]
if leak:
    fails.append("指令含禁词:%s" % leak)

print("编号-题号秩相关 %.4f;每批月份数 %d–%d;正文里出现自身题号 %d 条" % (rho, min(months_per), max(months_per), own_id_in_text))
if own_id_in_text:
    fails.append("有 %d 条记录的正文含自身题号(设计书要求批内不出现题号)" % own_id_in_text)
if fails:
    for f in fails:
        print("  !! " + f)
    raise SystemExit("!! %d 项不过,未写盘" % len(fails))

os.makedirs(OUT, exist_ok=True)
for i, rows in enumerate(out_batches, 1):
    io.open(os.path.join(OUT, "R2_blind_batch_%02d.json" % i), "w", encoding="utf-8").write(
        json.dumps(rows, ensure_ascii=False, indent=1))
io.open(os.path.join(OUT, "R2_token_map.json"), "w", encoding="utf-8").write(json.dumps(tok, indent=0))
io.open(os.path.join(OUT, "R2_ym_map.json"), "w", encoding="utf-8").write(
    json.dumps({str(q): by_q[q]["ym"] for q in sq}, indent=0))
io.open(os.path.join(OUT, "R2_PROMPT_TEMPLATE.txt"), "w", encoding="utf-8").write(tmpl)
res = dict(n=6000, batches=NB, batch_size=BS, token_id_spearman=round(float(rho), 4),
           months_per_batch_min=min(months_per), months_per_batch_max=max(months_per),
           seeds=dict(token=SEED_TOK, order=SEED_ORDER), own_id_in_text=own_id_in_text,
           prompt_sha256=hashlib.sha256(tmpl.encode("utf-8")).hexdigest())
io.open(os.path.join(HERE, "R2_build_result.json"), "w", encoding="utf-8").write(json.dumps(res, indent=1))
print("闸门全过;已写 %d 批 -> %s" % (NB, OUT))
print("--- 指令模板 ---\n" + tmpl)
