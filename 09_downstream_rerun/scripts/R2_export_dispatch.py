# -*- coding: utf-8 -*-
"""R2 派发记录导出(先设环境变量 R2_SESSION_DIR):从会话 jsonl 逐字导出所有描述以「R2」开头、且确实启动成功的子任务派发。

字段:dispatched_utc(派发所在行的时间戳)、description、model_alias(派发时指定的模型别名)、prompt(任务书原文)、launched。
被并发上限等拒绝、未启动的派发不收;后台派发以启动回执为准,前台派发以返回的子代理报告(含 agentId)为准。输出 工作文档\\R2_dispatch_log.jsonl(按时间排序,覆盖旧文件)。
自证:只扫首个会话时须逐字复现旧记录的 127 条,不复现则不写盘。
"""
import io, json, os, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
# 会话记录所在目录(本机路径不入包):由环境变量 R2_SESSION_DIR 给出
PROJ = os.environ.get("R2_SESSION_DIR", r"C:\Users\<user>\.claude\projects\<project>")
assert os.path.isdir(PROJ), "请设环境变量 R2_SESSION_DIR 为会话记录目录"
SESSIONS = ["f30e9490-c79d-4c5c-a765-5ffc3ac87b32.jsonl", "567bc5a2-af3f-48aa-9d02-be1ec34b1700.jsonl"]
OUT = os.path.join(HERE, "R2_dispatch_log.jsonl")


def scan(fn):
    uses, results = {}, {}
    for line in io.open(os.path.join(PROJ, fn), encoding="utf-8"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        msg = r.get("message") or {}
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for c in content:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "tool_use" and c.get("name") == "Agent":
                inp = c.get("input") or {}
                if str(inp.get("description", "")).startswith("R2"):
                    uses[c["id"]] = dict(dispatched_utc=r.get("timestamp"), description=inp["description"],
                                         model_alias=inp.get("model"), prompt=inp.get("prompt"))
            elif c.get("type") == "tool_result":
                t = c.get("content")
                t = " ".join(x.get("text", "") for x in t if isinstance(x, dict)) if isinstance(t, list) else str(t)
                results[c.get("tool_use_id")] = (bool(c.get("is_error")), t)
    out = []
    for k, u in uses.items():
        err, t = results.get(k, (True, ""))
        if not err and ("launched successfully" in t or "agentId:" in t):   # 后台派发回执 / 前台派发的子代理报告
            out.append(dict(u, launched=True))
    return sorted(out, key=lambda x: x["dispatched_utc"])


old = [json.loads(l) for l in io.open(OUT, encoding="utf-8")]
first = scan(SESSIONS[0])
assert len(first) == 127 and first == old[:127], "首个会话导出与旧记录前 127 条不一致"
rows = first + scan(SESSIONS[1])
assert all(r in rows for r in old), "旧记录中有条目在新导出里找不到"
assert len({(r["dispatched_utc"], r["description"]) for r in rows}) == len(rows), "有重复派发"
io.open(OUT, "w", encoding="utf-8", newline="\n").write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
print("自证:首个会话逐字复现旧记录 127 条;现有记录 %d 条全部在新导出中;共 %d 条" % (len(old), len(rows)))
for r in rows[127:]:
    print("  +", r["dispatched_utc"], r["description"], r["model_alias"])
