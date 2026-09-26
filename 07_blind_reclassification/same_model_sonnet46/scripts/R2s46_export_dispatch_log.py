"""从主会话记录导出 Sonnet 4.6 盲跑的派发记录（字段同 R2_dispatch_log.jsonl），并逐份比对任务书是否与 dispatch_prompts.json 逐字相同。只读会话记录。

用法: python R2s46_export_dispatch_log.py <主会话 jsonl>
输出: 同目录 R2_dispatch_log_s46.jsonl
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    main_jsonl = sys.argv[1]
    expected = {p["batch"]: p for p in json.load(open(os.path.join(HERE, "dispatch_prompts.json"), encoding="utf-8"))}
    uses, results = {}, {}
    for line in open(main_jsonl, encoding="utf-8"):
        r = json.loads(line)
        content = (r.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for it in content:
            if r.get("type") == "assistant" and it.get("type") == "tool_use" and it.get("name") == "Agent":
                desc = (it.get("input") or {}).get("description", "")
                if desc.startswith("R2s46"):
                    uses[it["id"]] = {"ts": r["timestamp"], "input": it["input"]}
            if r.get("type") == "user" and it.get("type") == "tool_result" and it.get("tool_use_id") in uses:
                txt = it.get("content")
                txt = txt if isinstance(txt, str) else json.dumps(txt, ensure_ascii=False)
                results[it["tool_use_id"]] = not it.get("is_error") and "launched successfully" in txt
    out, mismatches = [], []
    for tid, u in sorted(uses.items(), key=lambda kv: kv[1]["ts"]):
        inp = u["input"]
        desc = inp["description"]
        row = {"dispatched_utc": u["ts"], "description": desc, "model_alias": inp.get("model"),
               "subagent_type": inp.get("subagent_type"), "launched": results.get(tid, False), "prompt": inp.get("prompt", "")}
        out.append(row)
        batch = desc.split()[4] if desc.startswith("R2s46 blind rating batch") else None
        if batch:
            exp = expected[batch]["prompt"]
            if row["prompt"] != exp:
                mismatches.append(desc)
            row["prompt_sha256"] = hashlib.sha256(row["prompt"].encode("utf-8")).hexdigest()
            row["prompt_matches_registered"] = row["prompt"] == exp
    with open(os.path.join(HERE, "R2_dispatch_log_s46.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for row in out:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    n_batch = sum(1 for r in out if r["description"].startswith("R2s46 blind rating batch"))
    print("dispatches:", len(out), "batch dispatches:", n_batch, "launched:", sum(r["launched"] for r in out))
    print("model_alias values:", sorted({str(r["model_alias"]) for r in out}), "subagent_type:", sorted({str(r["subagent_type"]) for r in out}))
    print("prompt mismatches vs dispatch_prompts.json:", mismatches or "none")


if __name__ == "__main__":
    main()
