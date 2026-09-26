# SO 问题 AI-可替代性分类 rubric (component B)

给每个 Stack Overflow python 问题判定 **AI-可替代性**:一个有能力的 LLM 能否**仅凭问题文本**就给出完整正确答案,无需提问者的特定运行时上下文、专有代码、或多轮往返。

## 0–4 评分

- **4 = 纯 GENERATION**:概念/算法/标准 how-to,自足,有唯一标准答案,ChatGPT 一次答对。
  例:"如何一行读三个整数"、"为什么 `300 is 301-1` 返回 True"、"求树的所有根到叶路径"、"classmethod+property 在 3.11 的替代"。
- **3 = 偏 generation**:标准做法 + 轻微上下文。
  例:"按后缀 merge 多个 dataframe"、"按 config 重命名 CSV 列"、"pandas 多条件赋值"。
- **2 = 混合/偏 verification**:需要一些判断或提问者的具体设置。
  例:"Dash 回调我快写好了但缺点东西"、"mypy 拒绝我的 protocol 实现"。
- **1 = VERIFICATION**:调试提问者的具体报错/代码/环境、在其数据上调性能、生产环境特定。
  例:"conda proxy 在家庭 wifi 失败"、"merge 把内存撑到 1.6TB"、"celery 高负载下重复队列"。
- **0 = 纯 verification**:完全受上下文/判断约束,仅凭文本无法回答。

## 标签
`label = "GEN" if score >= 3 else "VER"`

## 关键原则
- 按问题的**内在类型**判定,**忽略提问时间**(不要推断 ChatGPT 前后)。
- 看 title + tags + body_excerpt;`[CODE]`/`[code]` 是被折叠的代码块标记。
- 判断核心:答案是"生成一段标准代码/解释"(GEN) 还是"对这个人的具体情况做诊断/权衡"(VER)。

## 输出格式
对每题输出 `{"question_id": <int>, "score": <0-4>, "label": "GEN"|"VER", "why": "<=12 词理由>"}`,汇总成一个 JSON 数组。
