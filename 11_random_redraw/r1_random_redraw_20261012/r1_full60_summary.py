# -*- coding: utf-8 -*-
"""r1_full60_summary.py -- 60 个月完整性汇总（只读本地产物，零 API 调用）。
每月一行：枚举总数、API total、抽中数、取到正文数、缺失数、cd 不符数、原面板最早100与当前总体最早100重合数。"""
import io, json, os, csv
import r1_common as C

H = C.HERE
orig = C.load_original_panel()
rows = []
for ym in C.parse_months(None):
    pp = os.path.join(H, "population", "pop_%s.json" % ym)
    if not os.path.exists(pp):
        rows.append(dict(ym=ym, status="NO_POP")); continue
    pop = json.load(io.open(pp, encoding="utf-8"))
    pids = [(q, c) for q, c in pop["ids"]]
    dp = os.path.join(H, "draw", "draw_%s.json" % ym)
    bp = os.path.join(H, "bodies", "bodies_%s.json" % ym)
    dr = json.load(io.open(dp, encoding="utf-8")) if os.path.exists(dp) else None
    bd = json.load(io.open(bp, encoding="utf-8")) if os.path.exists(bp) else None
    ofirst = {r["question_id"] for r in orig[ym]}
    first_now = {q for q, _ in pids[:100]}
    drawn = len(dr["ids"]) if dr else None
    got = len(bd) if bd is not None else None
    cd = {q: c for q, c in dr["ids"]} if dr else {}
    mism = sum(1 for r in (bd or []) if r["creation_date"] != cd.get(r["question_id"]))
    rows.append(dict(ym=ym, status="ok", n_enum=len(pids), n_api_total=pop["n_total_api"],
                     n_csv=pop["n_platform_monthly_totals_csv"], out_of_window=pop["n_out_of_window"],
                     api_calls=pop["api_calls"], drawn=drawn, bodies=got,
                     missing=(drawn - got) if (drawn is not None and got is not None) else None,
                     cd_mismatch=mism, orig_n=len(ofirst), orig_vs_first100_now=len(ofirst & first_now)))
cols = ["ym", "status", "n_enum", "n_api_total", "n_csv", "out_of_window", "api_calls", "drawn", "bodies", "missing",
        "cd_mismatch", "orig_n", "orig_vs_first100_now"]
with io.open(os.path.join(H, "full60_summary.csv"), "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
ok = [r for r in rows if r["status"] == "ok"]
print("=== RESULTS ===")
print("months_with_pop =", len(ok), "of", len(rows))
for r in rows:
    print("row", " ".join("%s=%s" % (k, r.get(k)) for k in cols))
print("sum_enum =", sum(r["n_enum"] for r in ok), " sum_api_total =", sum(r["n_api_total"] for r in ok),
      " sum_csv =", sum(r["n_csv"] or 0 for r in ok))
print("enum_ne_api_months =", [r["ym"] for r in ok if r["n_enum"] != r["n_api_total"]])
print("out_of_window_total =", sum(r["out_of_window"] for r in ok))
print("sum_api_calls_enum =", sum(r["api_calls"] for r in ok))
print("sum_drawn =", sum(r["drawn"] or 0 for r in ok), " sum_bodies =", sum(r["bodies"] or 0 for r in ok),
      " sum_missing =", sum(r["missing"] or 0 for r in ok), " sum_cd_mismatch =", sum(r["cd_mismatch"] for r in ok))
print("months_missing_gt0 =", [(r["ym"], r["missing"]) for r in ok if r["missing"]])
print("months_orig_vs_first100_lt100 =", [(r["ym"], r["orig_vs_first100_now"]) for r in ok if r["orig_vs_first100_now"] < 100])
print("sum_orig_vs_first100_now =", sum(r["orig_vs_first100_now"] for r in ok), "of", sum(r["orig_n"] for r in ok))
print("=== END RESULTS ===")
