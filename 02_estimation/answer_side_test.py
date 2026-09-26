# -*- coding: utf-8 -*-
"""C1 裁决性检验:验证者(回答者)侧是否崩塌?
柠檬崩溃预测:验证者退出 -> 存活问题(尤其判断密集 s1/s2)的回答率/回答量下降。
需求替代预测:提问端构成变化,但回答端能力完好 -> 答案率不随 score×post 系统性下滑。
设计:与主剂量反应同构的 DiD,结果变量换成 is_answered / answer_count,
月份 FE 吸收共同的答案累积时间差(新问题机械性答案更少的偏误)。"""
import json, csv, os
import numpy as np, pandas as pd
import statsmodels.api as sm

DATA = r"C:\Users\<user>\AppData\Local\Temp\claude\E-------\77fae8c6-f490-4ed9-96cb-fd023fd3807e\scratchpad\P9\P9_验证经济学_迁移包_20260629\P9_code\legB\data"
qs = (json.load(open(os.path.join(DATA,"so_questions_full.json"), encoding="utf-8"))
      + json.load(open(os.path.join(DATA,"so_questions_ext_py.json"), encoding="utf-8")))
lab = {}
for fn in ("question_labels.csv","question_labels_ext_py.csv"):
    for r in csv.DictReader(open(os.path.join(DATA,fn), encoding="utf-8")):
        lab[int(r["question_id"])] = int(r["score"])
rows = []
for q in qs:
    s = lab.get(q["question_id"])
    if s is None or s == 0: continue
    rows.append({"qid": q["question_id"], "ym": q["ym"], "score": s,
                 "is_answered": int(bool(q.get("is_answered"))),
                 "answer_count": int(q.get("answer_count") or 0)})
d = pd.DataFrame(rows)
ymi = lambda ym: int(ym[:4])*12 + int(ym[5:7]) - 1
d["t"] = d["ym"].map(ymi); e = ymi("2022-12")
d["post"] = (d["t"] >= e).astype(int)
d["dose"] = d["score"] * d["post"]
print(f"N = {len(d):,} python questions, {d.ym.nunique()} months")

print("\n=== 描述:各档 回答率 / 平均回答数 (pre vs post) ===")
for s in (1,2,3,4):
    pre = d[(d.score==s)&(d.post==0)]; post = d[(d.score==s)&(d.post==1)]
    print(f"  s{s}: is_answered {pre.is_answered.mean():.3f} -> {post.is_answered.mean():.3f}   "
          f"answer_count {pre.answer_count.mean():.2f} -> {post.answer_count.mean():.2f}")

def dose_did(dep, label):
    X = pd.concat([d[["dose"]].astype(float),
                   pd.get_dummies(d["score"], prefix="b", drop_first=True).astype(float),
                   pd.get_dummies(d["ym"], prefix="m", drop_first=True).astype(float)], axis=1)
    X = sm.add_constant(X)
    res = sm.OLS(d[dep].astype(float).to_numpy(), X.to_numpy()).fit(
        cov_type="cluster", cov_kwds={"groups": d["ym"].to_numpy()})
    i = list(X.columns).index("dose")
    print(f"  {label}: score×post = {res.params[i]:+.4f} (SE {res.bse[i]:.4f}, p={res.pvalues[i]:.3f})")
    return res.params[i], res.bse[i]

print("\n=== 回答端剂量反应 DiD(月 FE 吸收答案累积差;按月聚类) ===")
dose_did("is_answered", "回答率   ")
dose_did("answer_count", "回答数   ")

# 判断密集端单独看:s1+s2 的 post 变化(相对 s3+s4)已在 dose 里;再给二元版
d["ver"] = (d.score<=2).astype(int); d["vp"] = d.ver*d.post
X2 = pd.concat([d[["vp","ver"]].astype(float),
                pd.get_dummies(d["ym"], prefix="m", drop_first=True).astype(float)], axis=1)
X2 = sm.add_constant(X2)
r2 = sm.OLS(d["is_answered"].astype(float).to_numpy(), X2.to_numpy()).fit(
    cov_type="cluster", cov_kwds={"groups": d["ym"].to_numpy()})
i2 = list(X2.columns).index("vp")
print(f"  二元(VER×post,回答率): {r2.params[i2]:+.4f} (SE {r2.bse[i2]:.4f}, p={r2.pvalues[i2]:.3f})")

# 排除末6个月(答案累积最不完整)稳健性
d6 = d[d.t <= ymi("2025-11")]
print(f"\n=== 稳健性:剔除最后6个月 (N={len(d6):,}) ===")
for s in (1,4):
    pre = d6[(d6.score==s)&(d6.post==0)]; post = d6[(d6.score==s)&(d6.post==1)]
    print(f"  s{s}: is_answered {pre.is_answered.mean():.3f} -> {post.is_answered.mean():.3f}")
