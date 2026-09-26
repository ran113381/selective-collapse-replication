# -*- coding: utf-8 -*-
"""Third-channel candidate: community-edit exposure (Fable 5.1 adjudication).

The classifier and the human coders both scored the CURRENT text (fetched
2026), not the text as posted. Stack Overflow questions are edited by the
community for years after posting; edits typically strip greetings, fix
formatting and sometimes remove or add context. A 2021 question has had five
years of such exposure, a 2026 question a few months. If edits push text toward
the generic, pre-period questions would score MORE substitutable than when
posted, purely from edit exposure, in the same direction as the finding.

Tests:
  A. edit incidence and timing by period (is exposure actually different?);
  B. within period, do edited questions score differently from unedited ones?
     (if edits do not move the score, exposure cannot move the composition);
  C. counterfactual: give the post period the pre-period edit rate and the
     within-period edited/unedited score gap; how much of the mean-s fall
     could edit exposure explain at most?
"""
import os, sys, json, math
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
import warnings; warnings.simplefilter("ignore")
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
DATA=r"E:\智能体论文\_legB_data"; HERE=os.path.dirname(os.path.abspath(__file__))
def ym_int(y): a,b=y.split("-"); return int(a)*12+int(b)-1
EVENT=ym_int("2022-12")
lab=pd.read_csv(os.path.join(DATA,"question_labels.csv")).rename(columns={"score":"s"})
ed=pd.read_csv(os.path.join(HERE,"edit_meta.csv"))
own=pd.read_csv(os.path.join(HERE,"asker_owner.csv")).drop_duplicates("question_id")[["question_id","q_creation"]]
d=lab.merge(ed,on="question_id",how="left").merge(own,on="question_id",how="left")
d["mi"]=d.ym.map(ym_int); d["post"]=(d.mi>=EVENT).astype(int)
d["edited"]=d.last_edit_date.notna().astype(int)
d["days_to_edit"]=(d.last_edit_date-d.q_creation)/86400
d=d[d.s.between(1,4)&d.q_creation.notna()].copy()
res={}
print(f"N={len(d)}  pre={int((d.post==0).sum())}  post={int((d.post==1).sum())}")
print("\n=== A. edit incidence and timing ===")
for lbl,sub in (("pre",d[d.post==0]),("post",d[d.post==1])):
    e=sub[sub.edited==1]
    print(f"  {lbl:4s}: edited {sub.edited.mean():.1%}   median days-to-last-edit {e.days_to_edit.median():.0f}"
          f"   edited within 30d {(e.days_to_edit<=30).mean():.1%}   after 1y {(e.days_to_edit>365).mean():.1%}")
    res[f"edit_{lbl}"]={"rate":float(sub.edited.mean()),"median_days":float(e.days_to_edit.median()),
                        "within30":float((e.days_to_edit<=30).mean()),"after1y":float((e.days_to_edit>365).mean())}
# late edits are the exposure mechanism; early edits are mostly the asker's own fix
d["late_edit"]=((d.edited==1)&(d.days_to_edit>365)).astype(int)
print(f"  late (>1y) edits: pre {d.loc[d.post==0,'late_edit'].mean():.1%}  post {d.loc[d.post==1,'late_edit'].mean():.1%}")
print("\n=== B. does edit status move the score, within period? ===")
for lbl,sub in (("pre",d[d.post==0]),("post",d[d.post==1])):
    for ev in ("edited","late_edit"):
        a,c=sub.loc[sub[ev]==0,"s"],sub.loc[sub[ev]==1,"s"]
        if len(c)<20: print(f"  {lbl:4s} {ev:9s}: too few ({len(c)})"); continue
        diff=c.mean()-a.mean(); se=math.sqrt(a.var(ddof=1)/len(a)+c.var(ddof=1)/len(c))
        print(f"  {lbl:4s} {ev:9s}: unedited {a.mean():.3f} (N={len(a)})  edited {c.mean():.3f} (N={len(c)})  "
              f"gap {diff:+.3f} [{diff-1.96*se:+.3f},{diff+1.96*se:+.3f}]")
        res[f"gap_{lbl}_{ev}"]={"unedited":float(a.mean()),"edited":float(c.mean()),"gap":float(diff),"se":float(se)}
m=smf.ols("s ~ edited*post",data=d).fit(cov_type="HC1")
print(f"  OLS s ~ edited*post : edited {m.params['edited']:+.3f} (p={m.pvalues['edited']:.3f})  "
      f"edited:post {m.params['edited:post']:+.3f} (p={m.pvalues['edited:post']:.3f})")
print("\n=== C. counterfactual bound: how much of the mean-s fall could exposure explain? ===")
tot=d.loc[d.post==1,"s"].mean()-d.loc[d.post==0,"s"].mean()
for ev in ("edited","late_edit"):
    r0,r1=d.loc[d.post==0,ev].mean(),d.loc[d.post==1,ev].mean()
    g=res.get(f"gap_pre_{ev}",{}).get("gap",0.0)   # pre-period edited-unedited score gap
    # if exposure drives the fall, post questions would have scored higher by (r0-r1)*g had they been edited at the pre rate
    explained=(r0-r1)*g
    print(f"  {ev:9s}: edit-rate change {r0:.3f}->{r1:.3f}, pre gap {g:+.3f}  => attributable {explained:+.4f} of total {tot:+.4f} ({explained/tot*100:+.1f}%)")
    res[f"bound_{ev}"]={"rate_pre":float(r0),"rate_post":float(r1),"gap":float(g),"attributable":float(explained),"total":float(tot),"share":float(explained/tot)}
json.dump(res,open("edit_exposure_check.json","w"),indent=2)
print("\nwritten: edit_exposure_check.json")
