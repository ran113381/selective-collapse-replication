# -*- coding: utf-8 -*-
"""Phase B prep — fetch each question's FIRST-answer timestamp from the Stack
Exchange API, so the answer margin can use a fixed post-publication window
(30/90-day) instead of the scrape-date snapshot (the clean version
of the cohort-age mitigation in phaseA_answer_window.py).

For every python question in the leg-B sample it retrieves all answer creation
dates (sorted ascending), keeps the earliest per question, and writes:
    first_answer.csv : question_id, creation_date, first_answer_date, n_answers
Questions with no answer get an empty first_answer_date.

Design:
  * batches up to 100 question ids per call (SE API max), semicolon-joined
  * endpoint /2.3/questions/{ids}/answers?sort=creation&order=asc&pagesize=100
    filtered to include answer creation_date + question_id; paginates has_more
  * respects the API `backoff` field and stops politely near quota exhaustion
  * RESUMABLE: appends to first_answer.csv and skips ids already written, so a
    killed run resumes where it left off
  * optional key via env STACK_API_KEY (raises the daily quota from 300 to 10k);
    runs without a key for a small sample

Run (needs network):  python fetch_first_answers.py
Then:                  python fixed_window_answer.py
"""
import os, json, csv, time, sys
import urllib.request, urllib.parse

DATA = r"E:\智能体论文\_legB_data"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "first_answer.csv")
FILES = ["so_questions_full.json", "so_questions_ext_py.json"]
API = "https://api.stackexchange.com/2.3/questions/{ids}/answers"
KEY = os.environ.get("STACK_API_KEY")  # optional; raises quota
PAGESIZE = 100
SLEEP = 0.15  # polite base pause between calls


def load_targets():
    qs = {}
    for fn in FILES:
        for q in json.load(open(os.path.join(DATA, fn), encoding="utf-8")):
            qs[int(q["question_id"])] = int(q["creation_date"])
    return qs


def already_done():
    done = set()
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT, encoding="utf-8")):
            done.add(int(r["question_id"]))
    return done


def call(ids):
    params = {"site": "stackoverflow", "sort": "creation", "order": "asc",
              "pagesize": PAGESIZE, "filter": "!nNPvSNe7D9"}  # creation_date + question_id
    if KEY:
        params["key"] = KEY
    first = {}
    counts = {}
    page = 1
    while True:
        params["page"] = page
        url = API.format(ids=";".join(map(str, ids))) + "?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=60) as resp:
            data = json.load(resp)
        for a in data.get("items", []):
            qid = a["question_id"]; cd = a["creation_date"]
            counts[qid] = counts.get(qid, 0) + 1
            if qid not in first or cd < first[qid]:
                first[qid] = cd
        if data.get("backoff"):
            time.sleep(data["backoff"] + 1)
        if data.get("quota_remaining", 1) <= 5:
            print(f"[quota] near exhaustion (remaining {data.get('quota_remaining')}), stopping politely.")
            return first, counts, True
        if data.get("has_more"):
            page += 1
            time.sleep(SLEEP)
        else:
            break
    return first, counts, False


def main():
    targets = load_targets()
    done = already_done()
    todo = [q for q in targets if q not in done]
    print(f"targets={len(targets):,}  already done={len(done):,}  to fetch={len(todo):,}"
          f"  (key={'yes' if KEY else 'no — 300/day quota'})")
    new = not os.path.exists(OUT)
    f = open(OUT, "a", newline="", encoding="utf-8")
    w = csv.writer(f)
    if new:
        w.writerow(["question_id", "creation_date", "first_answer_date", "n_answers"])
    stop = False
    for i in range(0, len(todo), PAGESIZE):
        if stop:
            break
        batch = todo[i:i + PAGESIZE]
        try:
            first, counts, stop = call(batch)
        except Exception as e:
            print(f"[error] batch {i//PAGESIZE}: {e}; sleeping 5s and retrying once")
            time.sleep(5)
            try:
                first, counts, stop = call(batch)
            except Exception as e2:
                print(f"[error] retry failed: {e2}; stopping, run again to resume")
                break
        for qid in batch:
            w.writerow([qid, targets[qid], first.get(qid, ""), counts.get(qid, 0)])
        f.flush()
        print(f"  batch {i//PAGESIZE + 1}/{(len(todo)+PAGESIZE-1)//PAGESIZE} written "
              f"({i+len(batch)}/{len(todo)})", flush=True)
        time.sleep(SLEEP)
    f.close()
    print("done (resumable — re-run to continue if quota/backoff stopped it).")


if __name__ == "__main__":
    main()
