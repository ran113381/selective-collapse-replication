# -*- coding: utf-8 -*-
"""Criterion-validity v2 — fetch with the selection-bias fix.

Round 1 (criterion_sample.json, N=88) required a "credible" human answer
(accepted, or top-voted with score>=1) as the inclusion filter. That filter's
pass rate fell steeply with substitutability (s1 11% vs s4 31%+ of candidates),
so the included s1 items were an unrepresentative "surprisingly well-answered"
subset — a real design flaw, conservative in direction but a validity concern.

Fix: sample directly, no answer-existence filter. Every sampled question is kept.
Ground truth quality is graded, not gated:
  accepted   > top-voted (score>=1) > any answer (best available) > none
The judge (step 3) is told the quality tier and, for "none", judges the LLM
attempt on technical merit alone rather than against a human comparison.

Target: 80 per bin (320 total) — powers the generative-vs-verification contrast
at the ~154-per-group threshold from the round-1 power calc, with margin.
Excludes qids already used in round 1 (criterion_sample.json) for a clean,
independent sample.
"""
import os, json, csv, re, time, html, random
import urllib.request, urllib.parse

DATA = r"E:\智能体论文\_legB_data"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "criterion_sample_v2.json")
FILES = ["so_questions_full.json", "so_questions_ext_py.json"]
LAB = ["question_labels.csv", "question_labels_ext_py.csv"]
KEY = os.environ.get("STACK_API_KEY")
SEED = 20260726
PER_BIN_TARGET = 80
PER_BIN_CANDIDATES = 300   # ~34% of the first 110 survived (deleted/locked/migrated);
                           # widened with the same seed so the prior 150 are a subset, not re-picked fresh


def strip_html(s, cap=1600):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    return s[:cap]


def api(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def fetch_questions(ids):
    p = {"site": "stackoverflow", "filter": "withbody"}
    if KEY: p["key"] = KEY
    out = {}
    url = f"https://api.stackexchange.com/2.3/questions/{';'.join(map(str,ids))}?" + urllib.parse.urlencode(p)
    d = api(url)
    for it in d.get("items", []):
        out[it["question_id"]] = {"title": it.get("title", ""),
                                   "body": strip_html(it.get("body", "")),
                                   "tags": it.get("tags", [])}
    if d.get("backoff"): time.sleep(d["backoff"] + 1)
    return out


def fetch_best_answers(ids):
    """Best-available answer per question, graded not gated:
    tier 3=accepted, 2=top-voted score>=1, 1=any answer (highest score), 0=none."""
    p = {"site": "stackoverflow", "filter": "withbody", "sort": "votes",
         "order": "desc", "pagesize": 100}
    if KEY: p["key"] = KEY
    best = {}   # qid -> (tier, score, body)
    page = 1
    while True:
        p["page"] = page
        url = (f"https://api.stackexchange.com/2.3/questions/{';'.join(map(str,ids))}/answers?"
               + urllib.parse.urlencode(p))
        d = api(url)
        for it in d.get("items", []):
            qid = it["question_id"]; acc = bool(it.get("is_accepted"))
            sc = it.get("score", 0); body = strip_html(it.get("body", ""))
            tier = 3 if acc else (2 if sc >= 1 else 1)
            cur = best.get(qid)
            key = (tier, sc)
            if cur is None or key > (cur[0], cur[1]):
                best[qid] = (tier, sc, body)
        if d.get("backoff"): time.sleep(d["backoff"] + 1)
        if d.get("has_more") and page < 5:
            page += 1; time.sleep(0.2)
        else:
            break
    return best


TIER_NAME = {3: "accepted", 2: "top_voted", 1: "weak", 0: "none"}


def main():
    labels = {}
    for fn in LAB:
        for r in csv.DictReader(open(os.path.join(DATA, fn), encoding="utf-8")):
            labels[int(r["question_id"])] = int(r["score"])
    meta = {}
    for fn in FILES:
        for q in json.load(open(os.path.join(DATA, fn), encoding="utf-8")):
            meta[int(q["question_id"])] = q
    used = set()
    r1p = os.path.join(HERE, "criterion_sample.json")
    if os.path.exists(r1p):
        used = {r["qid"] for r in json.load(open(r1p, encoding="utf-8"))}
    print(f"excluding {len(used)} round-1 qids")

    by_bin = {1: [], 2: [], 3: [], 4: []}
    for qid, s in labels.items():
        if s in by_bin and qid in meta and qid not in used:
            by_bin[s].append(qid)
    rng = random.Random(SEED)
    cand = []
    for s in (1, 2, 3, 4):
        pool = by_bin[s][:]; rng.shuffle(pool)
        cand += [(qid, s) for qid in pool[:PER_BIN_CANDIDATES]]
    print(f"candidates: {len(cand)}  (pool sizes {[len(by_bin[s]) for s in (1,2,3,4)]})")

    qinfo, best = {}, {}
    ids = [c[0] for c in cand]
    for i in range(0, len(ids), 100):
        batch = ids[i:i+100]
        for fn, dst in ((fetch_questions, qinfo), (fetch_best_answers, best)):
            try:
                dst.update(fn(batch))
            except Exception as e:
                print(f"[batch {i//100} {fn.__name__}] error {e}; retry once"); time.sleep(4)
                try: dst.update(fn(batch))
                except Exception as e2: print(f"  retry failed {e2}")
            time.sleep(0.2)
        print(f"  fetched {min(i+100,len(ids))}/{len(ids)}", flush=True)

    score_of = dict(cand)
    kept = {1: [], 2: [], 3: [], 4: []}
    tier_counts = {1: {}, 2: {}, 3: {}, 4: {}}
    rows = []
    for qid, info in qinfo.items():
        s = score_of.get(qid)
        if s is None or len(kept[s]) >= PER_BIN_TARGET:
            continue
        tier, sc, body = best.get(qid, (0, 0, ""))
        kept[s].append(qid)
        tn = TIER_NAME[tier]
        tier_counts[s][tn] = tier_counts[s].get(tn, 0) + 1
        rows.append({"qid": qid, "sub_score": s, "title": info["title"],
                     "q_body": info["body"], "tags": info["tags"],
                     "reference_quality": tn, "reference_answer": body})
    json.dump(rows, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nkept {len(rows)} questions (target {4*PER_BIN_TARGET}): "
          f"{[len(kept[s]) for s in (1,2,3,4)]} per bin (s1..s4)")
    for s in (1, 2, 3, 4):
        print(f"  s{s} reference_quality: {tier_counts[s]}")
    print("written", OUT)


if __name__ == "__main__":
    main()
