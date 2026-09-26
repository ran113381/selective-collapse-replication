# -*- coding: utf-8 -*-
"""Phase 1.4 addendum — GLM-5.3 (Zhipu's frontier tier) for two specific roles.

Motivated by an obvious design question: "why not the most advanced model?"
The two roles need different answers, and the pilot data say so:

  answer  : GLM-5.3 answers the 320 criterion questions. THIS IS THE ONE THAT
            MATTERS. GLM-4.6 with thinking disabled solved 56.2%, landing in the
            weak tier next to Haiku 4.5 (53.1%; both are pilot figures, and the
            reported rates are in Table 4 of the manuscript), so the design matrix's
            "strong non-Claude" cell is still empty. GLM-5.3 cannot disable
            thinking (error 1210), which is exactly why it should land higher.
            Pilot: 454 in / 1265 out per question, 142-174 word answers.
            Output: criterion/batches_glm53/answer_out_<k>.json

  gold    : GLM-5.3 re-scores the 300 human-gold questions against the rubric.
            NOT expected to improve agreement — a 20-question pilot gave
            GLM-5.3 binary 18/20, exact 14/20 versus GLM-4.6's 19/20, 14/20,
            at 2.3x the output tokens and 2.5x the wall time. The point is to
            be able to say so with evidence: the agreement ceiling is the
            rubric's contested 2-vs-3 boundary (the two HUMAN coders agree at
            only kappa = 0.533 with each other), not model capability.
            Output: glm_relabel/gold_labels_glm-5.3.jsonl

Both resumable. Usage:
  python glm53_runs.py answer [--workers 3]
  python glm53_runs.py gold   [--workers 3]
"""
import os, sys, json, re, argparse, threading, glob
from concurrent.futures import ThreadPoolExecutor, as_completed
import importlib.util

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HERE = os.path.dirname(os.path.abspath(__file__))
CRIT = r"E:\智能体论文\P9_金标准_20260704\criterion"
GOLD = r"E:\智能体论文\P9_金标准_20260704"
MODEL = "glm-5.3"

spec = importlib.util.spec_from_file_location("glm_run", os.path.join(HERE, "glm_run.py"))
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)
_lock = threading.Lock()

INSTR = ("You are an expert Python engineer answering Stack Overflow questions.\n\n"
         "Write the answer you would post for the question below, using ONLY its title and body. "
         "You have no other context: no comments, no accepted answer, no follow-ups.\n\n"
         "Give a concrete technical answer: identify the likely cause and the fix, with a short code "
         "snippet where useful. Maximum 180 words. If the question cannot be fully answered from its "
         "text alone, say in one sentence what is missing and still give the most likely resolution. "
         "Do not mention that you are an AI. Output only the answer text.\n\n")


def answer(workers):
    out_dir = os.path.join(CRIT, "batches_glm53")
    os.makedirs(out_dir, exist_ok=True)
    for bp in sorted(glob.glob(os.path.join(CRIT, "batches_v2", "answer_batch_*.json")),
                     key=lambda p: int(re.search(r"_(\d+)\.json$", p).group(1))):
        k = int(re.search(r"_(\d+)\.json$", bp).group(1))
        op = os.path.join(out_dir, f"answer_out_{k}.json")
        batch = json.load(open(bp, encoding="utf-8"))
        have = {}
        if os.path.exists(op):
            have = {a["qid"]: a["answer"] for a in json.load(open(op, encoding="utf-8")) if str(a.get("answer", "")).strip()}
        todo = [q for q in batch if q["qid"] not in have]
        if not todo:
            print(f"batch {k}: complete ({len(have)})"); continue

        def run(q):
            # thinking stays ENABLED: GLM-5.3 cannot disable it, and max_tokens must
            # leave room for ~1100 reasoning tokens or content comes back empty.
            c, u = G.chat(MODEL, [{"role": "user", "content": INSTR + f"Title: {q['title']}\n\nBody:\n{q['q_body'][:6000]}"}],
                          temperature=0.2, max_tokens=4000, effort="low")
            return q["qid"], c.strip()

        with ThreadPoolExecutor(max_workers=workers) as ex:
            for fut in as_completed([ex.submit(run, q) for q in todo]):
                try:
                    qid, ans = fut.result()
                except Exception as e:
                    print(f"  [item failed] {str(e)[:80]}"); continue
                if ans:
                    have[qid] = ans
        json.dump([{"qid": q["qid"], "answer": have[q["qid"]]} for q in batch if q["qid"] in have],
                  open(op, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"batch {k}: {sum(1 for q in batch if q['qid'] in have)}/{len(batch)} → {op}", flush=True)
    print("answer done")


def gold(workers, batch_size=20):
    out_path = os.path.join(HERE, "glm_relabel", f"gold_labels_{MODEL}.jsonl")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    done = set()
    if os.path.exists(out_path):
        for line in open(out_path, encoding="utf-8"):
            try:
                done.add(int(json.loads(line)["question_id"]))
            except Exception:
                pass
    gs = json.load(open(os.path.join(GOLD, "gold_sample.json"), encoding="utf-8"))
    qs = [{"question_id": int(r["question_id"]), "title": r["title"], "tags": r.get("tags", []),
           "body_excerpt": r.get("body_excerpt", "")} for r in gs if int(r["question_id"]) not in done]
    print(f"gold labelling {MODEL}: total {len(gs)}, done {len(done)}, to do {len(qs)}")
    batches = [qs[i:i + batch_size] for i in range(0, len(qs), batch_size)]

    def run(batch):
        user = (G.RUBRIC + "\n\n---\n\n以下是本批问题（JSON 数组）。按 rubric 给每题打分，只输出一个 JSON 数组，不要任何其他文字：\n\n"
                + json.dumps(batch, ensure_ascii=False))
        c, u = G.chat(MODEL, [{"role": "user", "content": user}], temperature=0, max_tokens=16000)
        ids = {q["question_id"] for q in batch}
        good = []
        for r in G.parse_json_array(c):
            try:
                qid = int(r["question_id"]); s = int(r["score"])
                if qid in ids and 0 <= s <= 4:
                    good.append({"question_id": qid, "score": s, "label": "GEN" if s >= 3 else "VER",
                                 "why": str(r.get("why", ""))[:200], "model": MODEL})
            except Exception:
                continue
        return good

    n = 0
    with ThreadPoolExecutor(max_workers=workers) as ex, open(out_path, "a", encoding="utf-8") as f:
        for i, fut in enumerate(as_completed([ex.submit(run, b) for b in batches])):
            try:
                good = fut.result()
            except Exception as e:
                print(f"  [batch failed] {str(e)[:80]}"); continue
            with _lock:
                for r in good:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
                f.flush(); n += len(good)
            print(f"  {i+1}/{len(batches)} batches, {n} labels", flush=True)
    print(f"done → {out_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["answer", "gold"])
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    (answer if a.cmd == "answer" else gold)(a.workers)
