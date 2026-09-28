# -*- coding: utf-8 -*-
"""R2 模型身份核查的产物(设计书第 13、14 条;正文 §4.6「Model identity」、§7.1)。输出 工作文档\\R2m_result.json

A 会话记录核查:第三轮全部评判会话、答题会话,以及 S19 二十个评分会话,逐个读子代理会话记录中 assistant 消息的
  message.model;记下全程单一模型的会话数、换了模型的会话,以及写出产物文件那一回合的模型。
  (会话记录在本机 C:\\Users\\<user>\\.claude\\projects\\ 下,不随包;本脚本与其结果留作工作记录。)
B 评判一致率:09-23 原评判(claude-opus-4-8)对 09-25 Opus 5.5 重评(39 题 × 4)与对 09-25 的 4.8 重判(40 题 × 4)。
C 剔除第 70546406 题的稳健性:共同子样本上各答题者 Spearman 与「第二轮同规格」合并斜率,前后之差。
D S19 剔除对照第 05 批:照 R1d_analyze.py 同一算法,只排除 R1c_labels_batch_05.json。
"""
import glob, io, json, os, re, sys, collections
import numpy as np, pandas as pd, statsmodels.formula.api as smf
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
CDIR = os.path.join(HERE, "R2_criterion")
PROJ = os.environ.get("R2_SESSION_DIR", r"C:\Users\<user>\.claude\projects\<project>")
T = ("sonnet5", "haiku45", "glm46", "glm53")
Q = 70546406
R = {}

# ---- A 会话记录 ----
def sessions(fn):
    uses, res = {}, {}
    for line in io.open(os.path.join(PROJ, fn + ".jsonl"), encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        for x in (r.get("message") or {}).get("content") or []:
            if not isinstance(x, dict):
                continue
            if x.get("type") == "tool_use" and x.get("name") == "Agent":
                uses[x["id"]] = str((x.get("input") or {}).get("description", ""))
            elif x.get("type") == "tool_result":
                t = x.get("content")
                t = " ".join(y.get("text", "") for y in t if isinstance(y, dict)) if isinstance(t, list) else str(t)
                m = re.search(r"agentId:\s*([0-9a-f]{12,})", t)
                if m:
                    res[x.get("tool_use_id")] = m.group(1)
    out = []
    for k, d in uses.items():
        aid = res.get(k)
        fp = os.path.join(PROJ, fn, "subagents", "agent-%s.jsonl" % aid) if aid else ""
        if not (aid and os.path.exists(fp)):
            continue
        ms, writer = collections.Counter(), collections.Counter()
        for line in io.open(fp, encoding="utf-8", errors="replace"):
            rr = json.loads(line); msg = rr.get("message") or {}
            if rr.get("type") == "assistant" and msg.get("model"):
                ms[msg["model"]] += 1
                for x in msg.get("content") or []:
                    if isinstance(x, dict) and x.get("type") == "tool_use":
                        s = json.dumps(x.get("input") or {})
                        if re.search(r"judgment_out|answer_out|labels_batch", s) and (x.get("name") == "Write" or re.search(r"Set-Content|Out-File|WriteAllText|json\.dump|open\(", s)):
                            writer[msg["model"]] += 1
        out.append(dict(desc=d, models=dict(ms), writer=dict(writer)))
    return out

if os.path.isdir(PROJ):
    S = sessions("f30e9490-c79d-4c5c-a765-5ffc3ac87b32") + sessions("567bc5a2-af3f-48aa-9d02-be1ec34b1700")
    judge_orig = [s for s in S if re.match(r"R2c judge \w+ (\d+|swapfix|topup)$", s["desc"])]
    R["judging_sessions_round3"] = dict(n=len(judge_orig), single_opus55=sum(1 for s in judge_orig if list(s["models"]) == ["claude-opus-5-5"]),
                                        switched=[s["desc"] for s in judge_orig if len(s["models"]) > 1])
    R["rejudge_sessions"] = {s["desc"]: s["models"] for s in S if s["desc"].startswith("R2c rejudge")}
    R["judge89b_sessions"] = {s["desc"]: s["models"] for s in S if s["desc"].endswith(" 89b")}
    ans = [s for s in S if re.match(r"R2c (Sonnet5|Haiku45) answer", s["desc"]) or s["desc"].startswith(("R2 blind rating", "R2v date-visible"))]
    R["answer_and_classification_sessions"] = dict(n=len(ans), single_model=sum(1 for s in ans if len(s["models"]) == 1))
    s19 = sessions("75ee7d7d-3992-4b05-94b2-7f07c882888b")
    s19 = [s for s in s19 if s["desc"].startswith("Blind classify")]
    R["s19_rating_sessions"] = dict(n=len(s19), switched={s["desc"]: s for s in s19 if len(s["models"]) > 1})
else:
    print("未设 R2_SESSION_DIR,跳过 A")

# ---- B 评判一致率 ----
b = dict(opus48_vs_opus55=[0, 0], opus48_retest=[0, 0], solved_opus48=0, solved_opus55=0)
for t in T:
    d = os.path.join(CDIR, "batches_" + t)
    o = {int(x["qid"]): x for x in json.load(io.open(os.path.join(d, "_superseded_opus48", "judgment_out_89.json"), encoding="utf-8"))}
    n = {int(x["qid"]): x for x in json.load(io.open(os.path.join(d, "judgment_out_89b.json"), encoding="utf-8"))}
    r2 = {int(x["qid"]): x for x in json.load(io.open(os.path.join(d, "_superseded_opus48", "judgment_out_89_rejudge_20260925.json"), encoding="utf-8"))}
    b["opus48_vs_opus55"][0] += sum(o[q]["answerable"] == n[q]["answerable"] for q in n); b["opus48_vs_opus55"][1] += len(n)
    b["opus48_retest"][0] += sum(o[q]["answerable"] == r2[q]["answerable"] for q in r2); b["opus48_retest"][1] += len(r2)
    b.setdefault("by_answerer_solved_48_to_55", {})[t] = [sum(o[q]["answerable"] for q in n), sum(n[q]["answerable"] for q in n)]
b["opus48_vs_opus55_pct"] = round(100 * b["opus48_vs_opus55"][0] / b["opus48_vs_opus55"][1], 1)
b["opus48_retest_pct"] = round(100 * b["opus48_retest"][0] / b["opus48_retest"][1], 1)
b["opus55_stricter_every_answerer"] = all(v[1] < v[0] for v in b["by_answerer_solved_48_to_55"].values())
R["judging_agreement"] = b

# ---- C 剔除第 70546406 题 ----
Ssamp = pd.DataFrame(json.load(io.open(os.path.join(CDIR, "criterion_sample_v3.json"), encoding="utf-8")))
def load(t):
    fs = glob.glob(os.path.join(CDIR, "batches_" + t, "judgment_out_*.json"))
    J = pd.DataFrame([r for f in fs for r in json.load(io.open(f, encoding="utf-8"))]); J["qid"] = J.qid.astype(int)
    assert J.qid.is_unique, t
    return Ssamp.rename(columns={"sub_score": "s"}).merge(J[["qid", "answerable"]], on="qid")
D = {t: load(t) for t in T}
common = set.intersection(*[set(D[t].qid) for t in T])
FAM = {"sonnet5": ("claude", "strong"), "haiku45": ("claude", "weak"), "glm53": ("glm", "strong"), "glm46": ("glm", "weak")}
def metrics(qs):
    rho = {t: float(stats.spearmanr(D[t][D[t].qid.isin(qs)].s, D[t][D[t].qid.isin(qs)].answerable)[0]) for t in T}
    P = pd.concat([D[t][D[t].qid.isin(qs)].assign(tier=t) for t in T])
    P["family"] = P.tier.map(lambda t: FAM[t][0]); P["cap"] = P.tier.map(lambda t: FAM[t][1])
    m = smf.logit("answerable ~ s + C(family) + C(cap) + s:C(family) + s:C(cap)", P).fit(disp=0, cov_type="cluster", cov_kwds={"groups": P.qid})
    return rho, float(m.params["s"])
r_all, s_all = metrics(common); r_ex, s_ex = metrics(common - {Q})
R["exclude_70546406"] = dict(N=len(common - {Q}), rho={t: round(r_ex[t], 6) for t in T}, pooled_s=round(s_ex, 6),
                             max_abs_change=round(max([abs(r_ex[t] - r_all[t]) for t in T] + [abs(s_ex - s_all)]), 6),
                             bin_of_question=int(Ssamp[Ssamp.qid == Q].sub_score.iloc[0]))

# ---- D S19 剔除对照第 05 批(照 R1d_analyze.py) ----
src = io.open(os.path.join(HERE, "R1d_analyze.py"), encoding="utf-8").read()
src = src.replace('for f in sorted(glob.glob(os.path.join(HERE, "R1c_labels_batch_*.json"))):',
                  'for f in [g for g in sorted(glob.glob(os.path.join(HERE, "R1c_labels_batch_*.json"))) if not g.endswith("R1c_labels_batch_05.json")]:')
src = src.replace('os.path.join(HERE, "R1d_month_compare.csv")', 'os.path.join(HERE, "R2m_s19_excl05_month_compare.csv")').replace('os.path.join(HERE, "R1d_result.json")', 'os.path.join(HERE, "R2m_s19_excl05.json")')
assert "R1c_labels_batch_05.json" in src and "R2m_s19_excl05.json" in src
ns = {"__file__": os.path.join(HERE, "R1d_analyze.py"), "__name__": "r2m"}
import contextlib
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(src, "R1d_excl05", "exec"), ns); ns["main"]()
ex = json.load(io.open(os.path.join(HERE, "R2m_s19_excl05.json"), encoding="utf-8"))
full = json.load(io.open(os.path.join(HERE, "R1d_result.json"), encoding="utf-8"))
R["s19_excl_batch05"] = dict(excluded=ex, full=full, batch05_n=int(full["n_orig"] - ex["n_orig"]) if "n_orig" in full else None)
R["exclude_70546406"]["reported_bound"] = 0.005
assert R["exclude_70546406"]["max_abs_change"] < R["exclude_70546406"]["reported_bound"]
io.open(os.path.join(HERE, "R2m_result.json"), "w", encoding="utf-8").write(json.dumps(R, indent=1, ensure_ascii=False, default=str))
print(json.dumps({k: (v if k != "s19_excl_batch05" else "见文件") for k, v in R.items()}, ensure_ascii=False, default=str)[:1800])
