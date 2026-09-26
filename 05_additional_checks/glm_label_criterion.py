# -*- coding: utf-8 -*-
"""Phase 1.4(a) addendum — GLM labels the 320 criterion-validity questions.

Why this run exists. The cross-family check produced a result that needs
adjudicating: GLM-4.6 and Claude agree well on the binary construct
(kappa = 0.695, ABOVE the paper's same-family Opus rater at 0.65) and track the
human consensus standard equally well (0.523 vs 0.512), yet the dose-response
estimated on GLM's labels is a stable ~62% of the one estimated on Claude's
labels, in every parameterisation (binary, z-scored, per-point). Equal agreement
with humans cannot say whose labels carry less error with respect to the
construct that actually drives behaviour.

The criterion sample settles it: it is the one place where labels can be scored
against something external — whether a model can in fact answer the question.
Those 320 questions are disjoint from the classified panel (seed 20260726), so
GLM has never seen them. Labelling them lets us run the SAME criterion test on
GLM's labels as the paper ran on Claude's, and compare rho / solve-rate gradients
directly on identical questions and identical answer attempts.

Output: glm_relabel/criterion_labels_<model>.jsonl  ({qid, score, label, why})
Resumable; same rubric, same date-blind inputs, same batch size as glm_run.py.

Usage:  python glm_label_criterion.py [--model glm-4.6] [--workers 3]
"""
import os, sys, json, argparse, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import importlib.util

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HERE = os.path.dirname(os.path.abspath(__file__))
CRIT = r"E:\智能体论文\P9_金标准_20260704\criterion"

spec = importlib.util.spec_from_file_location("glm_run", os.path.join(HERE, "glm_run.py"))
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)

_lock = threading.Lock()


def main(model, workers, batch_size=20):
    out_path = os.path.join(HERE, "glm_relabel", f"criterion_labels_{model}.jsonl")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    done = set()
    if os.path.exists(out_path):
        for line in open(out_path, encoding="utf-8"):
            try:
                done.add(int(json.loads(line)["question_id"]))
            except Exception:
                pass
    sample = json.load(open(os.path.join(CRIT, "criterion_sample_v2.json"), encoding="utf-8"))
    # same field shape the rubric prompt expects; NO sub_score, NO date
    qs = [{"question_id": int(r["qid"]), "title": r["title"], "tags": r.get("tags", ""),
           "body_excerpt": r["q_body"][:1400]} for r in sample if int(r["qid"]) not in done]
    print(f"criterion labelling model={model}: total {len(sample)}, done {len(done)}, to do {len(qs)}")
    batches = [qs[i:i + batch_size] for i in range(0, len(qs), batch_size)]

    def run(batch):
        user = (G.RUBRIC + "\n\n---\n\n以下是本批问题（JSON 数组）。按 rubric 给每题打分，只输出一个 JSON 数组，不要任何其他文字：\n\n"
                + json.dumps(batch, ensure_ascii=False))
        content, usage = G.chat(model, [{"role": "user", "content": user}], temperature=0, max_tokens=12000)
        rows = G.parse_json_array(content)
        ids = {q["question_id"] for q in batch}
        good = []
        for r in rows:
            try:
                qid = int(r["question_id"]); s = int(r["score"])
                if qid in ids and 0 <= s <= 4:
                    good.append({"question_id": qid, "score": s, "label": "GEN" if s >= 3 else "VER",
                                 "why": str(r.get("why", ""))[:200], "model": model})
            except Exception:
                continue
        return good

    n = 0
    with ThreadPoolExecutor(max_workers=workers) as ex, open(out_path, "a", encoding="utf-8") as f:
        for i, fut in enumerate(as_completed([ex.submit(run, b) for b in batches])):
            try:
                good = fut.result()
            except Exception as e:
                print(f"  [batch failed] {e}"); continue
            with _lock:
                for r in good:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
                f.flush(); n += len(good)
            print(f"  {i+1}/{len(batches)} batches, {n} labels", flush=True)
    print(f"done → {out_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="glm-4.6")
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    main(a.model, a.workers)
