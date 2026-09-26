# -*- coding: utf-8 -*-
"""R2 C 阶段:第三轮效标样本切批 + GLM 两个答题者(脚本调端点)。

切批:与第二轮 split_batches_v2.py 相同——random.Random(9) 打乱、每批 20 题、只给 {qid,title,q_body}。
GLM 答题:逐字沿用第二轮的指令文本与参数(见包内 05_additional_checks/glm_run.py、glm53_runs.py):
  glm-4.6 : temperature 0.2, max_tokens 1000, thinking disabled
  glm-5.3 : temperature 0.2, max_tokens 4000, thinking enabled effort "low"(该模型不能关思考)
可续跑:已有非空答案的题跳过。
用法:python R2c_split_and_glm.py split | glm46 | glm53
"""
import glob, importlib.util, io, json, os, random, re, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HERE = os.path.dirname(os.path.abspath(__file__))
C = os.path.join(HERE, "R2_criterion")
PKG = r"E:\智能体论文\P9b_OSF_复现包_20260920"
spec = importlib.util.spec_from_file_location("glm_run", os.path.join(PKG, "05_additional_checks", "glm_run.py"))
G = importlib.util.module_from_spec(spec); spec.loader.exec_module(G)
INSTR = ("You are an expert Python engineer answering Stack Overflow questions.\n\n"
         "Write the answer you would post for the question below, using ONLY its title and body. "
         "You have no other context: no comments, no accepted answer, no follow-ups.\n\n"
         "Give a concrete technical answer: identify the likely cause and the fix, with a short code "
         "snippet where useful. Maximum 180 words. If the question cannot be fully answered from its "
         "text alone, say in one sentence what is missing and still give the most likely resolution. "
         "Do not mention that you are an AI. Output only the answer text.\n\n")
# 与第二轮原文逐字一致的自证
for src in ("glm53_runs.py",):
    s = io.open(os.path.join(PKG, "05_additional_checks", src), encoding="utf-8").read()
    body = re.search(r'INSTR = \((.*?)\)\n', s, re.S).group(1)
    orig = "".join(eval(x) for x in re.findall(r'"(?:[^"\\]|\\.)*"', body))
    assert orig == INSTR, "指令文本与第二轮不一致"

PARAMS = {"glm46": dict(model="glm-4.6", temperature=0.2, max_tokens=1000, thinking={"type": "disabled"}),
          "glm53": dict(model="glm-5.3", temperature=0.2, max_tokens=4000, effort="low")}


def split():
    d = json.load(io.open(os.path.join(C, "criterion_sample_v3.json"), encoding="utf-8"))
    random.Random(9).shuffle(d)
    os.makedirs(os.path.join(C, "batches_v3"), exist_ok=True)
    for k in range(16):
        part = d[k * 20:(k + 1) * 20]
        json.dump([{"qid": r["qid"], "title": r["title"], "q_body": r["q_body"]} for r in part],
                  io.open(os.path.join(C, "batches_v3", "answer_batch_%d.json" % k), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    assert sum(len(json.load(io.open(p, encoding="utf-8"))) for p in glob.glob(os.path.join(C, "batches_v3", "answer_batch_*.json"))) == 320
    print("16 批 × 20 题已写")


def glm(tag, workers=3):
    P = PARAMS[tag]
    out = os.path.join(C, "batches_" + tag); os.makedirs(out, exist_ok=True)
    for k in range(16):
        batch = json.load(io.open(os.path.join(C, "batches_v3", "answer_batch_%d.json" % k), encoding="utf-8"))
        op = os.path.join(out, "answer_out_%d.json" % k)
        have = {}
        if os.path.exists(op):
            have = {a["qid"]: a["answer"] for a in json.load(io.open(op, encoding="utf-8")) if str(a.get("answer", "")).strip()}
        todo = [q for q in batch if q["qid"] not in have]

        def run(q):
            kw = dict(temperature=P["temperature"], max_tokens=P["max_tokens"])
            if "thinking" in P: kw["thinking"] = P["thinking"]
            if "effort" in P: kw["effort"] = P["effort"]
            c, u = G.chat(P["model"], [{"role": "user", "content": INSTR + "Title: %s\n\nBody:\n%s" % (q["title"], q["q_body"][:6000])}], **kw)
            return q["qid"], c.strip()
        broke = False
        if todo:
            with ThreadPoolExecutor(max_workers=workers) as ex:
                futs = [ex.submit(run, q) for q in todo]
                for fut in as_completed(futs):
                    try:
                        qid, ans = fut.result()
                    except SystemExit as e:
                        print(e); broke = True; break
                    except Exception as e:
                        print("  [item failed] %s" % str(e)[:100])
                        if '"1113"' in str(e):          # 余额不足:存盘后停,不再逐题空重试
                            broke = True
                            for f in futs:
                                f.cancel()
                            break
                        continue
                    if ans:
                        have[qid] = ans
            json.dump([{"qid": q["qid"], "answer": have[q["qid"]]} for q in batch if q["qid"] in have],
                      io.open(op, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("%s batch %d: %d/%d" % (tag, k, sum(1 for q in batch if q["qid"] in have), len(batch)), flush=True)
        if broke:
            print(tag, "stopped early (quota/auth); rerun to resume"); return
    print(tag, "done")


if __name__ == "__main__":
    {"split": split, "glm46": lambda: glm("glm46"), "glm53": lambda: glm("glm53")}[sys.argv[1]]()
