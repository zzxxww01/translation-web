# Slack 收件箱

翻译服务顶部「Slack」页，按「动态」组织（2026-11-18 用户反馈原生 Slack 式的频道三栏太乱，改成活动列）：

- **左栏**（`inbox/ActivityList.tsx`）：一行筛选（浅灰底分段选择，选中白底）**全部 · 未读 · @我 · 私信 · 新帖 · 我参与的 · 我翻译的**（记在浏览器里，数字是这一类的未读数，
  可以重叠；「全部」按最近活动排；「新帖」= 最近 7 天没人回复、不是我发的；「我参与的」= Slack 记的我订阅的 thread，后端带 `following`）。
  右边「待办 N」回到中间的我的待办。选「未读」时列表顶部有「全部标为已读」（只记在翻译服务）。
  「我翻译的」= 最近 7 天有翻译稿的帖子，顶上有入口进**全部翻译记录**（`view=history`，不限 7 天、含帖子翻译页翻的）。
  每行只有两行字：标题（未读加粗 + 小圆点，@我 红字）和一行灰色说明（谁发起 · 几条回复 · 翻译草稿 / 已翻译）；后台自动翻好、还没看过的整行底色稍深。
- **中栏**：没选会话时是「我的待办」；点 thread 只看这一个 thread（顶部操作条：翻译这个帖子 / 翻译全部 / 总结一下），
  thread 标题下的频道名可以进整个频道的消息流；点私信是私信消息流。
- **右栏**：私信时是回复面板。
- **翻译模式**（`mode=translate`）：整页三栏，见下面「帖子翻译」。
- 触屏没有悬停：点一下消息显示 / 收起「译 / 复制 / thread / 在 Slack 打开」工具条。
- 快捷键：`j` / `k` 下一条 / 上一条（在当前筛选里切换并打开），`Esc` 关闭；在输入框里不生效。

URL：`/slack?tc=<会话>&t=<thread_ts>`（打开的 thread，加 `mode=translate` 是翻译模式）、`c=<会话>`（私信或整个频道）、`ai=1`（窄屏显示回复面板）。

左栏的搜索框、「动态 · 工作区」标题、AI 速览、「⋯」菜单都已去掉（2026-11-21/22 用户要求，太占地方 / 太乱）。

## AI 功能（2026-11-22 重做：全部直接调接口，不再用 skill agent）

模型：Slack 的所有调用都是 `slack` 任务，默认 `gpt-6.2-sol`（`config/llm_providers.yaml` 的 `task_defaults.slack`，OpenAI 官方直连，
失败只重试同一模型、不降级）。帖子翻译用帖子翻译页同一条链路（`post` 任务，同样是 `gpt-6.2-sol`）。
提示词在 `src/prompts/slack_zh.txt`、`slack_summary.txt`、`slack_todo.txt`、`slack_post_extract.txt`；缓存在
`data/slack_cache/ai/`，换模型或改提示词时改 `src/services/slack_ai.py` 的 `CACHE_TAG`。

### 1. 消息翻成中文（`POST /ai/translate`）
- 单条：消息工具条「译」，正文和链接卡片一起翻；自己发的消息不翻。私信、频道、thread 里都有。
- thread 顶部「翻译全部」：整个 thread 翻成中文，只对这个 thread 有效、不记住；按钮变「收起中文」。
- thread 回复带上根帖作为背景（`context`，只帮理解不翻）；译文保留换行、列表、表格、粗体。
- 原来的全局「全部中文」开关去掉了。

### 2. thread 摘要（`GET /conversations/{id}/threads/{ts}/summary`）
- 打开回复 ≥ 3 条的 thread 自动总结一次；更少的、没人回复的新帖默认不总结。
- 顶部「总结一下 / 重新总结」按钮一直都在。thread 开着时来了新回复只提示「有 N 条新回复 · 点这里更新」，不自动重算。
- 卡片标题固定「在聊什么」，内容是摘要 + 「要你做」。

### 3. 我的待办（`GET /todos`，替代原来的 AI 速览）
- 没选会话时中栏显示。只看**未读的 @我 和未读私信**，一次调用告诉我每件事「谁、要我干什么」（要回复 / 要处理 / 看一下）。
- 只被 @用户组 / @here 群发提到的不送模型，放在底部「不用处理」。底部「都处理完了」把这些标为已读（只记在翻译服务）。
- 左栏筛选行右边的「待办 N」回到这里（N = 未读的 @我 + 私信）。
- 「@我 的 thread 自动翻译」开关也在这里（`GET/PUT /settings`，存在 `data/slack_cache/settings.json`）。

### 4. 帖子翻译（翻译模式 + 翻译稿）
- thread 顶部主按钮「翻译这个帖子」（翻过的显示「继续翻译 · vN」「已完成」「自动翻好了」）→ `?mode=translate` 进入翻译模式：
  **原文和配图 | 译文 | Slack 原帖** 三栏（上面一条细工具条：返回 Slack、标题、存档状态、标记完成、模型）（`components/layout/ResizablePanes.tsx`），每栏可收起、可拖宽，记在浏览器里。
- 第一次进入自动跑 `POST /api/post-drafts/slack/{频道}/{thread_ts}/run`：提取（`slack_post_extract`，一个 thread 只出一篇，
  去掉编号 / @ / 请求 / 讨论，取最新版；有「posted <x.com/SemiAnalysis_…>」时以已发布的 X 帖为准；挑配图）→ 翻译 → 标题，存成翻译稿。
  「重新提取」带上要求（「用第一版」）再跑一次，旧版本保留、追加新版本。
- ② 栏和帖子翻译页是同一套代码（`features/post/usePostWorkspace.ts` + 每篇一份 `createPostStore()`）：版本切换、手改保存、
  预设优化 + 自定义、标题生成；另有「连标题复制」。
- ③ 栏：用来提取的消息左侧竖线；点图片加入 / 去掉配图；配图可调顺序、单张下载、`GET /api/post-drafts/{id}/images.zip` 打包。
- 翻译稿存在 `data/post_drafts/<id>.json`（`src/services/post_drafts.py`），帖子翻译页手动翻的也存这里，两边合成「翻译记录」：
  Slack 里在「我翻译的 → 全部翻译记录」，帖子翻译页在右上角「历史记录」（点开才展开；帖子翻译页是旧功能，其余布局不变，以后逐步迁到 Slack）。Slack 列表行和 thread 顶部显示「草稿 vN / ✓ 已翻 / 自动翻好」。
- **@我 的 thread 自动翻译**：后台每分钟（`post_drafts.auto_translate_loop`，随翻译服务后端启动）找最近 7 天有人直接 @我、还没有翻译稿的
  thread，自动跑一遍，生成「自动翻好 · 待查看」的草稿；失败一小时后再试（`data/slack_cache/auto_translate.json`）。
  提取发现没有要发的内容时只记一句说明，不进翻译记录。

### 5. 私信回复面板（私信右栏，`features/slack/reply/DmReplyPanel.tsx`）
- 对方要什么 + A 简洁 / B 标准 / C 正式三版（`/api/slack/process`）；「✎」改某一版的中文意思只重写这一版（`/slack/refine-version`）；
  一键调整（更短 / 更随意 / 更正式 / 更礼貌 / 加一句感谢，`/slack/refine` 三版并行）；「我想说」按中文意思出三版（`/slack/compose`）。
- 每次结果记一组，可翻回上一组，存在 `data/slack_cache/dm_replies/<会话>.json`（`GET/PUT /conversations/{id}/reply-state`）。
- 对方有未读新消息时打开自动生成一次；最后一条是我发的就显示「目前不需要回复」。翻译服务从不发送。

### 旧版工作台
原来 Slack 页里的「回复工作台」搬到「工具箱 → 旧版工作台」，功能不变。

skill-runner 里原来的 `slack-post-translate`、`slack-dm-reply` 两个 skill 已于 2026-11-22 删除。

## 接入方式

- 用个人网页会话凭证：`xoxc-` token + `d` cookie（`xoxd-`），不需要装 Slack App。
- 凭证存 `data/slack_credentials.json`（600，格式 `{"token": "...", "cookie_d": "..."}`）；失效时页面会弹出表单重新填写，只写不回显。
- 缓存：`data/slack_cache/`（用户名、附件、AI 结果、消息库）；会话列表在内存里缓存 30 秒，`client.userBoot` 5 分钟。

## 消息格式（2026-11-21）

- **正文优先用 blocks**（`blocks_to_mrkdwn`，`src/services/slack_inbox.py`）：消息的 `text` 只是通知用的简化版，表格会被压成一行、列表 / 引用 / 换行也不全。
  有 `blocks` 时先还原成 mrkdwn（rich_text 的样式、链接、@、emoji、列表、引用、代码块，section / header / context，`table` 写成 Markdown 表格），
  再走 `parse_slack_text`；没有 blocks（如搜索结果）或认不出来时退回 `text`。认不出的行内元素带 `url` 的按链接、带 `text` 的按文字显示，不丢内容。
- 消息正文按 Slack mrkdwn 渲染（`web/frontend/src/features/slack/inbox/mrkdwn.ts`）：`*粗*`、`_斜_`、`~删~`、`` `码` ``、` ``` ` 代码块、`>` 引用、`•` / `1.` 列表，
  也兼容直接贴进来的 Markdown（`**粗**`、`- 列表`）。链接 / 提及先换成占位符再交给 marked，原文里的 HTML 一律转义，结果经 DOMPurify 消毒；样式在 `mrkdwn.css`（`.slack-md`）。
- AI 中文、链接卡片正文、thread 摘要、速览摘要、私信助手的「对方要什么」也按同样方式渲染；列表行、搜索结果、Threads 卡片这类预览去掉记号只留文字（`stripMrkdwn`）。
- AI 面板里的对话气泡沿用 Agent 页的 `.skill-md` 排版；样式随 `ChatItems` 加载，不依赖先打开过 Agent 页。

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
- **已读只记在翻译服务本地**（`slack.db` 的 `read_state`，只往前推）。显示时已读位置取「Slack 记的」和「翻译服务本地记的」里更新的那个：
  在 Slack 里读过的翻译服务也算读过；在翻译服务里读过的只影响翻译服务，Slack 里的未读保持原样。
  thread 未读和 @我 角标按我参与的 thread 结合本地已读重新计算；在翻译服务里看过的非参与 thread 也会记已读。
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
| GET | `/threads` | 我参与的 thread，有新回复的在前 |
| GET | `/conversations/{id}/agent-context?thread_ts=` | Markdown + me/them 历史（thread 摘要、私信回复面板用） |
| POST | `/ai/translate` | `{"texts": [...], "context": 根帖}` 逐条中文（不需要翻的为 null） |
| GET | `/conversations/{id}/threads/{ts}/summary` | thread 中文摘要 |
| GET | `/todos` | 我的待办（未读的 @我 和私信；群发 @ 在 `fyi`） |
| GET/PUT | `/settings` | `auto_translate_mentions` |
| GET/PUT | `/conversations/{id}/reply-state` | 私信回复面板的历史 |
| POST | `/conversations/{id}/mark` | `{"ts"}` 在翻译服务本地记会话已读（只前进，不碰 Slack） |
| POST | `/mark-all` | 标已读，只记在翻译服务本地、不碰 Slack：不带参数时清空全部动态；带 `{"items": [{channel_id, ts, thread_ts}]}` 时只标这些（待办页「都处理完了」） |
| POST | `/conversations/{id}/threads/{ts}/mark` | `{"ts"}` 在翻译服务本地记 thread 已读（不碰 Slack） |
| GET | `/conversations/{id}/export?format=md\|json` | 导出最近 200 条（含 thread） |
| GET | `/files/{id}` | 附件代理；只内联 png/jpeg/gif/webp，其余一律下载 |

鉴权：2026-11-21 起整个翻译服务共用 Agent 页的口令登录（nginx `auth_request`，见 `skill_runner/README.md`），没登录访问这些接口返回 401。

## 翻译稿接口（`/api/post-drafts`）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `?q=&source=` | 翻译记录（手动 + Slack，按最近修改；`q` 搜标题、原文、译文） |
| POST | `` | 帖子翻译页第一次出译文时建稿（`m_…`） |
| GET/PUT | `/{id}` | 读 / 存（带 `rev`，对不上返回 409）；不提供删除（2026-11-22 用户要求） |
| GET | `/slack/{频道}/{thread_ts}` | 这个 thread 的翻译稿（没有为 null） |
| POST | `/slack/{频道}/{thread_ts}/run` | `{"instruction"}` 提取 → 翻译 → 标题 |
| GET | `/{id}/images.zip` | 配图按顺序打包 |

## Muse 怎么用

Muse 经 SSH 调 `translation-agent`：`slack-todos`（我的待办）、`drafts`（还没点「标记完成」的翻译）、`draft <id>`（译文、标题和原图）、`translate-slack-post`（跑上面同一条提取 → 翻译 → 标题流程）。见 [Muse自动化.md](Muse自动化.md)。
