# -*- coding: utf-8 -*-
"""R1 — 整月均匀随机抽样，用来检验「每月最早 100 题」这条规则有没有污染 γ。

背景（写在这里是为了让这个脚本自己说得清用途，不是为了给标注者看）：
主面板每月取该月**最早**创建的 100 题。前期高流量，100 题在约 6.8 小时内就攒满；
后期量塌了，窗口拉到中位 24 小时、最长 9.75 天。于是前期样本对「月中/月末」区域
**一条观测都没有**，现有样本再怎么切也切不出那块。本脚本抽的就是那块。

抽法：每月切 8 个等长时间层，层内用固定种子取一个随机起点，从该起点向后取 5 题。
层内随机起点是必要的——若一律取层首，8 个层首的小时数只会落在 4 个值上，
日内时段覆盖依旧残缺。

输出两份：
  R1_uniform_raw.json      带日期，供回接分析用，**不给标注者**
  R1_blind_batch_*.json    已打乱、已剥日期，只有 qid/title/body/tags，交盲标实例
"""
import os, re, json, html, time, random, urllib.request, gzip, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
API = "https://api.stackexchange.com/2.3/questions"
SEED = 20260922
STRATA = 8
PER_STRATUM = 5

PRE = ["2021-%02d" % m for m in range(6, 13)] + ["2022-%02d" % m for m in range(1, 12)]
POST = ["2022-12", "2023-01", "2023-03", "2023-06", "2023-09", "2023-12",
        "2024-03", "2024-06", "2024-12", "2025-06", "2025-12", "2026-05"]
MONTHS = PRE + POST


def month_bounds(ym):
    y, m = int(ym[:4]), int(ym[5:])
    import calendar, datetime as dt
    a = dt.datetime(y, m, 1, tzinfo=dt.timezone.utc)
    ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
    b = dt.datetime(ny, nm, 1, tzinfo=dt.timezone.utc)
    return int(a.timestamp()), int(b.timestamp())


def strip_html(s, maxlen=1400):
    """与主面板的 fetch_so_questions.strip_html 同一套规则，逐字照抄，
    否则新旧两批题面长度/结构不同，分类器看到的东西就不可比。"""
    s = s or ""
    s = re.sub(r"<pre[\s\S]*?</pre>", " [CODE] ", s, flags=re.I)
    s = re.sub(r"<code>[\s\S]*?</code>", " [code] ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:maxlen]


def get(url, tries=4):
    for k in range(tries):
        try:
            raw = urllib.request.urlopen(url, timeout=40).read()
            try:
                raw = gzip.decompress(raw)
            except Exception:
                pass
            return json.loads(raw.decode("utf-8"))
        except Exception as e:
            if k == tries - 1:
                raise
            time.sleep(2 + 3 * k)


def fetch():
    rng = random.Random(SEED)
    out, calls, quota = [], 0, None
    for ym in MONTHS:
        a, b = month_bounds(ym)
        width = (b - a) // STRATA
        for k in range(STRATA):
            lo = a + k * width
            hi = a + (k + 1) * width if k < STRATA - 1 else b
            start = rng.randint(lo, max(lo, hi - 3600))   # 层内随机起点
            u = ("%s?site=stackoverflow&tagged=python&fromdate=%d&todate=%d"
                 "&sort=creation&order=asc&pagesize=%d&filter=withbody"
                 % (API, start, hi, PER_STRATUM))
            d = get(u)
            calls += 1
            quota = d.get("quota_remaining", quota)
            for it in d.get("items", []):
                out.append({"question_id": it["question_id"],
                            "creation_date": it["creation_date"],
                            "ym": ym, "stratum": k,
                            "title": it.get("title", ""),
                            "body": strip_html(it.get("body", "")),
                            "tags": it.get("tags", []),
                            "is_answered": int(bool(it.get("is_answered"))),
                            "answer_count": it.get("answer_count", 0)})
            time.sleep(0.4)
        print("  %s  cum=%d  calls=%d  quota=%s" % (ym, len(out), calls, quota), flush=True)
        if quota is not None and quota < 15:
            print("  !! 配额将尽，停在 %s" % ym)
            break

    # 去重：层边界附近可能重复取到同一题
    seen, uniq = set(), []
    for r in out:
        if r["question_id"] not in seen:
            seen.add(r["question_id"])
            uniq.append(r)
    json.dump(uniq, open(os.path.join(HERE, "R1_uniform_raw.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    print("\n抓到 %d 题（去重后），覆盖 %d 个月，用了 %d 次调用"
          % (len(uniq), len(set(r["ym"] for r in uniq)), calls))
    return uniq


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.parse_args()
    fetch()
