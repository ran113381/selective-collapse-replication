# -*- coding: utf-8 -*-
"""Criterion-validity v2 step 3a — build blind judge batches (graded reference quality).

Joins LLM attempts (batches_v2/answer_out_k.json) with criterion_sample_v2.json.
Each item carries reference_quality (accepted/top_voted/weak/none) so the judge
prompt can branch: with a reference, judge against it; with none, judge the
attempt's technical soundness directly. The substitutability score is NEVER
included (blind).
"""
import json, os, glob

HERE = os.path.dirname(os.path.abspath(__file__))
BV = os.path.join(HERE, "batches_v2")
sample = {r["qid"]: r for r in json.load(open(os.path.join(HERE, "criterion_sample_v2.json"), encoding="utf-8"))}

nb = len(glob.glob(os.path.join(BV, "answer_batch_*.json")))
total = 0
missing_all = []
for k in range(nb):
    outp = os.path.join(BV, f"answer_out_{k}.json")
    if not os.path.exists(outp):
        raise SystemExit(f"missing {outp} — answer agent {k} not done yet")
    attempts = {a["qid"]: a["answer"] for a in json.load(open(outp, encoding="utf-8"))}
    binp = {x["qid"] for x in json.load(open(os.path.join(BV, f"answer_batch_{k}.json"), encoding="utf-8"))}
    missing = binp - set(attempts)
    if missing:
        missing_all += [(k, q) for q in missing]
    jb = []
    for qid, att in attempts.items():
        r = sample.get(qid)
        if not r:
            continue
        jb.append({"qid": qid,
                   "question": (r["title"] + "\n\n" + r["q_body"])[:2000],
                   "reference_quality": r["reference_quality"],
                   "reference_answer": (r["reference_answer"][:1600] if r["reference_answer"] else ""),
                   "llm_attempt": att[:1600]})
    json.dump(jb, open(os.path.join(BV, f"judge_batch_{k}.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    total += len(jb)
    print(f"judge_batch_{k}.json: {len(jb)} items")
print("total", total)
if missing_all:
    print("MISSING (need patch):", missing_all)
