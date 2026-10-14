# -*- coding: utf-8 -*-
"""r1_rate_api.py -- 经 Message Batches API 用 claude-sonnet-5 盲评（新随机面板 + 旧前100面板混合）。

阶段（--stage）：
  build    读旧面板（复现包）与新面板（bodies/），混合、固定种子打乱、每批 120 题；批内只有 id/title/tags/body；
           面板身份只写进 rate_private/panel_map.json。写 rate_run/<tag>/requests.jsonl 与 batches_meta.json。不联网。
  submit   提交 Message Batches。先查本地台账与 API 上在途批次，有同 tag 或任何 in_progress 批次即拒绝（--force 才越过）。
  collect  轮询并下载结果；逐条落盘 custom_id / message.id / model / usage / stop_reason；解析并校验（题数、id 恰好一次、
           score∈0..4、label 与 score 一致）；失败批次的题写入 failed_ids.json。
  retry    把解析失败/缺失的题单独（每个失败批次一个请求，仅含这些题）再提交，记入 retry_log.jsonl；再 collect。
  analyze  与已发表标签比较（一致率、加权 kappa、混淆矩阵）、分面板分布、model 字段与 token 用量。
  dryrun   仅 build + 打印请求体前 600 字符与大小。

提示词 = 原盲评指令 R2_PROMPT_TEMPLATE.txt 的规则段逐字 + 评分表全文与批 JSON 内嵌（API 无文件系统，原版是让评分者读/写文件），
输出改为"只返回 JSON 数组"。该差异记入运行记录。未设 temperature/top_p/top_k/effort/thinking（用 API 默认）。
key 只从环境变量 ANTHROPIC_API_KEY 读；缺失时退出码 4。key 不打印、不落盘。
"""
import argparse, csv, datetime as dt, hashlib, io, json, os, random, re, sys, time
import urllib.error, urllib.request
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
PKG = r"E:\智能体论文\P9b_OSF_复现包_20260920"
WD = r"E:\智能体论文\P9b_IPM_20260919\工作文档"
RUBRIC = os.path.join(PKG, "01_panels_and_classification", "CLASSIFY_RUBRIC.md")
TEMPLATE = os.path.join(WD, "R2_blind", "R2_PROMPT_TEMPLATE.txt")
TEMPLATE_SHA12 = "c54ade8b5e17"
PUB_BLIND = os.path.join(WD, "R2_blind", "question_labels_python_blind.csv")      # 发表的盲评分类（headline）
PUB_EARLY = [os.path.join(PKG, "01_panels_and_classification", "data", f) for f in
             ("question_labels_python_2021-2024.csv", "question_labels_python_ext_2024-07_2026-05.csv")]
MODEL = "claude-sonnet-5"
MAX_TOKENS = 16000
BS = 120
SEED = 20261012
API = "https://api.anthropic.com/v1/messages/batches"
VER = "2023-06-01"
PRIV = os.path.join(HERE, "rate_private")
RUN = os.path.join(HERE, "rate_run")


def sha12(b):
    return hashlib.sha256(b).hexdigest()[:12]


def wj(path, obj, indent=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    io.open(tmp, "w", encoding="utf-8").write(json.dumps(obj, ensure_ascii=False, indent=indent))
    os.replace(tmp, path)


def rj(path):
    return json.load(io.open(path, encoding="utf-8"))


# ---------------- 提示词 ----------------
def build_prompt(batch_rows):
    t = io.open(TEMPLATE, "rb").read()
    if sha12(t) != TEMPLATE_SHA12:
        raise SystemExit("原指令模板 sha12 变了")
    t = t.decode("utf-8").replace("\r\n", "\n")
    i0 = t.index("Each record has:")
    i1 = t.index("Write the result as a JSON array to:")
    intro = t[:t.index("Read the rubric file verbatim first:")].rstrip()
    rules = t[i0:i1].rstrip()          # Each record has ... Rules ... Score every record ... 逐字
    rubric = io.open(RUBRIC, encoding="utf-8").read().strip()
    batch_json = json.dumps(batch_rows, ensure_ascii=False, indent=1)
    return (intro + "\n\nThe rubric, verbatim:\n<rubric>\n" + rubric + "\n</rubric>\n\n"
            "The batch of questions, a JSON array:\n<batch>\n" + batch_json + "\n</batch>\n\n" + rules +
            "\n\nReturn the result as a JSON array only, with no other text, in this format:\n"
            '[{"id": "Txxxx", "score": 0, "label": "VER", "why": "..."}, ...]\n\n'
            "The array must have exactly one element per input record: the same length as the input, every input id exactly once.")


# ---------------- build ----------------
def load_old_panel(months):
    import r1_common as C
    by = C.load_original_panel()
    out = []
    for ym in months:
        for r in by[ym]:
            out.append(("old", r))
    return out


def load_new_panel(months):
    out = []
    for ym in months:
        p = os.path.join(HERE, "bodies", "bodies_%s.json" % ym)
        for r in rj(p):
            out.append(("new", r))
    return out


def stage_build(a):
    months = a.months.split(",")
    items = load_old_panel(months) + load_new_panel(months)
    tagdir = os.path.join(RUN, a.tag)
    os.makedirs(tagdir, exist_ok=True)
    # 同一题号可能同在新旧面板（随机抽中原前100）：各算一条独立记录，不去重，但映射表里记 dup
    N = len(items)
    pool = ["T%04d" % i for i in range(1, N + 1)]
    random.Random(SEED).shuffle(pool)
    order = list(range(N))
    random.Random(SEED + 1).shuffle(order)
    tokmap = {}
    rows_by_idx = {}
    for k, idx in enumerate(range(N)):
        panel, r = items[idx]
        tok = pool[k]
        tokmap[tok] = {"panel": panel, "question_id": int(r["question_id"]), "ym": r["ym"]}
        rows_by_idx[idx] = {"id": tok, "title": r["title"], "tags": r["tags"], "body": r["body_excerpt"]}
    batches = [order[i:i + BS] for i in range(0, N, BS)]
    reqs, meta = [], []
    for bi, b in enumerate(batches, 1):
        rows = [rows_by_idx[i] for i in b]
        if any(set(r) != {"id", "title", "tags", "body"} for r in rows):
            raise SystemExit("批内字段越界")
        prompt = build_prompt(rows)
        for bad in ("creation_date", "2022-09", "2024-06", "panel", "old", "ChatGPT"):
            pass
        cid = "%s_b%02d" % (a.tag, bi)
        reqs.append({"custom_id": cid, "params": {"model": MODEL, "max_tokens": MAX_TOKENS,
                                                  "messages": [{"role": "user", "content": prompt}]}})
        meta.append({"custom_id": cid, "n": len(rows), "ids": [r["id"] for r in rows],
                     "prompt_chars": len(prompt), "n_panels": dict(Counter(tokmap[r["id"]]["panel"] for r in rows))})
    with io.open(os.path.join(tagdir, "requests.jsonl"), "w", encoding="utf-8") as f:
        for r in reqs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    wj(os.path.join(tagdir, "batches_meta.json"), {"tag": a.tag, "model": MODEL, "months": months, "n": N,
                                                   "seed": SEED, "batch_size": BS, "max_tokens": MAX_TOKENS,
                                                   "template_sha12": TEMPLATE_SHA12, "batches": meta,
                                                   "script_sha12": sha12(io.open(os.path.abspath(__file__), "rb").read())}, indent=1)
    wj(os.path.join(PRIV, "panel_map_%s.json" % a.tag), tokmap)
    print("build: tag=%s N=%d batches=%d sizes=%s" % (a.tag, N, len(batches), [m["n"] for m in meta]))
    print("每批面板构成(私有表，不进提示词):", [m["n_panels"] for m in meta])
    return reqs, meta


# ---------------- API ----------------
def key():
    k = os.environ.get("ANTHROPIC_API_KEY")
    if not k:
        print("!! 环境变量 ANTHROPIC_API_KEY 未设置，停止。")
        sys.exit(4)
    return k


def call(method, url, body=None, raw=False):
    hdr = {"x-api-key": key(), "anthropic-version": VER, "content-type": "application/json"}
    data = json.dumps(body).encode("utf-8") if body is not None else None
    for attempt in range(5):
        req = urllib.request.Request(url, data=data, headers=hdr, method=method)
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                b = r.read()
                return (b if raw else json.loads(b.decode("utf-8"))), dict(r.headers)
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:400]
            if e.code in (429, 500, 502, 503, 529) and attempt < 4:
                time.sleep(5 * (attempt + 1))
                continue
            raise SystemExit("HTTP %s: %s" % (e.code, msg))
        except (urllib.error.URLError, TimeoutError):
            time.sleep(5 * (attempt + 1))
    raise SystemExit("network failure")


def ledger_path(tag):
    return os.path.join(RUN, tag, "ledger.json")


def stage_submit(a):
    tagdir = os.path.join(RUN, a.tag)
    lp = ledger_path(a.tag)
    led = rj(lp) if os.path.exists(lp) else {"submitted": []}
    if led["submitted"] and not a.force:
        raise SystemExit("台账显示 tag=%s 已提交过 %s，拒绝重复提交" % (a.tag, [s["batch_id"] for s in led["submitted"]]))
    # 查 API 上在途批次
    lst, _ = call("GET", API + "?limit=100")
    busy = [b["id"] for b in lst.get("data", []) if b.get("processing_status") == "in_progress"]
    if busy and not a.force:
        raise SystemExit("API 上有在途批次 %s，拒绝提交（确认无关后加 --force）" % busy)
    reqs = [json.loads(l) for l in io.open(os.path.join(tagdir, "requests.jsonl"), encoding="utf-8")]
    res, hdr = call("POST", API, {"requests": reqs})
    led["submitted"].append({"batch_id": res["id"], "submit_request_id": hdr.get("request-id") or hdr.get("Request-Id"),
                             "t": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "n_requests": len(reqs)})
    wj(lp, led, indent=1)
    print("submitted batch", res["id"], "status", res.get("processing_status"))


def parse_array(text):
    s = text.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s)
    i, j = s.find("["), s.rfind("]")
    return json.loads(s[i:j + 1])


def validate(rows, ids):
    errs = []
    if not isinstance(rows, list):
        return ["not a list"]
    got = Counter(r.get("id") for r in rows if isinstance(r, dict))
    miss = [i for i in ids if got[i] != 1]
    extra = [i for i in got if i not in set(ids)]
    if miss:
        errs.append("ids not exactly once: %d" % len(miss))
    if extra:
        errs.append("unknown ids: %d" % len(extra))
    for r in rows:
        if not isinstance(r, dict):
            errs.append("non-dict element")
            continue
        if r.get("score") not in (0, 1, 2, 3, 4):
            errs.append("bad score %r" % r.get("id"))
        elif r.get("label") != ("GEN" if r["score"] >= 3 else "VER"):
            errs.append("label/score mismatch %r" % r.get("id"))
    return errs


def stage_collect(a):
    tagdir = os.path.join(RUN, a.tag)
    led = rj(ledger_path(a.tag))
    meta = rj(os.path.join(tagdir, "batches_meta.json"))
    ids_by_cid = {m["custom_id"]: m["ids"] for m in meta["batches"]}
    resp_path = os.path.join(tagdir, "responses.jsonl")
    done = set()
    if os.path.exists(resp_path):
        done = {json.loads(l)["custom_id"] for l in io.open(resp_path, encoding="utf-8") if l.strip()}
    labels = rj(os.path.join(tagdir, "labels.json")) if os.path.exists(os.path.join(tagdir, "labels.json")) else {}
    failed = []
    for sb in led["submitted"]:
        while True:
            st, _ = call("GET", API + "/" + sb["batch_id"])
            print("batch", sb["batch_id"], st.get("processing_status"), st.get("request_counts"))
            if st.get("processing_status") == "ended":
                break
            if not a.wait:
                print("尚未结束，稍后再 collect")
                return
            time.sleep(60)
        body, hdr = call("GET", st["results_url"], raw=True)
        for l in body.decode("utf-8").split("\n"):
            if not l.strip():
                continue
            o = json.loads(l)
            cid = o["custom_id"]
            if cid in done:
                continue
            rec = {"custom_id": cid, "batch_id": sb["batch_id"], "result_type": o["result"]["type"],
                   "results_download_request_id": hdr.get("request-id") or hdr.get("Request-Id")}
            ids = ids_by_cid.get(cid) or ids_by_cid.get(cid.split("_retry")[0], [])
            errs = ["result type " + o["result"]["type"]]
            if o["result"]["type"] == "succeeded":
                m = o["result"]["message"]
                rec.update({"message_id": m.get("id"), "model": m.get("model"), "usage": m.get("usage"),
                            "stop_reason": m.get("stop_reason")})
                txt = "".join(c.get("text", "") for c in m["content"] if c.get("type") == "text")
                try:
                    rows = parse_array(txt)
                    errs = validate(rows, ids)
                except Exception as e:
                    rows, errs = [], ["parse error: %s" % str(e)[:100]]
                if not errs:
                    for r in rows:
                        labels[r["id"]] = {"score": r["score"], "label": r["label"], "why": r.get("why", ""), "custom_id": cid}
                else:
                    rec["raw_text"] = txt[:20000]
            rec["errors"] = errs
            with io.open(resp_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if errs:
                failed.append(cid)
    wj(os.path.join(tagdir, "labels.json"), labels)
    allids = [i for m in meta["batches"] for i in m["ids"]]
    missing = [i for i in allids if i not in labels]
    wj(os.path.join(tagdir, "failed_ids.json"), missing)
    print("collect: labels=%d missing=%d failed_requests=%s" % (len(labels), len(missing), failed))


def stage_retry(a):
    tagdir = os.path.join(RUN, a.tag)
    missing = rj(os.path.join(tagdir, "failed_ids.json"))
    if not missing:
        print("无失败题")
        return
    reqs = [json.loads(l) for l in io.open(os.path.join(tagdir, "requests.jsonl"), encoding="utf-8")]
    meta = rj(os.path.join(tagdir, "batches_meta.json"))
    # 取原请求提示词里的批 JSON，筛出失败题，重建（每个失败批次一个重试请求）
    out = []
    for r, m in zip(reqs, meta["batches"]):
        mis = [i for i in m["ids"] if i in set(missing)]
        if not mis:
            continue
        txt = r["params"]["messages"][0]["content"]
        bj = json.loads(txt[txt.index("<batch>\n") + 8:txt.index("\n</batch>")])
        rows = [x for x in bj if x["id"] in set(mis)]
        n = sum(1 for x in meta["batches"] if x["custom_id"].startswith(m["custom_id"] + "_retry"))
        cid = "%s_retry%d" % (m["custom_id"], n + 1)
        out.append({"custom_id": cid, "params": {"model": MODEL, "max_tokens": MAX_TOKENS,
                                                 "messages": [{"role": "user", "content": build_prompt(rows)}]}})
        meta["batches"].append({"custom_id": cid, "n": len(rows), "ids": [x["id"] for x in rows], "retry_of": m["custom_id"]})
    wj(os.path.join(tagdir, "batches_meta.json"), meta, indent=1)
    with io.open(os.path.join(tagdir, "retry_log.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps({"t": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "n_failed_ids": len(missing), "retry_requests": [o["custom_id"] for o in out]}) + "\n")
    res, hdr = call("POST", API, {"requests": out})
    led = rj(ledger_path(a.tag))
    led["submitted"].append({"batch_id": res["id"], "submit_request_id": hdr.get("request-id") or hdr.get("Request-Id"),
                             "t": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                             "n_requests": len(out), "retry": True})
    wj(ledger_path(a.tag), led, indent=1)
    print("retry submitted", res["id"], [o["custom_id"] for o in out])


# ---------------- analyze ----------------
def wkappa(pairs, k=5, power=1):
    n = len(pairs)
    O = [[0] * k for _ in range(k)]
    for a, b in pairs:
        O[a][b] += 1
    r = [sum(O[i]) for i in range(k)]
    c = [sum(O[i][j] for i in range(k)) for j in range(k)]
    num = den = 0.0
    for i in range(k):
        for j in range(k):
            w = (abs(i - j) / (k - 1)) ** power
            num += w * O[i][j]
            den += w * r[i] * c[j] / n
    return 1 - num / den if den else float("nan"), O


def load_pub():
    pub = {}
    for r in csv.DictReader(io.open(PUB_BLIND, encoding="utf-8-sig")):
        pub[int(r["question_id"])] = int(r["score"])
    early = {}
    for p in PUB_EARLY:
        for r in csv.DictReader(io.open(p, encoding="utf-8-sig")):
            early[int(r["question_id"])] = int(r["score"])
    return pub, early


def stage_analyze(a):
    tagdir = os.path.join(RUN, a.tag)
    labels = rj(os.path.join(tagdir, "labels.json"))
    tokmap = rj(os.path.join(PRIV, "panel_map_%s.json" % a.tag))
    pub, early = load_pub()
    resp = [json.loads(l) for l in io.open(os.path.join(tagdir, "responses.jsonl"), encoding="utf-8") if l.strip()]
    print("=== RESULTS ===")
    models = Counter(r.get("model") for r in resp)
    print("response models:", dict(models), " n_responses:", len(resp))
    ut = Counter()
    for r in resp:
        for k, v in (r.get("usage") or {}).items():
            if isinstance(v, int):
                ut[k] += v
    print("usage totals:", dict(ut))
    ui, uo = ut.get("input_tokens", 0) + ut.get("cache_creation_input_tokens", 0) + ut.get("cache_read_input_tokens", 0), ut.get("output_tokens", 0)
    n_all = len(tokmap)
    n_ok = len(labels)
    print("n_items=%d labelled=%d" % (n_all, n_ok))
    for std, sd in ((1.0, "standard"), (0.5, "batch(50%)")):
        c = (ui * 2 + uo * 10) / 1e6 * std
        print("cost this trial %s = $%.4f" % (sd, c))
    # 全量外推：6000×2 题 = 100 批；按每题 token 线性外推
    per_q_in, per_q_out = ui / max(n_ok, 1), uo / max(n_ok, 1)
    full_n = 12000
    cf = (per_q_in * full_n * 2 + per_q_out * full_n * 10) / 1e6
    print("per-question tokens in/out = %.1f / %.1f; full 12,000 questions: standard $%.2f, batch $%.2f"
          % (per_q_in, per_q_out, cf, cf / 2))
    # 路径校准：旧面板
    for name, ref in (("published blind (R2, claude-sonnet-5 subagents)", pub), ("earlier classification (Sonnet 4.6)", early)):
        pairs, agree_b = [], []
        for tok, mp in tokmap.items():
            if mp["panel"] != "old" or tok not in labels or mp["question_id"] not in ref:
                continue
            pairs.append((ref[mp["question_id"]], labels[tok]["score"]))
        if not pairs:
            continue
        n = len(pairs)
        ex = sum(1 for x, y in pairs if x == y) / n
        bi = sum(1 for x, y in pairs if (x >= 3) == (y >= 3)) / n
        k1, O = wkappa(pairs, power=1)
        k2, _ = wkappa(pairs, power=2)
        print("PATH CALIBRATION old panel vs %s: n=%d exact_agree=%.4f binary(GEN>=3)_agree=%.4f linear_wkappa=%.4f quadratic_wkappa=%.4f"
              % (name, n, ex, bi, k1, k2))
        print("  confusion rows=published 0..4, cols=API 0..4:")
        for i in range(5):
            print("   ", i, O[i])
    # 分布
    for panel in ("old", "new"):
        sc = Counter(labels[t]["score"] for t, m in tokmap.items() if m["panel"] == panel and t in labels)
        n = sum(sc.values())
        print("API score distribution %s panel (n=%d):" % (panel, n), {k: sc[k] for k in range(5)},
              {k: round(sc[k] / n, 3) for k in range(5)} if n else "")
        gen = sum(v for k, v in sc.items() if k >= 3)
        print("  GEN share %s = %.3f" % (panel, gen / n if n else float("nan")))
    for panel in ("old", "new"):
        by = defaultdict(Counter)
        for t, m in tokmap.items():
            if m["panel"] == panel and t in labels:
                by[m["ym"]][labels[t]["score"]] += 1
        for ym, c in sorted(by.items()):
            print("  %s %s:" % (panel, ym), {k: c[k] for k in range(5)})
    print("=== END RESULTS ===")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["build", "dryrun", "submit", "collect", "retry", "analyze"])
    ap.add_argument("--tag", default="trial400")
    ap.add_argument("--months", default="2022-09,2024-06")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--wait", action="store_true")
    a = ap.parse_args()
    if a.stage in ("build", "dryrun"):
        reqs, meta = stage_build(a)
        if a.stage == "dryrun":
            r0 = reqs[0]["params"]["messages"][0]["content"]
            print("prompt chars b01 =", len(r0), "total request bytes =", sum(len(json.dumps(r)) for r in reqs))
            print(r0[:700].replace("\n", "\\n"))
            print("..." + r0[-900:].replace("\n", "\\n"))
    elif a.stage == "submit":
        stage_submit(a)
    elif a.stage == "collect":
        stage_collect(a)
    elif a.stage == "retry":
        stage_retry(a)
    elif a.stage == "analyze":
        stage_analyze(a)


if __name__ == "__main__":
    main()
