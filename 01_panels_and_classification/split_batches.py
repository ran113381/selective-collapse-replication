"""Split so_questions_full.json into per-month batch files for parallel classification."""
import json
import os
import argparse
from collections import defaultdict

ap = argparse.ArgumentParser()
ap.add_argument("--src", default="so_questions_full.json")
ap.add_argument("--outdir", default="batches")
args = ap.parse_args()

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
src = os.path.join(DATA, args.src)
bdir = os.path.join(DATA, args.outdir)
os.makedirs(bdir, exist_ok=True)

data = json.load(open(src, encoding="utf-8"))
bm = defaultdict(list)
for q in data:
    bm[q["ym"]].append(q)

for ym, qs in sorted(bm.items()):
    with open(os.path.join(bdir, f"q_{ym}.json"), "w", encoding="utf-8") as f:
        json.dump(qs, f, ensure_ascii=False, indent=1)

months = sorted(bm.keys())
print(f"{len(months)} month files -> {bdir}  ({len(data)} questions total)")
print(f"first={months[0]}  last={months[-1]}  per-month={len(bm[months[0]])}")
