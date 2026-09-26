# -*- coding: utf-8 -*-
"""R1 覆盖度产物：把 §4.6 与 S19 里的窗口宽度、覆盖率算成可复现的 JSON。

为什么要单独有这个脚本。这几个数（前期 6.8 小时、后期 55.4 小时、末月 9.75 天、
新样本 95.1% 落在第 2 天以后）第一版是在命令行里现算的，稿子里写了，但没有任何
产物文件存着它们——i1 的零漂移闸门当场报红，报得对：数是真的，可是没有据。

本脚本从两份原始数据重算全部四个数并落盘，让它们和其它跑数产物一样有出处。
每个数都配一条断言，算出来对不上就中止，不写盘。
"""
import json, os, datetime as dt
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
LEGB = r"E:\智能体论文\_legB_data"
EVENT = "2022-12"


def month_start_ts(ym):
    y, m = int(ym[:4]), int(ym[5:])
    return dt.datetime(y, m, 1, tzinfo=dt.timezone.utc).timestamp()


def main():
    # ---- 主面板（每月最早 100 题） ----
    rows = []
    for fn in ("so_questions_full.json", "so_questions_ext_py.json"):
        rows += json.load(open(os.path.join(LEGB, fn), encoding="utf-8"))
    panel = pd.DataFrame([{"qid": q["question_id"], "ts": q["creation_date"], "ym": q["ym"]}
                          for q in rows]).drop_duplicates("qid")
    panel["h_from_m0"] = panel.apply(lambda r: (r.ts - month_start_ts(r.ym)) / 3600.0, axis=1)
    panel["dom"] = pd.to_datetime(panel.ts, unit="s", utc=True).dt.day
    panel["post"] = panel.ym >= EVENT

    # 两个定义必须分清，混用会写出对不上的句子（初版就栽在这里）：
    #   fill  = 末题 − 首题，该月这一百题「填满用了多久」
    #   reach = 末题 − 月初 00:00，窗口「触到月内多深」
    # 稿件 §4.6/S19 报的是 fill；「触及第几小时」这类说法属于 reach，两者不可互换。
    g = panel.groupby("ym").agg(first=("ts", "min"), last=("ts", "max")).reset_index()
    g["fill_h"] = (g["last"] - g["first"]) / 3600.0
    g["reach_h"] = g.apply(lambda r: (r["last"] - month_start_ts(r.ym)) / 3600.0, axis=1)
    g["post"] = g.ym >= EVENT
    pre_span = g[~g.post].fill_h
    post_span = g[g.post].fill_h
    pre_reach = g[~g.post].reach_h

    # ---- 整月均匀样本 ----
    uni = pd.DataFrame(json.load(open(os.path.join(HERE, "R1_uniform_raw.json"), encoding="utf-8")))
    uni["h_from_m0"] = uni.apply(lambda r: (r.creation_date - month_start_ts(r.ym)) / 3600.0, axis=1)
    uni["dom"] = pd.to_datetime(uni.creation_date, unit="s", utc=True).dt.day
    uni_pre = uni[uni.ym < EVENT]
    panel_pre = panel[~panel.post]

    out = {
        "note": "§4.6 与 S19 的窗口宽度与覆盖度。主面板每月取最早 100 题。"
                "*_span_* 键＝fill＝该月末题减首题（这一百题填满用了多久）；"
                "*_reach_* 键＝reach＝末题减月初 00:00 UTC（窗口触到月内多深）。"
                "两者不可互换：稿件报 fill，「触及第几小时」属 reach。",
        "panel_pre_span_hours_mean": round(float(pre_span.mean()), 1),
        "panel_pre_span_hours_median": round(float(pre_span.median()), 1),
        "panel_pre_span_hours_max": round(float(pre_span.max()), 1),
        "panel_post_span_hours_mean": round(float(post_span.mean()), 1),
        "panel_post_span_hours_median": round(float(post_span.median()), 1),
        "panel_post_span_hours_max": round(float(post_span.max()), 1),
        "panel_post_span_days_max": round(float(post_span.max()) / 24.0, 2),
        "panel_pre_median_h_from_month_start": round(float(panel_pre.h_from_m0.median()), 1),
        "uniform_pre_median_h_from_month_start": round(float(uni_pre.h_from_m0.median()), 1),
        "panel_pre_reach_hours_max": round(float(pre_reach.max()), 1),
        "panel_pre_pct_beyond_day1": round(100.0 * float((panel_pre.h_from_m0 > 24).mean()), 1),
        "uniform_pre_pct_beyond_day1": round(100.0 * float((uni_pre.h_from_m0 > 24).mean()), 1),
        "panel_pre_pct_beyond_day2": round(100.0 * float((panel_pre.h_from_m0 > 48).mean()), 1),
        "uniform_pre_pct_beyond_day2": round(100.0 * float((uni_pre.h_from_m0 > 48).mean()), 1),
        "panel_distinct_day_of_month": int(panel.dom.nunique()),
        "uniform_distinct_day_of_month": int(uni.dom.nunique()),
        "uniform_n_fetched": int(len(uni)),
        "uniform_n_months": int(uni.ym.nunique()),
        "uniform_overlap_with_panel": int(uni.question_id.isin(panel.qid).sum()),
    }

    # 断言：稿子里写的每个数必须由本脚本算出同值，对不上就不写盘
    checks = [
        ("panel_pre_span_hours_mean", 6.8),
        ("panel_post_span_hours_mean", 55.4),
        ("panel_post_span_days_max", 9.75),
        ("uniform_pre_pct_beyond_day1", 95.1),
        ("panel_pre_pct_beyond_day1", 0.0),
        ("panel_pre_span_hours_max", 10.3),
        ("panel_post_span_hours_median", 24.1),
        ("panel_pre_reach_hours_max", 10.4),
        ("uniform_distinct_day_of_month", 31),
        ("panel_distinct_day_of_month", 11),
        ("uniform_n_fetched", 1198),
        ("uniform_overlap_with_panel", 25),
    ]
    bad = [(k, v, out[k]) for k, v in checks if abs(out[k] - v) > 0.051]
    if bad:
        print("ABORT 算出来与稿件不符，未写盘：")
        for k, want, got in bad:
            print("   %-38s 稿件 %s  重算 %s" % (k, want, got))
        return 1

    json.dump(out, open(os.path.join(HERE, "R1_coverage_result.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("%d 条断言全过，已写 R1_coverage_result.json" % len(checks))
    for k in sorted(out):
        if k != "note":
            print("   %-38s %s" % (k, out[k]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
