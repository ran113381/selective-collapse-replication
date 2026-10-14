# -*- coding: utf-8 -*-
"""prep_full12k.py -- 全量 12,000 题盲评材料准备。不调 API、不派子代理、不联网。
复用 r1_rate_api.py 的 load_old_panel / load_new_panel 与 stage_build 的混合打乱逻辑
(SEED=20261012, 先 old 后 new 拼接, random.Random(SEED+1).shuffle(order), 每批 120)；
唯一差别: 评分者可见 id 改为 5 位 T00001.. (按打乱后顺序编号)，因为 12,000 题 4 位不够。
面板映射只写 rate_private/panel_map_full12k.json。
"""
import difflib, hashlib, io, json, os, random, re, sys
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.dirname(os.path.dirname(HERE))
WD = os.path.dirname(R)
sys.path.insert(0, R)
import r1_rate_api as A

TEMPLATE = os.path.join(WD, "R2_blind", "R2_PROMPT_TEMPLATE.txt")
RATER_DIR = os.path.join(WD, "R3_blind", "set12k")
PANEL_MAP = os.path.join(R, "rate_private", "panel_map_full12k.json")
OLD_B = r"E:\智能体论文\P9b_IPM_20260919\工作文档\R2_blind\R2_blind_batch_NN.json"
OLD_L = r"E:\智能体论文\P9b_IPM_20260919\工作文档\R2_blind\R2_labels_batch_NN.json"
PH_OLD, PH_NEW = "Pxxxx", "Txxxxx"          # 4 位示例 -> 5 位示例（多一个 x，最小改动）
SEED, BS = A.SEED, A.BS
sha12 = lambda b: hashlib.sha256(b).hexdigest()[:12]

BAD = [r"\b(19|20)\d\d\b", r"\b(19|20)\d\d[-/.]\d\d\b", r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b",
       r"creation_date", r"panel", r"first.?100", r"random", r"\bold\b", r"\bnew\b", r"redraw", r"re-draw", r"sampl", r"trial", r"stratif",
       r"随机", r"重抽", r"面板", r"旧", r"新", r"前100", r"r1_", r"rate_", r"\bR1\b", r"ChatGPT", r"full60", r"12k"]
BAD_PATH = [r"r1", r"随机", r"重抽", r"full60", r"full12k", r"rate_", r"private", r"panel", r"draw"]
RUBRIC_PATH = re.search(r"Read the rubric file verbatim first:\r?\n(\S+CLASSIFY_RUBRIC\.md)", open(TEMPLATE, encoding="utf-8").read()).group(1)


def leak_prompt(txt):
    txt = txt.replace(RUBRIC_PATH, "<RUBRIC_PATH>")
    txt = txt.replace(RATER_DIR, "<RATER_DIR>")          # 中性目录路径另行检查
    return [(p, m.group(0)) for p in BAD for m in [re.search(p, txt, re.I)] if m]


def leak_path(p):
    return [(q, m.group(0)) for q in BAD_PATH for m in [re.search(q, p, re.I)] if m]


STRICT_KEYS = ["id", "title", "tags", "body"]


def leak_batch_struct(rows, raw):
    f = []
    if any(list(r.keys()) != STRICT_KEYS for r in rows): f.append("keys")
    if any(not re.fullmatch(r"T\d{5}", r["id"]) for r in rows): f.append("id format")
    for pat in ("creation_date", "ym", "panel", "question_id", "score", "answer_count", "is_answered", "month", "date"):
        if re.search(r'^\s*"%s"\s*:' % pat, raw, re.M): f.append(pat)   # 仅当作为记录键出现；正文里的转义引号不算
    return f


def build():
    months = sorted(f[len("bodies_"):-5] for f in os.listdir(os.path.join(R, "bodies")) if re.fullmatch(r"bodies_\d{4}-\d\d\.json", f))
    assert len(months) == 60, len(months)
    items = A.load_old_panel(months) + A.load_new_panel(months)
    N = len(items)
    assert N == 12000, N
    for panel, r in items:           # 缺正文即停
        for k in ("title", "tags", "body_excerpt", "question_id", "ym"):
            if k not in r or r[k] is None or (k in ("title", "body_excerpt") and not str(r[k]).strip()):
                raise SystemExit("缺字段/缺正文: panel=%s qid=%s ym=%s key=%s" % (panel, r.get("question_id"), r.get("ym"), k))
    order = list(range(N))
    random.Random(SEED + 1).shuffle(order)
    rows_all, tokmap = [], {}
    for pos, idx in enumerate(order):
        panel, r = items[idx]
        tok = "T%05d" % (pos + 1)
        tokmap[tok] = {"panel": panel, "question_id": int(r["question_id"]), "ym": r["ym"], "batch": pos // BS + 1, "pos_in_batch": pos % BS + 1}
        rows_all.append({"id": tok, "title": r["title"], "tags": r["tags"], "body": r["body_excerpt"]})
    batches = [rows_all[i:i + BS] for i in range(0, N, BS)]
    return months, tokmap, batches


def main():
    tb = open(TEMPLATE, "rb").read()
    assert sha12(tb) == "c54ade8b5e17", sha12(tb)
    tt = tb.decode("utf-8")
    assert tt.count(OLD_B) == 1 and tt.count(OLD_L) == 1 and tt.count(PH_OLD) == 1 and tt.count("NN") == 2
    months, pm, batches = build()
    # 确定性: 再建一次必须相同
    _, pm2, batches2 = build()
    deterministic = (pm == pm2 and batches == batches2)
    print("路径检查(中性目录):", leak_path(RATER_DIR), " 提示词目录 full12k 位于 R 下，不进提示词")
    assert not leak_path(RATER_DIR)
    assert all(re.fullmatch(r"blind_batch_\d{3}\.json", f) for f in (os.listdir(RATER_DIR) if os.path.exists(RATER_DIR) else [])), "目标目录有非本脚本产物"
    os.makedirs(RATER_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(PANEL_MAP), exist_ok=True)
    json.dump(pm, io.open(PANEL_MAP, "w", encoding="utf-8"), ensure_ascii=False)
    assert [len(b) for b in batches] == [120] * 100
    fails, manifest, per_batch = [], [], []
    bsha, psha = [], []
    for k, rows in enumerate(batches, 1):
        raw = json.dumps(rows, ensure_ascii=False, indent=1).replace("\n", "\r\n")
        bpath = os.path.join(RATER_DIR, "blind_batch_%03d.json" % k)
        lpath = os.path.join(RATER_DIR, "labels_batch_%03d.json" % k)
        open(bpath, "wb").write(raw.encode("utf-8"))
        new = tt.replace(OLD_B, bpath).replace(OLD_L, lpath).replace(PH_OLD, PH_NEW)
        pp = os.path.join(HERE, "prompt_batch_%03d.txt" % k)
        open(pp, "wb").write(new.encode("utf-8"))
        # 还原比对
        back = new.replace(bpath, OLD_B).replace(lpath, OLD_L).replace(PH_NEW, PH_OLD)
        same = back.encode("utf-8") == tb
        ok_cnt = new.count(bpath) == 1 and new.count(lpath) == 1 and new.count(PH_NEW) == 1
        sm = difflib.SequenceMatcher(None, tt, new, autojunk=False)
        nops = sum(1 for t, *_ in sm.get_opcodes() if t != "equal")
        if not (same and ok_cnt): fails.append(("restore", k, same, ok_cnt))
        for f in leak_batch_struct(rows, raw): fails.append(("batch", k, f))
        for f in leak_prompt(new): fails.append(("prompt", k, f))
        fmt = json.dumps(json.loads(raw), ensure_ascii=False, indent=1).replace("\n", "\r\n").encode("utf-8") == raw.encode("utf-8") and not raw.encode("utf-8").startswith(b"\xef\xbb\xbf")
        if not fmt: fails.append(("format", k))
        bsha.append(sha12(raw.encode("utf-8"))); psha.append(sha12(new.encode("utf-8")))
        manifest.append("blind_batch_%03d.json %s" % (k, bsha[-1])); manifest.append("prompt_batch_%03d.txt %s" % (k, psha[-1]))
        c = Counter(pm[r["id"]]["panel"] for r in rows)
        per_batch.append((k, c["old"], c["new"]))
        print("prompt_batch_%03d: 还原后与模板字节相同=%s; opcode段=%d; 批 %d 题 格式同原批文件=%s; old/new=%d/%d" % (k, same, nops, len(rows), fmt, c["old"], c["new"]))
    # 完整性
    allids = [r["id"] for b in batches for r in b]
    cell = Counter((v["panel"], v["ym"]) for v in pm.values())
    cells_ok = len(cell) == 120 and set(cell.values()) == {100}
    idset_ok = len(allids) == 12000 and len(set(allids)) == 12000 and set(allids) == set(pm) == {"T%05d" % i for i in range(1, 12001)}
    qkeys = Counter((v["panel"], v["question_id"]) for v in pm.values())
    dup_within_panel = sum(1 for v in qkeys.values() if v > 1)
    both = {q for (p, q) in qkeys if p == "old"} & {q for (p, q) in qkeys if p == "new"}
    # 同一题号同在新旧面板
    nold = [x[1] for x in per_batch]
    # 文件全是否有 BOM / 目录文件数
    files = sorted(os.listdir(RATER_DIR))
    # 负样本
    print("--- 负样本 ---")
    ok_neg = True
    p1 = open(os.path.join(HERE, "prompt_batch_001.txt"), encoding="utf-8").read()
    for name, bad in [("日期", p1.replace("Rules:", "Rules (2022-09):")), ("年份", p1 + " 2024"), ("creation_date", p1 + " creation_date"), ("panel", p1 + " panel"),
                      ("first-100", p1 + " first-100"), ("random", p1 + " random"), ("old", p1 + " old"), ("new", p1 + " new"), ("中文随机", p1 + "随机"),
                      ("full60", p1 + " full60")]:
        hit = leak_prompt(bad); print("  提示词塞入[%s] 被拦: %s %s" % (name, bool(hit), hit[:1])); ok_neg &= bool(hit)
    for pth in [r"E:\x\r1_foo\R3_blind\a", r"E:\x\随机重抽\a", r"E:\x\full60\a"]:
        h = leak_path(pth); print("  路径[%s] 被拦: %s" % (pth, bool(h))); ok_neg &= bool(h)
    rows = batches[0]
    r2 = [dict(r) for r in rows]; r2[0]["creation_date"] = "2022-09-03"
    h = leak_batch_struct(r2, json.dumps(r2, indent=1)); print("  批文件塞入 creation_date 被拦:", bool(h), h); ok_neg &= bool(h)
    r3 = [dict(r) for r in rows]; r3[0]["id"] = "T0001"
    h = leak_batch_struct(r3, json.dumps(r3)); print("  批文件塞入 4 位编号被拦:", bool(h), h); ok_neg &= bool(h)
    r4 = [dict(r) for r in rows]; r4[0]["panel"] = "old"
    h = leak_batch_struct(r4, json.dumps(r4, indent=1)); print("  批文件塞入 panel 键被拦:", bool(h), h); ok_neg &= bool(h)
    # 正文自然年份（不改写，仅统计）
    ny = nym = 0
    for b in batches:
        for r in b:
            t = r["title"] + " " + r["body"]
            ny += bool(re.search(r"\b(19|20)\d\d\b", t)); nym += bool(re.search(r"\b(19|20)\d\d[-/.]\d\d\b", t))
    # 目录级清单 sha
    mt = "\n".join(manifest) + "\n"
    open(os.path.join(HERE, "manifest_full12k.txt"), "wb").write(mt.encode("utf-8"))
    bdir_sha = sha12("\n".join(m for m in manifest if m.startswith("blind")).encode("utf-8"))
    pdir_sha = sha12("\n".join(m for m in manifest if m.startswith("prompt")).encode("utf-8"))
    restore_true = sum(1 for f in fails if f[0] == "restore") == 0
    print("=== RESULTS ===")
    print("months", len(months), months[0], months[-1])
    print("N", len(allids), "unique_ids", len(set(allids)), "idset_ok_T00001..T12000", idset_ok)
    print("cells(panel,ym)", len(cell), "all_100", cells_ok)
    print("batches", len(batches), "sizes_all_120", all(len(b) == 120 for b in batches))
    print("old_per_batch min/max/mean", min(nold), max(nold), sum(nold) / len(nold), " (new = 120 - old)")
    print("deterministic_rebuild", deterministic)
    print("same_qid_in_both_panels", len(both), " dup_qid_within_panel", dup_within_panel)
    print("rater_dir_files", len(files), " rater_dir", RATER_DIR)
    print("rater_dir_has_labels_files", any(f.startswith("labels") for f in files))
    print("restore_all_True", restore_true, " (100 batches)")
    print("leak_fails", len(fails), fails[:5])
    print("negative_controls_all_caught", ok_neg)
    print("natural_year_questions(4-digit year)", ny, " natural_year_month", nym, " of 12000")
    print("blind_dir_manifest_sha12", bdir_sha, " prompt_dir_manifest_sha12", pdir_sha, " manifest_file_sha12", sha12(mt.encode("utf-8")))
    print("panel_map_full12k.json sha12", sha12(open(PANEL_MAP, "rb").read()))
    print("batch1 first/last ids", batches[0][0]["id"], batches[0][-1]["id"], " batch100 last", batches[-1][-1]["id"])
    allok = (not fails) and ok_neg and cells_ok and idset_ok and deterministic and restore_true
    print("ALL_OK", allok)
    print("=== END RESULTS ===")
    print("--- 每批 old/new ---")
    for k, o, n in per_batch: print("batch %03d old=%d new=%d" % (k, o, n))
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
