# -*- coding: utf-8 -*-
"""Phase 1.4(b) — build blind judge batches for an alternative ANSWERER tier.

Generalizes build_judge_batches_v2.py: same join (attempts x criterion_sample_v2
with graded reference quality), same field layout the judge prompt expects
({qid, question, reference_quality, reference_answer, llm_attempt}), the
substitutability score NEVER included. Differences:
  * --dir selects the answerer's output directory (batches_haiku45 / batches_glmflash)
  * judge files are PAIRED (batches 2j and 2j+1 -> judge_batch_<2j><2j+1>.json,
    40 items), matching how the paper's judgments were filed (judgment_out_01 ...).

Usage:  python build_judge_batches_tier.py --dir batches_haiku45
"""
import json, os, glob, argparse, re

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("--dir", required=True)
a = ap.parse_args()
D = os.path.join(HERE, a.dir)
sample = {r["qid"]: r for r in json.load(open(os.path.join(HERE, "criterion_sample_v2.json"), encoding="utf-8"))}

nb = len(glob.glob(os.path.join(HERE, "batches_v2", "answer_batch_*.json")))
missing_all, total = [], 0
for j in range(0, nb, 2):
    jb = []
    for k in (j, j + 1):
        if k >= nb:
            continue
        outp = os.path.join(D, f"answer_out_{k}.json")
        if not os.path.exists(outp):
            raise SystemExit(f"missing {outp} — answer batch {k} not done yet")
        attempts = {a_["qid"]: a_["answer"] for a_ in json.load(open(outp, encoding="utf-8"))}
        binp = {x["qid"] for x in json.load(open(os.path.join(HERE, "batches_v2", f"answer_batch_{k}.json"), encoding="utf-8"))}
        missing_all += [(k, q) for q in binp - set(attempts)]
        for qid, att in attempts.items():
            r = sample.get(qid)
            if not r:
                continue
            jb.append({"qid": qid,
                       "question": (r["title"] + "\n\n" + r["q_body"])[:2000],
                       "reference_quality": r["reference_quality"],
                       "reference_answer": (r["reference_answer"][:1600] if r["reference_answer"] else ""),
                       "llm_attempt": att[:1600]})
    name = f"judge_batch_{j}{j+1}.json" if j + 1 < nb else f"judge_batch_{j}.json"
    json.dump(jb, open(os.path.join(D, name), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    total += len(jb)
    print(f"{name}: {len(jb)} items")
print("total", total)
if missing_all:
    print("MISSING (need patch):", missing_all)
