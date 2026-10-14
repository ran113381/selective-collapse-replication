# -*- coding: utf-8 -*-
"""r1_fetch_bodies.py -- 按抽样清单取标题、标签、正文。

/questions/{ids}?site=stackoverflow&filter=withbody，每批最多 100 个 ID（本设计每月恰好一批）。
记录字段和正文预处理与原脚本 fetch_so_questions.py 完全一致：
  question_id, ym, creation_date, title, tags, score, answer_count, is_answered, body_excerpt = strip_html(body, 1400)
strip_html 取自 r1_common，加载时与原脚本逐行比对。
API 已删除/不可见的题号不会返回，记入日志 missing（不替补，如实上报）。
输出 bodies/bodies_YYYY-MM.json、bodies_log.json。
"""
import argparse, io, json, os, sys
import r1_common as C

HERE = C.HERE
DRAW = os.path.join(HERE, "draw")
BOD = os.path.join(HERE, "bodies")
LOG = os.path.join(HERE, "api_log.jsonl")
os.makedirs(BOD, exist_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", default=None)
    ap.add_argument("--key", default=None)
    a = ap.parse_args()
    C.set_key(a.key)
    orig_sha, nlines = C.check_strip_html_identical()
    me = C.sha12_file(os.path.abspath(__file__))
    log = {"script_sha12": me, "orig_fetch_so_questions_sha12": orig_sha, "months": {}}
    code = 0
    for ym in C.parse_months(a.months):
        dp = os.path.join(DRAW, "draw_%s.json" % ym)
        op = os.path.join(BOD, "bodies_%s.json" % ym)
        if not os.path.exists(dp):
            continue
        if os.path.exists(op):
            print("  %s: bodies exist, skip" % ym)
            continue
        dr = json.load(io.open(dp, encoding="utf-8"))
        want = [q for q, _ in dr["ids"]]
        cd = {q: c for q, c in dr["ids"]}
        got = {}
        try:
            for i in range(0, len(want), 100):
                chunk = want[i:i + 100]
                d = C.api_get("questions/" + ";".join(str(x) for x in chunk),
                              "site=stackoverflow&pagesize=100&filter=withbody", logfile=LOG)
                for it in d.get("items", []):
                    got[it["question_id"]] = it
        except C.ThrottleExhausted:
            print("  !! 配额耗尽，%s 未取" % ym)
            code = 3
            break
        recs, missing = [], [q for q in want if q not in got]
        for q in want:
            it = got.get(q)
            if it is None:
                continue
            recs.append({
                "question_id": it.get("question_id"),
                "ym": ym,
                "creation_date": it.get("creation_date"),
                "title": it.get("title"),
                "tags": it.get("tags"),
                "score": it.get("score"),
                "answer_count": it.get("answer_count"),
                "is_answered": it.get("is_answered"),
                "body_excerpt": C.strip_html(it.get("body", "")),
            })
        mism = [r["question_id"] for r in recs if r["creation_date"] != cd[r["question_id"]]]
        C.write_json(op, recs, indent=1)
        log["months"][ym] = {"n_requested": len(want), "n_returned": len(recs), "missing": missing,
                             "creation_date_mismatch": mism}
        print("  %s: requested=%d returned=%d missing=%d creation_date_mismatch=%d"
              % (ym, len(want), len(recs), len(missing), len(mism)))
    C.write_json(os.path.join(BOD, "bodies_log.json"), log, indent=1)
    print("=== RESULTS ===")
    print("script_sha12 =", me, " orig_fetch_so_questions_sha12 =", orig_sha, " strip_html_lines_identical =", nlines)
    for ym, m in log["months"].items():
        print("bodies %s: requested=%d returned=%d missing=%d cd_mismatch=%d" % (
            ym, m["n_requested"], m["n_returned"], len(m["missing"]), len(m["creation_date_mismatch"])))
    print("=== END RESULTS ===")
    sys.exit(code)


if __name__ == "__main__":
    main()
