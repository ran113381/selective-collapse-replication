#!/bin/bash
cd "E:/智能体论文/P9b_IPM_20260919/工作文档/r1_随机重抽_20261012"
export STACK_APPS_KEY="$(cat .stack_key | tr -d '\r\n')"
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
  D:/python.exe r1_enumerate.py >> enum_run_full60.log 2>&1
  rc=$?
  echo "[loop] attempt $i exit=$rc" >> enum_run_full60.log
  if [ $rc -eq 0 ] || [ $rc -eq 3 ]; then break; fi
  sleep 5
done
