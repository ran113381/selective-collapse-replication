# -*- coding: utf-8 -*-
"""r1 共用件：路径、月份、Stack Exchange API 取数（backoff / quota / 节流）、
正文预处理（逐字取自原脚本 fetch_so_questions.strip_html，并在加载时与原文件比对）。

API key 只从环境变量 STACK_APPS_KEY 或命令行 --key 传入；本模块任何输出都不含 key。
"""
import calendar, datetime as dt, gzip, hashlib, html, io, json, os, re, sys, time
import urllib.error, urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = r"E:\智能体论文\P9b_OSF_复现包_20260920"
ORIG_FETCH_Q = os.path.join(PKG, "01_panels_and_classification", "fetch_so_questions.py")
PLATFORM_TOTALS = os.path.join(PKG, "02_estimation", "platform_monthly_totals.csv")
PANEL_DIR = os.path.join(PKG, "01_panels_and_classification", "data")

API = "https://api.stackexchange.com/2.3/"
# 原脚本 UA 已在复现包里匿名化；这里沿用同一串
UA = "P9-verification-economics-research/0.1 (measure-only; contact withheld for anonymized review)"
# 自建的安全 filter：只含 question_id / creation_date + 分页与配额字段（/filters/create 返回，2026-10-12）
ENUM_FILTER = "!10dDZgbjRq0bF.6u"
SEED = 20261012
N_PER_MONTH = 100
FIRST_YM, LAST_YM = "2021-06", "2026-05"
EVENT_YM = "2022-12"          # 稿件：pre = 早于 2022-12 的月份（前期 18 个月），post = 2022-12 起 42 个月

API_KEY = os.environ.get("STACK_APPS_KEY") or None


def set_key(k):
    global API_KEY
    if k:
        API_KEY = k


def month_iter(a, b):
    y, m = (int(x) for x in a.split("-"))
    ey, em = (int(x) for x in b.split("-"))
    while (y, m) <= (ey, em):
        yield "%04d-%02d" % (y, m)
        m += 1
        if m > 12:
            m, y = 1, y + 1


def month_window(ym):
    """与原脚本 month_window 同一定义：[当月 1 日 00:00 UTC, 次月 1 日 00:00 UTC)，Unix 秒。"""
    y, m = (int(x) for x in ym.split("-"))
    f = calendar.timegm((y, m, 1, 0, 0, 0, 0, 0, 0))
    ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
    t = calendar.timegm((ny, nm, 1, 0, 0, 0, 0, 0, 0))
    return f, t


def is_pre(ym):
    return ym < EVENT_YM


def parse_months(arg):
    if not arg:
        return list(month_iter(FIRST_YM, LAST_YM))
    out = []
    for p in arg.split(","):
        p = p.strip()
        if ".." in p:
            a, b = p.split("..")
            out += list(month_iter(a, b))
        elif p:
            out.append(p)
    return out


def sha12_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]


def write_json(path, obj, indent=None):
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent)
    os.replace(tmp, path)


class ThrottleExhausted(Exception):
    def __init__(self, seconds):
        self.seconds = seconds
        super().__init__("quota exhausted; ~%s s until reset" % seconds)


def _scrub(s):
    return re.sub(r"key=[^&\s]+", "key=***", str(s))


def api_get(path, params, max_retries=6, sleep=0.2, logfile=None):
    """GET API+path?params。返回 dict。遵守 backoff；400/502 -> ThrottleExhausted。
    params 是已拼好的查询串（不含 key），key 在这里追加，永不打印。"""
    url = API + path + "?" + params + ("&key=" + API_KEY if API_KEY else "")
    delay = 2.0
    for attempt in range(max_retries):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                d = json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = ""
            try:
                eb = e.read()
                if e.headers.get("Content-Encoding") == "gzip":
                    eb = gzip.decompress(eb)
                body = eb.decode("utf-8", "replace")
            except Exception:
                pass
            if e.code == 400:
                if '"error_id":502' in body or "throttle_violation" in body:
                    m = re.search(r"available in (\d+) seconds", body)
                    raise ThrottleExhausted(int(m.group(1)) if m else None)
                raise RuntimeError("HTTP 400: " + _scrub(body[:300]))
            wait = delay * (attempt + 1)
            print("    HTTP %s; backoff %ds (%s)" % (e.code, wait, _scrub(body[:100])), flush=True)
            time.sleep(wait)
            continue
        except (urllib.error.URLError, TimeoutError) as e:
            wait = delay * (attempt + 1)
            print("    net error %s; retry in %ds" % (_scrub(e), wait), flush=True)
            time.sleep(wait)
            continue
        if logfile:
            with io.open(logfile, "a", encoding="utf-8") as lf:
                lf.write(json.dumps({"t": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                     "path": path, "q": _scrub(params)[:160],
                                     "quota_remaining": d.get("quota_remaining"),
                                     "n_items": len(d.get("items", [])) if "items" in d else None,
                                     "backoff": d.get("backoff")}) + "\n")
        if d.get("backoff"):
            time.sleep(float(d["backoff"]) + 1.0)
        elif sleep:
            time.sleep(sleep)
        return d
    raise RuntimeError("giving up after %d retries: %s" % (max_retries, _scrub(url)))


# ---- 正文预处理：逐字取自原脚本，并与原文件比对 -----------------------------
def strip_html(s, maxlen=1400):
    s = s or ""
    s = re.sub(r"<pre[\s\S]*?</pre>", " [CODE] ", s, flags=re.I)
    s = re.sub(r"<code>[\s\S]*?</code>", " [code] ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:maxlen]


def check_strip_html_identical():
    """把本文件的 strip_html 函数体与原脚本的逐行比对；不一致则抛错。返回(原脚本sha12, 函数体行数)。"""
    def body(path):
        t = io.open(path, encoding="utf-8").read().replace("\r\n", "\n").split("\n")
        i = [k for k, l in enumerate(t) if l.startswith("def strip_html(")][0]
        out = []
        for l in t[i:]:
            if out and l and not l.startswith((" ", "\t")):
                break
            out.append(l)
        # 去掉函数内文档字符串之前的差异：只比对以 's = s or ""' 起的可执行行
        ex = [l for l in out if l.strip() and not l.strip().startswith(('"""', "#"))]
        k = [j for j, l in enumerate(ex) if l.strip().startswith('s = s or ""')][0]
        return [l.rstrip() for l in ex[k:] if "Truncate" not in l and "HTML body" not in l
                and "structure without" not in l]
    a = body(ORIG_FETCH_Q)
    b = body(os.path.join(HERE, "r1_common.py"))
    # 原文 def 行里的 maxlen 默认值也要一致
    sig_o = [l for l in io.open(ORIG_FETCH_Q, encoding="utf-8") if l.startswith("def strip_html(")][0].strip()
    sig_n = [l for l in io.open(os.path.join(HERE, "r1_common.py"), encoding="utf-8")
             if l.startswith("def strip_html(")][0].strip()
    if a != b or sig_o != sig_n:
        raise RuntimeError("strip_html 与原脚本不一致:\n%s\n%s" % (a, b))
    return sha12_file(ORIG_FETCH_Q), len(a)


def load_original_panel():
    """原面板 6000 题（前 100）：{ym: [record,...]}。只读复现包。"""
    recs = []
    for fn in ("so_questions_python_2021-2024.json", "so_questions_python_ext_2024-07_2026-05.json"):
        recs += json.load(io.open(os.path.join(PANEL_DIR, fn), encoding="utf-8"))
    by = {}
    for r in recs:
        by.setdefault(r["ym"], []).append(r)
    return by
