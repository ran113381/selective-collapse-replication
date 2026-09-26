# -*- coding: utf-8 -*-
"""R2 C 阶段:效标样本第三轮(按设计书第四节)。

与第二轮的区别只有抽样与取数的正确性:
  - 分层依据:A 臂盲标签(工作文档\\R2_blind\\question_labels_python_blind.csv),s1–s4 各 80;
  - 候选:python 面板全部 60 个月,排除第一、二轮效标样本;每档以种子 20260926 打乱成固定顺序;
  - 取题:/questions/{ids} 显式 pagesize=100,并断言 has_more 为假、返回题号 ⊆ 请求题号;
    没返回的题 = 已删除/不可见,逐条记录,**按候选顺序跳过、不以返回顺序截满**;
  - 取参考答案:沿用第二轮 fetch_best_answers 的分档口径(accepted > 得票≥1 > 其他 > 无),
    翻页至 has_more 为假,断言没有被页数上限截断。
输出 工作文档\\R2_criterion\\criterion_sample_v3.json(字段与第二轮相同,另加 ym)与取数日志。
"""
import csv, html, io, json, os, random, re, sys, time
import urllib.request, urllib.parse, gzip

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
PKG = r"E:\智能体论文\P9b_OSF_复现包_20260920"
OUT = os.path.join(HERE, "R2_criterion")
CRIT = os.path.join(PKG, "03_validation", "criterion_validity_rounds1_2")
SEED, PER_BIN = 20260926, 80
KEY = os.environ.get("STACK_API_KEY")
TIER_NAME = {3: "accepted", 2: "top_voted", 1: "weak", 0: "none"}
LOG = []


def strip_html(s, cap=1600):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    return re.sub(r"\s+", " ", s).strip()[:cap]


def api(path, params):
    p = dict(params, site="stackoverflow")
    if KEY:
        p["key"] = KEY
    url = "https://api.stackexchange.com/2.3/" + path + "?" + urllib.parse.urlencode(p)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                d = json.loads(raw)
            if d.get("backoff"):
                time.sleep(d["backoff"] + 1)
            LOG.append(dict(path=path.split("/")[0] + "/…/" + path.split("/")[-1] if "/" in path else path,
                            n_ids=path.count(";") + 1, page=p.get("page", 1), items=len(d.get("items", [])),
                            has_more=d.get("has_more"), quota_remaining=d.get("quota_remaining")))
            return d
        except Exception as e:
            print("  重试 %d:%s" % (attempt + 1, e)); time.sleep(5 * (attempt + 1))
    raise SystemExit("API 连续失败,停止(未写任何样本文件)")


def fetch_questions(ids):
    d = api("questions/" + ";".join(map(str, ids)), dict(filter="withbody", pagesize=100))
    assert not d.get("has_more"), "取题分页未取尽"
    got = {it["question_id"]: it for it in d.get("items", [])}
    assert set(got) <= set(ids)
    return got


def fetch_best_answers(ids):
    best, page = {}, 1
    while True:
        d = api("questions/" + ";".join(map(str, ids)) + "/answers",
                dict(filter="withbody", sort="votes", order="desc", pagesize=100, page=page))
        for it in d.get("items", []):
            q, acc, sc = it["question_id"], bool(it.get("is_accepted")), it.get("score", 0)
            tier = 3 if acc else (2 if sc >= 1 else 1)
            cur = best.get(q)
            if cur is None or (tier, sc) > (cur[0], cur[1]):
                best[q] = (tier, sc, strip_html(it.get("body", "")))
        if not d.get("has_more"):
            return best
        page += 1
        assert page <= 20, "答案翻页超过 20 页,异常"
        time.sleep(0.3)


# ---------------------------------------------------------------- 候选
bl = {}
for r in csv.DictReader(io.open(os.path.join(HERE, "R2_blind", "question_labels_python_blind.csv"), encoding="utf-8")):
    bl[int(r["question_id"])] = (int(r["score"]), r["ym"])
used = {int(r["qid"]) for fn in ("criterion_sample.json", "criterion_sample_v2.json")
        for r in json.load(io.open(os.path.join(CRIT, fn), encoding="utf-8"))}
cand = {b: sorted(q for q, (s, _) in bl.items() if s == b and q not in used) for b in (1, 2, 3, 4)}
rng = random.Random(SEED)
for b in (1, 2, 3, 4):
    rng.shuffle(cand[b])
print("候选池(已排除前两轮 %d 题):%s" % (len(used), {b: len(cand[b]) for b in cand}))

# ---------------------------------------------------------------- 按候选顺序逐题取,缺则顺延
kept, skipped = {b: [] for b in (1, 2, 3, 4)}, {b: [] for b in (1, 2, 3, 4)}
qinfo = {}
for b in (1, 2, 3, 4):
    pos = 0
    while len(kept[b]) < PER_BIN:
        need = PER_BIN - len(kept[b])
        chunk = cand[b][pos:pos + min(100, max(need + 20, need))]
        assert chunk, "档 s%d 候选耗尽" % b
        pos += len(chunk)
        got = fetch_questions(chunk)
        qinfo.update(got)
        for q in chunk:                       # 严格按候选顺序
            if len(kept[b]) >= PER_BIN:
                break
            (kept[b] if q in got else skipped[b]).append(q)
        time.sleep(0.3)
    print("s%d:保留 %d,跳过(未返回)%d,用到候选前 %d 个" % (b, len(kept[b]), len(skipped[b]), pos))

allq = [q for b in (1, 2, 3, 4) for q in kept[b]]
best = {}
for i in range(0, len(allq), 100):
    best.update(fetch_best_answers(allq[i:i + 100]))
    time.sleep(0.3)

rows = []
for b in (1, 2, 3, 4):
    for q in kept[b]:
        it = qinfo[q]
        tier, sc, body = best.get(q, (0, 0, ""))
        rows.append(dict(qid=q, sub_score=b, ym=bl[q][1], title=html.unescape(it.get("title", "")),
                         q_body=strip_html(it.get("body", "")), tags=it.get("tags", []),
                         reference_quality=TIER_NAME[tier], reference_answer=body))
assert len(rows) == 4 * PER_BIN and len({r["qid"] for r in rows}) == len(rows)

EV = 2022 * 12 + 11
yr = {}
for r in rows:
    yr[r["ym"][:4]] = yr.get(r["ym"][:4], 0) + 1
pre = sum(1 for r in rows if int(r["ym"][:4]) * 12 + int(r["ym"][5:7]) - 1 < EV)
panel_pre = sum(1 for (s, ym) in bl.values() if 1 <= s <= 4 and int(ym[:4]) * 12 + int(ym[5:7]) - 1 < EV) / \
    sum(1 for (s, ym) in bl.values() if 1 <= s <= 4)
os.makedirs(OUT, exist_ok=True)
io.open(os.path.join(OUT, "criterion_sample_v3.json"), "w", encoding="utf-8").write(json.dumps(rows, ensure_ascii=False, indent=1))
meta = dict(seed=SEED, per_bin=PER_BIN, excluded_prior_rounds=len(used), skipped_not_returned={("s%d" % b): skipped[b] for b in skipped},
            by_year=dict(sorted(yr.items())), pre_period=pre, pre_share=round(pre / len(rows), 3),
            panel_pre_share_s1_s4=round(panel_pre, 3),
            reference_quality={t: sum(1 for r in rows if r["reference_quality"] == t) for t in TIER_NAME.values()},
            api_calls=LOG, key_used=bool(KEY), fetched_on=time.strftime("%Y-%m-%d %H:%M"))
io.open(os.path.join(OUT, "criterion_sample_v3_meta.json"), "w", encoding="utf-8").write(json.dumps(meta, ensure_ascii=False, indent=1))
print("已写 %d 题;年份 %s;事件前 %d 题(%.1f%%,面板 %.1f%%);参考答案档 %s"
      % (len(rows), meta["by_year"], pre, 100 * pre / len(rows), 100 * panel_pre, meta["reference_quality"]))
