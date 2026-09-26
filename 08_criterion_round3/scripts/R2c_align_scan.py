# -*- coding: utf-8 -*-
"""R2 C 阶段:答案与题目的对齐扫描(会话答题者可能把答案挂错题号;第二轮 Haiku 4.5 出过一次)。

对每个答题批,取每条答案的「特征词」(≥4 字母的标识符/单词,去常见停用词),与同批 20 道题各自的
标题+正文特征词算重合度;若答案与自己题目的重合度不是同批最高,且最高者明显更高,则标为疑似错位。
脚本只报告,不改任何文件;标出的逐条人工看。
"""
import io, json, os, re, sys

sys.stdout.reconfigure(encoding="utf-8")
C = os.path.join(os.path.dirname(os.path.abspath(__file__)), "R2_criterion")
STOP = set("this that with from have your what when where which there their would could should into about using "
           "python code value values error file files data self return print import function method class like need "
           "want also then than them they will just only does make more some other each list string true false none "
           "problem question answer following example works work used here".split())


def feats(t):
    return {w.lower() for w in re.findall(r"[A-Za-z_][A-Za-z0-9_\.]{3,}", t or "")} - STOP


flag = []
for tag in sys.argv[1:] or ["sonnet5", "haiku45"]:
    for k in range(16):
        qs = json.load(io.open(os.path.join(C, "batches_v3", "answer_batch_%d.json" % k), encoding="utf-8"))
        qf = {q["qid"]: feats(q["title"] + " " + q["q_body"]) for q in qs}
        ans = {int(a["qid"]): a["answer"] for a in json.load(io.open(os.path.join(C, "batches_" + tag, "answer_out_%d.json" % k), encoding="utf-8"))}
        pp = os.path.join(C, "batches_" + tag, "answer_out_patch.json")
        if os.path.exists(pp):
            for a in json.load(io.open(pp, encoding="utf-8")):
                if int(a["qid"]) in qf and int(a["qid"]) not in ans:
                    ans[int(a["qid"])] = a["answer"]
        for q, a in ans.items():
            af = feats(a)
            sc = {p: len(af & f) / (len(af | f) or 1) for p, f in qf.items()}
            best = max(sc, key=sc.get)
            if best != q and sc[best] > 1.5 * sc.get(q, 0) + 0.02:
                flag.append((tag, k, q, best, round(sc.get(q, 0), 3), round(sc[best], 3)))
print("疑似错位 %d 条" % len(flag))
for f in flag:
    print("  %s 批%d 题%d 的答案更像 题%d (自身 %.3f / 最像 %.3f)" % f)
