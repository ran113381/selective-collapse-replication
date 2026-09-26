# -*- coding: utf-8 -*-
"""R2 下游重估·S19 抽样窗口检验:凡是拿「主分类器面板标签」作比较基准的量(评分者对主分类器的漂移、
降幅比、匹配子样本上的 γ),主评分者换成盲标签后都要重算;评分者自己对自己的比较(两种抽样设计之差)不受影响。

做法同 R2d_downstream.py:把 工作文档 里的 R1 分析脚本与其输入(盲批次、标签批次、token 映射、原始抽取)复制进
两套镜像的 06\\ 目录,只把 _legB_data 路径改到镜像的 data\\,依次运行;原标签臂的输出逐叶对当年产物自证。
输出 工作文档\\R2d_r1_compare.json
"""
import glob, importlib.util, io, json, os, re, shutil, subprocess, sys

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("r2d", os.path.join(HERE, "R2d_downstream.py"))
r2d = importlib.util.module_from_spec(spec); spec.loader.exec_module(r2d)
ROOT = r2d.ROOT
SCRIPTS = ["R1_coverage.py", "R1_analyze.py", "R1c_analyze.py", "R1d_analyze.py", "R1_sensitivity.py", "R1_composition.py"]
OUTS = re.compile(r"(_result\.json|_month_compare\.csv)$")


def build_and_run(arm):
    base = os.path.join(ROOT, arm); d = os.path.join(base, "06")
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(d)
    for f in os.listdir(HERE):
        if re.match(r"R1[cd]?_", f) and f.endswith((".json", ".csv")) and not OUTS.search(f):
            shutil.copy2(os.path.join(HERE, f), d)
    for s in SCRIPTS:
        t = io.open(os.path.join(HERE, s), encoding="utf-8").read()
        io.open(os.path.join(d, s), "w", encoding="utf-8").write(r2d.patch(t, base))
    env = dict(os.environ, PYTHONIOENCODING="utf-8"); env.pop("STACK_API_KEY", None)
    rc = {}
    for s in SCRIPTS:
        r = subprocess.run([sys.executable, os.path.join(d, s)], cwd=d, env=env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=3600)
        io.open(os.path.join(base, "logs", "06_" + s.replace(".py", ".log")), "w", encoding="utf-8").write(
            r.stdout + "\n--- stderr ---\n" + r.stderr)
        rc[s] = r.returncode
        print("[%s] %-18s rc=%d" % (arm, s, r.returncode))
    return rc


if __name__ == "__main__":
    R = {"rc": {}, "selfproof": {}, "blind_vs_orig": {}}
    for arm in ("orig", "blind"):
        R["rc"][arm] = build_and_run(arm)
    o = {os.path.basename(f): f for f in glob.glob(os.path.join(ROOT, "orig", "06", "*_result.json"))}
    b = {os.path.basename(f): f for f in glob.glob(os.path.join(ROOT, "blind", "06", "*_result.json"))}
    for n, f in sorted(o.items()):
        ref = os.path.join(HERE, n)
        if os.path.exists(ref):
            k, dd = r2d.diff(json.load(io.open(ref, encoding="utf-8")), json.load(io.open(f, encoding="utf-8")))
            R["selfproof"][n] = dict(leaves=k, differ=len(dd), first=[list(x) for x in dd[:8]])
            print("自证 %-32s 叶 %d 不等 %d" % (n, k, len(dd)))
        if n in b:
            k, dd = r2d.diff(json.load(io.open(f, encoding="utf-8")), json.load(io.open(b[n], encoding="utf-8")))
            R["blind_vs_orig"][n] = dict(leaves=k, differ=len(dd), rows=[list(x) for x in dd])
            print("盲/原 %-32s 叶 %d 变 %d" % (n, k, len(dd)))
    io.open(os.path.join(HERE, "R2d_r1_compare.json"), "w", encoding="utf-8").write(json.dumps(R, indent=1, ensure_ascii=False, default=str))
