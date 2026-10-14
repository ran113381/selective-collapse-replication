# -*- coding: utf-8 -*-
"""derive_labels_by_question.py -- 把盲评标签(按评分者编号T)与面板映射(留在原目录、不随包发布)连接，
派生一张按题号排列的标签表。表中不含评分者编号(T...)、批号、批内位置；行按 (panel, ym, question_id) 排序。
本脚本随包发布仅为说明派生做法；包内没有映射文件，故在包内不能运行。
用法:
  python derive_labels_by_question.py full12k <panel_map_full12k.json> <set12k_dir> <out.csv>
  python derive_labels_by_question.py trial400 <panel_map_trial400.json> <round1_labels_dir> <round2_labels_dir> <out.csv>
panel 取值: "panel" = 旧面板(映射中 old), "redraw" = 本轮随机重抽(映射中 new)。
"""
import csv, hashlib, io, json, os, sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
sha12 = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]
NAME = {"old": "panel", "new": "redraw"}


def lab(s): return "GEN" if s >= 3 else "VER"


def load_labels(d, nfiles, pat, bpat=None):
    out = {}; prob = []
    for k in range(1, nfiles + 1):
        lp = os.path.join(d, pat % k)
        arr = json.load(io.open(lp, encoding="utf-8"))
        if bpat:
            bids = [r["id"] for r in json.loads(open(os.path.join(d, bpat % k), "rb").read().decode("utf-8"))]
            if sorted(r["id"] for r in arr) != sorted(bids): prob.append(("id set vs blind batch", k))
        for r in arr:
            s = r.get("score")
            if not (isinstance(s, int) and not isinstance(s, bool) and 0 <= s <= 4): prob.append(("bad score", r["id"], s))
            elif r.get("label") != lab(s): prob.append(("label/score", r["id"], s, r.get("label")))
            if r["id"] in out: prob.append(("duplicate", r["id"]))
            out[r["id"]] = dict(r, _file=k)
    return out, prob


def write(path, header, rows):
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n"); w.writerow(header); w.writerows(rows)


if sys.argv[1] == "full12k":
    pmp, d, out = sys.argv[2:5]
    pm = json.load(io.open(pmp, encoding="utf-8"))
    labels, prob = load_labels(d, 100, "labels_batch_%03d.json", "blind_batch_%03d.json")
    print("map sha12", sha12(pmp), "; entries", len(pm), "; labels", len(labels), "; problems", len(prob), prob[:5])
    assert not prob and set(labels) == set(pm) and len(labels) == 12000
    assert all(pm[i]["batch"] == labels[i]["_file"] for i in pm), "batch mismatch"
    rows = sorted(((NAME[pm[i]["panel"]], ym_, pm[i]["question_id"], labels[i]["score"], labels[i]["label"])
                   for i in pm for ym_ in [pm[i]["ym"]]), key=lambda r: (r[0], r[1], r[2]))
    rows = [(p, q, y, s, l) for p, y, q, s, l in rows]
    keys = Counter((r[0], r[1]) for r in rows)
    cell = Counter((r[0], r[2]) for r in rows)
    write(out, ["panel", "question_id", "ym", "score", "label"], rows)
    print("=== RESULTS ===")
    print("rows", len(rows), "; unique (panel,question_id)", len(keys), "; cells(panel x ym)", len(cell), "sizes", sorted(set(cell.values())))
    print("panel counts", dict(Counter(r[0] for r in rows)))
    print("score counts", dict(sorted(Counter(r[3] for r in rows).items())))
    qs = Counter(r[1] for r in rows); print("question_ids appearing in both panels", sum(1 for v in qs.values() if v == 2))
    print("out sha12", sha12(out))
    print("=== END RESULTS ===")
else:
    pmp, d1, d2, out = sys.argv[2:6]
    pm = json.load(io.open(pmp, encoding="utf-8"))
    l1, p1 = load_labels(d1, 4, "labels_batch_%02d.json"); l2, p2 = load_labels(d2, 4, "labels_batch_%02d.json", "blind_batch_%02d.json")
    print("map sha12", sha12(pmp), "; entries", len(pm), "; round1", len(l1), "round2", len(l2), "; problems", p1[:3], p2[:3])
    assert not p1 and not p2 and set(l1) == set(pm) == set(l2)
    rows = sorted(((NAME[pm[i]["panel"]], pm[i]["ym"], pm[i]["question_id"], l1[i]["score"], l1[i]["label"], l2[i]["score"], l2[i]["label"]) for i in pm),
                  key=lambda r: (r[0], r[1], r[2]))
    rows = [(p, q, y, a, b, c, e) for p, y, q, a, b, c, e in rows]
    write(out, ["panel", "question_id", "ym", "score_round1_high", "label_round1_high", "score_round2_xhigh", "label_round2_xhigh"], rows)
    print("=== RESULTS ===")
    print("rows", len(rows), "; panel counts", dict(Counter(r[0] for r in rows)))
    print("round1 vs round2 exact score agreement", sum(1 for r in rows if r[3] == r[5]), "of", len(rows))
    print("out sha12", sha12(out))
    print("=== END RESULTS ===")
