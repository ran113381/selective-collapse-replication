"""
P9 Leg B — WITHIN-SO probe: monthly question counts by AI-substitutability of question type.

WHY (within-SO identification, after the cross-site DiD failed):
  The cross-site design (SO vs other SE sites) cannot separate "AI killed SO" from
  "the whole SE network is collapsing" — every control site is itself AI-exposed and the
  network declines multi-causally. This script instead identifies the generation-vs-
  verification mechanism INSIDE Stack Overflow, holding language fixed (python) and
  varying question TYPE via co-tags:

    GENERATION-type co-tags (answer is canonical boilerplate/syntax — ChatGPT nails it,
      so users substitute away from SO):       regex, string, list, datetime, sorting, ...
    VERIFICATION-type co-tags (answer needs judgment / context-specific debugging — ChatGPT
      unreliable, so the question persists):    performance, debugging, concurrency, ...

  Prediction (mother thesis): post-ChatGPT (2022-12), GENERATION-type questions fall MORE
  than VERIFICATION-type. The network-wide decline is a common shock absorbed by month FE,
  so the GEN-vs-VER differential is a clean within-SO estimate of the mechanism — immune to
  the cross-site contamination that sank the previous design.

  ⚠ This is an ILLUSTRATIVE PROBE: the co-tag split is a hand-curated proxy for AI-
  substitutability, not a systematic classification. The rigorous version classifies actual
  question TEXT (SE data dump + LLM substitutability scoring). Use this only to see whether
  the differential exists before investing in the 64GB dump.

Method:
  SE API /questions?tagged=python;<cotag>&fromdate&todate&filter=total returns the count of
  questions carrying BOTH tags in the window (one call per cotag-month). Reuses the proven
  key/throttle/cache/ThrottleExhausted machinery from fetch_so_activity.

Outputs (legB/data/):
  so_tag_python_<cotag>.json     per-cotag {ym: count} cache (resumable)
  so_tag_panel.csv               tidy long panel: base,cotag,group,ym,date,year,month,count
  fetch_tags_summary.txt         validation report (GEN vs VER trajectory around 2022-12)

Usage:
  python fetch_so_tags.py --key XXXX                       # full probe 2021-01..2026-05
  python fetch_so_tags.py --key XXXX --start 2022-01 --end 2023-12
"""
import os
import sys
import csv
import json
import time
import argparse

import fetch_so_activity as base  # reuse _get_json, _keyed, month_iter, month_window, ThrottleExhausted, probe_quota, API, save/load patterns

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)

BASE_TAG = "python"   # language held fixed so the GEN/VER contrast isn't a topic confound

# Hand-curated proxy for AI-substitutability (see module docstring caveat). Co-tagged with
# python. GENERATION = canonical-answer how-tos ChatGPT answers in one shot. VERIFICATION =
# judgment / context-specific debugging where ChatGPT is unreliable.
GROUPS = {
    "generation": [
        "regex", "string", "list", "dictionary", "datetime",
        "sorting", "csv", "json",
    ],
    "verification": [
        "performance", "debugging", "multithreading", "optimization",
        "memory", "concurrency", "multiprocessing",
    ],
}


def cotag_group(cotag):
    for g, tags in GROUPS.items():
        if cotag in tags:
            return g
    return "?"


def cache_path(cotag):
    safe = cotag.replace(".", "_").replace("/", "_")
    return os.path.join(DATA, f"so_tag_{BASE_TAG}_{safe}.json")


def load_cache(cotag):
    p = cache_path(cotag)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cotag, d):
    p = cache_path(cotag)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=0, sort_keys=True)
    os.replace(tmp, p)


def fetch_tag_count(cotag, ym, throttle=0.15):
    """One monthly count of questions tagged BOTH base_tag AND cotag, via filter=total."""
    fromd, tod = base.month_window(ym)
    tagged = f"{BASE_TAG};{cotag}"        # ';' = AND in the SE API
    url = (base.API.format(endpoint="questions")
           + f"?site=stackoverflow&tagged={tagged}"
           + f"&fromdate={fromd}&todate={tod}&filter=total&pagesize=1")
    d = base._get_json(base._keyed(url))
    cnt = d.get("total")
    if cnt is None:
        raise RuntimeError(f"no 'total' for {tagged}/{ym}: {d}")
    if throttle:
        time.sleep(throttle)
    return int(cnt)


def fetch_cotag(cotag, months, throttle):
    """Fill {ym: count} for one cotag, resuming from cache; persists on throttle."""
    cache = load_cache(cotag)
    todo = [ym for ym in months if ym not in cache]
    if not todo:
        print(f"  [python;{cotag}] all {len(months)} months cached", flush=True)
        return cache
    print(f"  [python;{cotag}] fetching {len(todo)} of {len(months)} months", flush=True)
    for i, ym in enumerate(todo):
        try:
            cnt = fetch_tag_count(cotag, ym, throttle=throttle)
        except base.ThrottleExhausted:
            save_cache(cotag, cache)
            raise
        cache[ym] = cnt
        if i < 2 or i == len(todo) - 1:
            print(f"    {ym}: {cnt:,}", flush=True)
        if (i + 1) % 10 == 0:
            save_cache(cotag, cache)
    save_cache(cotag, cache)
    return cache


def build_panel(months):
    rows = []
    for g, tags in GROUPS.items():
        for cotag in tags:
            cache = load_cache(cotag)
            for ym in months:
                if ym not in cache:
                    continue
                y, m = (int(x) for x in ym.split("-"))
                rows.append({
                    "base": BASE_TAG, "cotag": cotag, "group": g,
                    "ym": ym, "date": f"{ym}-01", "year": y, "month": m,
                    "count": cache[ym],
                })
    out = os.path.join(DATA, "so_tag_panel.csv")
    cols = ["base", "cotag", "group", "ym", "date", "year", "month", "count"]
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in sorted(rows, key=lambda r: (r["group"], r["cotag"], r["ym"])):
            w.writerow(r)
    return rows, out


def group_totals(months):
    """Aggregate GEN vs VER monthly totals (sum across cotags) for a quick trajectory read."""
    tot = {g: {ym: 0 for ym in months} for g in GROUPS}
    have = {g: {ym: 0 for ym in months} for g in GROUPS}
    for g, tags in GROUPS.items():
        for cotag in tags:
            cache = load_cache(cotag)
            for ym in months:
                if ym in cache:
                    tot[g][ym] += cache[ym]
                    have[g][ym] += 1
    return tot, have


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2021-01")
    ap.add_argument("--end", default="2026-05")
    ap.add_argument("--throttle", type=float, default=0.15)
    ap.add_argument("--key", default=None,
                    help="Stack Apps key (10,000/day); falls back to $STACK_APPS_KEY")
    args = ap.parse_args()

    if args.key:
        base.API_KEY = args.key   # _keyed() reads base.API_KEY

    months = list(base.month_iter(args.start, args.end))
    cotags = [c for tags in GROUPS.values() for c in tags]

    print("=" * 64)
    print("P9 Leg B — WITHIN-SO tag probe (generation vs verification)")
    print("=" * 64)
    print(f"base tag  : {BASE_TAG}")
    print(f"gen tags  : {GROUPS['generation']}")
    print(f"ver tags  : {GROUPS['verification']}")
    print(f"window    : {args.start} .. {args.end}  ({len(months)} months)")
    print(f"calls     : up to {len(cotags)*len(months):,} (1 call/cotag-month)")
    print(f"api key   : " + ("set (10,000/day)" if base.API_KEY else "NONE (300/day)"))
    print()
    base.probe_quota()
    print()

    t0 = time.time()
    throttled = False
    for cotag in cotags:
        if throttled:
            break
        try:
            fetch_cotag(cotag, months, args.throttle)
        except base.ThrottleExhausted as ex:
            hrs = (ex.seconds or 0) / 3600.0
            print(f"\n[THROTTLED] quota exhausted (~{hrs:.1f}h). Cached; rebuilding from cache.")
            throttled = True
    dt_s = time.time() - t0

    rows, out_csv = build_panel(months)
    print(f"\n[panel] {len(rows):,} rows -> {out_csv}")

    # ---- quick GEN-vs-VER trajectory around the 2022-12 event ----
    lines = []
    def out(s=""):
        lines.append(s); print(s)
    out("=" * 64)
    out("within-SO probe — GEN vs VER monthly totals (python co-tagged)")
    out("=" * 64)
    out(f"window {args.start}..{args.end}  rows={len(rows)}  elapsed={dt_s:,.1f}s")
    base.probe_quota()
    tot, have = group_totals(months)
    anchors = ["2022-06", "2022-11", "2023-06", "2023-12", "2024-12", months[-1]]
    anchors = [a for a in anchors if a in months]
    out("")
    out(f"  {'month':9} {'GEN':>9} {'VER':>9}  {'GEN/VER ratio':>13}")
    base_ratio = None
    for a in anchors:
        gv = tot["generation"][a]
        vv = tot["verification"][a]
        r = (gv / vv) if vv else float("nan")
        if a == "2022-11":
            base_ratio = r
        out(f"  {a:9} {gv:>9,} {vv:>9,}  {r:>13.3f}")
    if base_ratio:
        out("")
        out("  GEN/VER ratio vs 2022-11 (a FALLING ratio = generation questions dropping")
        out("  faster than verification = consistent with the mother thesis):")
        for a in anchors:
            vv = tot["verification"][a]
            r = (tot["generation"][a] / vv) if vv else float("nan")
            if a >= "2022-11":
                out(f"    {a}: ratio {r:.3f}  ({(r/base_ratio-1)*100:+.1f}% vs 2022-11)")
    out("")
    out(f"[saved] {out_csv}")
    rpt = os.path.join(DATA, "fetch_tags_summary.txt")
    with open(rpt, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    out(f"[saved] {rpt}")


if __name__ == "__main__":
    main()
