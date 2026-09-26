# -*- coding: utf-8 -*-
"""Criterion-validity step 3a — build blind judge batches.

Joins the LLM attempts (answer_out_k.json) with the reference (human accepted /
top-voted) answers from criterion_sample.json, and writes judge_batch_k.json
containing {qid, question, reference_answer, llm_attempt} — WITHOUT the
substitutability score, so the judge is blind to it. Judges score whether the
LLM attempt correctly answers the question (against the human reference).
"""
import json, os, glob

HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(HERE, "batches")

sample = {r["qid"]: r for r in json.load(open(os.path.join(HERE, "criterion_sample.json"), encoding="utf-8"))}

# patch answers (for qids a batch agent skipped) are merged into whichever batch they belong to
patch = {}
pp = os.path.join(B, "answer_out_patch.json")
if os.path.exists(pp):
    patch = {a["qid"]: a["answer"] for a in json.load(open(pp, encoding="utf-8"))}
    print(f"(merging {len(patch)} patch answers)")

nb = 6
total = 0
seen = set()
for k in range(nb):
    outp = os.path.join(B, f"answer_out_{k}.json")
    if not os.path.exists(outp):
        raise SystemExit(f"missing {outp} — answer agent {k} not done yet")
    attempts = {a["qid"]: a["answer"] for a in json.load(open(outp, encoding="utf-8"))}
    # add any patch answers whose qid belongs to this input batch
    binp = {x["qid"] for x in json.load(open(os.path.join(B, f"answer_batch_{k}.json"), encoding="utf-8"))}
    for qid, att in patch.items():
        if qid in binp and qid not in attempts:
            attempts[qid] = att
    jb = []
    for qid, att in attempts.items():
        if qid in seen:
            continue
        seen.add(qid)
        r = sample.get(qid)
        if not r:
            continue
        jb.append({"qid": qid,
                   "question": (r["title"] + "\n\n" + r["q_body"])[:2000],
                   "reference_answer": r["accepted_answer"][:1600],
                   "llm_attempt": att[:1600]})
    json.dump(jb, open(os.path.join(B, f"judge_batch_{k}.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    total += len(jb)
    print(f"judge_batch_{k}.json: {len(jb)} items")
print("total", total)
