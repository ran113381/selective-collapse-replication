# -*- coding: utf-8 -*-
"""Split criterion_sample_v2.json into blind-answer batches (~20/batch -> ~16 agents)."""
import json, os, random

HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, "criterion_sample_v2.json"), encoding="utf-8"))
random.Random(9).shuffle(d)   # mix bins across batches
os.makedirs(os.path.join(HERE, "batches_v2"), exist_ok=True)
BS = 20
nb = (len(d) + BS - 1) // BS
for k in range(nb):
    part = d[k*BS:(k+1)*BS]
    ab = [{"qid": r["qid"], "title": r["title"], "q_body": r["q_body"]} for r in part]
    json.dump(ab, open(os.path.join(HERE, "batches_v2", f"answer_batch_{k}.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
print(f"wrote {nb} batches, sizes: {[len(d[k*BS:(k+1)*BS]) for k in range(nb)]}")
