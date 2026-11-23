# Muse 自动化 CLI（translation-agent）

Felix 的个人助手 Muse 经 SSH 按需调用翻译服务：**检测自动，动作确认**。Muse 负责定时检测、通知、征求确认、
轮询、交付和保存水位线；翻译服务只提供能力，凭证不出服务器。

```
Muse ──SSH（受限密钥）──> ~/bin/translation-agent <子命令>   （src/cli/automation.py，只用标准库，跑完就退出）
                               │ 直连本机，不读凭证
                               ▼
                 127.0.0.1:54321/internal/automation/*         （src/api/routers/automation.py）
```

- 接口挂在 `/internal/automation`，**不在 `/api` 下**：nginx 只转发 `/api/`、`/ws/`，公网到不了；接口再拒绝带
  `X-Forwarded-For` / `X-Real-IP` / `Forwarded` / `CF-Connecting-IP` 的请求和非本机来源（403）。
- 逻辑都在后端进程里：文章清单在后端内存里、翻译是后端的后台任务，CLI 另起进程去改会互相覆盖。
- 入口：`~/bin/translation-agent` → `~/releases/translation-agent-current/translation-agent-cli`，跟着线上版本走。

## 契约

所有子命令：stdout 只有一个 JSON 对象，日志写 stderr；退出码 0 成功、1 参数错误、2 连不上服务、3 服务返回错误；
失败时 JSON 是 `{"error": "...", "code": "..."}`。输出前过一遍脱敏正则（xox*-、sk-、AIza、substack.sid、Bearer……）兜底。

| 命令 | 说明 |
| --- | --- |
| `updates --since <ISO 或 Unix 秒/毫秒>` | 先同步（Substack 最新一页、Slack 只读同步），返回 `new_articles`（`published_at > since`）、`mentions`（`ts > since`）、`watermark`。可能带 `warnings`（某一边同步失败） |
| `translate-article <slug 或 Substack 链接> [--engine web\|claude\|codex\|antigravity]…` | 导入（已导入复用）→ 按 `--engine` 起翻译，**可写多次同时翻**（默认 `web`）。`web` = 网页版四步法，自动采用术语建议；`claude` / `codex` / `antigravity`（agy）= 交给 Claude 页的 Agent 跑 four-step-translate，后台每分钟看一次，翻完自动导回成该 Agent 的译本（`{项目}--codex` 等）。返回 `engines`：每个引擎 `started` / `resumed` / `already_exists`（在跑或已译完，附 `translation_status`）/ `failed`（附 `error`）；只给 `web` 时结果也平铺在顶层（老格式） |
| `slack-todos` | **我要处理什么**：和网页 Slack 页「我的待办」同一份。`items` 是找我的事（私信、thread 里直接 @我），每条有 `task`（谁要我干什么）、`action`（`reply` 要回复 / `do` 要做事，多半是翻译 / `read` 看看就行）、`conversation_id`、`thread_ts`、`draft`（已有翻译稿时给 `draft_id`、`status`）；`fyi` 是只被群发 @ 到的，不用处理 |
| `dms` | **私信**：还没回的每条私信给 `messages`（对方的英文原话，未读的那几条）、`task`（找你干什么，中文）、`translation`（中文理解）、`replies`（A 简洁 / B 标准 / C 正式，各有 `english`、`chinese`）、`link`。和网页私信回复面板同一套输入（对方在你最后一次发言之后的消息 + 之前的对话），结果也存进面板历史，网页上能看到同一组；对方没发新消息就直接用存着的，**定时拉不重复花钱**。一次最多新生成 10 条，其余带 `note`，下次再生成 |
| `drafts [--status draft\|done\|all] [--sent yes\|no] [--source slack\|manual] [--q 关键词] [--limit 50]` | **翻译记录**（网页「我翻译的」/「全部翻译记录」）。默认 `--status draft`：还没点「标记完成」的。每条有 `draft_id`、`title`、`preview`（译文开头）、`versions`（0 = 只提取了原文还没出译文）、`image_count`、`auto`（后台或 Muse 自动翻的）、`sent_at`（标记已发送的时间，没标过 null；和 `status` 无关）、`sent_changed`（标了之后译文又改过）。`--sent no` 只看还没发的 |
| `draft <draft_id> [--no-images]` | **一份翻译结果**：`source_text`（要翻的英文）、`translation`（当前版译文）、`titles` / `selected_title`、`slack.permalink`、`link`（网页打开这份稿子），`images` 按发帖顺序给**原图**：`n`、`name`、`mimetype`、`size`、`sha256`、`data_base64`（单张 >30MB 或合计 >100MB 的只给元数据和 `error`）。`--no-images` 只给元数据 |
| `optimize-draft <draft_id> (--option X \| --instruction 要求)` | **快捷指令优化**翻译稿，和网页帖子翻译的优化按钮同一套：`coherence` 更连贯 / `readable` 可读性 / `idiomatic` 地道 / `professional` 专业（4 个快捷项），`shorten` 精简 / `expand` 展开说明 / `formal` 正式公文 / `story` 故事化 / `qa` 问答格式 / `social` 社交媒体（「更多…」，指令在 `config/post_more_options.json`，网页同一份），或 `--instruction` 自定义一句话。在当前版上优化，存成新版本并设为当前（网页上能看到、能切回），最近 3 次要求作为上下文带上。返回和 `draft --no-images` 一样的结果 |
| `translate-slack-post <conversation_id> <thread_ts> [--instruction 说明] [--no-images]` | 把一个 thread 当帖子翻，和网页「翻译这个帖子」同一条流程：提取原文和配图 → 翻译 → 生成标题，存成翻译稿（标成自动翻的），返回和 `draft` 一样的结果。已有稿子时追加新版本。`--instruction` 用在 AI 挑错了时（如「翻第二版文案」）。几十秒到两分钟 |
| `translate-slack <conversation_id> <message_ts> [--thread-ts T] [--with-thread]` | 翻译任意一条 Slack 消息的正文或它所在的整个 thread（不存翻译稿；翻帖子用上面的 `translate-slack-post`），**同步**返回 `translation`，`status` 为 `done`（新翻）或 `already_exists`（同样内容翻过，直接给缓存）；`project_id` 形如 `slack-<会话>-<ts>[-thread]` |
| `translate-post [原文] [--hashtags]` | **直接翻一段帖子原文**（推文、公众号段落……），和网页「帖子翻译」同一条链路（术语库、帖子翻译默认模型），同步返回 `translation`、`model`；不存翻译稿。默认不加话题标签，`--hashtags` 才在末尾加小红书标签。上限 10000 字符 |
| `slack-reply [内容] [--mode auto\|incoming\|compose] [--history JSON]` | **帮 Felix 回 Slack**，和网页「Slack 回复」同一套。对方的英文消息（`incoming`）→ `translation`（中文理解）+ `replies`（3 版英文回复）；Felix 的中文草稿（`compose`）→ `replies`（3 版英文）。每版有 `version`（A/B/C）、`style`、`english`、`chinese`。`auto` 按中文占比判断，返回的 `mode` 是实际用的。`--history` 给之前的对话：`[{"role":"them\|me","content":"..."}]` |
| `status <project_id> [--with-markdown] [--engine E]` | 文章：`running`（附 `stage`）/ `done`（`result` 是翻译服务链接）/ `failed`（`error`）/ `not_started`，看的是网页上显示的主译本；带 `zh_title`、`zh_summary`。`engines` 给每个引擎各自的进度（`web` 总有；Agent 只列起过的）：`running` / `done`（附 `variant_id`）/ `failed`（附 `error`）。`--with-markdown` 完成时附中文 Markdown 全文，`--engine codex` 就给 Codex 那一版。`slack-…`：`done`，`result` 是译文 |
| `articles [--status unsent\|sent] [--limit 50]` | 导入过的文章里 **译完还没发的**（`unsent`，默认，按发布时间从新到旧）或 **已发送的**（`sent`，按标记时间从新到旧）。每条有 `project_id`、`title`、`zh_title`、`url`、`published_at`、`sent_at`、`result`（翻译服务链接）。只读，不去 Substack 同步 |
| `mark-sent <project_id\|draft_id> [--undo]` | 把文章或翻译稿标记为**已发送**（Felix 在系统外发出去之后），和网页上「标记已发送」是同一个记录（`m_…` / `s_…` 按翻译稿，其余按文章）；`--undo` 撤销。返回 `sent_at`。`status`、`updates` 里的文章也带 `sent_at`（`updates` 的 `status` 标过就是 `sent`） |
| `health` | `substack` / `slack` / `models` / `agents` 各自 `ok` 或 `error: …`（`models` 只检查配置，不发请求；`agents` 是能不能调通 Claude 页）；`slack_groups` 是自动识别 / 手配的用户组个数 |

### updates 细节

- **watermark = 这次调用开始同步那一刻**（UTC ISO），不是数据里的最大时间：同步期间新到的下次还会出现，不漏；
  极少数会重复一次，Muse 按 `slug`、`conversation_id + message_ts` 去重。Slack 同步失败时 watermark 不前进（= since）。
- **私信**（`dm`）：私信和群聊私信里别人发的每一条都返回（不管有没有 @，含 thread 回复；不含自己发的、Slackbot / bot、入群改名这类系统消息）。
- **其余会话的 mention_type**：`direct`（`<@U0A8T7U5D7A>`）> `group`（`<!subteam^ID>` 且 ID 在 `AUTOMATION_SLACK_GROUP_IDS` 里）>
  `channel`（`<!channel>` / `<!here>` / `<!everyone>`）；一条只返回一次，取最强的一类；自己发的不算；只在链接卡片里出现的不算。
  企业版工作区查不了 `usergroups.*`：「我所在的组」先从 `client.userBoot` 的 `subteams.self` 自动识别，再并上
  `AUTOMATION_SLACK_GROUP_IDS`（逗号分隔，`.env` 里设）。`health` 的 `slack_groups` 能看到两边各几个，都是 0 时 group 为空。
- 每条 mention 带 `thread_ts`（thread 里的回复才有）和 `permalink`，翻译时把 `thread_ts` 原样传给 `translate-slack --thread-ts`。
- 先从本地副本 `slack.db` 查；本地只同步 Felix 参与的 thread，所以再用 `search.messages`（只读）搜 `<@U0A8T7U5D7A>` 兜底，
  补上没参与、Slack 也没自动订阅的 thread 里的 @。搜索索引有延迟，每次往回多看 30 分钟；搜到的存进本地副本，
  靠「本地有没有」去重，同一条只报一次（`translate-slack` 也能直接找到）。搜索失败只记日志，照常返回本地结果。
- **只读**：Slack 走现有只读白名单；不碰翻译服务本地已读（`read_state`）；不导入、不翻译。

### Muse 的典型用法（三个场景，Muse 定时拉，Felix 只核对、选择）

1. **帖子里 @我**：`drafts` 看后台自动翻好的稿子（`slack-todos` 里 `action: do` 且 `draft` 为空的，可 `translate-slack-post` 补翻）→
   Felix 要时 `draft <id>` 给完整译本（原文、译文、标题、原图）→ Felix 说「更地道」「精简」「第二段别用赋能」→ `optimize-draft`；发出去后 `mark-sent <draft_id>`，`drafts --sent no` 查还没发的。
2. **SemiAnalysis 新文章**：`updates` 拿到新文章（带中文标题、摘要）→ Felix 决定翻不翻、用什么翻（可多选）→
   `translate-article <slug> --engine web --engine codex` → 定时 `status <project_id>` 看 `engines`，翻完给链接或 `--with-markdown --engine X` 全文。
   Felix 发出去后 `mark-sent <project_id>`；`articles` 随时查还有哪些翻完没发。
3. **私信**：`dms` → 每条给英文原话、找我干什么、中文理解、3 版回复 → Felix 挑一版自己复制发（翻译服务对 Slack 只读）。

### Agent 翻译（`--engine claude/codex/antigravity`）细节

- 做的是网页文章页「交给 Agent 翻」同一套（`web/frontend/src/features/articles/lib/claude.ts`），只是搬到了后端（`src/services/agent_translate.py`）：
  上传 `source.html` 到 Claude 页跑 four-step-translate（等术语确认 10 分钟没人回自动按推荐继续）→ 这一轮结束、不在等确认 →
  取同一目录的 `zh.md` / `en.md` → 对齐导成该 Agent 的译本。不依赖有人开着网页；网页工作台也能看到这个任务（写了 `claude_run_id`）。
- **登录**：后端读 Claude 页的 env 文件（`SKILL_RUNNER_ENV_FILE`，默认 `~/.config/skill-runner/env`）里的口令，按 skill-runner 同样的算法签 cookie
  （2026-11-23 用户选的方案：直接用口令，不另建专用凭证）。口令不落盘、不打日志。改了 Claude 页口令不用改翻译服务。
- 任务记录在 `data/automation_agent_runs.json`（`AUTOMATION_AGENT_RUNS_FILE`），后台每 60 秒轮询一次，翻译服务重启后接着看。
- 失败（`engines.<agent>.status = failed`）：Agent 出错、这一轮结束却没找到 `zh.md`/`en.md`、英文稿和原文对不上（<80% 段落）、
  Claude 页里任务被删。重新 `translate-article --engine <agent>` 会再起一次。
- Agent 跑一篇要几十分钟，占 Claude 页并发名额（最多 3 个，满了排队）。

### translate-article 细节

- 后端一把锁串行处理，同一篇并发调用只会导入一个项目、起一次翻译；翻译槽被网页那边占了（409）也当 `already_exists`。
- 直接调 `start_longform_workflow`（绕过网页用的 3 次/分钟限流），参数等于网页「一键翻译」+ `auto_accept_terms`。
- Muse 起的翻译在跑时，翻译服务发版的 precheck 会拦住，和网页起的一样。

### slack-todos / drafts / draft / translate-slack-post 细节

- `slack-todos` 直接调网页待办的同一个函数（未读的私信和 @我，最近几天），会调一次轻量模型（`task: slack`）概括每件事，结果有缓存；不改 Slack、不改翻译服务已读。
- `drafts` / `draft` 只读 `data/post_drafts/`；提取后发现没有要发的帖子（纯讨论）的稿子不进 `drafts`，`draft` 直接查时 `no_post: true`、`note` 说明原因。
- 配图来自 Slack 文件（只读下载、本地有缓存）；某张拿不到时那一张带 `error`，不影响其余。
- `translate-slack-post` 与网页、后台自动翻译共用每个 thread 一把锁，不会同时跑两遍；模型同网页（提取 `task: slack`，翻译、标题走帖子翻译默认模型）。

### translate-slack 细节

- 原文：只读消息正文，不读链接卡片（和帖子提取一致）；`--with-thread` 时是整个 thread，每条前面标作者。Slack 用户提及换成名字。
- 走帖子翻译链路（术语库），模型固定 `gpt-6.2-sol`（和 Slack 页一致），不加话题标签；超过 10000 字符拒绝。
- 结果存 `data/slack_cache/automation_translations.json`，按原文 hash 判断：内容没变直接返回缓存，消息被编辑过才重新翻。
- 一把锁串行；Slack 端照旧只读（只读本地副本，缺了才用白名单里的 history / replies 补拉）。

## SSH 受限密钥

给 Muse 单独一把密钥，在 `~/.ssh/authorized_keys` 里写成：

```
command="/home/zxw/bin/translation-agent --ssh",no-pty,no-port-forwarding,no-agent-forwarding,no-X11-forwarding,no-user-rc ssh-ed25519 AAAA... muse
```

`--ssh` 从 `SSH_ORIGINAL_COMMAND` 读子命令（开头的 `translation-agent` 可写可不写），只放行上面的子命令，
不允许 `--base-url`，也不认 `TRANSLATION_SERVICE_URL`。Muse 调用：`ssh -p 42022 zxw@<host> translation-agent updates --since ...`。

## 配置（`src/settings.py`）

- `AUTOMATION_SLACK_GROUP_IDS`：Felix 所在用户组 ID，逗号分隔。
- `AUTOMATION_PUBLIC_URL`：交付链接前缀，默认 `https://momo.beauty`。

## 和仓库里其他命令行的关系

`translation-agent` 是本仓库唯一给外部调用的命令行入口（机器人、脚本都用它）。早期给人在终端用的
`translate-post`、`slack-reply` 两个脚本已删除（2026-11-23），功能就是这里的同名子命令。
`src/cli/cost_report.py`、`scripts/*` 是开发 / 运维工具，不给机器人。
