"""
P9 Leg B — Stack Exchange monthly activity fetcher (VOLUNTARY-commons collapse pole).

Theory mapping (开干包 / bifurcation, moat 2):
  English Stack Overflow is a VOLUNTARY knowledge commons. When generative AI made
  answers cheap to PRODUCE but expensive to VERIFY, SO banned AI answers (2022-12-05)
  and participation unravelled (Akerlof lemons; del Rio-Chanona et al. PNAS Nexus 2024
  measured -25% activity within 6 months). This is the LEMONS POLE of the bifurcation,
  to be paired with Leg A's GitHub "mandated-resilience" pole.

What this script does:
  Pulls MONTHLY question & answer COUNTS for English Stack Overflow (treated, ChatGPT/
  AI-exposed) plus control sites from the Stack Exchange API. Controls are chosen so the
  AI-exposure differs while the platform/governance is held fixed:
    - ru.stackoverflow      : same platform, Russian-language Q&A (ChatGPT weak in Russian
                              and largely unavailable in Russia in late 2022) — primary control
    - pt.stackoverflow      : Portuguese SO (weaker early ChatGPT exposure)
    - es.stackoverflow      : Spanish SO (weaker early ChatGPT exposure)
    - math.stackexchange    : English, but math/LaTeX reasoning where early ChatGPT was poor
    - mathoverflow.net      : research-math, expert-gated, low LLM substitutability
    - superuser             : English consumer-tech help (LLM-substitutable; secondary treated)
  (Control set mirrors del Rio-Chanona's design — Russian/Chinese SO + math forums.)

API notes (api.stackexchange.com v2.3; 300/day quota is SHARED PER IP and easily spent —
a free Stack Apps key via --key/$STACK_APPS_KEY gives a separate 10,000/day per-key quota):
  - Endpoint /questions and /answers accept fromdate/todate as UNIX seconds (UTC).
  - filter=total returns ONLY {"total": N} for the window => exact monthly count in ONE call,
    no paging, minimal payload. This is how we get clean monthly counts.
  - filter=total strips quota fields, so we periodically issue a default-filter probe to read
    quota_remaining / quota_max and back off as it drains.
  - Respect has_more / backoff fields; honour HTTP 429 + the "backoff" seconds the API returns.
  - 'requests' is unavailable in this env -> stdlib urllib + gzip + json only.

Outputs (legB/data/):
  so_raw_<site>_<endpoint>.json      raw {ym: total} cache per site/endpoint (resumable)
  so_monthly_panel.csv               tidy long panel: site,endpoint,ym,date,count,treated,...
  fetch_summary.txt                  human-readable validation report

Usage:
  python fetch_so_activity.py --sites stackoverflow,ru.stackoverflow \
      --start 2022-06 --end 2023-06            # proof run across 2 sites
  python fetch_so_activity.py                  # full default panel 2021-01..2024-12
  python fetch_so_activity.py --probe-quota    # one quota probe, then exit
  python fetch_so_activity.py --key XXXX        # use a Stack Apps key (10,000/day quota)
"""
import os
import sys
import json
import gzip
import time
import argparse
import calendar
import datetime as dt
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)

API = "https://api.stackexchange.com/2.3/{endpoint}"
UA = "P9-verification-economics-research/0.1 (measure-only; contact withheld for anonymized review)"

# A free Stack Apps key raises the daily quota from 300 (shared per-IP) to 10,000
# (per-key). Register at https://stackapps.com/apps/oauth/register — for read-only
# count calls ONLY the returned 'key' string is used (no OAuth/token flow). Supply it
# via --key or the STACK_APPS_KEY env var; without it we fall back to the 300/IP quota.
API_KEY = os.environ.get("STACK_APPS_KEY") or None

# treated = English SO (full early-ChatGPT exposure). Everything else is a control,
# with superuser as a secondary (English, LLM-substitutable) treated-ish robustness arm.
TREATED = {"stackoverflow"}
DEFAULT_SITES = [
    "stackoverflow",        # TREATED: English programming Q&A
    "ru.stackoverflow",     # control: Russian SO (low early ChatGPT exposure)
    "pt.stackoverflow",     # control: Portuguese SO
    "es.stackoverflow",     # control: Spanish SO
    "math.stackexchange",   # control: English math (LaTeX reasoning, poor early ChatGPT)
    "mathoverflow.net",     # control: research math, expert-gated
    "superuser",            # robustness: English consumer tech (LLM-substitutable)
]
ENDPOINTS = ["questions", "answers"]


def month_iter(start_ym, end_ym):
    """Yield 'YYYY-MM' strings from start to end inclusive."""
    y, m = (int(x) for x in start_ym.split("-"))
    ey, em = (int(x) for x in end_ym.split("-"))
    while (y, m) <= (ey, em):
        yield f"{y:04d}-{m:02d}"
        m += 1
        if m > 12:
            m, y = 1, y + 1


def month_window(ym):
    """'YYYY-MM' -> (fromdate, todate) UNIX seconds [first-of-month, first-of-next)."""
    y, m = (int(x) for x in ym.split("-"))
    fromd = calendar.timegm((y, m, 1, 0, 0, 0, 0, 0, 0))
    if m == 12:
        ny, nm = y + 1, 1
    else:
        ny, nm = y, m + 1
    tod = calendar.timegm((ny, nm, 1, 0, 0, 0, 0, 0, 0))
    return fromd, tod


def _keyed(url):
    """Append the Stack Apps key if configured (raises quota 300 -> 10,000/day).

    Safe to call on any endpoint URL here: every URL already carries a query string,
    so '&key=' never lands as the first parameter.
    """
    return url + (f"&key={API_KEY}" if API_KEY else "")


class ThrottleExhausted(Exception):
    """Per-IP (or per-key) daily quota is spent: the API returns HTTP 400 with
    error_id 502 'throttle_violation'. This is a TIME-based soft limit, not a malformed
    request — callers should persist progress and resume later (or supply --key for the
    separate per-key quota), never treat it as a hard failure. Carries seconds-to-reset.
    """

    def __init__(self, seconds, detail=""):
        self.seconds = seconds
        super().__init__(f"quota exhausted; {seconds}s until reset ({detail})")


def _parse_throttle_seconds(body):
    """Pull the 'more requests available in N seconds' hint from a throttle body."""
    import re
    m = re.search(r"more requests available in (\d+) seconds", body or "")
    return int(m.group(1)) if m else None


def _get_json(url, max_retries=6):
    """GET with gzip, honouring 429 + backoff, exponential retry. Returns dict."""
    delay = 2.0
    for attempt in range(max_retries):
        req = urllib.request.Request(
            url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = ""
            try:
                eb = e.read()
                if e.headers.get("Content-Encoding") == "gzip":
                    eb = gzip.decompress(eb)
                body = eb.decode("utf-8", "replace")
            except Exception:
                pass
            # 429 = throttle violation; SE asks you to wait. 400 = bad request (don't retry).
            if e.code == 400:
                # error_id 502 / throttle_violation = soft, time-based quota limit, NOT a
                # malformed request. Surface it as a typed, resumable signal so callers can
                # persist progress and retry later instead of dying with a stack trace.
                if '"error_id":502' in body or "throttle_violation" in body:
                    raise ThrottleExhausted(_parse_throttle_seconds(body), body[:160])
                raise RuntimeError(f"HTTP 400 from API: {body[:300]}")
            wait = delay * (attempt + 1)
            print(f"    HTTP {e.code}; backing off {wait:.0f}s "
                  f"({body[:120]})", flush=True)
            time.sleep(wait)
        except (urllib.error.URLError, TimeoutError) as e:
            wait = delay * (attempt + 1)
            print(f"    net error {e}; retry in {wait:.0f}s", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"giving up after {max_retries} retries: {url}")


def probe_quota():
    """One default-filter call to read quota_remaining / quota_max / backoff.

    Returns (None, None, None) if the quota is already exhausted, so an offline panel
    rebuild can still proceed instead of crashing on the probe.
    """
    url = (API.format(endpoint="info") + "?site=stackoverflow")
    try:
        d = _get_json(_keyed(url))
    except ThrottleExhausted as ex:
        hrs = (ex.seconds or 0) / 3600.0
        print(f"  [quota] EXHAUSTED — ~{hrs:.1f}h until reset"
              + ("" if API_KEY
                 else "; register a free Stack Apps key for a separate 10,000/day quota"))
        return None, None, None
    qmax = d.get("quota_max")
    qrem = d.get("quota_remaining")
    backoff = d.get("backoff")
    print(f"  [quota] remaining={qrem}/{qmax}"
          + (f"  backoff={backoff}s" if backoff else ""))
    return qrem, qmax, backoff


def fetch_count(site, endpoint, ym, throttle=0.3):
    """One monthly count for (site, endpoint, ym) via filter=total.

    Returns (count:int, backoff:float|None). filter=total payload = {"total": N}.
    """
    fromd, tod = month_window(ym)
    url = (API.format(endpoint=endpoint)
           + f"?site={site}&fromdate={fromd}&todate={tod}"
           + "&filter=total&pagesize=1")
    d = _get_json(_keyed(url))
    # filter=total strips has_more/quota; 'total' is the whole answer for the window.
    cnt = d.get("total")
    backoff = d.get("backoff")  # present only if API decides to throttle
    if cnt is None:
        raise RuntimeError(f"no 'total' in response for {site}/{endpoint}/{ym}: {d}")
    if throttle:
        time.sleep(throttle)
    if backoff:
        print(f"    API backoff {backoff}s requested", flush=True)
        time.sleep(float(backoff) + 0.5)
    return int(cnt), backoff


def cache_path(site, endpoint):
    safe = site.replace(".", "_")
    return os.path.join(DATA, f"so_raw_{safe}_{endpoint}.json")


def load_cache(site, endpoint):
    p = cache_path(site, endpoint)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(site, endpoint, d):
    p = cache_path(site, endpoint)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=0, sort_keys=True)
    os.replace(tmp, p)


def fetch_site_endpoint(site, endpoint, months, throttle, probe_every=40):
    """Fill {ym: count} for a (site, endpoint), resuming from cache."""
    cache = load_cache(site, endpoint)
    todo = [ym for ym in months if ym not in cache]
    if not todo:
        print(f"  [{site}/{endpoint}] all {len(months)} months cached", flush=True)
        return cache
    print(f"  [{site}/{endpoint}] fetching {len(todo)} of {len(months)} months "
          f"(rest cached)", flush=True)
    for i, ym in enumerate(todo):
        try:
            cnt, _ = fetch_count(site, endpoint, ym, throttle=throttle)
        except ThrottleExhausted:
            save_cache(site, endpoint, cache)   # persist partial progress before bailing
            raise
        cache[ym] = cnt
        if i < 3 or i == len(todo) - 1:
            print(f"    {ym}: {cnt:,}", flush=True)
        if (i + 1) % 10 == 0:
            save_cache(site, endpoint, cache)
        if (i + 1) % probe_every == 0:
            _, _, _ = probe_quota()
    save_cache(site, endpoint, cache)
    return cache


def discover_cached_sites():
    """Find every site that has a cached raw file, so rebuilding the combined CSV
    never silently drops sites just because they were not on this run's --sites."""
    found = set()
    for fn in os.listdir(DATA):
        if fn.startswith("so_raw_") and fn.endswith(".json"):
            mid = fn[len("so_raw_"):-len(".json")]
            for ep in ENDPOINTS:
                if mid.endswith("_" + ep):
                    found.add(mid[: -(len(ep) + 1)].replace("_", "."))
    return sorted(found)


def build_panel(sites, endpoints, months):
    """Combine all caches into a tidy long CSV. Returns list-of-rows + writes CSV.

    Always unions in any other cached sites so the panel is cumulative across runs.
    """
    sites = sorted(set(sites) | set(discover_cached_sites()))
    rows = []
    for site in sites:
        treated = int(site in TREATED)
        for endpoint in endpoints:
            cache = load_cache(site, endpoint)
            for ym in months:
                if ym not in cache:
                    continue
                y, m = (int(x) for x in ym.split("-"))
                rows.append({
                    "site": site,
                    "endpoint": endpoint,
                    "ym": ym,
                    "date": f"{ym}-01",
                    "year": y,
                    "month": m,
                    "count": cache[ym],
                    "treated": treated,
                })
    # write CSV with stdlib (no pandas dependency for the fetch step)
    import csv
    out = os.path.join(DATA, "so_monthly_panel.csv")
    cols = ["site", "endpoint", "ym", "date", "year", "month", "count", "treated"]
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in sorted(rows, key=lambda r: (r["site"], r["endpoint"], r["ym"])):
            w.writerow(r)
    return rows, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", default=",".join(DEFAULT_SITES),
                    help="comma-separated site keys")
    ap.add_argument("--endpoints", default=",".join(ENDPOINTS),
                    help="comma-separated: questions,answers")
    ap.add_argument("--start", default="2021-01", help="YYYY-MM inclusive")
    ap.add_argument("--end", default="2024-12", help="YYYY-MM inclusive")
    ap.add_argument("--throttle", type=float, default=0.3,
                    help="seconds to sleep between calls (politeness)")
    ap.add_argument("--probe-quota", action="store_true",
                    help="just print remaining quota and exit")
    ap.add_argument("--key", default=None,
                    help="Stack Apps key (raises quota 300->10,000/day); "
                         "falls back to $STACK_APPS_KEY")
    args = ap.parse_args()

    global API_KEY
    if args.key:
        API_KEY = args.key

    if args.probe_quota:
        probe_quota()
        return

    sites = [s.strip() for s in args.sites.split(",") if s.strip()]
    endpoints = [e.strip() for e in args.endpoints.split(",") if e.strip()]
    months = list(month_iter(args.start, args.end))

    print("=" * 64)
    print("P9 Leg B — Stack Exchange monthly activity fetch")
    print("=" * 64)
    print(f"sites     : {sites}")
    print(f"endpoints : {endpoints}")
    print(f"window    : {args.start} .. {args.end}  ({len(months)} months)")
    print(f"calls     : up to {len(sites)*len(endpoints)*len(months):,} "
          f"(filter=total, 1 call/cell)")
    print(f"api key   : "
          + ("set (quota 10,000/day)" if API_KEY else "NONE (quota 300/day, per-IP)"))
    print()
    q0 = probe_quota()
    print()

    t0 = time.time()
    throttled = False
    for site in sites:
        if throttled:
            break
        for endpoint in endpoints:
            try:
                fetch_site_endpoint(site, endpoint, months, args.throttle)
            except ThrottleExhausted as ex:
                hrs = (ex.seconds or 0) / 3600.0
                print(f"\n[THROTTLED] daily quota exhausted (~{hrs:.1f}h until reset). "
                      f"Cached progress saved; rebuilding panel from cache now. "
                      f"Re-run later or pass --key to fetch the remaining months.")
                throttled = True
                break
    dt_s = time.time() - t0

    rows, out_csv = build_panel(sites, endpoints, months)
    print(f"\n[panel] {len(rows):,} rows -> {out_csv}")

    # ---- validation report ----
    lines = []
    def out(s=""):
        lines.append(s)
        print(s)

    out("=" * 64)
    out("P9 Leg B — fetch validation")
    out("=" * 64)
    out(f"window    : {args.start} .. {args.end}  ({len(months)} months)")
    out(f"sites     : {len(sites)}   endpoints: {endpoints}")
    out(f"rows      : {len(rows):,}   elapsed: {dt_s:,.1f}s")
    qf = probe_quota()
    if q0 and q0[0] is not None and qf and qf[0] is not None:
        out(f"quota used this run : {q0[0]-qf[0]} of {q0[1]}")
    out("")
    # per-site sanity: first / ChatGPT-month / last question counts
    out("-- questions per site (Jan'22 | Nov'22 ChatGPT | last month) --")
    for site in sites:
        c = load_cache(site, "questions")
        def g(ym):
            return f"{c.get(ym):>9,}" if ym in c else "    n/a"
        tag = "TREATED" if site in TREATED else "control"
        out(f"  {site:22} {tag:8} "
            f"2022-01={g('2022-01')}  2022-11={g('2022-11')}  "
            f"{months[-1]}={g(months[-1])}")
    out("")
    # quick treated drop signal (Nov'22 -> 12 months later) for the headline site
    so = load_cache("stackoverflow", "questions")
    if "2022-11" in so:
        base = so["2022-11"]
        for k in ("2023-05", "2023-11", "2024-11"):
            if k in so and base:
                out(f"  stackoverflow questions {k} vs 2022-11: "
                    f"{so[k]:,} ({(so[k]/base-1)*100:+.1f}%)")
    out("")
    out(f"[saved] {out_csv}")
    rpt = os.path.join(DATA, "fetch_summary.txt")
    with open(rpt, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    out(f"[saved] {rpt}")


if __name__ == "__main__":
    main()
