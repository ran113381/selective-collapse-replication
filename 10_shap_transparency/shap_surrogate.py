# -*- coding: utf-8 -*-
"""SHAP scale-transparency check. Follows 步骤2_SHAP设计说明_20261004.md (pre-registered).
Features, regexes, hyperparameters, folds and criteria are fixed there; nothing is tuned here.
Run with D:\\python3\\python.exe, PYTHONIOENCODING=utf-8.
"""
import os, sys, re, json, csv, glob, hashlib, time, platform
import numpy as np
import pandas as pd
import scipy
import sklearn, lightgbm, shap
from scipy.stats import spearmanr
from sklearn.model_selection import KFold
from sklearn.metrics import roc_auc_score
import lightgbm as lgb

BASE = r"E:\智能体论文\P9b_IPM_20260919\工作文档"
BLIND = os.path.join(BASE, "R2_blind")
OUTD = os.path.join(BASE, "步骤3_SHAP")
DESIGN = os.path.join(BASE, "步骤2_SHAP设计说明_20261004.md")
LOGP = os.path.join(OUTD, "shap_run.log")
SEED = 20261004

_logf = open(LOGP, "w", encoding="utf-8")


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    _logf.write(s + "\n")
    _logf.flush()


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha_arr(a):
    return sha_bytes(np.ascontiguousarray(a).tobytes())


def sha_file(p):
    return sha_bytes(open(p, "rb").read())


# ---------------- guard for the period file (自证 4) ----------------
OOF_DONE = False
YM_OPENED = False


def open_ym_map():
    global YM_OPENED
    assert OOF_DONE, "R2_ym_map.json requested before out-of-fold SHAP finished"
    YM_OPENED = True
    return json.load(open(os.path.join(BLIND, "R2_ym_map.json"), encoding="utf-8"))


# ---------------- 0. design hash ----------------
rec = open(os.path.join(BASE, "步骤2_SHAP设计说明_sha256.txt"), encoding="utf-8").read()
design_hash = sha_file(DESIGN)
assert design_hash in rec, "design-note sha256 does not match the record"
log("design sha256 =", design_hash, "(matches record)")

# ---------------- 1. data ----------------
items = []
for i in range(1, 51):
    items += json.load(open(os.path.join(BLIND, "R2_blind_batch_%02d.json" % i), encoding="utf-8"))
key_sets = {tuple(sorted(d.keys())) for d in items}
log("input records:", len(items), "key sets:", key_sets)
check1 = (len(items) == 6000 and key_sets == {("body", "id", "tags", "title")})

score_by_id = {}
for i in range(1, 51):
    for d in json.load(open(os.path.join(BLIND, "R2_labels_batch_%02d.json" % i), encoding="utf-8")):
        score_by_id[d["id"]] = int(d["score"])   # only id and score are read
assert len(score_by_id) == 6000

tokmap = json.load(open(os.path.join(BLIND, "R2_token_map.json"), encoding="utf-8"))
csv_score = {}
for r in csv.DictReader(open(os.path.join(BLIND, "question_labels_python_blind.csv"), encoding="utf-8")):
    csv_score[int(r["question_id"])] = int(r["score"])   # only question_id and score are read
mism = [t for t in score_by_id if csv_score.get(int(tokmap[t])) != score_by_id[t]]
log("self-check 2: score mismatches vs csv via token map:", len(mism), "of", len(score_by_id))
check2 = (len(mism) == 0 and len(csv_score) >= 6000)

ids = [d["id"] for d in items]
assert len(set(ids)) == 6000 and set(ids) == set(score_by_id)
y = np.array([score_by_id[t] for t in ids], dtype=float)

# ---------------- 2. features ----------------
I = re.IGNORECASE
RX = {
    "F04": r"\b(expected|desired) (output|result)s?\b|\bsample (data|input)\b|\bexample (data|input|output)\b|\binput\s*:|\boutput\s*:",
    "F05": r"\btraceback\b|\berror\b|\bexception\b|\berrno\b|\bstack ?trace\b|\bwarning\b|\bfail(s|ed|ing)?\b",
    "F06": r"\b(windows|linux|ubuntu|macos|mac os|wsl|docker|conda|anaconda|virtualenv|venv|pip|server|production|deploy(ed|ment)?|aws|azure|gcp|kubernetes|vs ?code|pycharm|jupyter|colab|ide)\b",
    "F07": r"\bversion\b|\b(python|pandas|numpy|django|tensorflow|torch|pip)\s?v?\d+(\.\d+)+",
    "F08": r"[A-Za-z]:\\|/(home|usr|var|etc|opt|Users)/|\b[\w\-]+\.(py|csv|json|txt|xlsx?|yaml|yml|toml|ini|cfg|log|db|sqlite)\b",
    "F09": r"\bmy\b",
    "F10": r"\bmy (code|script|program|project|app|application|function|class|model|dataset|dataframe|data|file|server|module)\b|\bhere is my\b|\bbelow is my\b|\bi have the following\b",
    "F11": r"^\s*how (to|do i|can i|do you|would i|should i)\b",
    "F12": r"\b(best (way|practice|approach)|better|recommend(ed)?|should i|which (is|one)|pros and cons|trade-?offs?|efficient(ly)?|performance|optimi[sz]e|faster|slow|scal(e|able|ability))\b",
    "F13": r"\bwhat (is|are|does)\b|\bdifference between\b|\bmeaning of\b|\bpurpose of\b",
    "F14": r"\bwhy\b",
    "F15": r"\b(list|lists|dict|dicts|dictionary|dictionaries|string|strings|tuple|tuples|set|integer|integers|int|float|loop|recursion|regex|sort|sorted|sorting|index|slice|array|arrays)\b",
    "F16": r"\bany (ideas?|suggestions?|advice)\b|\bwhat are (the|my) options\b|\balternatives?\b|\bdesign\b|\barchitecture\b|\bstructure (my|the) (code|project)\b",
    "F17": r"\bi (have )?tried\b|\bi've tried\b|\btried to\b|\battempt(s|ed)?\b|\bdoesn'?t work\b|\bdoes not work\b|\bnot working\b|\bdidn'?t work\b|\bstill (getting|not|doesn)\b|\bno luck\b",
    "F18": r"\bedit\b|\bupdate\b|\bsolved\b|\[edit\]|\[update\]",
    "F03": r"\[CODE\]",
}
CRX = {k: re.compile(v, I) for k, v in RX.items()}


def cnt(k, s):
    return sum(1 for _ in CRX[k].finditer(s))


# meta: id -> (group, display name, direction)
META = {
    "F01": ("P1", "Body length", "-"),
    "F02": ("P1", "Title word count", "0"),
    "F03": ("P1", "Code blocks", "-"),
    "F04": ("P1", "Example input or output terms", "+"),
    "F05": ("P2", "Error or exception terms", "-"),
    "F06": ("P2", "Environment terms", "-"),
    "F07": ("P2", "Version numbers", "-"),
    "F08": ("P2", "Paths or file names", "-"),
    "F09": ("P2", "Density of \u201cmy\u201d", "-"),
    "F10": ("P2", "Reference to own code or project", "-"),
    "F11": ("P3", "\u201cHow to\u201d title", "+"),
    "F12": ("P3", "Judgment or performance terms", "-"),
    "F13": ("P3", "Concept terms", "+"),
    "F14": ("P3", "\u201cWhy\u201d count", "0"),
    "F15": ("P4", "Basic data-structure terms", "+"),
    "F16": ("P4", "Open-ended help terms", "-"),
    "F17": ("P5", "Tried or not working", "-"),
    "F18": ("P5", "Edit or update markers", "-"),
    "F19": ("P5", "Question marks", "0"),
    "F20": ("T", "Number of tags", "0"),
}
# tag dummies: tags other than python occurring >= 120 times in 6,000 questions
from collections import Counter
tc = Counter()
for d in items:
    for t in set(d["tags"]):
        tc[t] += 1
tag_list = sorted([t for t, c in tc.items() if t != "python" and c >= 120], key=lambda t: (-tc[t], t))
log("tags >=120 (excluding python):", [(t, tc[t]) for t in tag_list])
assert len(tag_list) == 9, "expected nine tag dummies by the rule; got %d" % len(tag_list)
for j, t in enumerate(tag_list, 1):
    META["T%02d" % j] = ("T", "Tag: " + t, "0")
FEATS = ["F%02d" % i for i in range(1, 21)] + ["T%02d" % j for j in range(1, 10)]
assert len(FEATS) == 29 and list(META) == FEATS


def feat_row(title, body, tags):
    """Only title, body and tags enter; no id, token or date."""
    T = title + "\n" + body
    nw = max(len(T.split()), 1)
    r = {}
    r["F01"] = len(body)
    r["F02"] = len(title.split())
    r["F03"] = cnt("F03", T)
    for k in ("F04", "F05", "F06", "F07", "F08"):
        r[k] = cnt(k, T)
    r["F09"] = cnt("F09", T) / nw * 100.0
    r["F10"] = cnt("F10", T)
    r["F11"] = 1 if CRX["F11"].match(title) else 0
    for k in ("F12", "F13", "F14", "F15", "F16", "F17", "F18"):
        r[k] = cnt(k, T)
    r["F19"] = T.count("?")
    r["F20"] = len(tags)
    for j, t in enumerate(tag_list, 1):
        r["T%02d" % j] = 1 if t in tags else 0
    return r


X = pd.DataFrame([feat_row(d["title"], d["body"], d["tags"]) for d in items])[FEATS]
Xv = X.values.astype(float)
check3 = (X.shape == (6000, 29) and list(X.columns) == FEATS)
log("feature matrix:", X.shape, "constant columns:", [c for c in FEATS if X[c].nunique() < 2])

# ---------------- 3. model ----------------
HP = dict(objective="regression", n_estimators=400, learning_rate=0.05, num_leaves=15,
          min_child_samples=40, subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
          reg_lambda=1.0, random_state=SEED, n_jobs=1, deterministic=True,
          force_row_wise=True, verbose=-1)


def run_oof(cols):
    Xs = Xv[:, cols]
    oof = np.zeros(len(y))
    sh = np.zeros((len(y), len(cols)))
    kf = KFold(n_splits=5, shuffle=True, random_state=SEED)
    for tr, te in kf.split(Xs):
        m = lgb.LGBMRegressor(**HP)
        m.fit(Xs[tr], y[tr])
        oof[te] = m.predict(Xs[te])
        ex = shap.TreeExplainer(m)
        sh[te] = np.asarray(ex.shap_values(Xs[te]))
    return oof, sh


def criteria(oof, sh, cols):
    names = [FEATS[c] for c in cols]
    gen = (y >= 3).astype(int)
    auc = float(roc_auc_score(gen, oof))
    rho_sp = float(spearmanr(oof, y).correlation)
    ms = np.abs(sh).mean(axis=0)
    total = ms.sum()
    attr = sum(ms[i] for i, n in enumerate(names) if META[n][0] != "T")
    c2 = float(attr / total)
    med = float(np.median(ms))
    rows = []
    for i, n in enumerate(names):
        col = Xv[:, cols[i]]
        if np.std(col) == 0 or np.std(sh[:, i]) == 0:
            rho = float("nan")
        else:
            rho = float(spearmanr(col, sh[:, i]).correlation)
        rows.append(dict(id=n, name=META[n][1], group=META[n][0], expected=META[n][2],
                         mean_abs_shap=float(ms[i]), rho=rho))
    order = np.argsort(-ms, kind="stable")
    for rk, i in enumerate(order, 1):
        rows[i]["rank"] = rk
    sel = 0
    cons = 0
    for r in rows:
        if r["expected"] in ("+", "-"):
            r["selected_c3"] = bool(r["mean_abs_shap"] >= med)
            if not np.isnan(r["rho"]) and r["rho"] != 0:
                sign = "+" if r["rho"] > 0 else "-"
                r["consistent"] = (sign == r["expected"])
            else:
                r["consistent"] = False
            if r["selected_c3"]:
                sel += 1
                cons += int(r["consistent"])
        else:
            r["selected_c3"] = None
            r["consistent"] = None
    gshare = {}
    for g in ("P1", "P2", "P3", "P4", "P5", "T"):
        gshare[g] = float(sum(ms[i] for i, n in enumerate(names) if META[n][0] == g) / total)
    return dict(C1_auc=auc, C1_spearman=rho_sp, C2_attr_share=c2,
                C3_consistent=cons, C3_selected=sel, C3_ratio=(cons / sel if sel else None),
                median_mean_abs_shap=med, group_share=gshare, table=rows), ms


ALL = list(range(29))
log("== pass 1 ==")
t0 = time.time()
oof1, sh1 = run_oof(ALL)
log("pass 1 done in %.1fs" % (time.time() - t0))
log("== pass 2 ==")
oof2, sh2 = run_oof(ALL)
h_oof = (sha_arr(oof1), sha_arr(oof2))
h_sh = (sha_arr(sh1), sha_arr(sh2))
log("oof sha256 pass1/pass2:", h_oof)
log("shap sha256 pass1/pass2:", h_sh)
check5 = (h_oof[0] == h_oof[1] and h_sh[0] == h_sh[1])

OOF_DONE = True   # period file may be opened only after this line

main, ms_main = criteria(oof1, sh1, ALL)
log("C1 AUC = %.4f ; Spearman(pred, score) = %.4f" % (main["C1_auc"], main["C1_spearman"]))
log("C2 attribute share = %.4f" % main["C2_attr_share"])
log("C3 consistent %d / selected %d" % (main["C3_consistent"], main["C3_selected"]))

# R1: drop F01, F02, same folds, same hyperparameters
cols_r1 = [i for i, n in enumerate(FEATS) if n not in ("F01", "F02")]
oof_r1, sh_r1 = run_oof(cols_r1)
r1, _ = criteria(oof_r1, sh_r1, cols_r1)
log("R1 (drop F01,F02): C1 %.4f C2 %.4f C3 %d/%d" % (r1["C1_auc"], r1["C2_attr_share"], r1["C3_consistent"], r1["C3_selected"]))

# S1: pre / post stability (opens the period file; allowed now)
ymmap = open_ym_map()
yms = [ymmap[str(tokmap[t])] for t in ids]   # ym map is keyed by question_id; joined via token map
assert all(re.fullmatch(r"\d{4}-\d{2}", s) for s in yms)
post = np.array([s >= "2022-12" for s in yms])
v_pre = np.abs(sh1[~post]).mean(axis=0)
v_post = np.abs(sh1[post]).mean(axis=0)
s1 = float(spearmanr(v_pre, v_post).correlation)
log("S1 Spearman(pre, post mean|SHAP|) = %.4f ; n_pre=%d n_post=%d" % (s1, int((~post).sum()), int(post.sum())))

# ---------------- 4. self-check 4: static source scan ----------------
src = open(__file__, encoding="utf-8").read()
why_hits = re.findall(r"[\"']why[\"']", src)
check1 = check1 and (len(why_hits) == 0)
check4 = (YM_OPENED and OOF_DONE)  # guard asserts the order at runtime
log("static scan for a why-key literal:", len(why_hits))

# ---------------- 5. outputs ----------------
checks = {
    "1_input_keys_and_no_why_access": bool(check1),
    "2_scores_match_csv_via_tokenmap": bool(check2),
    "3_feature_matrix_29_cols_names_match": bool(check3),
    "4_ym_map_opened_only_after_oof": bool(check4),
    "5_two_pass_hash_identical": bool(check5),
}
log("self-checks:", checks)
for k, v in checks.items():
    if not v:
        log("SELF-CHECK FAILED:", k, "-> stop, no result")
        sys.exit(2)

feature_spec = {"regex_flags": "IGNORECASE", "F11_matched_on": "title only (re.match, leading whitespace ignored)",
                "regex": RX,
                "F01": "len(body)", "F02": "len(title.split())", "F03": "count of [CODE] in title+newline+body",
                "F09": "count(\\bmy\\b) / len(T.split()) * 100", "F19": "T.count('?')", "F20": "len(tags)",
                "tag_dummies": {"T%02d" % j: t for j, t in enumerate(tag_list, 1)},
                "tag_counts": {t: tc[t] for t in tag_list},
                "T": "title + newline + body"}
res = dict(
    design_sha256=design_hash,
    feature_spec=feature_spec,
    display_names={n: "[%s] %s" % (META[n][0], META[n][1]) for n in FEATS},
    group_names={"P1": "Self-containedness", "P2": "Context dependence", "P3": "Judgment vs retrieval",
                 "P4": "Answer uniqueness", "P5": "One-shot vs iterative", "T": "Topic tags"},
    hyperparameters=HP, seed=SEED,
    self_checks=checks,
    C1=dict(value=main["C1_auc"], threshold=0.65, passed=bool(main["C1_auc"] >= 0.65),
            spearman_pred_vs_score=main["C1_spearman"]),
    C2=dict(value=main["C2_attr_share"], threshold=0.50, passed=bool(main["C2_attr_share"] >= 0.50)),
    C3=dict(consistent=main["C3_consistent"], selected=main["C3_selected"], ratio=main["C3_ratio"],
            threshold=2 / 3, passed=bool(main["C3_ratio"] is not None and main["C3_ratio"] >= 2 / 3),
            median_mean_abs_shap_all29=main["median_mean_abs_shap"]),
    group_share=main["group_share"],
    per_feature=sorted(main["table"], key=lambda r: r["rank"]),
    R1=dict(dropped=["F01", "F02"], C1_auc=r1["C1_auc"], C1_spearman=r1["C1_spearman"],
            C2_attr_share=r1["C2_attr_share"], C3_consistent=r1["C3_consistent"],
            C3_selected=r1["C3_selected"], C3_ratio=r1["C3_ratio"],
            median_mean_abs_shap=r1["median_mean_abs_shap"],
            note="C2 denominator = 27 features; C3 median over the 27 remaining features; same folds and hyperparameters"),
    S1=dict(spearman_pre_vs_post=s1, n_pre=int((~post).sum()), n_post=int(post.sum()),
            split="ym < 2022-12 vs >= 2022-12"),
    hashes=dict(oof_pass1=h_oof[0], oof_pass2=h_oof[1], shap_pass1=h_sh[0], shap_pass2=h_sh[1]),
    versions=dict(python=platform.python_version(), lightgbm=lightgbm.__version__, shap=shap.__version__,
                  sklearn=sklearn.__version__, numpy=np.__version__, scipy=scipy.__version__,
                  pandas=pd.__version__),
    deviations="none (design note section 7 untouched)",
    fig_shap_allowed=bool(main["C1_auc"] >= 0.65),
)
json.dump(res, open(os.path.join(OUTD, "shap_result.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
np.savez_compressed(os.path.join(OUTD, "shap_oof.npz"), oof_pred=oof1, shap=sh1, X=Xv,
                    feature_names=np.array(FEATS), tokens=np.array(ids), y=y,
                    oof_pred_r1=oof_r1, shap_r1=sh_r1)
log("wrote shap_result.json and shap_oof.npz")
if not res["fig_shap_allowed"]:
    log("C1 < 0.65: no fig_shap")
