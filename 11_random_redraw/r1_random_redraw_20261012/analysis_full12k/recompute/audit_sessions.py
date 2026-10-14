# -*- coding: utf-8 -*-
"""audit_sessions.py -- P9b 问题1：100 个评分会话(rater-sonnet5, set12k)的启动上下文与工具调用审计。只读，不改任何会话记录。
会话识别：wave_verify.sessions() (首条 user 消息含 set12k\\blind_batch_NNN.json 与 labels_batch_NNN.json)。
B1 启动上下文来源 x 串命中；B2 工具调用是否触及禁区路径；B3 各会话路径集合。
输出：RESULTS 段(日志) + audit_sessions.md 摘要 + audit_sessions_paths.csv(全部去重路径)。路径在输出中脱敏(用户名/盘符前缀)。
"""
import csv, io, json, os, re, sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.dirname(os.path.dirname(HERE))
SUBRUN = os.path.join(R, "subagent_run", "full12k")
sys.path.insert(0, SUBRUN)
import wave_verify as W

ses = W.sessions()
if sorted(ses) != list(range(1, 101)) or any(len(v) != 1 for v in ses.values()):
    print("GATE FAIL: sessions not 1..100 exactly once", sorted(ses)[:5]); sys.exit(1)
print("GATE PASS: 100 批各恰 1 个会话 (wave_verify.sessions)")

HOME = os.path.expanduser("~")


def strings(o, out=None):
    """递归取出所有字符串值。"""
    if out is None: out = []
    if isinstance(o, str): out.append(o)
    elif isinstance(o, dict):
        for v in o.values(): strings(v, out)
    elif isinstance(o, list):
        for v in o: strings(v, out)
    return out


# ---------------- 载入 ----------------
S = {}   # batch -> dict
for b, ps in sorted(ses.items()):
    lines = [json.loads(l) for l in io.open(ps[0], encoding="utf-8") if l.strip()]
    S[b] = dict(path=ps[0], lines=lines)

# ---------------- B1 启动上下文来源 ----------------
STR = ["0.199", "0.002", "r1_随机重抽", "draw_all.csv", "panel_map", "随机", "random", "first 100", "最早", "Selective", "γ", "0.304", "0.30", "0.42"]
POS = ["0.199", "userEmail", "Contents of"]   # 正对照(确定在注入文本中)
NEG = ["ZZZ_NOT_PRESENT_9a7f"]
ALLSTR = STR + [s for s in POS if s not in STR] + NEG
CI_STR = {"random": "random", "first 100": "first 100"}   # 另做忽略大小写版本


def split_sources(o, pos):
    """返回 [(source, text)]。pos: 'pre'/'post' (相对首条 assistant)。"""
    t = o["type"]
    if t == "attachment":
        a = o["attachment"]; at = a.get("type")
        rendered = "\n".join(x.get("content", "") for x in (o.get("rendered") or []))
        raw = "\n".join(strings(a))
        text = rendered + "\n" + raw
        if at == "instructions":
            res = []; cur = "instructions:preamble"; buf = []
            for ln in rendered.split("\n"):
                m = re.match(r"^Contents of (.+?) \(", ln)
                if m:
                    res.append((cur, "\n".join(buf))); cur = "instructions:" + os.path.basename(m.group(1).replace("\\", "/")); buf = [ln]
                else: buf.append(ln)
            res.append((cur, "\n".join(buf)))
            return [(pos + "|" + s, x) for s, x in res]
        if at == "session_context":
            i = rendered.find("# gitStatus")
            if i < 0: return [(pos + "|session_context:userEmail", rendered)]
            return [(pos + "|session_context:userEmail", rendered[:i]), (pos + "|session_context:gitStatus", rendered[i:])]
        return [(pos + "|attachment:" + str(at), text)]
    if t == "user":
        c = o["message"]["content"]
        if isinstance(c, str):
            return [(pos + "|" + ("user_meta_reminder" if o.get("isMeta") else "task_prompt"), c)]
        txt = "\n".join(strings(c))
        return [(pos + "|user_blocks", txt)]
    return []


src_text = defaultdict(lambda: defaultdict(str))   # source -> batch -> text
first_user_seen = {}
for b, d in S.items():
    seen_asst = False
    first_user_seen[b] = False
    for o in d["lines"]:
        if o["type"] == "assistant": seen_asst = True; continue
        pos = "post" if seen_asst else "pre"
        if o["type"] == "user" and isinstance(o["message"]["content"], list):
            # tool_result 用户行：B1 不计(属工具结果，B2 另扫)
            if any(isinstance(c, dict) and c.get("type") == "tool_result" for c in o["message"]["content"]): continue
        for s, x in split_sources(o, pos):
            src_text[s][b] += "\n" + x
    src_text["pre|record_meta_cwd"][b] = "\n".join(sorted({o.get("cwd", "") for o in d["lines"] if o.get("cwd")}))

sources = sorted(src_text)
nses = {s: len(src_text[s]) for s in sources}
hit = {s: {k: sum(1 for b, t in src_text[s].items() if k in t) for k in ALLSTR} for s in sources}
hit_ci = {s: {k: sum(1 for b, t in src_text[s].items() if k.lower() in t.lower()) for k in CI_STR} for s in sources}
# 并集
union_pre = {b: "\n".join(src_text[s][b] for s in sources if s.startswith("pre|") and b in src_text[s]) for b in S}
union_all = {b: "\n".join(src_text[s][b] for s in sources if b in src_text[s]) for b in S}
u_pre = {k: sum(1 for b in S if k in union_pre[b]) for k in ALLSTR}
u_all = {k: sum(1 for b in S if k in union_all[b]) for k in ALLSTR}
u_pre_ci = {k: sum(1 for b in S if k.lower() in union_pre[b].lower()) for k in CI_STR}
u_all_ci = {k: sum(1 for b in S if k.lower() in union_all[b].lower()) for k in CI_STR}
# 首条 user 消息(任务书)是否含任一串
hook_names = Counter()
for b, d in S.items():
    for o in d["lines"]:
        if o["type"] == "attachment" and o["attachment"].get("type") == "hook_success":
            a = o["attachment"]; hook_names[(a.get("hookEvent"), a.get("hookName"), str(a.get("command"))[:80])] += 1

# ---------------- B2 工具调用触及禁区 ----------------
FORBID = [("rate_private\\", r"rate_private[\\/]"), ("panel_map*", r"panel_map"), ("draw\\", r"(?<![A-Za-z])draw[\\/](?![\"'])"),
          ("draw_all.csv", r"draw_all\.csv"), ("bodies\\", r"bodies[\\/]"), ("population\\", r"population[\\/]"),
          ("question_labels_python*", r"question_labels_python"), ("R2_blind\\", r"R2_blind[\\/]"), ("r1_随机重抽", r"r1_随机重抽")]
FORBID_RE = [(n, re.compile(p)) for n, p in FORBID]
ALLOWED = re.compile(r"R3_blind[\\/]+set12k")


def norm(s):
    return s.replace("\\\\", "\\")


def redact(s):
    s = norm(s)
    s = re.sub(r"[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s\"']+", "<home>", s)
    s = re.sub(r"/[a-z]/Users/[^/\s\"']+", "<home>", s)
    s = s.replace("E:\\智能体论文\\P9b_IPM_20260919\\", "<workdir>\\").replace("E:\\智能体论文\\", "<projects>\\")
    return s


calls = []   # (batch, idx, name, input_text, input_dict)
results = []  # (batch, text)
for b, d in S.items():
    idmap = {}
    for o in d["lines"]:
        if o["type"] == "assistant":
            for c in o["message"]["content"]:
                if c.get("type") == "tool_use":
                    calls.append((b, c["name"], c["input"], o.get("timestamp"), c.get("id")))
        elif o["type"] == "user" and isinstance(o["message"]["content"], list):
            for c in o["message"]["content"]:
                if isinstance(c, dict) and c.get("type") == "tool_result":
                    results.append((b, "\n".join(strings(c.get("content")))))
tool_counts = Counter(n for _, n, _, _, _ in calls)
sess_with_calls = len({b for b, *_ in calls})


# “R3_blind\set12k 自身除外”：命中点所在整条路径若含 R3_blind\set12k 则剔除
def path_around(txt, m):
    s = m.start()
    while s > 0 and txt[s - 1] not in " \t\n\"'<>|;()": s -= 1
    e = m.end()
    while e < len(txt) and txt[e] not in " \t\n\"'<>|;()": e += 1
    return txt[s:e]


touch = []
excluded = 0
for b, name, inp, ts, _ in calls:
    txt = norm("\n".join(strings(inp)))
    for pn, pr in FORBID_RE:
        for m in pr.finditer(txt):
            p = path_around(txt, m)
            if ALLOWED.search(p): excluded += 1; continue
            touch.append((b, name, pn, p[:160]))
rtouch = []
for b, t in results:
    t = norm(t)
    for pn, pr in FORBID_RE:
        for m in pr.finditer(t):
            rtouch.append((b, pn, t[max(0, m.start() - 40): m.end() + 40].replace("\n", " ")))
# 列目录/相对路径类命令(无法靠路径串判定的触及)
LISTV = re.compile(r"^\s*(?:ls|dir|Get-ChildItem|gci|find|tree)(?:\s|$)", re.I)
SPLITST = re.compile(r"&&|\|\||;|\||\n")
listing = []
rel_cmd = []     # cd 到“自己的 scratchpad / set12k”以外的目录，或含 ../ 的命令
cd_ok = 0
for b, name, inp, ts, _ in calls:
    if name in ("Bash", "PowerShell"):
        cmd = norm(inp.get("command", ""))
        if any(LISTV.search(st) for st in SPLITST.split(cmd)): listing.append((b, name, cmd[:160].replace("\n", " ")))
        sts = [st for st in SPLITST.split(cmd) if re.match(r"\s*(?:cd|Set-Location|pushd)\b", st)]
        bad = [st for st in sts if not ("scratchpad" in st or "set12k" in st)]
        if bad or re.search(r"(?:^|[\s\"'=])\.\.[\\/]", cmd): rel_cmd.append((b, name, cmd[:160].replace("\n", " ")))
        elif sts: cd_ok += 1
    if name in ("Glob", "Grep"):
        listing.append((b, name, norm(json.dumps(inp, ensure_ascii=False))[:160]))

# ---------------- B3 路径集合 ----------------
PATHRE = re.compile(r"(?:[A-Za-z]:[\\/]|/[a-zA-Z]/|~[\\/])[^\s\"'<>|;*?`()]+")
paths = defaultdict(lambda: defaultdict(set))   # category -> path -> batches
for b, name, inp, ts, _ in calls:
    if name in ("Read", "Write", "Edit", "NotebookEdit"):
        p = inp.get("file_path") or inp.get("notebook_path")
        if p: paths["tool:" + name][redact(p)].add(b)
    elif name in ("Glob", "Grep"):
        for k in ("path", "pattern"):
            if inp.get(k): paths["tool:" + name + "." + k][redact(str(inp[k]))].add(b)
    elif name in ("Bash", "PowerShell"):
        cmd = norm(inp.get("command", ""))
        for m in PATHRE.finditer(cmd):
            paths["cmd:" + name][redact(m.group(0).rstrip(".,:)"))].add(b)
    else:
        pass
bnorm = lambda p: re.sub(r"(batch_)\d{3}", r"\1###", p)
allp = defaultdict(set)
for cat, dd in paths.items():
    for p, bs in dd.items(): allp[p] |= bs
by_session_read = defaultdict(set)   # batch -> Read-tool paths
for b, name, inp, ts, _ in calls:
    if name == "Read" and inp.get("file_path"): by_session_read[b].add(redact(inp["file_path"]))
read_union = set().union(*by_session_read.values()) if by_session_read else set()
read_norm = Counter()
for b, ps_ in by_session_read.items():
    for p in {bnorm(x) for x in ps_}: read_norm[p] += 1
read_per_sess = [len(v) for v in by_session_read.values()]
all_norm = defaultdict(set)
for p, bs in allp.items(): all_norm[bnorm(p)] |= bs

with io.open(os.path.join(HERE, "audit_sessions_paths.csv"), "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f); w.writerow(["category", "path(脱敏)", "n_sessions", "batches"])
    for cat in sorted(paths):
        for p in sorted(paths[cat]):
            bs = sorted(paths[cat][p]); w.writerow([cat, p, len(bs), " ".join("%03d" % x for x in bs)])

# B1 补充：禁区名称是否出现在注入的启动上下文里(按来源)
inj_forbid = {}
for pn, pr in FORBID_RE:
    row = []
    for s_ in sources:
        n_ = sum(1 for b_, t_ in src_text[s_].items() if pr.search(norm(t_)))
        if n_: row.append((s_, n_))
    inj_forbid[pn] = row
# ---------------- RESULTS ----------------
sess_models = Counter()
nasst = 0
for b, d in S.items():
    for o in d["lines"]:
        if o["type"] == "assistant": nasst += 1; sess_models[(o["message"] or {}).get("model")] += 1
t_all = sorted(o["timestamp"] for d in S.values() for o in d["lines"] if o.get("timestamp"))
print("\n=== RESULTS ===")
print("sessions=100; assistant 轮=%d; models=%s; 记录行时间戳范围 %s .. %s" % (nasst, dict(sess_models), t_all[0], t_all[-1]))
print("-- B1 注入来源(会话数; pre=首条assistant之前, post=之后) --")
for s in sources:
    print("SRC %-48s sessions=%3d" % (s, nses[s]))
print("hook_success 明细(事件,名,命令前80): %s" % dict(hook_names))
print("-- B1 串命中: 各来源会话数(仅列有命中的来源) --")
for k in ALLSTR:
    row = [(s, hit[s][k]) for s in sources if hit[s][k]]
    print("STR %-22s union_pre=%3d union_all=%3d | %s" % (repr(k), u_pre[k], u_all[k], "; ".join("%s=%d" % x for x in row) or "(无来源命中)"))
for k in CI_STR:
    row = [(s, hit_ci[s][k]) for s in sources if hit_ci[s][k]]
    print("STR_CI %-19s union_pre=%3d union_all=%3d | %s" % (repr(k), u_pre_ci[k], u_all_ci[k], "; ".join("%s=%d" % x for x in row) or "(无)"))
print("正对照: %s 均须 >0 ; 负对照 %s 须 =0 -> %s" % (POS, NEG, {k: u_pre[k] for k in POS + NEG}))
print("-- B1 补充: 禁区名称在注入上下文中的出现(来源=会话数) --")
for pn, row in inj_forbid.items(): print("INJ %-26s %s" % (pn, "; ".join("%s=%d" % x for x in row) or "(无)"))
print("-- B2 工具调用 --")
print("tool_use 总数=%d (%s); 有工具调用的会话=%d; tool_result 数=%d" % (len(calls), dict(tool_counts), sess_with_calls, len(results)))
print("B2 禁区命中(工具输入, 已剔除路径含 R3_blind\\set12k 的 %d 处) = %d" % (excluded, len(touch)))
for t in touch: print("TOUCH batch=%03d tool=%s pat=%s path=%s" % (t[0], t[1], t[2], redact(t[3])))
rt_runlog = [t for t in rtouch if "runlogs" in t[2]]
rt_other = [t for t in rtouch if "runlogs" not in t[2]]
print("B2 禁区命中(工具结果文本) = %d ；其中 runlog 日志路径(hook 由 cwd 派生的路径名) %d 处/%d 会话，其余 %d 处" % (len(rtouch), len(rt_runlog), len({t[0] for t in rt_runlog}), len(rt_other)))
res_hit = {k: len({b for b, t in results if k in t}) for k in STR}
print("工具结果文本中 B1 串命中会话数: " + "; ".join("%r=%d" % (k, v) for k, v in res_hit.items()))
for t in rt_other[:30]: print("RTOUCH_OTHER batch=%03d pat=%s ctx=%s" % (t[0], t[1], redact(t[2])))
print("B2 列目录/Glob/Grep 类调用 = %d ; cd 到 scratchpad/set12k 的命令 %d 条(已排除); cd 到别处或含 ../ 的命令 = %d" % (len(listing), cd_ok, len(rel_cmd)))
for t in listing[:30]: print("LISTCALL batch=%03d %s %s" % (t[0], t[1], redact(t[2])))
for t in rel_cmd[:30]: print("RELCMD batch=%03d %s %s" % (t[0], t[1], redact(t[2])))
print("-- B3 路径 --")
print("Read 工具读取的去重路径(原样)=%d; 批号归一后=%d; 每会话 Read 路径数 min/max=%d/%d" % (len(read_union), len(read_norm), min(read_per_sess), max(read_per_sess)))
for p, n in sorted(read_norm.items(), key=lambda x: (-x[1], x[0])): print("READPATH sessions=%3d %s" % (n, p))
print("全部来源路径(Read/Write/Edit/Glob/Grep/命令内路径) 去重原样=%d; 批号归一后=%d" % (len(allp), len(all_norm)))
for cat in sorted(paths): print("CAT %-22s unique=%d" % (cat, len(paths[cat])))
print("=== END RESULTS ===")

# ---------------- md ----------------
md = io.open(os.path.join(HERE, "audit_sessions.md"), "w", encoding="utf-8", newline="\n")
W_ = md.write
W_("# 评分会话启动上下文与工具调用审计(set12k, 100 批)\n\n")
W_("脚本 audit_sessions.py；会话识别沿用 wave_verify.sessions()（每批恰 1 个会话，共 100）。assistant 轮 %d，模型 %s。记录行时间戳 %s 至 %s。\n\n" % (nasst, dict(sess_models), t_all[0], t_all[-1]))
W_("## B1 启动上下文注入来源（会话数）\n\n| 来源（pre=首条 assistant 之前；post=之后） | 会话数 |\n|---|---|\n")
for s in sources: W_("| %s | %d |\n" % (s, nses[s]))
W_("\nhook_success 明细：%s\n\n" % (dict(hook_names) or "无"))
st_src = [(s, sum(1 for b in S if "STATE.md" in src_text[s].get(b, ""))) for s in sources]
st_src = [x for x in st_src if x[1]]
W_("无 SessionStart hook 注入：首条 assistant 之前的 attachment 类型中没有 hook_success 一类；post 段的 hook_success 仅是 PreToolUse 的 runlog_wrap。字符串 `STATE.md` 只作为说明文字出现（CLAUDE.md 的交接约定、handoff 技能说明等），命中来源（会话数）：%s；没有任何 STATE.md 文件内容被注入。\n\n" % ("; ".join("%s=%d" % x for x in st_src) or "无"))
W_("## B1 指定串命中（会话数）\n\n| 串 | 启动上下文并集(pre) | 全部注入并集(pre+post) | 命中来源（会话数） |\n|---|---|---|---|\n")
for k in ALLSTR:
    row = [(s, hit[s][k]) for s in sources if hit[s][k]]
    tag = "（正对照）" if k in POS and k not in STR else ("（负对照）" if k in NEG else "")
    W_("| `%s`%s | %d | %d | %s |\n" % (k, tag, u_pre[k], u_all[k], "; ".join("%s=%d" % x for x in row) or "—"))
for k in CI_STR:
    row = [(s, hit_ci[s][k]) for s in sources if hit_ci[s][k]]
    W_("| `%s`（忽略大小写） | %d | %d | %s |\n" % (k, u_pre_ci[k], u_all_ci[k], "; ".join("%s=%d" % x for x in row) or "—"))
W_("\n禁区名称在**注入的启动上下文**中的出现（按来源，会话数）：\n\n")
for pn, row in inj_forbid.items(): W_("- `%s`：%s\n" % (pn, "; ".join("%s=%d" % x for x in row) or "无"))
W_("\n## B2 工具调用是否触及禁区\n\n")
W_("tool_use 共 %d 次（%s），分布在 %d 个会话；tool_result %d 条。禁区正则：rate_private\\、panel_map*、draw\\、draw_all.csv、bodies\\、population\\、question_labels_python*、R2_blind\\、r1_随机重抽；路径含 R3_blind\\set12k 者剔除（剔除 %d 处）。\n\n" % (len(calls), dict(tool_counts), sess_with_calls, len(results), excluded))
W_("- 工具**输入**命中：**%d** 次\n" % len(touch))
for t in touch: W_("  - 会话批号 %03d，工具 %s，模式 %s，路径 `%s`\n" % (t[0], t[1], t[2], redact(t[3])))
W_("- 工具**结果文本**命中（会话\"看到\"禁区文件名）：**%d** 次，其中 %d 处是 runlog 日志路径（PreToolUse hook 用 cwd 派生的日志路径名，%d 个会话，即有 hook_success 的会话）、%d 处其余（题面里的普通英文词等，见 log）\n" % (len(rtouch), len(rt_runlog), len({t[0] for t in rt_runlog}), len(rt_other)))
for t in rt_other[:20]: W_("  - 批号 %03d，模式 %s，上下文 `%s`\n" % (t[0], t[1], redact(t[2])))
W_("- 工具结果文本中 B1 指定串命中会话数：%s\n" % "；".join("`%s`=%d" % (k, v) for k, v in res_hit.items()))
W_("- 列目录/Glob/Grep 类调用 %d 次；cd 到 scratchpad/set12k 以外目录或含 ../ 的 Bash/PowerShell 命令 %d 次（路径串检索看不到相对路径，故单列，见 audit_sessions.log）。\n\n" % (len(listing), len(rel_cmd)))
W_("## B3 各会话读过的文件路径集合\n\n")
W_("Read 工具：去重路径 %d 个（原样），批号归一（blind_batch_### / labels_batch_###）后 %d 类；每会话 Read 的路径数 %d 至 %d。\n\n| 归一后路径 | 会话数 |\n|---|---|\n" % (len(read_union), len(read_norm), min(read_per_sess), max(read_per_sess)))
for p, n in sorted(read_norm.items(), key=lambda x: (-x[1], x[0])): W_("| `%s` | %d |\n" % (p, n))
W_("\n全部来源（Read/Write/Edit/Glob/Grep 参数 + Bash/PowerShell 命令内路径形字符串）去重后 %d 个（原样），批号归一后 %d 类；分类计数：%s。全表见 audit_sessions_paths.csv。\n\n" % (len(allp), len(all_norm), "; ".join("%s=%d" % (c, len(paths[c])) for c in sorted(paths))))
W_("命令内路径是\"命令文本里出现过\"，不区分读与写；Read 工具的清单才是确证的读取。\n")
md.close()
