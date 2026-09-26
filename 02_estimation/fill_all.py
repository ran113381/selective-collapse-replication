# -*- coding: utf-8 -*-
"""Fill the three remaining gaps, one item per call, generous retries.
Non-random attrition (s1 20% vs s4 5%, chi2 p=.021) is why these matter:
completing them lets the 4-tier comparison use all 320 instead of the
attrition-safe 284 common subset.
(Interim figures, recorded when this script was written. After it ran, 32 items
still returned nothing; the reported attrition figures and the 288-question
common subset are in Supplementary Section S13.)"""
import importlib.util, json, os, sys
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HERE=os.path.dirname(os.path.abspath(__file__))
spec=importlib.util.spec_from_file_location('g',os.path.join(HERE,'glm_run.py')); G=importlib.util.module_from_spec(spec); spec.loader.exec_module(G)
CRIT=r'E:\智能体论文\P9_金标准_20260704\criterion'
GOLD=r'E:\智能体论文\P9_金标准_20260704'

INSTR=("You are an expert Python engineer answering Stack Overflow questions.\n\n"
 "Write the answer you would post for the question below, using ONLY its title and body. "
 "You have no other context: no comments, no accepted answer, no follow-ups.\n\n"
 "Give a concrete technical answer: identify the likely cause and the fix, with a short code "
 "snippet where useful. Maximum 180 words. If the question cannot be fully answered from its "
 "text alone, say in one sentence what is missing and still give the most likely resolution. "
 "Do not mention that you are an AI. Output only the answer text.\n\n")

# ---- 1. GLM-5.3 answers ----
n_ok=0
for k in range(16):
    p=os.path.join(CRIT,'batches_glm53',f'answer_out_{k}.json')
    batch=json.load(open(os.path.join(CRIT,'batches_v2',f'answer_batch_{k}.json'),encoding='utf8'))
    have={x['qid']:x['answer'] for x in json.load(open(p,encoding='utf8'))} if os.path.exists(p) else {}
    have={q:a for q,a in have.items() if str(a).strip()}
    todo=[q for q in batch if q['qid'] not in have]
    if not todo: continue
    print(f'[answers] batch {k}: {len(todo)} to fill')
    for q in todo:
        try:
            c,u=G.chat('glm-5.3',[{'role':'user','content':INSTR+"Title: "+q['title']+"\n\nBody:\n"+q['q_body'][:2500]}],
                       temperature=0.2,max_tokens=8000,effort='low',retries=6)
            if c.strip():
                have[q['qid']]=c.strip(); n_ok+=1; print(f"   {q['qid']} ok ({len(c.split())}w)")
            else: print(f"   {q['qid']} EMPTY")
        except Exception as e: print(f"   {q['qid']} FAIL {str(e)[:60]}")
    json.dump([{'qid':q['qid'],'answer':have[q['qid']]} for q in batch if q['qid'] in have],
              open(p,'w',encoding='utf8'),ensure_ascii=False,indent=1)
print(f'[answers] filled {n_ok}')

# ---- 2. main labels ----
done={int(json.loads(l)['question_id']) for l in open(os.path.join(HERE,'glm_relabel','labels_glm-4.6.jsonl'),encoding='utf8')}
todo=[q for q in G.load_questions() if q['question_id'] not in done]
if todo:
    print(f'[labels] {len(todo)} to fill')
    with open(os.path.join(HERE,'glm_relabel','labels_glm-4.6.jsonl'),'a',encoding='utf8') as f:
        for q in todo:
            try:
                c,u=G.chat('glm-4.6',[{'role':'user','content':G.RUBRIC+'\n\n---\n\n以下是本批问题（JSON 数组）。按 rubric 给每题打分，只输出一个 JSON 数组，不要任何其他文字：\n\n'+json.dumps([q],ensure_ascii=False)}],0,12000,retries=6)
                for r in G.parse_json_array(c):
                    if int(r['question_id'])==q['question_id']:
                        f.write(json.dumps({'question_id':q['question_id'],'score':int(r['score']),'label':'GEN' if int(r['score'])>=3 else 'VER','why':str(r.get('why',''))[:200],'model':'glm-4.6'},ensure_ascii=False)+'\n'); f.flush(); print(f"   {q['question_id']} ok")
            except Exception as e: print(f"   {q['question_id']} FAIL {str(e)[:60]}")

# ---- 3. gold labels ----
gp=os.path.join(HERE,'glm_relabel','gold_labels_glm-5.3.jsonl')
done={int(json.loads(l)['question_id']) for l in open(gp,encoding='utf8')}
gs=[r for r in json.load(open(os.path.join(GOLD,'gold_sample.json'),encoding='utf8')) if int(r['question_id']) not in done]
if gs:
    print(f'[gold] {len(gs)} to fill')
    with open(gp,'a',encoding='utf8') as f:
        for r in gs:
            q={'question_id':int(r['question_id']),'title':r['title'],'tags':r.get('tags',[]),'body_excerpt':r.get('body_excerpt','')}
            try:
                c,u=G.chat('glm-5.3',[{'role':'user','content':G.RUBRIC+'\n\n---\n\n以下是本批问题（JSON 数组）。按 rubric 给每题打分，只输出一个 JSON 数组，不要任何其他文字：\n\n'+json.dumps([q],ensure_ascii=False)}],0,16000,retries=6)
                for x in G.parse_json_array(c):
                    if int(x['question_id'])==q['question_id']:
                        f.write(json.dumps({'question_id':q['question_id'],'score':int(x['score']),'label':'GEN' if int(x['score'])>=3 else 'VER','why':str(x.get('why',''))[:200],'model':'glm-5.3'},ensure_ascii=False)+'\n'); f.flush(); print(f"   {q['question_id']} ok")
            except Exception as e: print(f"   {q['question_id']} FAIL {str(e)[:60]}")
print('ALL DONE')
