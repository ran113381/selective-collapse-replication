# -*- coding: utf-8 -*-
"""R2 C 阶段:评判批次(照第二轮 build_judge_batches_tier.py)。

对每个答题者目录:答题批 2j 与 2j+1 合成 judge_batch_<2j><2j+1>.json(40 题),
字段 {qid, question, reference_quality, reference_answer, llm_attempt},截断长度与第二轮相同
(question 2000、reference 1600、attempt 1600)。**可替代性分数与月份一概不放进评判批次**(脚本自检)。
用法:python R2c_build_judge.py sonnet5 | haiku45 | glm53 | glm46
"""
import io, json, os, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
C = os.path.join(HERE, "R2_criterion")
tag = sys.argv[1]
D = os.path.join(C, "batches_" + tag)
sample = {r["qid"]: r for r in json.load(io.open(os.path.join(C, "criterion_sample_v3.json"), encoding="utf-8"))}
missing, empty, total = [], [], 0
for j in range(0, 16, 2):
    jb = []
    for k in (j, j + 1):
        op = os.path.join(D, "answer_out_%d.json" % k)
        if not os.path.exists(op):
            raise SystemExit("缺 %s" % op)
        att = {int(a["qid"]): a["answer"] for a in json.load(io.open(op, encoding="utf-8"))}
        want = {x["qid"] for x in json.load(io.open(os.path.join(C, "batches_v3", "answer_batch_%d.json" % k), encoding="utf-8"))}
        pp = os.path.join(D, "answer_out_patch.json")            # 缺答补答(与第二轮 answer_out_patch 同法)
        if os.path.exists(pp):
            for a in json.load(io.open(pp, encoding="utf-8")):
                if int(a["qid"]) in want and not str(att.get(int(a["qid"]), "")).strip():
                    att[int(a["qid"])] = a["answer"]
        missing += [(k, q) for q in want - set(att)]
        for q in sorted(want & set(att)):
            if not str(att[q]).strip():
                empty.append((k, q)); continue
            r = sample[q]
            jb.append({"qid": q, "question": (r["title"] + "\n\n" + r["q_body"])[:2000],
                       "reference_quality": r["reference_quality"],
                       "reference_answer": (r["reference_answer"][:1600] if r["reference_answer"] else ""),
                       "llm_attempt": str(att[q])[:1600]})
    for it in jb:                                   # 防泄漏自检
        assert set(it) == {"qid", "question", "reference_quality", "reference_answer", "llm_attempt"}
    name = "judge_batch_%d%d.json" % (j, j + 1)
    json.dump(jb, io.open(os.path.join(D, name), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    total += len(jb)
print("%s:评判批 8 个,共 %d 题;缺答 %d、空答 %d" % (tag, total, len(missing), len(empty)))
if missing or empty:
    print("  缺/空:", missing[:10], empty[:10])
