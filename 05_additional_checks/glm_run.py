# -*- coding: utf-8 -*-
"""Phase 1.4 — cross-family measurement robustness via Z.ai GLM.

Two sub-commands, both RESUMABLE and safe to re-run:

  relabel  : GLM re-scores all 6,000 python questions against the SAME rubric
             (_legB_data/_validation/CLASSIFY_RUBRIC.md, verbatim) that the
             primary Claude classifier used; same inputs (title + tags +
             body_excerpt, NO creation date). Batches of 20 questions per call,
             temperature 0, thinking effort "low" (GLM-5.x cannot disable
             thinking). Output: glm_relabel/labels_<model>.jsonl
             (one {question_id, score, label, why} per line).

  answer   : GLM answers the 320 criterion-validity questions blind (title +
             body only, <=180 words), one question per call, using the SAME
             instruction text as the Haiku 4.5 run
             (P9_金标准_20260704/criterion/answer_prompt_template.txt) so the
             three answerers (Sonnet 5 = paper, Haiku 4.5, GLM) differ only in
             the model. Output: criterion/batches_glmflash/answer_out_<k>.json
             in the paper's {qid, answer} format so build_judge_batches can be
             reused unchanged.

Usage:
  python glm_run.py relabel [--model glm-5.3] [--workers 4]
  python glm_run.py answer  [--model glm-5.3-flash] [--workers 4]

Key: ZAI_API_KEY (process env, else the Windows user-level env var).
Endpoint: https://api.z.ai/api/paas/v4/chat/completions (OpenAI-compatible).
"""
import os, sys, json, time, re, argparse, subprocess, threading
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

DATA = r"E:\智能体论文\_legB_data"
CRIT = r"E:\智能体论文\P9_金标准_20260704\criterion"
HERE = os.path.dirname(os.path.abspath(__file__))
RELABEL_DIR = os.path.join(HERE, "glm_relabel")
# bigmodel.cn (Zhipu's mainland platform) rather than api.z.ai: the same key
# authenticates on both, but the FREE tier models (glm-4.7-flash / glm-4.5-flash)
# are reliably reachable here at zero balance, whereas api.z.ai returned 1305
# overload for 4.7-flash. Paid models return 1113 on both until the account is
# topped up — not needed, see the smoke test in the revision log.
ENDPOINT = os.environ.get("GLM_ENDPOINT", "https://open.bigmodel.cn/api/paas/v4/chat/completions")
RUBRIC = open(os.path.join(DATA, "_validation", "CLASSIFY_RUBRIC.md"), encoding="utf-8").read()
ANSWER_TEMPLATE = open(os.path.join(CRIT, "answer_prompt_template.txt"), encoding="utf-8").read()
_lock = threading.Lock()


def api_key():
    k = os.environ.get("ZAI_API_KEY")
    if k:
        return k
    try:
        k = subprocess.run(["powershell", "-NoProfile", "-Command",
                            '[Environment]::GetEnvironmentVariable("ZAI_API_KEY","User")'],
                           capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:
        k = ""
    if not k:
        raise SystemExit("ZAI_API_KEY not found in env or Windows user env")
    return k


KEY = None


def chat(model, messages, temperature, max_tokens, effort="low", retries=8, thinking=None):
    """Error codes seen on this platform, all as HTTP 429:
      1113 "余额不足" — NOT reliably fatal: it also fires spuriously under
           concurrency while the account clearly has balance (verified by a
           single call succeeding seconds later). So retry it; only give up
           after every attempt has failed the same way.
      1302 account rate limit, 1305 model overloaded — transient, back off.
    """
    global KEY
    if KEY is None:
        KEY = api_key()
    body = {"model": model, "messages": messages, "temperature": temperature,
            "max_tokens": max_tokens,
            "thinking": thinking if thinking is not None else {"type": "enabled", "effort": effort}}
    last = ""
    for attempt in range(retries):
        req = urllib.request.Request(ENDPOINT, data=json.dumps(body).encode("utf-8"),
                                     headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.load(r)
            msg = d["choices"][0]["message"]
            return msg.get("content") or "", d.get("usage", {})
        except urllib.error.HTTPError as e:
            last = e.read()[:200].decode("utf-8", "ignore")
            transient = any(c in last for c in ("1113", "1302", "1305"))
            time.sleep(min(60, 8 * (attempt + 1)) if transient else 5 * (attempt + 1))
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"API call failed after {retries} retries; last error: {last}")


def parse_json_array(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    try:
        v = json.loads(t)
        return v if isinstance(v, list) else v.get("items") or v.get("results") or [v]
    except Exception:
        m = re.search(r"\[.*\]", t, re.S)
        if m:
            return json.loads(m.group(0))
        raise


# ---------------------------------------------------------------- relabel ----
def load_questions():
    items = []
    for fn in ("so_questions_full.json", "so_questions_ext_py.json"):
        items += json.load(open(os.path.join(DATA, fn), encoding="utf-8"))
    seen, out = set(), []
    for q in items:
        qid = int(q["question_id"])
        if qid in seen:
            continue
        seen.add(qid)
        out.append({"question_id": qid, "title": q.get("title", ""), "tags": q.get("tags", []),
                    "body_excerpt": q.get("body_excerpt", "")})   # NO creation_date / ym: classifier stays date-blind
    return out


def relabel(model, workers, batch_size=20):
    os.makedirs(RELABEL_DIR, exist_ok=True)
    out_path = os.path.join(RELABEL_DIR, f"labels_{model}.jsonl")
    done = set()
    if os.path.exists(out_path):
        for line in open(out_path, encoding="utf-8"):
            try:
                done.add(int(json.loads(line)["question_id"]))
            except Exception:
                pass
    qs = [q for q in load_questions() if q["question_id"] not in done]
    print(f"relabel model={model}: total 6000, done {len(done)}, to do {len(qs)}")
    batches = [qs[i:i + batch_size] for i in range(0, len(qs), batch_size)]
    usage_tot = {"prompt_tokens": 0, "completion_tokens": 0}
    n_written = 0

    def run(batch):
        user = (RUBRIC + "\n\n---\n\n以下是本批问题（JSON 数组）。按 rubric 给每题打分，只输出一个 JSON 数组，不要任何其他文字：\n\n"
                + json.dumps(batch, ensure_ascii=False))
        content, usage = chat(model, [{"role": "user", "content": user}], temperature=0, max_tokens=12000)
        rows = parse_json_array(content)
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
        return good, usage, len(batch)

    with ThreadPoolExecutor(max_workers=workers) as ex, open(out_path, "a", encoding="utf-8") as f:
        futs = [ex.submit(run, b) for b in batches]
        for i, fut in enumerate(as_completed(futs)):
            try:
                good, usage, n = fut.result()
            except SystemExit as e:
                print(e); break
            except Exception as e:
                print(f"  [batch failed] {e}"); continue
            with _lock:
                for r in good:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
                f.flush()
                n_written += len(good)
                for k in usage_tot:
                    usage_tot[k] += usage.get(k, 0)
            if (i + 1) % 10 == 0 or i == len(futs) - 1:
                print(f"  {i+1}/{len(futs)} batches; labels written {n_written}; "
                      f"missing in this batch {n-len(good)}; tokens {usage_tot}", flush=True)
    print(f"done → {out_path}  (re-run to fill any missing ids)")


# ----------------------------------------------------------------- answer ----
def answer(model, workers):
    out_dir = os.path.join(CRIT, "batches_glmflash")
    os.makedirs(out_dir, exist_ok=True)
    # the per-question instruction = the file-level template minus the file I/O sentences
    instr = ("You are an expert Python engineer answering Stack Overflow questions.\n\n"
             "Write the answer you would post for the question below, using ONLY its title and body. "
             "You have no other context: no comments, no accepted answer, no follow-ups.\n\n"
             "Give a concrete technical answer: identify the likely cause and the fix, with a short code "
             "snippet where useful. Maximum 180 words. If the question cannot be fully answered from its "
             "text alone, say in one sentence what is missing and still give the most likely resolution. "
             "Do not mention that you are an AI. Output only the answer text.\n\n")
    import glob
    for bp in sorted(glob.glob(os.path.join(CRIT, "batches_v2", "answer_batch_*.json")),
                     key=lambda p: int(re.search(r"_(\d+)\.json$", p).group(1))):
        k = int(re.search(r"_(\d+)\.json$", bp).group(1))
        op = os.path.join(out_dir, f"answer_out_{k}.json")
        batch = json.load(open(bp, encoding="utf-8"))
        have = {}
        if os.path.exists(op):
            have = {a["qid"]: a["answer"] for a in json.load(open(op, encoding="utf-8"))}
        todo = [q for q in batch if q["qid"] not in have]
        if not todo:
            print(f"batch {k}: complete ({len(have)})"); continue

        def run(q):
            user = instr + f"Title: {q['title']}\n\nBody:\n{q['q_body'][:6000]}"
            # thinking DISABLED: with it on, GLM-4.6 spends the whole completion
            # budget on reasoning tokens and returns an EMPTY content field (verified:
            # max_tokens=700 -> 700 reasoning, 0 words). Disabling also matches how the
            # Sonnet 5 / Haiku 4.5 answerers were called, so the tiers stay comparable.
            content, usage = chat(model, [{"role": "user", "content": user}], temperature=0.2,
                                  max_tokens=1000, thinking={"type": "disabled"})
            return q["qid"], content.strip(), usage

        with ThreadPoolExecutor(max_workers=workers) as ex:
            for fut in as_completed([ex.submit(run, q) for q in todo]):
                try:
                    qid, ans, usage = fut.result()
                except SystemExit as e:
                    print(e); return
                except Exception as e:
                    print(f"  [item failed] {e}"); continue
                have[qid] = ans
        json.dump([{"qid": q["qid"], "answer": have[q["qid"]]} for q in batch if q["qid"] in have],
                  open(op, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"batch {k}: wrote {sum(1 for q in batch if q['qid'] in have)}/{len(batch)} → {op}")
    print("answer done")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["relabel", "answer"])
    ap.add_argument("--model", default=None)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    if a.cmd == "relabel":
        relabel(a.model or "glm-4.7-flash", a.workers)
    else:
        answer(a.model or "glm-4.7-flash", a.workers)
