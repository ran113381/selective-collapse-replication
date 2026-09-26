"""
P9 Leg B — component A: pull SO question TEXT (title+body+tags+meta) for LLM
AI-substitutability classification (rigorous within-SO). Reuses key/throttle from
fetch_so_activity.

SE API: /questions?...&filter=withbody returns item.body (HTML) on top of the default
fields (title, tags, score, creation_date, answer_count, is_answered, accepted_answer_id).

PROTOTYPE first: pull a small sample to validate the classification rubric BEFORE scaling
to the full ~400/mo × 42mo design (so we don't burn opus budget on a bad rubric).

Usage:
  python fetch_so_questions.py --key XXXX --start 2023-06 --end 2023-06 --pagesize 30
  python fetch_so_questions.py --key XXXX --start 2021-06 --end 2024-06 --per-month 400  # scale
"""
import os
import re
import json
import html
import time
import argparse

import fetch_so_activity as base

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)


def strip_html(s, maxlen=1400):
    """HTML body -> readable plain text; collapse code blocks to a [CODE] marker so the
    classifier sees structure without huge code dumps. Truncate for prompt economy."""
    s = s or ""
    s = re.sub(r"<pre[\s\S]*?</pre>", " [CODE] ", s, flags=re.I)
    s = re.sub(r"<code>[\s\S]*?</code>", " [code] ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:maxlen]


def fetch_month(tag, ym, max_pages, pagesize, throttle):
    """Pull up to max_pages of questions created in month ym (sorted by creation asc)."""
    fromd, tod = base.month_window(ym)
    items = []
    for page in range(1, max_pages + 1):
        url = (base.API.format(endpoint="questions")
               + f"?site=stackoverflow&tagged={tag}&fromdate={fromd}&todate={tod}"
               + f"&sort=creation&order=asc&pagesize={pagesize}&page={page}&filter=withbody")
        d = base._get_json(base._keyed(url))
        items.extend(d.get("items", []))
        if not d.get("has_more"):
            break
        if throttle:
            time.sleep(throttle)
        if d.get("backoff"):
            time.sleep(float(d["backoff"]) + 0.5)
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="python")
    ap.add_argument("--start", default="2023-06")
    ap.add_argument("--end", default="2023-06")
    ap.add_argument("--per-month", type=int, default=30, help="questions per month (<=100/page)")
    ap.add_argument("--throttle", type=float, default=0.2)
    ap.add_argument("--key", default=None)
    ap.add_argument("--out", default="so_questions_sample.json")
    args = ap.parse_args()
    if args.key:
        base.API_KEY = args.key

    pagesize = min(args.per_month, 100)
    max_pages = max(1, (args.per_month + pagesize - 1) // pagesize)

    rows = []
    for ym in base.month_iter(args.start, args.end):
        try:
            items = fetch_month(args.tag, ym, max_pages, pagesize, args.throttle)
        except base.ThrottleExhausted as ex:
            print(f"[THROTTLED] ~{(ex.seconds or 0)/3600:.1f}h until reset; saving partial.")
            break
        items = items[:args.per_month]
        for it in items:
            rows.append({
                "question_id": it.get("question_id"),
                "ym": ym,
                "creation_date": it.get("creation_date"),
                "title": it.get("title"),
                "tags": it.get("tags"),
                "score": it.get("score"),
                "answer_count": it.get("answer_count"),
                "is_answered": it.get("is_answered"),
                "body_excerpt": strip_html(it.get("body", "")),
            })
        print(f"  {ym}: {len(items)} questions")

    out = os.path.join(DATA, args.out)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    print(f"[saved] {out}  ({len(rows)} questions)")


if __name__ == "__main__":
    main()
