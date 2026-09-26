# -*- coding: utf-8 -*-
"""金标准第二轮:校准题集 + 修订版问卷生成器(2026-08-16)。

第一轮失败诊断(见 金标准第一轮结果诊断_20260816.md):人-人 κ=0.104。
根因:问卷指导语只给了五行一句话定义,而 LLM 分类当年用的 CLASSIFY_RUBRIC.md
每档都带具体锚点例句 —— 人类拿到的 rubric 比模型薄,端点档无锚点故不敢用
(编码员 A 有 94.7% 的题压在 2-3 档)。

本脚本产出:
  1) 校准题集 20 题(每档 5 题),取自 300 题与效标两轮之外的题池,带参考答案与理由
     —— 校准会用,不进任何统计分析。
  2) 修订版问卷 v2:同一批 300 题、重排呈现顺序(新 seed),指导语补全逐档锚点例句
     + 量表使用提示 + 校准环节说明。
  3) 配套的 v2 空白评分表(order 对应新顺序)。

不改动 gold_sample.json / answer_key / 第一轮已填表 —— 第一轮结果完整保留。

用法: py -V:3.13 make_calibration_and_v2.py
"""
import collections
import csv
import json
import os
import random
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = r"E:\智能体论文\_legB_data"
SEED_CAL = 20260816       # 校准题抽样
SEED_ORDER_V2 = 20260817  # 第二轮呈现顺序重排
PER_BIN_CAL = 5

# ---------------------------------------------------------------- 载入题池
questions = []
for fn in ("so_questions_full.json", "so_questions_ext_py.json"):
    questions += json.load(open(os.path.join(DATA, fn), encoding="utf-8"))
qmeta = {int(q["question_id"]): q for q in questions}

labels = {}
for fn in ("question_labels.csv", "question_labels_ext_py.csv"):
    for r in csv.DictReader(open(os.path.join(DATA, fn), encoding="utf-8")):
        labels[int(r["question_id"])] = int(r["score"])

gold = json.load(open(os.path.join(HERE, "gold_sample.json"), encoding="utf-8"))
used = {int(s["question_id"]) for s in gold}
for f in ("criterion/criterion_sample.json", "criterion/criterion_sample_v2.json"):
    p = os.path.join(HERE, f)
    if os.path.exists(p):
        for x in json.load(open(p, encoding="utf-8")):
            used.add(int(x.get("qid") or x.get("question_id")))

avail = collections.defaultdict(list)
for qid, s in labels.items():
    if qid not in used and s in (1, 2, 3, 4) and qid in qmeta:
        avail[s].append(qid)

# ---------------------------------------------------------------- 校准题抽样
#
# 【方法学要点,勿改】校准题**不得**向编码员出示模型标注作为"参考答案"。
# 金标准存在的唯一目的是独立于模型家族地检验分类器;若先用模型标注训练人类,
# 之后的人-模型 κ 即为循环论证,审稿人一眼可见。
# 正确做法(Krippendorff / Neuendorf 的内容分析规范):校准阶段以**编码手册本身**
# 为仲裁者 —— 两人各自独立打分,再对照彼此分歧,回到 rubric 的锚点例句上讨论,
# 必要时澄清 rubric 并记录该澄清。模型标注单独封存,仅供事后描述,永不出示。
rng = random.Random(SEED_CAL)
cal = []
for s in (4, 3, 2, 1):                      # 抽样时按档取,保证覆盖全量程
    pool = sorted(avail[s])
    rng.shuffle(pool)
    for qid in pool[:PER_BIN_CAL]:
        q = qmeta[qid]
        cal.append({"question_id": qid, "model_score_SEALED": s,
                    "title": q["title"], "tags": q["tags"],
                    "body_excerpt": q.get("body_excerpt", "")})
rng.shuffle(cal)                            # 打乱,避免按档聚堆泄露量表结构
for i, c in enumerate(cal, 1):
    c["cal_order"] = i
json.dump(cal, open(os.path.join(HERE, "calibration_set_20_封存勿开.json"), "w",
                    encoding="utf-8"), ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- 第二轮顺序
sample_v2 = [dict(s) for s in gold]
random.Random(SEED_ORDER_V2).shuffle(sample_v2)
for i, s in enumerate(sample_v2, 1):
    s["order_v2"] = i
json.dump(sample_v2, open(os.path.join(HERE, "gold_sample_v2_order.json"), "w",
                          encoding="utf-8"), ensure_ascii=False, indent=1)

for coder in ("A", "B"):
    with open(os.path.join(HERE, f"coding_sheet_{coder}_v2.csv"), "w", newline="",
              encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["order", "question_id", "score_0_4", "备注(可空)"])
        for s in sample_v2:
            w.writerow([s["order_v2"], s["question_id"], "", ""])

# ---------------------------------------------------------------- 文档生成
from docx import Document
from docx.shared import Pt, RGBColor

# 锚点例句:逐字取自 CLASSIFY_RUBRIC.md(LLM 分类当年实际使用的版本)
RUBRIC = [
    ("4 = 纯 GENERATION", "概念/算法/标准 how-to,自足,有唯一标准答案,一次就能答对。",
     ["如何一行读三个整数", "为什么 300 is 301-1 返回 True",
      "求树的所有根到叶路径", "classmethod+property 在 3.11 的替代"]),
    ("3 = 偏 generation", "标准做法 + 轻微上下文。",
     ["按后缀 merge 多个 dataframe", "按 config 重命名 CSV 列", "pandas 多条件赋值"]),
    ("2 = 混合/偏 verification", "需要一些判断或提问者的具体设置。",
     ["Dash 回调我快写好了但缺点东西", "mypy 拒绝我的 protocol 实现"]),
    ("1 = VERIFICATION", "调试提问者的具体报错/代码/环境、在其数据上调性能、生产环境特定。",
     ["conda proxy 在家庭 wifi 失败", "merge 把内存撑到 1.6TB",
      "celery 高负载下重复队列"]),
    ("0 = 纯 verification", "完全受上下文/判断约束,仅凭文本无法回答。", []),
]


def clean(t):
    t = re.sub(r"\s+", " ", t or "").strip()
    return t[:1200] + (" …[截断]" if len(t) > 1200 else "")


def write_rubric(doc):
    doc.add_heading("评分标准(0-4 AI 可替代性)", level=1)
    for k, v, egs in RUBRIC:
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(k + ":").bold = True
        p.add_run(v)
        if egs:
            pe = doc.add_paragraph()
            pe.paragraph_format.left_indent = Pt(36)
            r = pe.add_run("典型例子:" + "、".join(f"“{e}”" for e in egs))
            r.font.size = Pt(9)
            r.font.color.rgb = RGBColor(0x40, 0x60, 0x90)
    doc.add_paragraph(
        "关键原则:按问题的内在类型判定;判断核心是——答案是“生成一段标准代码/解释”"
        "(高分)还是“对这个人的具体情况做诊断/权衡”(低分)。[CODE] 与 [code] 均为被折叠的代码标记。")


# ---- 校准题集(无参考答案,两位编码员共用) ----
doc = Document()
st = doc.styles["Normal"]
st.font.name = "Times New Roman"
st.font.size = Pt(10.5)

doc.add_heading("金标准校准题集(20 题)", level=0)
p = doc.add_paragraph()
p.add_run("用途:正式编码前对齐量表刻度。这 20 题取自 300 题正式样本之外,"
          "不进入任何统计分析,可以公开讨论。").bold = True
doc.add_paragraph(
    "这里没有标准答案,也不会有人给你们一份“正确分数”。原因是:本研究要检验的正是"
    "某个自动分类器的判断是否可靠,如果先拿它的答案训练两位编码员,之后测出来的"
    "一致性就没有意义了。校准的目标不是猜中某个答案,而是让两位对同一条标准的"
    "理解对齐。")

doc.add_heading("校准流程(约 30-45 分钟)", level=1)
for step in [
    "第一步(各 15 分钟,独立):两人分别给这 20 题打 0-4 分,写在下方横线上,期间不交流。",
    "第二步(对照):把两人的分数并排列出,标出不一致的题。",
    "第三步(讨论,重点):只讨论不一致的题。讨论时回到评分标准的档位定义和典型例子上"
    "——“这题更像 4 分例子里的‘如何一行读三个整数’,还是更像 1 分例子里的"
    "‘conda proxy 在家庭 wifi 失败’?”把判断依据说出来,而不是各让一步取中间值。",
    "第四步(记录):如果讨论后发现评分标准本身有含糊之处,把双方达成的澄清写下来"
    "(例如“报错信息完整贴出但属于通用错误,算 2 不算 1”),这条澄清在正式编码时对两人同时生效。",
    "第五步:确认两人对“自足 / 需要提问者情境”这条界线理解一致后,再开始正式的 300 题。",
]:
    doc.add_paragraph(style="List Number").add_run(step).font.size = Pt(10)

p = doc.add_paragraph()
r = p.add_run("特别提醒:第一轮的主要问题是量表被压缩——几乎所有题都打了 2 或 3,"
              "两端的 0、1、4 极少使用。校准时请特别练习端点档的识别:"
              "什么样的题该毫不犹豫给 4,什么样的题该给 1 或 0。")
r.bold = True
r.font.size = Pt(10)

write_rubric(doc)
doc.add_page_break()

for s in cal:
    p = doc.add_paragraph()
    r = p.add_run(f"[校{s['cal_order']:02d}]  {s['title']}")
    r.bold = True
    r.font.size = Pt(11)
    p2 = doc.add_paragraph()
    r2 = p2.add_run("tags: " + ", ".join(s["tags"]))
    r2.font.size = Pt(9)
    r2.font.color.rgb = RGBColor(0x60, 0x60, 0x60)
    doc.add_paragraph(clean(s["body_excerpt"]))
    p3 = doc.add_paragraph()
    r3 = p3.add_run("我的评分(0-4):____")
    r3.font.color.rgb = RGBColor(0x2E, 0x5A, 0x88)
doc.save(os.path.join(HERE, "校准题集_20题.docx"))

# 旧的含参考分版本若存在,删除以免误发
old = os.path.join(HERE, "校准题集_20题_含参考分.docx")
if os.path.exists(old):
    os.remove(old)
    print("[removed] 校准题集_20题_含参考分.docx (含模型标注,不可外发)")
old_json = os.path.join(HERE, "calibration_set_20.json")
if os.path.exists(old_json):
    os.remove(old_json)

# ---- 第二轮正式问卷 v2 ----
doc = Document()
st = doc.styles["Normal"]
st.font.name = "Times New Roman"
st.font.size = Pt(10.5)

doc.add_heading("P9 腿B 人工金标准编码问卷 v2(300 题,盲态)", level=0)
p = doc.add_paragraph()
p.add_run("用途:为 Stack Overflow 问题的 AI 可替代性分类建立人工金标准。"
          "两位编码员独立作答,期间不得讨论、不得查看对方评分、不得查询问题的发布日期。").bold = True
doc.add_paragraph(
    "与第一版的关系:题目完全相同,呈现顺序重新打乱,评分标准补上了每一档的典型例子。"
    "请按现在的理解重新独立评分,不要试图回忆或复制上一次的打分。")
doc.add_paragraph("评分录入:请在 coding_sheet_A_v2.csv / coding_sheet_B_v2.csv 的 "
                  "score_0_4 列填写 0-4 整数(与本问卷的 order 对应,注意顺序已与上一版不同)。")
p = doc.add_paragraph()
p.add_run("分两次交:请先做前 50 题(order 1-50),把评分表发回等确认后,再继续第 51-300 题。"
          "这是一次中途校验,用来尽早发现量表使用上的偏差——第一轮正是因为没有这道关卡,"
          "两人各做完 300 题才发现刻度对不齐。").bold = True

doc.add_heading("作答纪律(与盲态直接相关,请严格遵守)", level=1)
for rule in [
    "不得使用任何 AI 工具(ChatGPT / Claude / Copilot / 搜索引擎的 AI 摘要等)辅助判分。"
    "本问卷的全部意义就是取得一份不依赖模型家族的人类基准,一旦借助模型作答,这份金标准即告失效。",
    "不得在 Stack Overflow 或搜索引擎上回搜原题。原页面会同时暴露发布日期与已有答案,"
    "两者都直接破坏盲态。",
    "凭题面(标题 + 标签 + 正文节选)判分即可。[CODE] 与 [code] 都是被折叠的代码标记,"
    "遇到它们就按“这类问题一般需要多少提问者自身的上下文”来判断,不必设法还原代码。",
    "只填 0-4 的整数,不填小数、不留空。确实拿不准时按第一印象给最接近的一档,"
    "并在 coding_sheet 的备注列写一句理由或标“存疑”;不要为了追求前后一致而回头成批改分。",
    "建议一次连续做 60-100 题,中途可休息;全部 300 题约 2.5-4 小时。",
]:
    doc.add_paragraph(style="List Bullet").add_run(rule).font.size = Pt(10)

write_rubric(doc)

doc.add_heading("量表使用提示", level=1)
for tip in [
    "请把 0 到 4 五个档都用起来。如果绝大多数题都落在 2 和 3,通常说明量表被压缩了——"
    "遇到明显自足、答案唯一的题就大胆给 4,遇到明显只能靠提问者自身环境才能解决的题就给 1 或 0。",
    "一个实用的自问:把这道题原封不动发给一个没见过你项目的资深同行,"
    "他能不能直接写出可用的答案?能 → 偏 3-4;必须先反问“你的环境/数据/报错完整堆栈是什么” → 偏 0-1。",
    "题目里出现对方特有的变量名、目录结构、具体报错堆栈、自有数据样貌,通常是低分信号;"
    "问的是通用写法、语言特性、标准库用法,通常是高分信号。",
    "难度不等于低分。一道很难但有标准解法的算法题仍然是高分;"
    "一道很简单但必须看对方屏幕才知道哪错了的题是低分。",
]:
    doc.add_paragraph(style="List Bullet").add_run(tip).font.size = Pt(10)
doc.add_page_break()

for s in sample_v2:
    p = doc.add_paragraph()
    r = p.add_run(f"[{s['order_v2']:03d}]  {s['title']}")
    r.bold = True
    r.font.size = Pt(11)
    p2 = doc.add_paragraph()
    r2 = p2.add_run("tags: " + ", ".join(s["tags"]))
    r2.font.size = Pt(9)
    r2.font.color.rgb = RGBColor(0x60, 0x60, 0x60)
    doc.add_paragraph(clean(s["body_excerpt"]))
    p3 = doc.add_paragraph()
    r3 = p3.add_run("评分(0-4):____")
    r3.font.color.rgb = RGBColor(0x2E, 0x5A, 0x88)

doc.save(os.path.join(HERE, "人工金标准_问卷v2_300题.docx"))

# ---------------------------------------------------------------- 有机日期条目(扫描生成)
# 第一轮的手工清单只有 3 条(order 38/194/297),2026-08-16 的发送包审计用更宽的
# 日期正则(YYYY-MM / YYYY/M / YYYY年M)扫出第 4 条(qid=74974516,正文含
# 2017-01-02 试算表时间戳,窄扫描漏掉)。改为扫描生成,与 audit_v2_package.py
# 保持同一正则 —— 单一真相源,清单不再手工维护。
v2_by_qid = {s["question_id"]: s["order_v2"] for s in sample_v2}
date_re = re.compile(r"\b(20[12]\d)[-/年](0?[1-9]|1[0-2])\b")
org = [s for s in sorted(gold, key=lambda x: x["order"])
       if date_re.search(s["title"] + " " + s.get("body_excerpt", ""))]
with open(os.path.join(HERE, "organic_date_items.txt"), "w", encoding="utf-8") as f:
    f.write("# 题面(标题+正文节选)含有机日期的条目;预注册敏感性:剔除后重算 κ\n")
    f.write("# 本清单由 make_calibration_and_v2.py 扫描生成(正则与 audit_v2_package.py 一致),勿手改\n")
    f.write("# question_id 为准;order_r1 = 第一轮问卷序号, order_v2 = 第二轮问卷序号\n")
    f.write("# question_id, order_r1, order_v2\n")
    for s in org:
        f.write(f"{s['question_id']},{s['order']},{v2_by_qid[s['question_id']]}\n")
print(f"有机日期条目: {len(org)} 条 ->", [s["question_id"] for s in org])

print("校准题 20 题(每档 5,已打乱):",
      collections.Counter(c["model_score_SEALED"] for c in cal))
print("v2 问卷 300 题,顺序 seed =", SEED_ORDER_V2)
print("产出: 校准题集_20题.docx(无参考分,可外发) / 人工金标准_问卷v2_300题.docx / "
      "coding_sheet_A_v2.csv / coding_sheet_B_v2.csv / "
      "calibration_set_20_封存勿开.json(含模型标注,禁止外发) / "
      "gold_sample_v2_order.json / organic_date_items.txt(已补 v2 序号)")
