# -*- coding: utf-8 -*-
u"""Export, from the working-session records, which files each blind rating session touched.

Rules: SIM27_access_rules.md (written before the first export). Two groups of sub-sessions:
  H  the fifty sessions of the blind classification (Section 4.2 of the manuscript), identified by
     writing 工作文档/R2_blind/R2_labels_batch_NN.json;
  W  the twenty rating sessions of the sampling-window test (Section 7.1 of the manuscript), identified by
     writing 工作文档/R1_labels_batch_NN.json or 工作文档/R1c_labels_batch_NN.json.
Only structured fields are read: line type, timestamp, message.model, the name and input of each tool
call, and the text of tool results (searched for a watch-list of file names only, never exported).
Assistant text, thinking, the task text, attachments and meta files are not read.

Usage:
  python SIM27_access_audit.py --sessions <dir holding the project's session records> --out <dir>
The session directory defaults to ~/.claude/projects/E------- (expanded at run time; no user name is
written into this file or its outputs).
"""
import argparse, collections, csv, io, json, os, re, sys

sys.stdout.reconfigure(encoding="utf-8")
ap = argparse.ArgumentParser()
ap.add_argument("--sessions", default=os.path.join(os.path.expanduser("~"), ".claude", "projects", "E-------"))
ap.add_argument("--out", required=True)
args = ap.parse_args()
SESS = args.sessions
HOME = os.path.expanduser("~")
USER = os.path.basename(HOME)

SEP = r"[\\/]+"
PAT_H = re.compile(r"工作文档" + SEP + r"R2_blind" + SEP + r"R2_labels_batch_(\d{2})\.json")
PAT_W = re.compile(r"工作文档" + SEP + r"(R1c?)_labels_batch_(\d{2})\.json")
GROUPS = {
    "H": {"pat": PAT_H, "t0": "2026-09-23T00:00", "t1": "2026-09-25T00:00",
          "dir": re.compile(r"工作文档" + SEP + r"R2_blind[\\/]*(?=[\"'\s*]|$)"),   # 追加 3:目标止于目录本身
          "maps": ["R2_token_map", "R2_ym_map"],
          "watch": ["question_labels_python_blind", "within_so_llm_panel_python_blind", "ids_list.txt",
                    "R2_design_sha256", "设计书", "question_labels", "within_so_llm_panel", "so_questions_", "_result.json"]},
    "W": {"pat": PAT_W, "t0": "2026-09-22T00:00", "t1": "2026-09-23T00:00",
          "dir": re.compile(r"工作文档[\\/]*(?=[\"'\s*]|$)"),   # 追加 3:目标止于目录本身
          "maps": ["R1_token_map", "R1c_token_map", "R1_uniform_raw"],
          "watch": ["R1_month_compare", "设计书", "question_labels", "within_so_llm_panel", "so_questions_", "_result.json"]},
}
GROUPS["H"]["inp"] = re.compile(r"R2_blind_batch_(\d{2})\.json")
GROUPS["W"]["inp"] = re.compile(r"(R1c?)_blind_batch_(\d{2})\.json")
UESC = re.compile(r"\\u([0-9a-fA-F]{4})")


def unesc(s):
    """追加 2:把 \\uXXXX 转义还原为字符,只用于匹配。"""
    return UESC.sub(lambda m: chr(int(m.group(1), 16)), s)


rejected = []
GROUPS["H"]["cd"] =re.compile(r"\bcd\s+(?:/d\s+)?[\"']?[^\"'\n&;]*工作文档" + SEP + r"R2_blind[\\/]*[\"']?(?:\s|&|;|$)")
GROUPS["H"]["rel"] = re.compile(r"(?<![\w\\/])(?:\.[\\/])?R2_labels_batch_(\d{2})\.json")
GROUPS["W"]["cd"] = re.compile(r"\bcd\s+(?:/d\s+)?[\"']?[^\"'\n&;]*工作文档[\\/]*[\"']?(?:\s|&|;|$)")
GROUPS["W"]["rel"] = re.compile(r"(?<![\w\\/])(?:\.[\\/])?(R1c?)_labels_batch_(\d{2})\.json")
LISTCMD = re.compile(r"(?:^|[\s;|&(])(?:ls|dir|Get-ChildItem|gci|find|tree)(?:\s|$)", re.I)
PATHRE = re.compile(r"(?:[A-Za-z]:[\\/]|/[a-zA-Z]/|~[\\/])[^\s\"'<>|;*?`]+")


HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n.*?\n\1[ \t]*(?=\n|$)", re.S)
SPLIT = re.compile(r"&&|\|\||;|\||\n")
VERB = re.compile(r"^\s*(?:ls|dir|Get-ChildItem|gci|find|tree)(?:\s|$)", re.I)


def is_listing(cmd, G):
    """追加 4:按语句切分,只看以列表命令开头的语句;heredoc 正文先剔除。"""
    cmd = HEREDOC.sub(" <heredoc> ", cmd.replace("\\\\", "\\"))
    in_dir = False
    for st in SPLIT.split(cmd):
        s = st.strip()
        if re.match(r"(?i)^(?:cd|Set-Location|pushd)\b", s):
            in_dir = bool(G["dir"].search(s + " "))
            continue
        if VERB.match(s):
            args_ = [a for a in s.split()[1:] if not a.startswith("-")]
            if G["dir"].search(s + " ") or (in_dir and not args_):
                return True
    return False


def sanitize(p):
    s = p.replace("\\\\", "/").replace("\\", "/")
    s = re.sub(r"^/([a-zA-Z])/", lambda m: m.group(1).upper() + ":/", s)
    s = re.sub(r"(?i)^E:/智能体论文/P9b_IPM_20260919/", "<workdir>/", s)
    s = re.sub(r"(?i)^E:/智能体论文/", "<projects>/", s)
    s = re.sub(r"(?i)^C:/Users/[^/]+/AppData/Local/Temp/claude/[^/]+/[^/]+/scratchpad/?", "<scratchpad>/", s)
    s = re.sub(r"(?i)^C:/Users/[^/]+/\.claude/", "<claude_home>/", s)
    s = re.sub(r"(?i)^C:/Users/[^/]+/", "<home>/", s)
    s = re.sub(r"(?i)^~/", "<home>/", s)
    s = re.sub(r"(?i)^[A-Z]:/", "<drive>/", s)
    return s


def strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from strings(v)


def result_text(b):
    c = b.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "\n".join(x.get("text", "") for x in c if isinstance(x, dict))
    return ""


def load(path):
    """-> list of events: ('use', ts, model, name, input) | ('res', ts, text) | ('asst', ts, model)."""
    ev = []
    for line in io.open(path, encoding="utf-8"):
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("type") not in ("user", "assistant"):
            continue
        msg = d.get("message") or {}
        ts = d.get("timestamp", "")
        blocks = msg.get("content")
        if d["type"] == "assistant":
            ev.append(("asst", ts, msg.get("model")))
        if not isinstance(blocks, list):
            continue
        for b in blocks:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use":
                ev.append(("use", ts, msg.get("model"), b.get("name", ""), b.get("input") or {}))
            elif b.get("type") == "tool_result":
                ev.append(("res", ts, result_text(b)))
    return ev


def detect(ev, g):
    """Per-session flags under the rules. Pure function of the event list, so it can be tested."""
    G = GROUPS[g]
    f = {"map_in_tool_input": False, "map_read_tool": False, "watch_in_tool_input": [], "dir_listed": False,
         "map_name_in_results": False, "map_names_seen": [], "paths": []}
    for e in ev:
        if e[0] == "use":
            name, inp = e[3], e[4]
            ss = [unesc(x) for x in strings(inp)]
            joined = "\n".join(ss)
            if any(m in joined for m in G["maps"]):
                f["map_in_tool_input"] = True
            if name == "Read" and any(m in str(inp.get("file_path", "")) for m in G["maps"]):
                f["map_read_tool"] = True
            for w in G["watch"]:
                if w in joined and w not in f["watch_in_tool_input"]:
                    f["watch_in_tool_input"].append(w)
            if name in ("Bash", "PowerShell"):
                cmd = unesc(str(inp.get("command", "")))
                if is_listing(cmd, G):
                    f["dir_listed"] = True
                verb = cmd.strip().split()[0] if cmd.strip() else ""
                for p in PATHRE.findall(cmd):
                    f["paths"].append((e[1], name, "command:" + os.path.basename(verb)[:20], sanitize(p)))
            else:
                for k in ("file_path", "path", "notebook_path") + (("pattern",) if name == "Glob" else ()):
                    v = inp.get(k)
                    if isinstance(v, str) and v:
                        f["paths"].append((e[1], name, k, sanitize(v)))
                if name in ("Glob", "LS") and any(G["dir"].search(str(inp.get(k, "")) + " ") for k in ("path", "pattern")):
                    f["dir_listed"] = True
        elif e[0] == "res":
            for m in G["maps"]:
                if m in e[2]:
                    f["map_name_in_results"] = True
                    if m not in f["map_names_seen"]:
                        f["map_names_seen"].append(m)
    return f


# ---------------- controls on synthetic samples (must fail / must pass) ----------------
def synth(items):
    return [("use", "t", "m", n, i) if k == "use" else ("res", "t", i) for k, n, i in items]


bad_H = synth([("use", "Read", {"file_path": r"E:\智能体论文\P9b_IPM_20260919\工作文档\R2_blind\R2_token_map.json"}),
               ("use", "Bash", {"command": 'ls "E:/智能体论文/P9b_IPM_20260919/工作文档/R2_blind/"'}),
               ("res", None, "R2_blind_batch_01.json\nR2_ym_map.json\n")])
good_H = synth([("use", "Read", {"file_path": r"E:\智能体论文\P9b_OSF_复现包_20260920\01_panels_and_classification\CLASSIFY_RUBRIC.md"}),
                ("use", "Read", {"file_path": r"E:\智能体论文\P9b_IPM_20260919\工作文档\R2_blind\R2_blind_batch_01.json"}),
                ("res", None, "[{\"id\": \"P0001\"}]")])
fb, fg = detect(bad_H, "H"), detect(good_H, "H")
assert fb["map_in_tool_input"] and fb["map_read_tool"] and fb["dir_listed"] and fb["map_name_in_results"], fb
assert not (fg["map_in_tool_input"] or fg["map_read_tool"] or fg["dir_listed"] or fg["map_name_in_results"]), fg
bad_W = synth([("use", "Bash", {"command": 'ls -la "E:/智能体论文/P9b_IPM_20260919/工作文档/" | head -50'}),
               ("res", None, "R1_token_map.json\nR1_uniform_raw.json")])
fw = detect(bad_W, "W")
assert fw["dir_listed"] and fw["map_name_in_results"] and not fw["map_in_tool_input"], fw
# 追加 3 的对照:列目录本身判真;列目录里的单个文件判假
one_file = synth([("use", "Bash", {"command": r'ls -la "E:\智能体论文\P9b_IPM_20260919\工作文档\R2_blind\R2_labels_batch_35.json"'})])
whole_dir = synth([("use", "Bash", {"command": r'ls E:\智能体论文\P9b_IPM_20260919\工作文档\R2_blind | grep x'})])
glob_dir = synth([("use", "Glob", {"pattern": "*.json", "path": r"E:\智能体论文\P9b_IPM_20260919\工作文档\R2_blind"})])
assert not detect(one_file, "H")["dir_listed"] and detect(whole_dir, "H")["dir_listed"] and detect(glob_dir, "H")["dir_listed"]
# 追加 4 的对照
heredoc_tree = synth([("use", "Bash", {"command": 'cd "E:/智能体论文/P9b_IPM_20260919/工作文档/R2_blind" && cat > /tmp/b.py << \'PYEOF\'\nrows = [\n("P1", 3, "walk the tree"),\n]\ntree of options\nPYEOF\npython /tmp/b.py'})])
cd_ls = synth([("use", "Bash", {"command": 'cd "E:/智能体论文/P9b_IPM_20260919/工作文档/R2_blind" && ls -la'})])
assert not detect(heredoc_tree, "H")["dir_listed"] and detect(cd_ls, "H")["dir_listed"]
print("合成样本:应失败样本三项全判真,干净样本全判假 —— 通过")

# ---------------- identify sessions ----------------
files = []
for parent in sorted(os.listdir(SESS)):
    sd = os.path.join(SESS, parent, "subagents")
    if os.path.isdir(sd):
        files += [os.path.join(sd, x) for x in sorted(os.listdir(sd)) if x.endswith(".jsonl")]
print("子代理会话记录 %d 个" % len(files))

found = {"H": [], "W": []}
for fp in files:
    ev = load(fp)
    ts = [e[1] for e in ev if e[1]]
    if not ts:
        continue
    t_first = min(ts)
    for g, G in GROUPS.items():
        if not (G["t0"] <= t_first < G["t1"]):
            continue
        hits = set()
        inputs = set()
        methods = set()
        for e in ev:
            if e[0] != "use":
                continue
            for s in strings(e[4]):
                s = unesc(s)
                for m in G["inp"].finditer(s):
                    inputs.add(m.groups())
                for m in G["pat"].finditer(s):
                    hits.add(m.groups())
                    if e[3] in ("Write", "Edit") and G["pat"].search(unesc(str(e[4].get("file_path", "")))):
                        methods.add("write_tool")
                    elif e[3] in ("Bash", "PowerShell"):
                        methods.add("via_command")
                    else:
                        methods.add("via_script_or_other")
            # 追加 1:cd 进本组输入目录后以相对路径写出
            if e[3] in ("Bash", "PowerShell"):
                cmd = unesc(str(e[4].get("command", "")))
                if G["cd"].search(cmd):
                    for m in G["rel"].finditer(cmd):
                        hits.add(m.groups())
                        methods.add("via_command")
        # 追加 2:恰指名一个本组输入批,且与恰一个写出的标签文件批号一致
        if hits and len(hits) == 1 and inputs == hits:
            method = ("write_tool" if "write_tool" in methods else
                      "via_command" if "via_command" in methods else "via_script_or_other")
            found[g].append((fp, ev, sorted(hits), method))
        elif hits:
            rejected.append((g, os.path.basename(fp), sorted(hits), sorted(inputs)))

for r_ in rejected:
    print("  未认(不满足追加 2):", r_)
# expectation checks (abort before writing anything if not met)
bh = collections.Counter(k[0] for _, _, hs, _ in found["H"] for k in hs)
assert len(found["H"]) == 50 and sorted(bh) == ["%02d" % i for i in range(1, 51)] and set(bh.values()) == {1}, \
    ("组 H 识别不符", len(found["H"]), bh)
bw = collections.Counter(k for _, _, hs, _ in found["W"] for k in hs)
want_w = sorted([("R1", "%02d" % i) for i in range(1, 11)] + [("R1c", "%02d" % i) for i in range(1, 11)])
assert len(found["W"]) == 20 and sorted(bw) == want_w and set(bw.values()) == {1}, ("组 W 识别不符", len(found["W"]), bw)
print("识别:组 H 50 个会话(批 01–50 各一);组 W 20 个会话(R1、R1c 各 01–10 各一)")

# ---------------- positive control on the parent (batch-building) sessions ----------------
parents = {g: sorted({os.path.basename(os.path.dirname(os.path.dirname(fp))) for fp, _, _, _ in found[g]}) for g in found}
ctrl = {}
for g, ps in parents.items():
    for p in ps:
        pf = os.path.join(SESS, p + ".jsonl")
        fpar = detect(load(pf), g)
        n_use = 0
        for e in load(pf):
            if e[0] == "use" and any(m in "\n".join(strings(e[4])) for m in GROUPS[g]["maps"]):
                n_use += 1
        ctrl[(g, p)] = n_use
        print("正对照 组 %s 父会话 %s…:引用映射的工具调用 %d 次" % (g, p[:8], n_use))
for g in found:
    assert any(ctrl[(g, p)] > 0 for p in parents[g]), "正对照失败:组 %s 的父会话里检测不到映射引用" % g

# ---------------- export ----------------
os.makedirs(args.out, exist_ok=True)
summ, rows = [], []
for g in ("H", "W"):
    for fp, ev, hs, method in sorted(found[g], key=lambda x: x[2]):
        f = detect(ev, g)
        models = collections.Counter(e[2] for e in ev if e[0] == "asst" and e[2])
        uses = [e for e in ev if e[0] == "use"]
        ts = sorted(e[1] for e in ev if e[1])
        agent = os.path.basename(fp)[:-6]
        batch = "%s_%s" % hs[0] if g == "W" else "R2_%s" % hs[0][0]
        summ.append({
            "group": {"H": "blind_classification_S20", "W": "sampling_window_S19"}[g],
            "batch": batch, "session": agent,
            "first_timestamp_utc": ts[0], "last_timestamp_utc": ts[-1],
            "models": ";".join("%s×%d" % kv for kv in sorted(models.items())),
            "assistant_messages": sum(models.values()), "tool_calls": len(uses),
            "label_file_written_by": method,
            "map_named_in_any_tool_input": int(f["map_in_tool_input"]),
            "map_opened_with_Read": int(f["map_read_tool"]),
            "input_directory_listed": int(f["dir_listed"]),
            "map_file_name_seen_in_tool_results": int(f["map_name_in_results"]),
            "map_file_names_seen_in_tool_results": ";".join(f["map_names_seen"]),
            "other_watchlist_names_in_tool_input": ";".join(f["watch_in_tool_input"]),
            "distinct_paths": len({p[3] for p in f["paths"]}),
        })
        for ts_, tool, field, path in f["paths"]:
            rows.append({"group": summ[-1]["group"], "batch": batch, "session": agent, "timestamp_utc": ts_,
                         "tool": tool, "field": field, "path": path})

S1 = os.path.join(args.out, "session_access_summary.csv")
S2 = os.path.join(args.out, "session_file_paths.csv")
for fn, data in ((S1, summ), (S2, rows)):
    with io.open(fn, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(data[0].keys()))
        w.writeheader()
        w.writerows(data)

# ---------------- post-export guards: no user name, no absolute drive paths ----------------
for fn in (S1, S2):
    t = io.open(fn, encoding="utf-8").read()
    assert USER.lower() not in t.lower(), "输出含本机用户名:" + fn
    assert not re.search(r"(?i)users[\\/]", t), "输出含 Users 路径:" + fn
    assert not re.search(r"(?<![<\w])[A-Za-z]:[\\/]", t), "输出含盘符绝对路径:" + fn

agg = {}
for g, name in (("H", "blind_classification_S20"), ("W", "sampling_window_S19")):
    ss = [s for s in summ if s["group"] == name]
    agg[name] = {
        "sessions": len(ss),
        "map_named_in_any_tool_input": sum(s["map_named_in_any_tool_input"] for s in ss),
        "map_opened_with_Read": sum(s["map_opened_with_Read"] for s in ss),
        "input_directory_listed": sum(s["input_directory_listed"] for s in ss),
        "map_file_name_seen_in_tool_results": sum(s["map_file_name_seen_in_tool_results"] for s in ss),
        "sessions_with_other_watchlist_names": sum(1 for s in ss if s["other_watchlist_names_in_tool_input"]),
        "other_watchlist_names": sorted({w for s in ss for w in s["other_watchlist_names_in_tool_input"].split(";") if w}),
        "tool_calls": sum(s["tool_calls"] for s in ss), "assistant_messages": sum(s["assistant_messages"] for s in ss),
        "models": dict(collections.Counter(m.split("×")[0] for s in ss for m in s["models"].split(";"))),
        "written_by": dict(collections.Counter(s["label_file_written_by"] for s in ss)),
        "first": min(s["first_timestamp_utc"] for s in ss), "last": max(s["last_timestamp_utc"] for s in ss),
    }
agg["_positive_control_parent_tool_calls_naming_maps"] = {"%s:%s" % (g, p[:8]): n for (g, p), n in ctrl.items()}
agg["_n_subagent_records_scanned"] = len(files)
io.open(os.path.join(args.out, "session_access_counts.json"), "w", encoding="utf-8").write(
    json.dumps(agg, indent=1, ensure_ascii=False))
print(json.dumps(agg, indent=1, ensure_ascii=False))
