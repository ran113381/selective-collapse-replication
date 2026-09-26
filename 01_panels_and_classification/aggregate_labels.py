"""Aggregate per-month LLM labels + question meta into:
  - question_labels.csv        question-level (id, ym, score, label, title)
  - within_so_llm_panel.csv    month-level counts + gen_share + score-bin counts (for DiD)
Run after the classification workflow; handles whatever labels_*.json exist (incremental)."""
import json
import os
import csv
import argparse
from collections import defaultdict

ap = argparse.ArgumentParser()
ap.add_argument("--indir", default="batches")
ap.add_argument("--tag", default="")  # output suffix, e.g. "_java"
args = ap.parse_args()

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
BATCHES = os.path.join(DATA, args.indir)


def load(fp):
    with open(fp, encoding="utf-8") as f:
        return json.load(f)


rows = []
months = []
for fn in sorted(os.listdir(BATCHES)):
    if not (fn.startswith("labels_") and fn.endswith(".json")):
        continue
    ym = fn[len("labels_"):-len(".json")]
    qfile = os.path.join(BATCHES, f"q_{ym}.json")
    if not os.path.exists(qfile):
        continue
    labels = {int(l["question_id"]): l for l in load(os.path.join(BATCHES, fn))}
    qs = load(qfile)
    n_lab = 0
    for q in qs:
        lab = labels.get(int(q["question_id"]))
        if not lab:
            continue
        n_lab += 1
        rows.append({
            "question_id": q["question_id"], "ym": ym,
            "score": lab["score"], "label": lab["label"],
            "title": (q.get("title") or "")[:120],
        })
    months.append((ym, len(qs), n_lab))

qout = os.path.join(DATA, f"question_labels{args.tag}.csv")
with open(qout, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["question_id", "ym", "score", "label", "title"])
    w.writeheader()
    w.writerows(rows)

# month-level panel: counts + gen_share + per-score-bin counts (for within-SO DiD/dose-response)
by = defaultdict(lambda: defaultdict(int))
for r in rows:
    by[r["ym"]]["n"] += 1
    by[r["ym"]][r["label"]] += 1
    by[r["ym"]][f"s{r['score']}"] += 1

pout = os.path.join(DATA, f"within_so_llm_panel{args.tag}.csv")
score_cols = [f"s{i}" for i in range(5)]
with open(pout, "w", encoding="utf-8", newline="") as f:
    cols = ["ym", "n", "GEN", "VER", "gen_share"] + score_cols
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for ym in sorted(by):
        d = by[ym]
        n = d["n"]
        row = {"ym": ym, "n": n, "GEN": d["GEN"], "VER": d["VER"],
               "gen_share": round(d["GEN"] / n, 4) if n else 0}
        for s in score_cols:
            row[s] = d.get(s, 0)
        w.writerow(row)

print(f"{len(rows)} labeled questions across {len(months)} months")
print(f"[saved] {qout}")
print(f"[saved] {pout}")
if months:
    print("coverage (first/last):")
    for ym, nq, nl in months[:2] + months[-2:]:
        print(f"  {ym}: {nl}/{nq} labeled")
