# -*- coding: utf-8 -*-
"""Fetch last_edit_date / last_activity_date for the 6,000 python questions.
Third-channel candidate: community edits accumulate over years and typically
strip greetings, noise and sometimes context. Pre-period questions have had far
longer to be edited than post-period ones, so the fetched (current) text may
differ from the posted text in a time-correlated way. Resumable."""
import os, sys, json, csv, time, urllib.request, urllib.parse
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HERE=os.path.dirname(os.path.abspath(__file__)); DATA=r"E:\智能体论文\_legB_data"
OUT=os.path.join(HERE,"edit_meta.csv"); API="https://api.stackexchange.com/2.3/questions/{ids}"
ids=pd.read_csv(os.path.join(DATA,"question_labels.csv")).question_id.astype(int).tolist()
done=set(pd.read_csv(OUT).question_id.astype(int)) if os.path.exists(OUT) else set()
todo=[i for i in ids if i not in done]; print(f"have {len(done)}, need {len(todo)}")
f=open(OUT,"a",newline="",encoding="utf-8"); w=csv.writer(f)
if not done: w.writerow(["question_id","last_edit_date","last_activity_date","view_count","is_answered"])
for bi in range(0,len(todo),100):
    batch=todo[bi:bi+100]
    for k in range(5):
        try:
            q=urllib.parse.urlencode({"site":"stackoverflow","pagesize":100})
            with urllib.request.urlopen(f"{API.format(ids=';'.join(map(str,batch)))}?{q}",timeout=60) as r:
                d=json.loads(r.read().decode()); break
        except Exception as e:
            time.sleep(3*(k+1)); d=None
    if d is None: print("FAILED at",bi); break
    if d.get("backoff"): time.sleep(int(d["backoff"])+1)
    got={it["question_id"]:it for it in d.get("items",[])}
    for qid in batch:
        it=got.get(qid,{})
        w.writerow([qid,it.get("last_edit_date",""),it.get("last_activity_date",""),it.get("view_count",""),it.get("is_answered","")])
    f.flush(); time.sleep(0.25)
    if (bi//100+1)%10==0: print(f"  batch {bi//100+1}  quota_remaining={d.get('quota_remaining')}")
f.close(); print("done ->",OUT)
