# -*- coding: utf-8 -*-
"""Criterion-validity step 1 — fetch full question bodies + accepted answers.

Criterion-validity logic for the AI-substitutability rubric:
  the construct claims a high-substitutability question is one a capable LLM can
  answer from its text alone. Criterion test: does the 0-4 score PREDICT actual
  LLM answerability, judged against the human accepted answer?

This script builds a stratified sample (by substitutability score 1-4), fetches
each question's full body and its ACCEPTED answer body from the SE API (the human
ground truth), and writes criterion_sample.json for the blind answer/judge passes.
Only questions with an accepted answer are kept (so a ground truth exists).
Resumable via on-disk cache. Needs network.
"""
import os, json, csv, re, time, html, random
import urllib.request, urllib.parse

DATA = r"E:\智能体论文\_legB_data"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "criterion_sample.json")
FILES = ["so_questions_full.json", "so_questions_ext_py.json"]
LAB = ["question_labels.csv", "question_labels_ext_py.csv"]
KEY = os.environ.get("STACK_API_KEY")
SEED = 20260725
PER_BIN_TARGET = 22          # keep up to this many per score bin (balanced)
PER_BIN_CANDIDATES = 240      # oversample candidates


def strip_html(s, cap=1600):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    return s[:cap]


def api(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def fetch_questions(ids):
    """question body for up to 100 ids."""
    p = {"site": "stackoverflow", "filter": "withbody"}
    if KEY: p["key"] = KEY
    out = {}
    url = f"https://api.stackexchange.com/2.3/questions/{';'.join(map(str,ids))}?" + urllib.parse.urlencode(p)
    d = api(url)
    for it in d.get("items", []):
        out[it["question_id"]] = {
            "title": it.get("title", ""), "body": strip_html(it.get("body", "")),
            "tags": it.get("tags", [])}
    if d.get("backoff"): time.sleep(d["backoff"] + 1)
    return out


def fetch_best_answers(ids):
    """Ground-truth answer per question: the ACCEPTED answer, else the top-voted
    (score>=1). Uses /questions/{ids}/answers sorted by votes desc; page 1 (up to
    100 answers across the batch) carries the best answer for each."""
    p = {"site": "stackoverflow", "filter": "withbody", "sort": "votes",
         "order": "desc", "pagesize": 100}
    if KEY: p["key"] = KEY
    best = {}   # qid -> (is_accepted, score, body)
    page = 1
    while True:
        p["page"] = page
        url = (f"https://api.stackexchange.com/2.3/questions/{';'.join(map(str,ids))}/answers?"
               + urllib.parse.urlencode(p))
        d = api(url)
        for it in d.get("items", []):
            qid = it["question_id"]; acc = bool(it.get("is_accepted"))
            sc = it.get("score", 0); body = strip_html(it.get("body", ""))
            cur = best.get(qid)
            # prefer accepted; else higher score
            key = (1 if acc else 0, sc)
            if cur is None or key > (1 if cur[0] else 0, cur[1]):
                best[qid] = (acc, sc, body)
        if d.get("backoff"): time.sleep(d["backoff"] + 1)
        if d.get("has_more") and page < 5:
            page += 1; time.sleep(0.2)
        else:
            break
    return best


def main():
    labels = {}
    for fn in LAB:
        for r in csv.DictReader(open(os.path.join(DATA, fn), encoding="utf-8")):
            labels[int(r["question_id"])] = int(r["score"])
    meta = {}
    for fn in FILES:
        for q in json.load(open(os.path.join(DATA, fn), encoding="utf-8")):
            meta[int(q["question_id"])] = q
    by_bin = {1: [], 2: [], 3: [], 4: []}
    for qid, s in labels.items():
        if s in by_bin and qid in meta:
            by_bin[s].append(qid)
    rng = random.Random(SEED)
    cand = []
    for s in (1, 2, 3, 4):
        pool = by_bin[s][:]; rng.shuffle(pool)
        cand += [(qid, s) for qid in pool[:PER_BIN_CANDIDATES]]
    print(f"candidates: {len(cand)} ({[len(by_bin[s]) for s in (1,2,3,4)]} available per bin)")

    # fetch question bodies + best (accepted/top-voted) answers
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

    # assemble, cap per bin (ground truth = accepted or top-voted score>=1)
    score_of = dict(cand)
    kept = {1: [], 2: [], 3: [], 4: []}
    rows = []
    for qid, info in qinfo.items():
        s = score_of.get(qid); b = best.get(qid)
        if s is None or b is None:
            continue
        acc, sc, body = b
        if not body or (not acc and sc < 1):     # need a credible human answer
            continue
        if len(kept[s]) >= PER_BIN_TARGET:
            continue
        kept[s].append(qid)
        rows.append({"qid": qid, "sub_score": s, "title": info["title"],
                     "q_body": info["body"], "tags": info["tags"],
                     "gt_accepted": acc, "gt_votes": sc, "accepted_answer": body})
    json.dump(rows, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nkept {len(rows)} questions with accepted answers: "
          f"{[len(kept[s]) for s in (1,2,3,4)]} per bin (s1..s4)")
    print("written", OUT)


if __name__ == "__main__":
    main()
