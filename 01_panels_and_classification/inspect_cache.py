"""Quick cache-coverage audit for Leg B. Lists every raw cache, its month span,
count, and any internal gaps. Also reports the common balanced window across sites."""
import os, json

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

ENDPOINTS = ["questions", "answers"]


def months_between(a, b):
    ya, ma = (int(x) for x in a.split("-"))
    yb, mb = (int(x) for x in b.split("-"))
    out = []
    y, m = ya, ma
    while (y, m) <= (yb, mb):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return out


spans = {}
print(f"{'file':42} {'n':>4} {'first':>8} {'last':>8} {'gaps':>5}")
print("-" * 72)
for fn in sorted(os.listdir(DATA)):
    if fn.startswith("so_raw_") and fn.endswith(".json"):
        with open(os.path.join(DATA, fn), encoding="utf-8") as f:
            c = json.load(f)
        ks = sorted(c.keys())
        if not ks:
            print(f"{fn:42} {0:>4}  EMPTY")
            continue
        full = months_between(ks[0], ks[-1])
        gaps = [m for m in full if m not in c]
        print(f"{fn:42} {len(ks):>4} {ks[0]:>8} {ks[-1]:>8} {len(gaps):>5}"
              + (f"  missing: {gaps}" if gaps else ""))
        spans[fn] = (ks[0], ks[-1], set(c.keys()))

# common balanced window per endpoint (intersection of all sites' coverage)
print("\n-- common balanced window (intersection across all cached sites) --")
for ep in ENDPOINTS:
    sites_cov = [v[2] for fn, v in spans.items() if fn.endswith(f"_{ep}.json")]
    n_sites = len(sites_cov)
    if not sites_cov:
        continue
    common = set.intersection(*sites_cov)
    if common:
        cm = sorted(common)
        print(f"  {ep:10}: {n_sites} sites, {len(cm)} common months  {cm[0]}..{cm[-1]}")
    else:
        print(f"  {ep:10}: {n_sites} sites, NO common months")
