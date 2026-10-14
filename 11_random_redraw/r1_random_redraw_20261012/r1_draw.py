# -*- coding: utf-8 -*-
"""r1_draw.py -- 从总体清单（population/pop_YYYY-MM.json）每月无放回均匀随机抽 100 题。

固定种子 20261012；每月独立播种 random.Random("20261012-YYYY-MM")，所以某个月的样本不依赖
同批还抽了哪些月（先跑两个月、后跑全量，这两个月的样本不变）。总体先按 (creation_date, question_id) 排序再抽，
排序键与 API 返回顺序无关。月总体不足 100 题则全取并在日志里标出。
输出：draw/draw_YYYY-MM.json、draw_all.csv、draw_log.json（总体规模、种子、脚本 sha、总体文件 sha）。
"""
import argparse, csv, io, json, os, random, sys
import r1_common as C

HERE = C.HERE
POP = os.path.join(HERE, "population")
DRAW = os.path.join(HERE, "draw")
os.makedirs(DRAW, exist_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", default=None)
    ap.add_argument("--seed", type=int, default=C.SEED)
    ap.add_argument("--n", type=int, default=C.N_PER_MONTH)
    a = ap.parse_args()
    me = C.sha12_file(os.path.abspath(__file__))
    common_sha = C.sha12_file(os.path.join(HERE, "r1_common.py"))
    log = {"seed": a.seed, "n_per_month": a.n, "script": "r1_draw.py", "script_sha12": me,
           "r1_common_sha12": common_sha, "months": {}}
    rows = []
    for ym in C.parse_months(a.months):
        pp = os.path.join(POP, "pop_%s.json" % ym)
        if not os.path.exists(pp):
            print("  %s: 无总体清单，跳过" % ym)
            continue
        pop = json.load(io.open(pp, encoding="utf-8"))
        ids = sorted((tuple(x) for x in pop["ids"]), key=lambda x: (x[1], x[0]))
        assert len({q for q, _ in ids}) == len(ids), "总体清单有重复题号 " + ym
        rng = random.Random("%d-%s" % (a.seed, ym))
        k = min(a.n, len(ids))
        pick = rng.sample(ids, k)
        pick.sort(key=lambda x: (x[1], x[0]))
        C.write_json(os.path.join(DRAW, "draw_%s.json" % ym),
                     {"ym": ym, "seed": a.seed, "rng": "random.Random('%d-%s').sample" % (a.seed, ym),
                      "population_n": len(ids), "population_file_sha12": C.sha12_file(pp),
                      "n_drawn": k, "ids": [[q, c] for q, c in pick]})
        log["months"][ym] = {"population_n": len(ids), "n_total_api": pop["n_total_api"],
                             "n_drawn": k, "short_of_100": k < a.n, "population_file_sha12": C.sha12_file(pp)}
        rows += [(ym, q, c) for q, c in pick]
        print("  %s: N=%d drawn=%d" % (ym, len(ids), k))
    # 汇总 CSV：只含本次涉及月份；若 draw/ 里已有其他月份的单月文件，一并汇总
    allrows = []
    for fn in sorted(os.listdir(DRAW)):
        if fn.startswith("draw_") and fn.endswith(".json") and fn != "draw_log.json":
            d = json.load(io.open(os.path.join(DRAW, fn), encoding="utf-8"))
            allrows += [(d["ym"], q, c) for q, c in d["ids"]]
    with io.open(os.path.join(HERE, "draw_all.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ym", "question_id", "creation_date"])
        w.writerows(allrows)
    log["draw_all_rows"] = len(allrows)
    log["draw_all_sha12"] = C.sha12_file(os.path.join(HERE, "draw_all.csv"))
    C.write_json(os.path.join(DRAW, "draw_log.json"), log, indent=1)
    print("=== RESULTS ===")
    print("seed =", a.seed, " script_sha12 =", me, " r1_common_sha12 =", common_sha)
    for ym, m in log["months"].items():
        print("draw %s: population_n=%d n_drawn=%d pop_file_sha12=%s" % (ym, m["population_n"], m["n_drawn"], m["population_file_sha12"]))
    print("draw_all.csv rows =", len(allrows), " sha12 =", log["draw_all_sha12"])
    print("=== END RESULTS ===")


if __name__ == "__main__":
    main()
