# -*- coding: utf-8 -*-
"""r1_verify_models.py -- 校验一批子代理会话 jsonl 里 assistant 消息的 message.model。
用法:
  D:/python.exe r1_verify_models.py --sessions-json subagent_run/sessions_R2.json      # 批号->jsonl 路径(正对照)
  D:/python.exe r1_verify_models.py --files a.jsonl b.jsonl ...
  D:/python.exe r1_verify_models.py --match-prompt-dir <RATER_DIR> --expect 4         # 在 ~/.claude/projects 下按提示词里的批文件路径找会话
  可加 --expect-model claude-sonnet-5(默认) --expect-sessions N
输出: 每会话 model 计数、合计 dict、同时报告 effort 字段取值；凡出现非期望 model、或会话数不符、或某会话无 assistant 消息 => FAIL(退出码 1)。
"""
import argparse, glob, io, json, os, re, sys
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8")


def scan(path):
    models, efforts, n = Counter(), Counter(), 0
    for l in io.open(path, encoding="utf-8"):
        if not l.strip():
            continue
        try:
            o = json.loads(l)
        except Exception:
            continue
        if o.get("type") == "assistant":
            m = (o.get("message") or {}).get("model")
            models[m if m else "<missing>"] += 1
            efforts[str(o.get("effort"))] += 1
            n += 1
    return models, efforts


def find_by_prompt_dir(d, n_expect):
    """在子代理会话里找首条 user 消息含 <d>\\blind_batch_NN.json 与 labels_batch_NN.json 的会话"""
    root = os.path.expanduser("~/.claude/projects")
    pat = re.compile(re.escape(os.path.basename(d.rstrip("\\/"))) + r"[\\/]+blind_batch_(\d\d)\.json")
    out = {}
    for p in glob.glob(os.path.join(root, "*", "*", "subagents", "agent-*.jsonl")):
        try:
            lines = io.open(p, encoding="utf-8").read().split("\n")
        except Exception:
            continue
        for l in lines[:5]:
            if '"user"' in l and "blind_batch_" in l and "labels_batch_" in l:
                m = pat.search(l.replace("\\\\", "\\"))
                if m:
                    out.setdefault(m.group(1), []).append(p)
                break
    return out


def run(files, expect_model, expect_sessions):
    total, tot_eff, fails = Counter(), Counter(), []
    print("%-48s %s" % ("session", "message.model counts | effort"))
    for key, p in files:
        mo, ef = scan(p)
        total.update(mo); tot_eff.update(ef)
        bad = {k: v for k, v in mo.items() if k != expect_model}
        if not mo:
            fails.append((key, "no assistant messages"))
        if bad:
            fails.append((key, bad))
        print("%-48s %s | %s" % (key, dict(mo), dict(ef)))
    if expect_sessions is not None and len(files) != expect_sessions:
        fails.append(("sessions", "found %d expected %d" % (len(files), expect_sessions)))
    print("=== RESULTS ===")
    print("sessions:", len(files))
    print("model counts:", dict(total))
    print("effort field counts:", dict(tot_eff))
    print("FAIL" if fails else "PASS", fails[:10])
    print("=== END RESULTS ===")
    return 1 if fails else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sessions-json"); ap.add_argument("--files", nargs="*"); ap.add_argument("--match-prompt-dir")
    ap.add_argument("--expect-model", default="claude-sonnet-5"); ap.add_argument("--expect-sessions", type=int)
    a = ap.parse_args()
    files = []
    if a.sessions_json:
        files += sorted(json.load(io.open(a.sessions_json, encoding="utf-8")).items())
    if a.files:
        files += [(os.path.basename(f), f) for f in a.files]
    if a.match_prompt_dir:
        fb = find_by_prompt_dir(a.match_prompt_dir, a.expect_sessions)
        dup = {k: v for k, v in fb.items() if len(v) > 1}
        if dup:
            print("WARN 同一批多个会话(重派/重试):", {k: len(v) for k, v in dup.items()})
        files += [("batch%s:%s" % (k, os.path.basename(p)), p) for k, v in sorted(fb.items()) for p in v]
    if not files:
        sys.exit("no sessions given/found")
    sys.exit(run(files, a.expect_model, a.expect_sessions))
