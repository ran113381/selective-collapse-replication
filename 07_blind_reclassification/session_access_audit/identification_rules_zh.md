# 盲评会话文件访问清单:识别规则(导出前写定,2026-09-27)

本文件在运行 `SIM27_access_audit.py` 导出之前写成;脚本按此执行,规则若在导出后改动,须在本文件末尾追加并写明理由,不回改正文。

## 数据来源与可用字段

- 来源:`C:\Users\<user>\.claude\projects\E-------\<父会话>\subagents\agent-*.jsonl`(子代理会话记录);父会话记录 `E-------\<父会话>.jsonl` 只用于正对照。
- 只读以下结构化字段:
  - `type`、`timestamp`、`message.role`、`message.model`;
  - 助手消息里 `tool_use` 块的 `name` 与 `input`(只从 `input` 中取路径与命令首词,不导出命令全文);
  - 用户消息里 `tool_result` 块的文本,只用来检索下列「观察名单」文件名是否出现,不导出结果文本。
- 不读、不导出:助手的 `text`/`thinking` 块;首条用户消息(任务书)的文本;`attachment` 行(其中可能含注入的项目说明或记忆索引,不属于会话主动访问,不在本清单范围内);`*.meta.json`。

## 两组会话的识别

**组 H(头条盲评,Claude Sonnet 5,S20)**:子代理会话中存在一次 `tool_use`,其 `input` 的任一字符串字段含有指向 `工作文档/R2_blind/R2_labels_batch_NN.json` 的路径(分隔符 `/`、`\`、`\\` 均认;目录名须恰为 `R2_blind`,`R2_blind_s46` 等不算),且该会话首条时间戳落在 2026-09-23T00:00Z 至 2026-09-25T00:00Z。批号 NN 取自该路径。写出方式记为:`Write`/`Edit` 的 `file_path` 命中 → `write_tool`;否则经 `Bash`/`PowerShell` 命令命中 → `via_command`。

**组 W(抽样窗检验评分,Claude Opus 5,S19)**:同上,路径为 `工作文档/R1_labels_batch_NN.json` 或 `工作文档/R1c_labels_batch_NN.json`(直接位于 `工作文档` 下),首条时间戳落在 2026-09-22T00:00Z 至 2026-09-23T00:00Z。设计记为 `uniform`(R1)或 `panel_subsample`(R1c)。

识别只用写出目标,不用 `message.model`(模型是被报告的量,不作选择条件),也不用任务书文本。预期:组 H 恰 50 个会话、批号 01–50 各一;组 W 恰 20 个会话、R1 与 R1c 各 01–10 各一。不符即中止,不导出。

## 观察名单(映射与带日期的文件)

- 组 H 的输入目录 `工作文档/R2_blind/`:`R2_token_map.json`(不透明编号 → 题号)、`R2_ym_map.json`(题号 → 月份)。另列入观察:`question_labels_python_blind.csv`、`within_so_llm_panel_python_blind.csv`、`ids_list.txt`、`R2_design_sha256.txt`、`R2_设计书` 字样(设计书)。
- 组 W 的输入目录 `工作文档/`:`R1_token_map.json`、`R1c_token_map.json`(不透明编号 → 题号)、`R1_uniform_raw.json`(按抓取原样保存的抽样题,含每题创建时间)、`R1_month_compare.csv`。
- 两组共同再列:`question_labels`、`within_so_llm_panel`、`so_questions_`、`_result.json`、`设计书`(面板、原始题面、结果与设计书)。

## 每个会话判定的量

1. `map_in_tool_input`:任一 `tool_use.input` 的字符串字段里出现本组的映射文件名(组 H:`R2_token_map`、`R2_ym_map`;组 W:`R1_token_map`、`R1c_token_map`、`R1_uniform_raw`)。这是「打开过」的上界:凡 Read、cat、Get-Content、python open 等打开动作都必然在输入里写出文件名。
2. `map_read_tool`:`Read` 工具的 `file_path` 是映射文件(「打开过」的确证)。
3. `watch_in_tool_input`:输入里出现观察名单中任何一项(映射之外)。
4. `dir_listed`:列过本组输入目录——`Bash`/`PowerShell` 命令含 `ls`、`dir`、`Get-ChildItem`、`gci`、`find`、`tree` 且含输入目录路径;或 `Glob`/`LS` 的路径或模式落在输入目录。
5. `map_name_in_results`:任一 `tool_result` 文本中出现本组映射文件名(即列目录等操作让会话「看到了文件名」)。
6. `paths`:从 `tool_use.input` 取出的全部文件路径(`file_path`、`path`、`notebook_path`、`pattern` 字段,以及命令中的路径形字符串),按下文脱敏。

## 脱敏

- `E:\智能体论文\P9b_IPM_20260919\` → `<workdir>/`;`E:\智能体论文\` → `<projects>/`;
- `C:\Users\<任何用户名>\AppData\Local\Temp\claude\<项目>\<会话>\scratchpad\` → `<scratchpad>/`;`C:\Users\<任何用户名>\.claude\` → `<claude_home>/`;其余 `C:\Users\<任何用户名>\` → `<home>/`;
- 同样处理 `/c/Users/...`、`C:/Users/...`、`/e/智能体论文/...` 等写法;分隔符统一为 `/`。
- 导出后断言:输出文件中不出现 `Users/` 或 `Users\` 后接真实用户名、不出现本机用户名字符串、不出现盘符绝对路径。

## 正对照与应失败样本

- 正对照:对建批的主会话记录(父会话 `.jsonl`,即组 H 各会话的父会话)用同一检测函数,`map_in_tool_input` 必须为真(建批脚本读写过映射)。组 W 的父会话同样。
- 应失败样本:一段合成记录,含一次 `Read` 映射文件与一次 `ls` 输入目录、结果中含映射文件名;检测函数必须三项全判真。另一段只 `Read` 量表与本批输入的合成记录,三项必须全判假。任一不符即中止。

## 追加 1(2026-09-27,首次运行后、任何导出之前)

首次运行在「识别」一步按规则中止:组 H 只识别出 49 个会话,缺批 15。未写出任何输出。定位(只看工具调用名称与输入):批 15 的会话先把标签写进自己的草稿目录,再以一条命令 `cd` 进 `工作文档/R2_blind` 后用相对路径 `./R2_labels_batch_15.json` 复制过去;原规则只认含 `工作文档/R2_blind/` 前缀的路径,故漏认。

改动:组 H 与组 W 的识别另认一种写法——同一条 `Bash`/`PowerShell` 命令里既 `cd` 进本组输入目录(组 H 为 `工作文档/R2_blind`,组 W 为 `工作文档`),又以不带目录前缀的相对路径(可带 `./`)写出 `R2_labels_batch_NN.json`(组 W 为 `R1_labels_batch_NN.json`/`R1c_labels_batch_NN.json`)。写出方式记为 `via_command`。「每批恰一个会话」的断言不变,多认即中止。其余规则不变。

## 追加 2(2026-09-27,第二次运行后、任何导出之前)

第二次运行在「识别」一步按规则中止:组 H 已得 50 个会话、批 01–50 各一;组 W 得 21 个,R1c 第 09 批缺失,R1 第 01 批、R1c 第 01 与 05 批多认。未写出任何输出。定位(只看工具调用名称与输入、时间戳与 message.model):
- 多认的 2 个会话在另一父会话下、始于 2026-09-22T11:10Z,message.model 为 claude-fable-5-1,工具调用是读稿件与结果文件、`cd 工作文档` 后 `cat` 结果;它们在命令里提到标签文件名,不是评分会话。
- R1c 第 09 批的会话在命令内的 Python 字符串里把 `工作文档` 写成了 `工作文档` 转义形式,原规则只认字面形式。

改动:(a) 匹配前,把工具输入字符串里的 `\uXXXX` 转义还原为字符再匹配(只用于识别与检索,不改导出的路径以外的任何东西);(b) 识别另加一条必要条件——该会话的工具输入恰好指名一个本组输入批文件(组 H `R2_blind_batch_NN.json`,组 W `R1_blind_batch_NN.json` 或 `R1c_blind_batch_NN.json`),且其批号与设计同写出的标签文件一致,写出的标签文件也恰为一个。仍不用 message.model 作选择条件(上面提到模型只是定位时的描述)。「每批恰一个会话」的断言不变。

## 追加 3(2026-09-27,第三次运行后;该次输出只写到草稿目录,未进复现包)

第三次运行通过全部识别断言与正对照,输出写到本会话草稿目录。复看输出时发现第 4 项「列过输入目录」判得过宽:组 H 的 8 个「列过目录」里有 7 个是 `ls -la` 列自己刚写出的单个标签文件(路径以 `…/R2_blind/R2_labels_batch_NN.json` 结尾),不是列目录。原规则写的是「含输入目录路径」,而单个文件的路径也含目录路径。

改动:第 4 项只在列表命令的目标就是目录本身时判真——路径止于 `R2_blind`(组 H)或 `工作文档`(组 W),其后只能是分隔符、引号、空白、行尾或通配符 `*`;`Glob`/`LS` 同理。另加一列 `map_file_names_seen_in_tool_results`,逐会话列出结果中出现的映射文件名。另记:观察名单中的 `ids_list.txt` 经查是批 42 的会话在该目录里自己写出的临时文件(3 字节,写于 2026-09-23T10:30:44Z),不是映射或数据;命中的 3 个会话是批 42 自己与另两个在各自草稿目录写同名临时文件的会话。该项保留在观察名单中照实输出,不删。其余规则不变。

更正(同日,追加 3 写完后核对):另两个会话分别是批 22(写在它自己的草稿目录)与批 04(写在临时目录 `Temp/claude/` 下,不在草稿目录);三者都是会话自己写出的题号清单,不是读入。

## 追加 4(2026-09-27,第四次运行后;输出仍只在草稿目录)

第四次运行中组 H 仍有一个「列过目录」是假阳:批 37 的命令先 `cd` 进 `R2_blind`,再用 heredoc 写一个脚本,脚本里的评分理由文字含英文单词(如 tree、find),被当成了列表命令。原判据只要求命令里任意位置出现这些词。

改动:把命令按 `&&`、`||`、`;`、`|`、换行切成语句,只看以 `ls`、`dir`、`Get-ChildItem`、`gci`、`find`、`tree` 开头的语句;该语句自身的参数指向本组输入目录(止于目录本身),或该语句不带路径参数而此前语句已 `cd` 进本组输入目录,才判「列过目录」。应失败样本另加两条:heredoc 正文里出现 `tree` 不判真;`cd` 进目录后裸 `ls` 判真。其余规则不变。
