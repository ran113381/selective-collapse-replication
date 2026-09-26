# -*- coding: utf-8 -*-
"""Sharpened version of the S17 relabelling test, run as independent adjudication (Fable 5.1).

Objection to S17's bound: it assumes a migrant carries its donor bin's closure
rate and answer count into the receiving bin. But the rival's mechanism IS a
text change, and closure and answers respond to text. A polished s4 question
may be closed less and answered less than an unpolished one, so the tracers
are attenuated by the very thing being tested.

Partial fix: condition on length. The rival says migrants are the LONG
questions in the receiving bin (polishing adds context). So compare long-s1
questions after the event to long-s1 questions before it. Under migration the
post group contains former-s4 questions and should show higher closure and
answers than the pre group AT THE SAME LENGTH. Under exit both groups are just
long s1 questions. Holding length fixed removes the crudest form of tracer
attenuation, though not all of it.
"""
import os, sys, json, math
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
import warnings; warnings.simplefilter("ignore")
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
DATA=r"E:\智能体论文\_legB_data"; HERE=os.path.dirname(os.path.abspath(__file__))
def ym_int(y): a,b=y.split("-"); return int(a)*12+int(b)-1
EVENT=ym_int("2022-12"); WINDOW=90
lab=pd.read_csv(os.path.join(DATA,"question_labels.csv")).rename(columns={"score":"s"})
clo=pd.read_csv(os.path.join(HERE,"closure_meta.csv")).rename(columns={"score":"so_score"})
own=pd.read_csv(os.path.join(HERE,"asker_owner.csv")).drop_duplicates("question_id")[["question_id","q_creation"]]
d=lab.merge(clo,on="question_id",how="left").merge(own,on="question_id",how="left")
d["mi"]=d.ym.map(ym_int); d["post"]=(d.mi>=EVENT).astype(int)
d["dup"]=((d.closed_reason=="Duplicate")&((d.closed_date-d.q_creation)/86400<=WINDOW)).astype(int)
cut=d.mi.max()-math.ceil(WINDOW/30)
txt={}
for f in ("so_questions_full.json","so_questions_ext_py.json"):
    for q in json.load(open(os.path.join(DATA,f),encoding="utf8")):
        txt[q["question_id"]]=len(q.get("title") or "")+len(q.get("body_excerpt") or "")
d["nchar"]=d.question_id.map(txt)
full=d[(d.mi<=cut)&d.q_creation.notna()&d.s.between(1,4)&d.nchar.notna()].copy()
res={}
print("=== A. length-conditioned tracers in the receiving bins ===")
print("  'long' = above the PRE-period median length of that bin (fixed cut)")
for b in (1,2):
    sub=full[full.s==b]; med=sub[sub.post==0].nchar.median()
    L=sub[sub.nchar>med]
    pre,pst=L[L.post==0],L[L.post==1]
    for nm,col in (("dup≤90d","dup"),("answers","answer_count")):
        a,c=pre[col],pst[col]
        if col=="dup":
            se=math.sqrt(a.mean()*(1-a.mean())/len(a)+c.mean()*(1-c.mean())/len(c))
        else:
            se=math.sqrt(a.var(ddof=1)/len(a)+c.var(ddof=1)/len(c))
        diff=c.mean()-a.mean()
        print(f"  s{b} long  {nm:9s}: pre {a.mean():.3f} (N={len(a)})  post {c.mean():.3f} (N={len(c)})  "
              f"diff {diff:+.3f} [{diff-1.96*se:+.3f}, {diff+1.96*se:+.3f}]")
        res[f"s{b}_long_{col}"]={"pre":float(a.mean()),"post":float(c.mean()),"diff":float(diff),
                                 "ci":[float(diff-1.96*se),float(diff+1.96*se)],"n_pre":int(len(a)),"n_post":int(len(c))}
    # what would migrants look like? long s4 pre (the donor's long tail)
    L4=full[(full.s==4)&(full.post==0)]; L4=L4[L4.nchar>full[(full.s==4)&(full.post==0)].nchar.median()]
    print(f"      reference, long-s4 pre: dup {L4.dup.mean():.3f}  answers {L4.answer_count.mean():.3f}  (N={len(L4)})")
    res[f"ref_long_s4_pre"]={"dup":float(L4.dup.mean()),"answers":float(L4.answer_count.mean())}
print("\n=== B. does length itself predict the tracers, within bin, pre-period? ===")
print("  (if length has little tracer effect, S17's attenuation worry is small)")
pre=full[full.post==0].copy(); pre["lognchar"]=np.log(pre.nchar)
for col in ("dup","answer_count"):
    m=smf.ols(f"{col} ~ lognchar + C(s)",data=pre).fit(cov_type="HC1")
    print(f"  {col:13s} ~ log(length) | bin FE :  {m.params['lognchar']:+.4f} (SE {m.bse['lognchar']:.4f}, p={m.pvalues['lognchar']:.3f})")
    res[f"pre_len_effect_{col}"]={"coef":float(m.params["lognchar"]),"se":float(m.bse["lognchar"]),"p":float(m.pvalues["lognchar"])}
print("\n=== C. tracer gradient with length controlled (post only) ===")
pst=full[full.post==1].copy(); pst["lognchar"]=np.log(pst.nchar)
for col in ("dup","answer_count"):
    m0=smf.ols(f"{col} ~ s",data=pst).fit(cov_type="HC1")
    m1=smf.ols(f"{col} ~ s + lognchar",data=pst).fit(cov_type="HC1")
    print(f"  {col:13s}: s slope {m0.params['s']:+.4f} -> with length {m1.params['s']:+.4f}")
    res[f"post_gradient_{col}"]={"raw":float(m0.params["s"]),"len_ctrl":float(m1.params["s"])}
json.dump(res,open(os.path.join(HERE,"s17_length_conditioned.json"),"w"),indent=2)
print("\nwritten: s17_length_conditioned.json")
