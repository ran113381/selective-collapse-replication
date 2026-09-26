# -*- coding: utf-8 -*-
u"""Exploratory version of p0_3: of the nine placebo cutoffs before the event, how
many have a window lying entirely before the true event?

Uses the placebo test's window definition (dd.t >= ev-9 and dd.t < ev+9, i.e.
ev-9 .. ev+8) and lists each candidate's start, end and overlap with the treated
period.
"""
import os, sys, numpy as np, pandas as pd
sys.stdout.reconfigure(encoding="utf-8")

DATA = r"E:\智能体论文\_legB_data"
EVENT = 2022 * 12 + 11          # 2022-12
W = 9


def lab(t):
    return "%04d-%02d" % (t // 12, t % 12 + 1)


wpy = pd.read_csv(os.path.join(DATA, "within_so_llm_panel.csv"))
ts = sorted(int(y) * 12 + (int(m) - 1) for y, m in
            (s.split("-") for s in wpy["ym"]))
cands = [t for t in ts if t - W >= ts[0] and t + W - 1 <= ts[-1]]
pre = [e for e in cands if e < EVENT]

print("面板 %s .. %s  共 %d 月" % (lab(ts[0]), lab(ts[-1]), len(ts)))
print("真实事件 %s；候选截点 %d 个，其中截点早于真实事件的 %d 个"
      % (lab(EVENT), len(cands), len(pre)))
print()
print("%-9s %-9s %-9s %7s %7s  %s" % ("截点", "窗口起", "窗口止", "窗内", "处理月", "判定"))
clean = 0
for ev in pre:
    lo, hi = ev - W, ev + W - 1
    overlap = sum(1 for t in range(lo, hi + 1) if t >= EVENT)
    ok = overlap == 0
    clean += ok
    print("%-9s %-9s %-9s %7d %7d  %s"
          % (lab(ev), lab(lo), lab(hi), hi - lo + 1, overlap,
             "干净" if ok else "窗口含真实处理期"))
print()
print("整段未受处理的安慰剂：%d 个（稿件第 7.1 节称九个）" % clean)
print("真实事件前的月份数 = %d；窗口宽 %d 月，故最多只能有 %d 个干净安慰剂"
      % (EVENT - ts[0], 2 * W, max(0, (EVENT - ts[0]) - 2 * W + 1)))
