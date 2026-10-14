# 评分会话启动上下文与工具调用审计(set12k, 100 批)

脚本 audit_sessions.py；会话识别沿用 wave_verify.sessions()（每批恰 1 个会话，共 100）。assistant 轮 1307，模型 {'claude-sonnet-5': 1307}。记录行时间戳 2026-10-12T23:16:37.018Z 至 2026-10-13T00:06:16.728Z。

## B1 启动上下文注入来源（会话数）

| 来源（pre=首条 assistant 之前；post=之后） | 会话数 |
|---|---|
| post|attachment:agent_listing_delta | 100 |
| post|attachment:auto_mode | 100 |
| post|attachment:hook_success | 14 |
| post|attachment:mcp_instructions_delta | 100 |
| post|attachment:prompt_snapshot | 100 |
| post|attachment:read_truncation_notice | 100 |
| post|attachment:total_tokens_reminder | 100 |
| post|user_meta_reminder | 5 |
| pre|attachment:credential_org | 100 |
| pre|attachment:date | 100 |
| pre|attachment:deferred_tools_delta | 100 |
| pre|attachment:environment | 100 |
| pre|attachment:model | 100 |
| pre|attachment:prompt_snapshot | 100 |
| pre|attachment:remote_session_change | 100 |
| pre|attachment:skill_listing | 100 |
| pre|instructions:CLAUDE.md | 100 |
| pre|instructions:MEMORY.md | 100 |
| pre|instructions:preamble | 100 |
| pre|record_meta_cwd | 100 |
| pre|session_context:gitStatus | 100 |
| pre|session_context:userEmail | 100 |
| pre|task_prompt | 100 |
| pre|user_meta_reminder | 100 |

hook_success 明细：{('PreToolUse', 'PreToolUse:PowerShell', '"D:\\python.exe" "C:\\Users\\<user>\\.claude\\hooks\\runlog_wrap.py"'): 2, ('PreToolUse', 'PreToolUse:Bash', '"D:\\python.exe" "C:\\Users\\<user>\\.claude\\hooks\\runlog_wrap.py"'): 12}

无 SessionStart hook 注入：首条 assistant 之前的 attachment 类型中没有 hook_success 一类；post 段的 hook_success 仅是 PreToolUse 的 runlog_wrap。字符串 `STATE.md` 只作为说明文字出现（CLAUDE.md 的交接约定、handoff 技能说明等），命中来源（会话数）：pre|attachment:skill_listing=100; pre|instructions:CLAUDE.md=100; pre|session_context:gitStatus=100；没有任何 STATE.md 文件内容被注入。

## B1 指定串命中（会话数）

| 串 | 启动上下文并集(pre) | 全部注入并集(pre+post) | 命中来源（会话数） |
|---|---|---|---|
| `0.199` | 100 | 100 | pre|instructions:MEMORY.md=100 |
| `0.002` | 100 | 100 | pre|instructions:MEMORY.md=100 |
| `r1_随机重抽` | 100 | 100 | pre|attachment:environment=100; pre|record_meta_cwd=100; pre|session_context:gitStatus=100 |
| `draw_all.csv` | 100 | 100 | pre|session_context:gitStatus=100 |
| `panel_map` | 0 | 0 | — |
| `随机` | 100 | 100 | pre|attachment:environment=100; pre|record_meta_cwd=100; pre|session_context:gitStatus=100 |
| `random` | 0 | 0 | — |
| `first 100` | 0 | 0 | — |
| `最早` | 0 | 0 | — |
| `Selective` | 100 | 100 | pre|instructions:MEMORY.md=100 |
| `γ` | 0 | 0 | — |
| `0.304` | 0 | 0 | — |
| `0.30` | 0 | 0 | — |
| `0.42` | 0 | 0 | — |
| `userEmail`（正对照） | 100 | 100 | pre|session_context:userEmail=100 |
| `Contents of`（正对照） | 100 | 100 | pre|instructions:CLAUDE.md=100; pre|instructions:MEMORY.md=100 |
| `ZZZ_NOT_PRESENT_9a7f`（负对照） | 0 | 0 | — |
| `random`（忽略大小写） | 0 | 0 | — |
| `first 100`（忽略大小写） | 0 | 0 | — |

禁区名称在**注入的启动上下文**中的出现（按来源，会话数）：

- `rate_private\`：无
- `panel_map*`：无
- `draw\`：pre|session_context:gitStatus=100
- `draw_all.csv`：pre|session_context:gitStatus=100
- `bodies\`：pre|session_context:gitStatus=100
- `population\`：无
- `question_labels_python*`：无
- `R2_blind\`：无
- `r1_随机重抽`：pre|attachment:environment=100; pre|record_meta_cwd=100; pre|session_context:gitStatus=100

## B2 工具调用是否触及禁区

tool_use 共 788 次（{'Read': 300, 'Write': 128, 'Bash': 245, 'SubagentHandback': 100, 'PowerShell': 15}），分布在 100 个会话；tool_result 788 条。禁区正则：rate_private\、panel_map*、draw\、draw_all.csv、bodies\、population\、question_labels_python*、R2_blind\、r1_随机重抽；路径含 R3_blind\set12k 者剔除（剔除 0 处）。

- 工具**输入**命中：**0** 次
- 工具**结果文本**命中（会话"看到"禁区文件名）：**14** 次，其中 14 处是 runlog 日志路径（PreToolUse hook 用 cwd 派生的日志路径名，14 个会话，即有 hook_success 的会话）、0 处其余（题面里的普通英文词等，见 log）
- 工具结果文本中 B1 指定串命中会话数：`0.199`=0；`0.002`=2；`r1_随机重抽`=14；`draw_all.csv`=0；`panel_map`=0；`随机`=14；`random`=93；`first 100`=6；`最早`=0；`Selective`=0；`γ`=0；`0.304`=0；`0.30`=2；`0.42`=2
- 列目录/Glob/Grep 类调用 22 次；cd 到 scratchpad/set12k 以外目录或含 ../ 的 Bash/PowerShell 命令 7 次（路径串检索看不到相对路径，故单列，见 audit_sessions.log）。

## B3 各会话读过的文件路径集合

Read 工具：去重路径 101 个（原样），批号归一（blind_batch_### / labels_batch_###）后 2 类；每会话 Read 的路径数 2 至 2。

| 归一后路径 | 会话数 |
|---|---|
| `<projects>\P9b_OSF_复现包_20260920\01_panels_and_classification\CLASSIFY_RUBRIC.md` | 100 |
| `<workdir>\工作文档\R3_blind\set12k\blind_batch_###.json` | 100 |

全部来源（Read/Write/Edit/Glob/Grep 参数 + Bash/PowerShell 命令内路径形字符串）去重后 308 个（原样），批号归一后 111 类；分类计数：cmd:Bash=157; cmd:PowerShell=15; tool:Read=101; tool:Write=128。全表见 audit_sessions_paths.csv。

命令内路径是"命令文本里出现过"，不区分读与写；Read 工具的清单才是确证的读取。
