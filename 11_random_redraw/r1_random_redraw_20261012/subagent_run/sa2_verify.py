# -*- coding: utf-8 -*-
"""sa2_verify.py -- 第二轮(xhigh)闸门: 找到 L 目录对应的全部子代理会话(应 8 个), 按首条时间戳分第一轮/第二轮(各 4),
列出第二轮每会话路径、首末时间戳、message.model 计数、effort 计数。
PASS 当且仅当: 会话共 8 个、第二轮恰 4 个(每批各 1)、第二轮 message.model 全为 --expect-model、effort 全为 --expect-effort。
用法: D:/python.exe sa2_verify.py [--expect-effort xhigh] [--expect-model claude-sonnet-5]
负对照: --expect-effort high (对第二轮必须 FAIL, 退出码 1)
"""
import argparse, io, json, os, sys
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__)); R1 = os.path.dirname(HERE); WD = os.path.dirname(R1)
sys.path.insert(0, R1)
sys.stdout.reconfigure(encoding="utf-8")
import r1_verify_models as V

LAB = os.path.join(WD, "R3_blind", "sa400")


def info(p):
    mo, ef = Counter(), Counter()
    ts_all, first_user = [], None
    for l in io.open(p, encoding="utf-8"):
        if not l.strip():
            continue
        try:
            o = json.loads(l)
        except Exception:
            continue
        ts = o.get("timestamp")
        if ts:
            ts_all.append(ts)
        if o.get("type") == "user" and first_user is None and ts:
            first_user = ts
        if o.get("type") == "assistant":
            mo[(o.get("message") or {}).get("model") or "<missing>"] += 1
            ef[str(o.get("effort"))] += 1
    return {"first": min(ts_all) if ts_all else None, "last": max(ts_all) if ts_all else None,
            "first_user": first_user, "models": mo, "efforts": ef}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--expect-effort", default="xhigh"); ap.add_argument("--expect-model", default="claude-sonnet-5")
    a = ap.parse_args()
    fb = V.find_by_prompt_dir(LAB, 8)
    sess = []
    for k, ps in sorted(fb.items()):
        for p in ps:
            i = info(p); i["batch"] = k; i["path"] = p; sess.append(i)
    sess.sort(key=lambda i: i["first"] or "")
    fails = []
    print("all matched sessions: %d (sorted by first timestamp)" % len(sess))
    for i in sess:
        print("  batch%s %s first=%s last=%s" % (i["batch"], os.path.basename(i["path"]), i["first"], i["last"]))
    if len(sess) != 8:
        fails.append("matched %d sessions, expected 8" % len(sess))
    r1, r2 = sess[:4], sess[4:]
    if r1 and r2:
        print("round1 latest first-ts: %s ; round2 earliest first-ts: %s" % (max(i["first"] for i in r1), min(i["first"] for i in r2)))
        if max(i["last"] for i in r1) >= min(i["first"] for i in r2):
            fails.append("round1/round2 time ranges overlap")
    if sorted(i["batch"] for i in r2) != ["01", "02", "03", "04"]:
        fails.append("round2 batches %s" % [i["batch"] for i in r2])
    print("--- ROUND 2 sessions")
    tm, te = Counter(), Counter()
    for i in r2:
        print("  batch%s\n    path=%s\n    first=%s last=%s\n    message.model=%s effort=%s" % (
            i["batch"], i["path"], i["first"], i["last"], dict(i["models"]), dict(i["efforts"])))
        tm.update(i["models"]); te.update(i["efforts"])
        if not i["models"]:
            fails.append("batch%s no assistant msgs" % i["batch"])
    bad_m = {k: v for k, v in tm.items() if k != a.expect_model}
    bad_e = {k: v for k, v in te.items() if k != a.expect_effort}
    if bad_m: fails.append("model not %s: %s" % (a.expect_model, bad_m))
    if bad_e: fails.append("effort not %s: %s" % (a.expect_effort, bad_e))
    print("--- ROUND 1 (reference only)")
    for i in r1:
        print("  batch%s %s model=%s effort=%s" % (i["batch"], os.path.basename(i["path"]), dict(i["models"]), dict(i["efforts"])))
    print("=== RESULTS ===")
    print("expect model=%s effort=%s" % (a.expect_model, a.expect_effort))
    print("matched sessions:", len(sess), "| round2 sessions:", len(r2))
    print("round2 first ts:", min((i["first"] for i in r2), default=None), "last ts:", max((i["last"] for i in r2), default=None))
    print("round2 model counts:", dict(tm))
    print("round2 effort counts:", dict(te))
    print("GATE", "FAIL" if fails else "PASS", fails)
    print("=== END RESULTS ===")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
