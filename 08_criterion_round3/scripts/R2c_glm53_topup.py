# -*- coding: utf-8 -*-
"""R2 C 阶段·GLM-5.3 缺答补跑(设计书第 8、9 条,先登记后执行)。

规则:8 道无答案题按可确定的有效尝试次数补足到 4 次(余额错误那一次不算);参数、指令与客户端取自
R2c_split_and_glm.py(import 其 PARAMS / INSTR / G,指令与第二轮原文的逐字自证在该模块载入时执行);
逐题顺序调用,答出即停;遇余额错误(1113)存盘即停,充值后重跑即从断点续。
产物先落 工作文档\\R2_criterion_topup\\(独立复核进行中不动 R2_criterion\\),之后 merge 并入:
  answer_out_topup.json   补答 {qid, answer}
  topup_attempts.json     逐次记录 {qid, batch, attempt, result, detail, time}
  glm53_run_5_补跑.log     运行日志
  judge_batch_topup.json  补答的评判批(字段与截断同 R2c_build_judge.py,不含可替代性分数与月份)
用法:python R2c_glm53_topup.py run | judge | merge
"""
import importlib.util, io, json, os, shutil, sys, time

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("r2cg", os.path.join(HERE, "R2c_split_and_glm.py"))
M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
C = M.C
P = M.PARAMS["glm53"]
D = os.path.join(C, "batches_glm53")
ST = os.path.join(HERE, "R2_criterion_topup")
os.makedirs(ST, exist_ok=True)
F_ANS, F_ATT = os.path.join(ST, "answer_out_topup.json"), os.path.join(ST, "topup_attempts.json")
F_LOG, F_JB = os.path.join(ST, "glm53_run_5_补跑.log"), os.path.join(ST, "judge_batch_topup.json")
F_JO = os.path.join(ST, "judgment_out_topup.json")
# 各批缺答题可确定的已有有效尝试次数(依据四份运行日志;第 12 批只计可确定的 2 次),见设计书第 5、8 条
PRIOR = {3: 4, 7: 3, 12: 2, 13: 2, 14: 2}
EXPECT_MISSING = {3: 3, 7: 1, 12: 2, 13: 1, 14: 1}
TARGET = 4


def rd(p, default):
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else default


def wr(p, obj):
    json.dump(obj, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def missing():
    out = {}
    for k in range(16):
        batch = json.load(io.open(os.path.join(C, "batches_v3", "answer_batch_%d.json" % k), encoding="utf-8"))
        have = {int(a["qid"]) for a in json.load(io.open(os.path.join(D, "answer_out_%d.json" % k), encoding="utf-8"))
                if str(a.get("answer", "")).strip()}
        m = [q for q in batch if int(q["qid"]) not in have]
        if m:
            out[k] = m
    return out


def run():
    miss = missing()
    assert {k: len(v) for k, v in miss.items()} == EXPECT_MISSING, {k: len(v) for k, v in miss.items()}
    ans = {int(a["qid"]): a["answer"] for a in rd(F_ANS, [])}
    att = rd(F_ATT, [])
    log = io.open(F_LOG, "a", encoding="utf-8")

    def say(s):
        print(s); log.write(s + "\n"); log.flush()

    say("== glm53 补跑 %s(目标:每题 %d 次有效尝试)" % (time.strftime("%Y-%m-%d %H:%M:%S"), TARGET))
    for k in sorted(miss):
        for q in miss[k]:
            qid = int(q["qid"])
            while qid not in ans:
                done = sum(1 for a in att if a["qid"] == qid and a["result"] != "credit_error")
                n = PRIOR[k] + done + 1
                if n > TARGET:
                    break
                kw = dict(temperature=P["temperature"], max_tokens=P["max_tokens"])
                if "thinking" in P: kw["thinking"] = P["thinking"]
                if "effort" in P: kw["effort"] = P["effort"]
                try:
                    c, u = M.G.chat(P["model"], [{"role": "user", "content": M.INSTR + "Title: %s\n\nBody:\n%s" % (q["title"], q["q_body"][:6000])}], **kw)
                    text = c.strip()
                    res, detail = ("answered" if text else "empty"), ""
                except SystemExit as e:              # 客户端对鉴权类错误直接退出:不计一次,停
                    say("  stopped: %s" % str(e)[:120]); return
                except Exception as e:
                    text = ""
                    res = "credit_error" if '"1113"' in str(e) else "error"
                    detail = str(e)[:160]
                att.append(dict(qid=qid, batch=k, attempt=n if res != "credit_error" else None, result=res, detail=detail,
                                time=time.strftime("%Y-%m-%d %H:%M:%S")))
                wr(F_ATT, att)
                say("batch %d qid %d attempt %s -> %s%s" % (k, qid, n if res != "credit_error" else "-", res,
                                                           " (%d chars)" % len(text) if text else (" " + detail[:80] if detail else "")))
                if res == "credit_error":
                    say("glm53 余额不足,存盘停止;充值后重跑本命令即从断点续"); return
                if text:
                    ans[qid] = text
                    wr(F_ANS, [{"qid": x, "answer": ans[x]} for x in sorted(ans)])
    left = sum(len(v) for v in miss.values()) - len(ans)
    say("glm53 补跑结束:补得 %d 题,仍无答案 %d 题" % (len(ans), left))


def judge():
    ans = rd(F_ANS, [])
    assert ans, "没有补答"
    sample = {r["qid"]: r for r in json.load(io.open(os.path.join(C, "criterion_sample_v3.json"), encoding="utf-8"))}
    jb = []
    for a in ans:
        r = sample[int(a["qid"])]
        jb.append({"qid": int(a["qid"]), "question": (r["title"] + "\n\n" + r["q_body"])[:2000],
                   "reference_quality": r["reference_quality"],
                   "reference_answer": (r["reference_answer"][:1600] if r["reference_answer"] else ""),
                   "llm_attempt": str(a["answer"])[:1600]})
    for it in jb:                                   # 防泄漏自检,同 R2c_build_judge.py
        assert set(it) == {"qid", "question", "reference_quality", "reference_answer", "llm_attempt"}
    wr(F_JB, jb)
    print("补答评判批 %d 题 -> %s" % (len(jb), F_JB))


def merge():
    jb = rd(F_JB, None); jo = rd(F_JO, None)
    assert jb and jo, "评判批或评判结果缺"
    assert sorted(int(x["qid"]) for x in jb) == sorted(int(x["qid"]) for x in jo), "评判结果与评判批题号不一致"
    done = set()
    for f in os.listdir(D):
        if f.startswith("judgment_out_") and f != "judgment_out_topup.json":
            done |= {int(a["qid"]) for a in json.load(io.open(os.path.join(D, f), encoding="utf-8"))}
    assert not done & {int(x["qid"]) for x in jo}, "补答题号与已评判题号重复"
    for src, dst in ((F_ANS, D), (F_ATT, D), (F_JB, D), (F_JO, D), (F_LOG, C)):
        tgt = os.path.join(dst, os.path.basename(src))
        assert not os.path.exists(tgt) or open(tgt, "rb").read() == open(src, "rb").read(), "目标已存在且内容不同:" + tgt
        shutil.copy2(src, tgt)
        print("并入", os.path.relpath(tgt, HERE))


if __name__ == "__main__":
    {"run": run, "judge": judge, "merge": merge}[sys.argv[1]]()
