# -*- coding: utf-8 -*-
"""r1_enumerate.py -- 按月枚举 stackoverflow 上 tagged=python 的全部问题 (question_id, creation_date)。

总体定义（与原面板一致）：site=stackoverflow，tagged=python，含已关闭题（/questions 不排除），
月份 = [当月1日 00:00 UTC, 次月1日 00:00 UTC)。sort=creation asc，pagesize=100，翻页。
分页：无 key 时 API 不允许 page>25 之外的深翻页的可靠性未知，所以每 25 页以最后一题的 creation_date
作为新的 fromdate 重新从 page 1 起翻（fromdate 含边界，重叠的题按 id 去重）。
断点续跑：每页后落盘 _state/state_YYYY-MM.json；quota_remaining < --min-quota 时存盘并退出码 3。
输出：population/pop_YYYY-MM.json（总体清单，可审计）与 api_log.jsonl（每次调用的配额读数）。

用法：D:/python.exe r1_enumerate.py --months 2022-09,2024-06 [--key XXX | env STACK_APPS_KEY]
"""
import argparse, csv, datetime as dt, io, json, os, sys, time
import r1_common as C

HERE = C.HERE
POP = os.path.join(HERE, "population")
STATE = os.path.join(HERE, "_state")
LOG = os.path.join(HERE, "api_log.jsonl")
for d in (POP, STATE):
    os.makedirs(d, exist_ok=True)

PAGE_CAP = 25


def platform_total(ym):
    for r in csv.DictReader(io.open(C.PLATFORM_TOTALS, encoding="utf-8")):
        if r["tag"] == "python" and r["ym"] == ym:
            return int(r["total"])
    return None


def enumerate_month(ym, min_quota, sleep):
    f0, t_excl = C.month_window(ym)
    t_incl = t_excl - 1            # 次月 1 日 00:00:00 的题不重复计入（原脚本 todate=t_excl 为含边界）
    sp = os.path.join(STATE, "state_%s.json" % ym)
    if os.path.exists(sp):
        st = json.load(io.open(sp, encoding="utf-8"))
    else:
        st = {"ym": ym, "ids": {}, "next_from": f0, "next_page": 1, "done": False, "calls": 0,
              "n_total_api": None, "started_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    if st["done"]:
        return st
    if st["n_total_api"] is None:
        d = C.api_get("questions", "site=stackoverflow&tagged=python&fromdate=%d&todate=%d&filter=total&pagesize=1"
                      % (f0, t_incl), sleep=sleep, logfile=LOG)
        st["n_total_api"] = d["total"]
        st["calls"] += 1
        C.write_json(sp, st)
        print("  %s: API total = %d (platform_monthly_totals.csv: %s)" % (ym, st["n_total_api"], platform_total(ym)), flush=True)
    while True:
        params = ("site=stackoverflow&tagged=python&fromdate=%d&todate=%d&sort=creation&order=asc"
                  "&pagesize=100&page=%d&filter=%s" % (st["next_from"], t_incl, st["next_page"], C.ENUM_FILTER))
        d = C.api_get("questions", params, sleep=sleep, logfile=LOG)
        st["calls"] += 1
        if "items" not in d:
            raise RuntimeError("响应无 items 字段（filter 有误？）: %s" % sorted(d.keys()))
        items = d["items"]
        for it in items:
            st["ids"][str(it["question_id"])] = it["creation_date"]
        if not d.get("has_more") or not items:
            st["done"] = True
        elif st["next_page"] >= PAGE_CAP:
            st["next_from"] = items[-1]["creation_date"]
            st["next_page"] = 1
        else:
            st["next_page"] += 1
        C.write_json(sp, st)
        q = d.get("quota_remaining")
        if st["calls"] % 20 == 0 or st["done"]:
            print("  %s: calls=%d ids=%d/%s quota_remaining=%s" % (ym, st["calls"], len(st["ids"]), st["n_total_api"], q), flush=True)
        if st["done"]:
            return st
        if q is not None and q < min_quota:
            print("  !! quota_remaining=%s < %d, 存盘退出（%s 未完成，下次从断点续）" % (q, min_quota, ym))
            raise C.ThrottleExhausted(None)


def finalize(ym, st):
    f0, t_excl = C.month_window(ym)
    rows = sorted(((int(k), v) for k, v in st["ids"].items()), key=lambda x: (x[1], x[0]))
    bad = [r for r in rows if not (f0 <= r[1] < t_excl)]
    out = {"ym": ym, "tag": "python", "site": "stackoverflow",
           "window_utc": [f0, t_excl], "n_enumerated": len(rows), "n_total_api": st["n_total_api"],
           "n_platform_monthly_totals_csv": platform_total(ym),
           "n_out_of_window": len(bad), "api_calls": st["calls"],
           "retrieved_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "ids": [[a, b] for a, b in rows]}
    C.write_json(os.path.join(POP, "pop_%s.json" % ym), out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", default=None, help="逗号分隔或 a..b 区间；缺省为 2021-06..2026-05 全部 60 个月")
    ap.add_argument("--key", default=None)
    ap.add_argument("--min-quota", type=int, default=8)
    ap.add_argument("--sleep", type=float, default=0.2)
    a = ap.parse_args()
    C.set_key(a.key)
    months = C.parse_months(a.months)
    print("api key: %s; months=%d: %s" % ("set" if C.API_KEY else "NONE (300/day per IP)", len(months), months[:6]))
    res = []
    code = 0
    for ym in months:
        if os.path.exists(os.path.join(POP, "pop_%s.json" % ym)):
            print("  %s: already enumerated, skip" % ym)
            continue
        try:
            st = enumerate_month(ym, a.min_quota, a.sleep)
        except C.ThrottleExhausted:
            code = 3
            break
        out = finalize(ym, st)
        res.append(out)
        print("  %s: DONE enumerated=%d api_total=%s csv_total=%s out_of_window=%d calls=%d"
              % (ym, out["n_enumerated"], out["n_total_api"], out["n_platform_monthly_totals_csv"],
                 out["n_out_of_window"], out["api_calls"]), flush=True)
    print("=== RESULTS ===")
    print("script_sha12 =", C.sha12_file(os.path.abspath(__file__)))
    for o in res:
        print("pop %s: n_enumerated=%d n_total_api=%s n_csv=%s out_of_window=%d api_calls=%d"
              % (o["ym"], o["n_enumerated"], o["n_total_api"], o["n_platform_monthly_totals_csv"],
                 o["n_out_of_window"], o["api_calls"]))
    print("exit_status =", "THROTTLED_OR_LOW_QUOTA(3)" if code else "OK")
    print("=== END RESULTS ===")
    sys.exit(code)


if __name__ == "__main__":
    main()
