# Slack 收件箱

momo 顶部「Slack」页，布局照原生 Slack 三栏：

- **左栏**：Threads（我参与的 thread）、频道（可展开，列出最近 7 天有回复的 thread）、私信（含群聊私信）；
  未读加粗，@我 显示红色角标。底部「自由翻译」是原来的 Slack 回复助手。
- **中栏**：消息流。日期分隔、同一人 5 分钟内连发合并、打开时在 Slack 的已读位置画「新消息」线，@我 的消息黄底。
- **右栏**：thread 面板，默认「消息」标签页（根消息 + 全部回复，「新回复」线），另有「AI 翻译」标签页。
- 没选会话时中栏显示一段说明：频道 / thread / 私信各是什么，AI 怎么用。会话标题下写明类型（频道、私有频道、私信、群聊私信）。

URL：`/slack?c=<会话>`、`view=threads|reply`、`tc=<会话>&t=<thread_ts>`（右栏 thread）。

## AI：每个 thread / 私信背后一个 skill agent

- **频道 thread → 帖子翻译助手**（skill `slack-post-translate`）：thread 面板默认是「AI 翻译」标签页。agent 找出要发的
  内容（根帖、链接卡片里的 X 帖、`1/N…N/N` 分段取最新版），走 `translate-post`（术语库），再出标题候选。
- **私信 → 回复助手**（skill `slack-dm-reply`）：打开私信时右栏是「AI 回复」。agent 用中文说清对方要什么，
  用 `slack-reply` 给 A/B/C 三版英文；选一版「复制并打开 Slack」，到 Slack 里粘贴发送（momo 从不发送）。
- **点「开始」才启动**（2026-11-17 用户反馈：自动启动太吵、容易排队报错）：thread 面板的「AI 翻译」标签页、私信右栏各有一个说明卡片和「开始」按钮。
  同一时间只跑一个 Slack agent（2 GB 内存），其余在页面上排队、每 15 秒重试。
- 绑定：skill-runner 的 run 带 `source = slack:<会话>[:<thread_ts>]`，同一个 source 只建一个对话；Claude 页的对话列表不显示这些。
- 上下文：`GET /api/slack-inbox/conversations/{id}/agent-context?thread_ts=` 导出 Markdown（作者标「（我）」、链接卡片全文）
  和 `history`（me/them）。前端把它们作为附件交给 agent。之后有新消息，右栏提示「让 AI 重新看」，把最新上下文发给同一个对话。
- 结果：skill 每次都重写运行目录里的 `result.json`，页面据此显示带「复制」按钮的结果卡片；格式见两个 SKILL.md。
- skill 源文件在仓库 `skill_runner/skills/`；`~/.agents/skills/<名字>` 软链接到 `~/skill-runner/src/skill_runner/skills/<名字>`，
  随 skill-runner 一起 `git pull` 更新。

## 模型：全部走官方 GPT Sol（2026-11-17 用户要求）

- 轻量 AI（消息中文、thread 标题和摘要、速览、搜索词改写）、回复工作台、私信回复（`slack-reply`）：都是 `slack` 任务，
  默认模型 `gpt-6.1-sol`（`config/llm_providers.yaml` 的 `task_defaults.slack`，OpenAI 官方直连）。官方路由是隔离的：
  失败只重试同一模型，不降级到 Gemini / DeepSeek；`OPENAI_API_KEY` 失效时 Slack AI 直接报错。
- 帖子翻译助手里的 `translate-post` 和标题接口显式带 `--model gpt-6.1-sol` / `"model": "gpt-6.1-sol"`（「帖子翻译」页本身不变）。
- 两个 agent 本身用 Codex（OpenAI 官方）跑 `gpt-6.1-sol`：前端启动时传 `harness=codex, model=gpt-6.1-sol`，`agents.json` 里也默认 codex。
- AI 缓存键带 `CACHE_TAG`（`src/services/slack_ai.py`），换模型时改它，旧模型的结果不再复用。

## 轻量 AI：消息中文、thread 中文标题和摘要

不走 agent，直接调短文本模型（`task_type="slack"`），`src/services/slack_ai.py`：

- **消息中文**：默认显示英文原文（2026-11-17 用户反馈不要全部自动翻译）。悬停工具条上的「译」翻单条；顶栏「全部中文」开关（全局，默认关）打开后逐条翻。前端 20 条一批 `POST /ai/translate`，
  只翻英文为主的消息（中文、只有链接 / 表情的跳过），带术语库，链接不抄进译文。
- **thread 中文短标题**：侧栏展开频道、Threads 页，`POST /ai/titles`（thread_ts → 根消息原文）。
- **thread 摘要**：thread「消息」页顶部点「用中文总结这个 thread」才生成，`GET /conversations/{id}/threads/{ts}/summary`，含「要你做」一句。
- 缓存：`data/slack_cache/ai/{zh,titles,summaries}.json`，按内容 hash（摘要按最新回复 ts）。改翻译提示词时把
  `ZH_PROMPT_VERSION` 加一，旧缓存自然失效。
- 侧栏 thread / 私信行尾显示 agent 状态：转圈 = 在跑，橙点 = 等你确认，红 ! = 出错，✨ = 已处理（需登录 Claude 页）。

## AI 速览和搜索

- **AI 速览**（侧栏「AI 速览」，`GET /api/slack-inbox/digest`）：每个有未读的会话、每个有新回复的 thread 一段——一句话总结、
  最多 5 条要点、「要你做」。@我 / 有待办的排前面。只读，不标已读；按（会话、thread、已读位置、最新消息）缓存，
  3 段并行，单段失败只在那一段显示。
- **搜索**（侧栏搜索框，`GET /api/slack-inbox/search?q=`）：带中文时 AI 先改写成 2–5 个英文关键词（缓存），再调
  Slack 的 `search.messages`（只读白名单），按时间倒序 30 条。能在 momo 打开的会话直接跳过去（thread 回复同时开右栏），
  其余在 Slack 里打开。

## 接入方式

- 用个人网页会话凭证：`xoxc-` token + `d` cookie（`xoxd-`），不需要装 Slack App。
- 凭证存 `data/slack_credentials.json`（600，格式 `{"token": "...", "cookie_d": "..."}`）；失效时页面会弹出表单重新填写，只写不回显。
- 缓存：`data/slack_cache/`（用户名、附件、AI 结果、消息库）；会话列表在内存里缓存 30 秒，`client.userBoot` 5 分钟。

## 本地副本（`data/slack_cache/slack.db`，`src/services/slack_store.py`）

消息存在服务器上，页面一律从本地读；向 Slack 只要本地没有的：

- **第一次打开会话**：拉最近 100 条。之后按 `client.counts` 里的最新 ts 判断，本地已经有了就一次都不问 Slack，
  有新的才用 `oldest=本地最新` 只拉新的。
- **往前翻**：本地有就直接给；翻到本地最早那条之前，才用 `latest=本地最早` 向 Slack 补一页，补全后记 `complete`。
- **旧消息上的变化**（编辑、删除、表情、回复数）：每个会话每 5 分钟重拉最近 7 天一次；这段时间里本地有、Slack 没有的标为删除。
- **thread**：每 30 秒用 `oldest=本地最新回复` 只拉新回复，每 10 分钟整个重拉一次补编辑和删除；根消息的回复数顺带更新到频道消息流。
- **后台同步**：服务启动时（有凭证）起一个线程，每 60 秒把所有会话的新消息、有新回复的 thread 拉进本地。
  第二轮起没有新消息时只调 `client.counts` 等几个元数据接口，不调 history。
- **图片**：新消息里 slack.com 上的图片（≤25 MB）后台预取到 `files/`，打开时直接从本地出；`files/` 超过 2 GB 时按时间删最旧的，删到 80%。
- 只是缓存：删掉 `slack.db` 不丢任何东西，下次会重新从 Slack 拉。侧栏顶部显示本地已存条数和上次同步时间。

## 企业版工作区的限制（2026-11 实测）

SemiAnalysis 是 Enterprise Grid：`conversations.list`、`users.conversations`、`usergroups.*` 返回
`enterprise_is_restricted` / `user_is_restricted`。会话清单用网页端自己的接口：

- `client.userBoot`：侧栏的完整频道列表和打开着的私信（`client.counts` 只给有动静的会话，不全）。拿不到时退回只用 `client.counts`。
- `client.counts`（`thread_counts_by_channel=true`）：每个会话的 `last_read`、未读、@我 数，以及按频道的 thread 未读 / @我 数。
- `subscriptions.thread.getView`：我参与的 thread，带 thread 的 `last_read`。没参与的 thread Slack 不记已读。

用户组名拿不到，`<!subteam^…>` 显示为「@用户组」。群聊私信名从「Group messaging with: @a @b @me」整理成「a, b」。

## 完全只读（2026-11-17 用户要求：对 Slack 及其状态都只读）

`src/services/slack_inbox.py`：

- `ALLOWED_METHODS` 只读白名单：`auth.test`、`client.counts`、`client.userBoot`、`conversations.info/history/replies`、
  `search.messages`、`subscriptions.thread.getView`、`users.info`。客户端只发 GET。
- 白名单外的方法直接抛错，单测锁定：发送、改消息、加表情、加入频道，以及 `conversations.mark`、`subscriptions.thread.mark`
  （改 Slack 已读状态）都会被拒。附件只从 `*.slack.com` 下载。
- **已读只记在 momo 本地**（`slack.db` 的 `read_state`，只往前推）。显示时已读位置取「Slack 记的」和「momo 本地记的」里更新的那个：
  在 Slack 里读过的 momo 也算读过；在 momo 里读过的只影响 momo，Slack 里的未读保持原样。
  thread 未读和 @我 角标按我参与的 thread 结合本地已读重新计算；在 momo 里看过的非参与 thread 也会记已读。
- 前端只在页面可见时记已读，同一条消息只发一次请求。

## 展示范围

- 频道：侧栏里我加入的全部频道（未归档）。
- 私信：Slack 侧栏里打开着的私信 / 群聊私信，加上最近 `SLACK_DM_RECENT_DAYS`（默认 30）天内有消息的；
  隐藏 Slackbot、Slack 官方账号、自己和 bot。

## 接口（`/api/slack-inbox`）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/status` | 凭证是否有效、当前用户和工作区 |
| PUT | `/credentials` | 保存凭证（`token`、`cookie_d`） |
| GET | `/conversations?refresh=` | 会话列表（含 `last_read`、未读、@我、thread 未读）+ 全局 thread 角标 |
| GET | `/conversations/{id}/messages?limit=&cursor=` | 消息，新→旧，分页 |
| GET | `/conversations/{id}/replies/{ts}` | thread 全部消息 + 我的 thread 已读位置 |
| GET | `/conversations/{id}/threads` | 频道最近 7 天有回复的 thread（侧栏展开用） |
| GET | `/threads` | 我参与的 thread，有新回复的在前 |
| GET | `/conversations/{id}/agent-context?thread_ts=` | 交给 agent 的上下文（Markdown + me/them 历史） |
| POST | `/ai/translate` | `{"texts": [...]}` 逐条中文（不需要翻的为 null） |
| POST | `/ai/titles` | `{"items": {thread_ts: 根消息}}` 中文短标题 |
| GET | `/conversations/{id}/threads/{ts}/summary` | thread 中文摘要 |
| GET | `/digest` | AI 速览（未读按会话 / thread 中文总结） |
| GET | `/search?q=` | 搜索（中文先改写成英文关键词） |
| POST | `/conversations/{id}/mark` | `{"ts"}` 在 momo 本地记会话已读（只前进，不碰 Slack） |
| POST | `/conversations/{id}/threads/{ts}/mark` | `{"ts"}` 在 momo 本地记 thread 已读（不碰 Slack） |
| GET | `/conversations/{id}/export?format=md\|json` | 导出最近 200 条（含 thread） |
| GET | `/files/{id}` | 附件代理；只内联 png/jpeg/gif/webp，其余一律下载 |

⚠️ momo 目前没有登录，这些接口和页面对公网可见（2026-11-17 用户确认暂不加）；正式使用前要加鉴权。
