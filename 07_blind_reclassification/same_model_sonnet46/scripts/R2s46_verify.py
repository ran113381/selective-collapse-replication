"""Sonnet 4.6 同模型盲跑（设计书第 13 条(二)、第 15 条）：逐批核子代理实际模型与标签完整性。只读。

用法: python R2s46_verify.py <会话目录>
  会话目录 = C:\\Users\\<user>\\.claude\\projects\\<project>\\<session-id>（其下有 subagents\\agent-*.jsonl）
输出: 同目录 R2s46_verify_result.json，并打印逐批表。
"""
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = "claude-sonnet-4-6"
OUT_RE = re.compile(r"R2_blind_s46\\R2_labels_batch_(\d{2})\.json")


def first_user_text(rows):
    for r in rows:
        if r.get("type") == "user":
            c = r["message"].get("content")
            if isinstance(c, str):
                return c
            if isinstance(c, list):
                return "".join(x.get("text", "") for x in c if isinstance(x, dict))
    return ""


def is_write_to(item, nn):
    name, inp = item.get("name"), item.get("input") or {}
    tail = f"R2_blind_s46\\R2_labels_batch_{nn}.json"
    if name in ("Write", "Edit"):
        return inp.get("file_path", "").replace("/", "\\").endswith(tail)
    if name in ("Bash", "PowerShell"):
        cmd = inp.get("command", "").replace("/", "\\")
        if f"R2_labels_batch_{nn}" not in cmd or "R2_blind_s46" not in cmd:
            return False
        return bool(re.search(r"json\.dump|\.write\(|open\([^)]*['\"]w|Set-Content|Out-File|>\s*\S*R2_labels", cmd))
    return False


def scan_session(path):
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    text = first_user_text(rows)
    m = OUT_RE.search(text)
    probe = "PROBE" in text and m is None
    if not m and not probe:
        return None
    nn = m.group(1) if m else None
    models = collections.Counter()
    stops = collections.Counter()
    writers = []
    for r in rows:
        if r.get("type") != "assistant":
            continue
        msg = r["message"]
        models[msg.get("model")] += 1
        if msg.get("stop_reason"):
            stops[msg["stop_reason"]] += 1
        for it in msg.get("content") or []:
            if it.get("type") == "tool_use" and nn and is_write_to(it, nn):
                writers.append({"timestamp": r["timestamp"], "uuid": r["uuid"], "model": msg.get("model"), "tool": it["name"]})
    meta_p = path[:-6] + ".meta.json"
    meta = json.load(open(meta_p, encoding="utf-8")) if os.path.exists(meta_p) else {}
    ts = [r["timestamp"] for r in rows if r.get("timestamp")]
    return {
        "agent_file": os.path.basename(path),
        "description": meta.get("description"),
        "agentType": meta.get("agentType"),
        "batch": nn,
        "probe": probe,
        "first_ts": min(ts) if ts else None,
        "last_ts": max(ts) if ts else None,
        "models": dict(models),
        "stop_reasons": dict(stops),
        "writer_turns": writers,
        "writer_model": writers[-1]["model"] if writers else None,
    }


def check_labels(nn):
    inp = os.path.join(HERE, "input", f"R2_blind_batch_{nn}.json")
    out = os.path.join(HERE, f"R2_labels_batch_{nn}.json")
    if not os.path.exists(out):
        return {"exists": False, "ok": False}
    ids_in = [r["id"] for r in json.load(open(inp, encoding="utf-8"))]
    try:
        lab = json.load(open(out, encoding="utf-8"))
    except Exception as e:
        return {"exists": True, "ok": False, "error": f"json: {e}"}
    ids_out = [r.get("id") for r in lab]
    bad_score = [r.get("id") for r in lab if not (isinstance(r.get("score"), int) and 0 <= r["score"] <= 4)]
    bad_label = [r.get("id") for r in lab if isinstance(r.get("score"), int) and r.get("label") != ("GEN" if r["score"] >= 3 else "VER")]
    ok = (len(lab) == len(ids_in) and sorted(ids_out) == sorted(ids_in) and len(set(ids_out)) == len(ids_out)
          and not bad_score and not bad_label)
    return {"exists": True, "ok": ok, "n_in": len(ids_in), "n_out": len(lab),
            "missing": sorted(set(ids_in) - set(ids_out))[:10], "extra": sorted(set(ids_out) - set(ids_in))[:10],
            "dup": len(ids_out) - len(set(ids_out)), "bad_score": bad_score[:10], "bad_label": bad_label[:10]}


def main():
    sess = sys.argv[1]
    sub = os.path.join(sess, "subagents")
    runs = []
    for f in sorted(os.listdir(sub)):
        if f.startswith("agent-") and f.endswith(".jsonl"):
            s = scan_session(os.path.join(sub, f))
            if s:
                runs.append(s)
    runs.sort(key=lambda s: s["first_ts"] or "")
    by_batch = collections.defaultdict(list)
    for s in runs:
        if s["batch"]:
            by_batch[s["batch"]].append(s)
    batches = {}
    for i in range(1, 51):
        nn = f"{i:02d}"
        sess_list = by_batch.get(nn, [])
        writer_sessions = [s for s in sess_list if s["writer_model"]]
        last_writer = writer_sessions[-1] if writer_sessions else None
        lab = check_labels(nn)
        batches[nn] = {
            "n_sessions": len(sess_list),
            "last_writer_session": last_writer["agent_file"] if last_writer else None,
            "last_writer_model": last_writer["writer_model"] if last_writer else None,
            "last_writer_all_models": last_writer["models"] if last_writer else None,
            "labels": lab,
            "accept": bool(last_writer and last_writer["writer_model"] == TARGET
                           and set(last_writer["models"]) == {TARGET} and lab["ok"]),
        }
    res = {"target_model": TARGET, "sessions": runs, "batches": batches,
           "n_accept": sum(b["accept"] for b in batches.values()),
           "not_accepted": [nn for nn, b in batches.items() if not b["accept"]]}
    json.dump(res, open(os.path.join(HERE, "R2s46_verify_result.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for s in runs:
        if s["probe"]:
            print("PROBE", s["agent_file"], s["models"], s["stop_reasons"])
    for nn, b in batches.items():
        if b["n_sessions"] or b["labels"]["exists"]:
            print(nn, "sessions", b["n_sessions"], "writer", b["last_writer_model"], "all", b["last_writer_all_models"],
                  "labels_ok", b["labels"]["ok"], "ACCEPT" if b["accept"] else "--")
    print("accepted", res["n_accept"], "/ 50; not accepted:", res["not_accepted"])


if __name__ == "__main__":
    main()
