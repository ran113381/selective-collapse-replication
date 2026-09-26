# -*- coding: utf-8 -*-
"""Criterion-validity robustness — cross-model agreement of the answerer.

Batches 4 and 5 were answered twice, once by Fable 5 (before its credit ceiling)
and once by Haiku 4.5 (the uniform primary answerer). Judging both on the same 28
questions tests whether the criterion result depends on which "capable LLM" is
used to operationalize answerability. Builds a judge batch that interleaves both
models' attempts, blind to both the substitutability score AND the model identity.
"""
import json, os, random

HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(HERE, "batches")
sample = {r["qid"]: r for r in json.load(open(os.path.join(HERE, "criterion_sample.json"), encoding="utf-8"))}

items = []
for k in (4, 5):
    fab = {a["qid"]: a["answer"] for a in json.load(open(os.path.join(B, f"answer_out_fable_{k}.json"), encoding="utf-8"))}
    hai = {a["qid"]: a["answer"] for a in json.load(open(os.path.join(B, f"answer_out_{k}.json"), encoding="utf-8"))}
    for qid in fab:
        if qid not in hai or qid not in sample:
            continue
        r = sample[qid]
        for tag, att in (("A", fab[qid]), ("B", hai[qid])):
            items.append({"item_id": f"{qid}_{tag}", "qid": qid,
                          "question": (r["title"] + "\n\n" + r["q_body"])[:2000],
                          "reference_answer": r["accepted_answer"][:1600],
                          "llm_attempt": att[:1600]})
random.Random(11).shuffle(items)   # blind to model identity by ordering
json.dump(items, open(os.path.join(B, "judge_crossmodel.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
# key kept separately, not shown to the judge
key = {it["item_id"]: ("fable" if it["item_id"].endswith("_A") else "haiku") for it in items}
json.dump(key, open(os.path.join(HERE, "crossmodel_key.json"), "w", encoding="utf-8"), indent=1)
print(f"judge_crossmodel.json: {len(items)} items ({len(items)//2} questions x 2 models)")
