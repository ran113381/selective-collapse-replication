# -*- coding: utf-8 -*-
"""Third-channel candidate (independent adjudication, Fable 5.1): classifier
memorisation of pre-period content.

The classifier (Claude Sonnet 4.6) was trained on corpora that include Stack
Overflow. Pre-2022 questions are far more heavily represented in such corpora
than 2024-26 ones, and some of the latter post-date the model's cutoff. Two of
the five properties the rubric's level descriptions draw on are 'judgment
versus retrieval' and 'answer uniqueness'. A model that has effectively memorised a question's canonical
answer will rate it as retrievable, i.e. MORE substitutable. So measured
substitutability could fall after the event simply because later questions are
less memorised, with no change in what was asked. Date-blindness does not
protect against this; neither do month FE nor the volume reconstruction.

Test: humans do not memorise Stack Overflow. On the 300 human-coded questions,
compare the pre->post shift in the CLASSIFIER's score with the shift in the
HUMAN score on the same questions. If memorisation drives the classifier, its
score should fall more than the humans' and the classifier-minus-human gap
should be larger pre than post.
"""
import os, sys, json, math
import numpy as np, pandas as pd
from scipy import stats
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
G=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"03_validation","gold_standard")
def ym_int(y): a,b=y.split("-"); return int(a)*12+int(b)-1
EVENT=ym_int("2022-12")
gold=pd.DataFrame(json.load(open(os.path.join(G,"gold_sample.json"),encoding="utf8")))
B=pd.read_csv(os.path.join(G,"coding_sheet_B_v2.csv"),encoding="utf-8-sig")[["question_id","score_0_4"]].rename(columns={"score_0_4":"B"})
A=pd.read_csv(os.path.join(G,"coding_sheet_A_v2.csv"),encoding="utf-8-sig")[["question_id","score_0_4"]].rename(columns={"score_0_4":"A"})
CONS=pd.read_csv(os.path.join(G,"裁决记录表.csv"),encoding="utf-8-sig")[["question_id","consensus_0_4"]]
d=gold.merge(A,on="question_id").merge(B,on="question_id").merge(CONS,on="question_id",how="left")
d["human"]=d[["A","B"]].mean(axis=1)
d["human_bin"]=np.where(d.consensus_0_4.notna(), (d.consensus_0_4>=3).astype(int),
                        ((d.A>=3)&(d.B>=3)).astype(int))
d["model"]=d.model_score.astype(float)
d["mi"]=d.ym.map(ym_int); d["post"]=(d.mi>=EVENT).astype(int)
print(f"N={len(d)}  pre={int((d.post==0).sum())}  post={int((d.post==1).sum())}  months {d.ym.min()}..{d.ym.max()}")
res={}
def shift(col):
    a,c=d.loc[d.post==0,col],d.loc[d.post==1,col]
    diff=c.mean()-a.mean(); se=math.sqrt(a.var(ddof=1)/len(a)+c.var(ddof=1)/len(c))
    return a.mean(),c.mean(),diff,se
print("\n=== pre -> post shift on the SAME 300 questions ===")
for nm,col in (("classifier (Sonnet 4.6)","model"),("human mean (A,B)","human"),("human binary GEN","human_bin")):
    a,c,diff,se=shift(col)
    print(f"  {nm:24s}: {a:.3f} -> {c:.3f}   diff {diff:+.3f}  [{diff-1.96*se:+.3f}, {diff+1.96*se:+.3f}]")
    res[col]={"pre":float(a),"post":float(c),"diff":float(diff),"se":float(se)}
print("\n=== classifier minus human, by period (memorisation => gap shrinks post) ===")
d["gap"]=d.model-d.human
a,c=d.loc[d.post==0,"gap"],d.loc[d.post==1,"gap"]
diff=c.mean()-a.mean(); se=math.sqrt(a.var(ddof=1)/len(a)+c.var(ddof=1)/len(c))
print(f"  gap pre {a.mean():+.3f}  post {c.mean():+.3f}   change {diff:+.3f}  [{diff-1.96*se:+.3f}, {diff+1.96*se:+.3f}]"
      f"   Welch p={stats.ttest_ind(a,c,equal_var=False).pvalue:.3f}")
res["gap"]={"pre":float(a.mean()),"post":float(c.mean()),"change":float(diff),"se":float(se)}
print("\n=== paired view: does the classifier's shift exceed the humans' on the same items? ===")
dm=res["model"]["diff"]; dh=res["human"]["diff"]
# difference-in-shifts with a paired SE (the two scores are on the same questions)
d["m_minus_h"]=d.model-d.human
a,c=d.loc[d.post==0,"m_minus_h"],d.loc[d.post==1,"m_minus_h"]
dd=c.mean()-a.mean(); se=math.sqrt(a.var(ddof=1)/len(a)+c.var(ddof=1)/len(c))
print(f"  classifier shift {dm:+.3f}  vs human shift {dh:+.3f}   excess {dd:+.3f}  [{dd-1.96*se:+.3f}, {dd+1.96*se:+.3f}]")
print(f"  => classifier explains {dm/dh*100:.0f}% of the human shift" if dh!=0 else "")
res["excess_shift"]={"classifier":float(dm),"human":float(dh),"excess":float(dd),"se":float(se)}
print("\n=== by year (classifier vs human means) ===")
d["yr"]=d.ym.str[:4]
print(d.groupby("yr")[["model","human"]].agg(["mean","count"]).round(2).to_string())
json.dump(res,open("memorization_check.json","w"),indent=2)
print("\nwritten: memorization_check.json")
