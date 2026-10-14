# -*- coding: utf-8 -*-
"""wave_verify.py -- 全量 12k 盲评：按波核子代理会话的 message.model / effort，并校验 labels 文件。
用法: D:/python.exe wave_verify.py --batches 1-25 [--expect-model claude-sonnet-5] [--expect-effort xhigh]
会话识别: ~/.claude/projects/*/*/subagents/agent-*.jsonl，首条 user 消息含 set12k\\blind_batch_NNN.json 与 labels_batch_NNN.json。
判定: 每个批恰 1 个会话；全部 assistant 行 model==期望、effort==期望；labels 题数=批文件题数、id 各一次、score 0-4 整数、label 与 score 一致。任一不符 FAIL，退出码 1。"""
import argparse, glob, io, json, os, re, sys
from collections import Counter

RATER = r"E:\智能体论文\P9b_IPM_20260919\工作文档\R3_blind\set12k"
PAT = re.compile(r"set12k[\\/]+blind_batch_(\d{3})\.json")


def sessions():
    out = {}
    for p in glob.glob(os.path.join(os.path.expanduser("~/.claude/projects"), "*", "*", "subagents", "agent-*.jsonl")):
        try:
            lines = io.open(p, encoding="utf-8").read().split("\n")
        except Exception:
            continue
        for l in lines[:5]:
            if '"user"' in l and "blind_batch_" in l and "labels_batch_" in l:
                m = PAT.search(l.replace("\\\\", "\\"))
                if m:
                    out.setdefault(int(m.group(1)), []).append(p)
                break
    return out


def scan(p):
    mod, eff = Counter(), Counter()
    for l in io.open(p, encoding="utf-8"):
        try:
            o = json.loads(l)
        except Exception:
            continue
        if o.get("type") == "assistant":
            mod[str((o.get("message") or {}).get("model"))] += 1
            eff[str(o.get("effort"))] += 1
    return mod, eff


def check_labels(n):
    bp = os.path.join(RATER, "blind_batch_%03d.json" % n)
    lp = os.path.join(RATER, "labels_batch_%03d.json" % n)
    if not os.path.exists(lp):
        return ["missing labels file"]
    ids = [r["id"] for r in json.load(io.open(bp, encoding="utf-8-sig"))]
    rows = json.load(io.open(lp, encoding="utf-8-sig"))
    probs = []
    c = Counter(r.get("id") for r in rows)
    if len(rows) != len(ids): probs.append("count %d != %d" % (len(rows), len(ids)))
    if set(c) != set(ids): probs.append("id set mismatch")
    if any(v != 1 for v in c.values()): probs.append("duplicate ids")
    for r in rows:
        s = r.get("score")
        if not isinstance(s, int) or isinstance(s, bool) or not 0 <= s <= 4:
            probs.append("bad score %s" % r.get("id")); continue
        if r.get("label") != ("GEN" if s >= 3 else "VER"):
            probs.append("label mismatch %s" % r.get("id"))
    return probs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batches", required=True)
    ap.add_argument("--expect-model", default="claude-sonnet-5")
    ap.add_argument("--expect-effort", default="xhigh")
    a = ap.parse_args()
    lo, hi = [int(x) for x in a.batches.split("-")]
    want = list(range(lo, hi + 1))
    ss = sessions()
    fails, tm, te = [], Counter(), Counter()
    for n in want:
        ps = ss.get(n, [])
        if len(ps) != 1:
            fails.append((n, "sessions=%d" % len(ps)))
        for p in ps:
            m, e = scan(p)
            tm.update(m); te.update(e)
            print("%03d %s model=%s effort=%s" % (n, os.path.basename(p), dict(m), dict(e)))
            if set(m) != {a.expect_model}: fails.append((n, "model %s" % dict(m)))
            if set(e) != {a.expect_effort}: fails.append((n, "effort %s" % dict(e)))
        for pr in check_labels(n):
            fails.append((n, pr))
    print("=== RESULTS ===")
    print("batches %03d-%03d n=%d expect model=%s effort=%s" % (lo, hi, len(want), a.expect_model, a.expect_effort))
    print("total model counts", dict(tm))
    print("total effort counts", dict(te))
    print("GATE", "PASS" if not fails else "FAIL", fails)
    print("=== END RESULTS ===")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
