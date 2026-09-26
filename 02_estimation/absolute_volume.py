# -*- coding: utf-8 -*-
"""Phase 1.2 — platform monthly totals + N_t x p-hat_s,t absolute-volume
reconstruction.

The manuscript's dose-response is a COMPOSITION estimand by construction: the
classified panel is a fixed random sample of 100 questions/month/language, so
the four substitutability bins sum to a constant and gamma is identified from
cross-bin shares, not raw counts, so the
abstract/results should not be read as literal absolute-volume claims without
this reconstruction. This script does the reconstruction directly:

  1. Fetch the REAL total monthly question volume per language (not the
     100-question subsample) from the public SE API, filter=total (a
     built-in SE filter that returns only {"total": N} per call -- 1 call
     per (language, month), 180 calls for 60 months x 3 languages).
  2. Merge with the classified-panel bin shares p_hat_{s,t} = bin_count/100
     (already a proportion since the monthly sample size is fixed at 100).
  3. N_hat_{s,t} = N_t * p_hat_{s,t} recovers an ESTIMATED absolute count per
     substitutability bin per month.
  4. Report: (a) platform-level pre/post totals (sanity check against the
     manuscript's "~80% smaller by 2024" and the del Rio-Chanona benchmark);
     (b) absolute pre/post level and % change PER BIN (s1..s4), which is the
     number the "commons is not dying, it is being distilled" claim actually
     needs and which the manuscript does not currently report.

RESUMABLE (like fetch_first_answers.py / closure_check.py): appends to
platform_monthly_totals.csv, skips (tag, ym) pairs already fetched.

Run (needs network):  python absolute_volume.py
"""
import os, sys, csv, json, time
import urllib.request, urllib.parse
from datetime import datetime, timezone
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

DATA = r"E:\智能体论文\_legB_data"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_CSV = os.path.join(HERE, "platform_monthly_totals.csv")
OUT_JSON = os.path.join(HERE, "absolute_volume.json")

API = "https://api.stackexchange.com/2.3/questions"
KEY = os.environ.get("STACK_API_KEY")
SLEEP = 0.15
EVENT_YM = "2022-12"

PANELS = {
    "python": "within_so_llm_panel.csv",
    "javascript": "within_so_llm_panel_js.csv",
    "java": "within_so_llm_panel_java.csv",
}
TAG_MAP = {"python": "python", "javascript": "javascript", "java": "java"}

MONTHS = [f"{y:04d}-{m:02d}" for y in (2021, 2022, 2023, 2024, 2025, 2026) for m in range(1, 13)]
MONTHS = [ym for ym in MONTHS if "2021-06" <= ym <= "2026-05"]
assert len(MONTHS) == 60, len(MONTHS)


def month_bounds(ym):
    y, m = map(int, ym.split("-"))
    start = datetime(y, m, 1, tzinfo=timezone.utc)
    end = datetime(y + 1, 1, 1, tzinfo=timezone.utc) if m == 12 else datetime(y, m + 1, 1, tzinfo=timezone.utc)
    return int(start.timestamp()), int(end.timestamp())


def ym_int(y):
    a, b = y.split("-")
    return int(a) * 12 + int(b) - 1


EVENT = ym_int(EVENT_YM)


def already_done():
    done = set()
    if os.path.exists(OUT_CSV):
        for r in csv.DictReader(open(OUT_CSV, encoding="utf-8")):
            done.add((r["tag"], r["ym"]))
    return done


def fetch_total(tag, ym):
    fromdate, todate = month_bounds(ym)
    params = {"site": "stackoverflow", "tagged": tag, "fromdate": fromdate,
              "todate": todate, "filter": "total"}
    if KEY:
        params["key"] = KEY
    url = API + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.load(resp)
    return data.get("total"), data.get("quota_remaining")


def fetch_all():
    done = already_done()
    todo = [(tag, ym) for tag in TAG_MAP for ym in MONTHS if (tag, ym) not in done]
    print(f"targets={len(TAG_MAP)*len(MONTHS)}  already done={len(done)}  to fetch={len(todo)}"
          f"  (key={'yes' if KEY else 'no — 300/day quota'})")
    new = not os.path.exists(OUT_CSV)
    f = open(OUT_CSV, "a", newline="", encoding="utf-8")
    w = csv.writer(f)
    if new:
        w.writerow(["tag", "ym", "total"])
    stop = False
    for i, (tag, ym) in enumerate(todo):
        if stop:
            break
        try:
            total, qr = fetch_total(tag, ym)
        except Exception as e:
            print(f"[error] {tag} {ym}: {e}; sleeping 5s and retrying once")
            time.sleep(5)
            try:
                total, qr = fetch_total(tag, ym)
            except Exception as e2:
                print(f"[error] retry failed for {tag} {ym}: {e2}; stopping, run again to resume")
                break
        w.writerow([tag, ym, total])
        f.flush()
        if (i + 1) % 20 == 0 or i == len(todo) - 1:
            print(f"  {i+1}/{len(todo)} written (quota_remaining={qr})", flush=True)
        if qr is not None and qr <= 5:
            print(f"[quota] near exhaustion (remaining {qr}), stopping politely.")
            stop = True
            break
        time.sleep(SLEEP)
    f.close()
    print("fetch done (resumable — re-run to continue if quota/backoff stopped it).")


def analyze():
    totals = pd.read_csv(OUT_CSV)
    results = {}

    print("\n=== (a) platform-level totals: pre/post average monthly volume, by language ===")
    for tag in TAG_MAP:
        t = totals[totals.tag == tag].copy()
        t["t"] = t["ym"].map(ym_int)
        t["post"] = (t.t >= EVENT).astype(int)
        pre_mean = t[t.post == 0]["total"].mean()
        post_mean = t[t.post == 1]["total"].mean()
        # also last-12-months to compare with the "~80% smaller by 2024" claim's spirit
        last12 = t.sort_values("t").tail(12)["total"].mean()
        pct = (post_mean / pre_mean - 1) if pre_mean else np.nan
        pct_last12 = (last12 / pre_mean - 1) if pre_mean else np.nan
        print(f"  {tag:12s} pre={pre_mean:8.1f}/mo  post_avg={post_mean:8.1f}/mo ({pct:+.1%})"
              f"  last12avg={last12:8.1f}/mo ({pct_last12:+.1%})")
        results[f"platform_total_{tag}"] = {"pre_mean": float(pre_mean), "post_mean": float(post_mean),
                                             "pct_change": float(pct), "last12_mean": float(last12),
                                             "pct_change_last12": float(pct_last12)}

    print("\n=== (b) absolute volume by substitutability bin: N_t x p_hat_s,t ===")
    for tag, panel_fn in PANELS.items():
        panel = pd.read_csv(os.path.join(DATA, panel_fn))
        t = totals[totals.tag == tag][["ym", "total"]]
        m = panel.merge(t, on="ym", how="inner")
        assert len(m) == 60, f"{tag}: expected 60 months, got {len(m)}"
        m["tt"] = m["ym"].map(ym_int)
        m["post"] = (m.tt >= EVENT).astype(int)
        print(f"\n  -- {tag} --")
        bin_res = {}
        for s in (1, 2, 3, 4):
            m[f"phat_s{s}"] = m[f"s{s}"] / m["n"]          # n is 100 every month by design
            m[f"Nhat_s{s}"] = m["total"] * m[f"phat_s{s}"]
            pre = m[m.post == 0][f"Nhat_s{s}"].mean()
            post = m[m.post == 1][f"Nhat_s{s}"].mean()
            pct = (post / pre - 1) if pre else np.nan
            print(f"    s{s}: pre_abs={pre:8.1f}/mo  post_abs={post:8.1f}/mo  Δ={pct:+.1%}")
            bin_res[f"s{s}"] = {"pre_abs": float(pre), "post_abs": float(post), "pct_change": float(pct)}
        # sanity: sum of bin absolutes should ~= platform total x (sampled GEN+VER share, i.e. ~1 since s1..s4 covers ~all non-s0)
        m["Nhat_sum"] = sum(m[f"Nhat_s{s}"] for s in (1, 2, 3, 4))
        ratio = (m["Nhat_sum"] / m["total"]).mean()
        print(f"    [sanity] mean (sum of Nhat_s1..s4) / platform_total = {ratio:.3f} (expect ~ (100-s0)/100)")
        results[f"absolute_by_bin_{tag}"] = bin_res
        results[f"absolute_sanity_ratio_{tag}"] = float(ratio)
        # save the monthly reconstructed series for later figure use
        m[["ym", "total"] + [f"Nhat_s{s}" for s in (1, 2, 3, 4)]].to_csv(
            os.path.join(HERE, f"absolute_volume_series_{tag}.csv"), index=False)

    json.dump(results, open(OUT_JSON, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"\nwritten: {OUT_JSON}")
    print("per-language monthly reconstructed series: absolute_volume_series_{python,javascript,java}.csv")


if __name__ == "__main__":
    if "--analyze-only" not in sys.argv:
        fetch_all()
    if os.path.exists(OUT_CSV):
        analyze()
    else:
        print("no platform_monthly_totals.csv yet; fetch must have failed immediately.")
