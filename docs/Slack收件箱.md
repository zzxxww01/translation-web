# Slack 收件箱

momo 顶部「Slack」页，布局照原生 Slack 三栏：

- **左栏**：Threads（我参与的 thread）、频道（可展开，列出最近 7 天有回复的 thread）、私信（含群聊私信）；
  未读加粗，@我 显示红色角标。底部「自由翻译」是原来的 Slack 回复助手。
- **中栏**：消息流。日期分隔、同一人 5 分钟内连发合并、打开时在 Slack 的已读位置画「新消息」线，@我 的消息黄底。
- **右栏**：thread 面板，根消息 + 全部回复，「新回复」线。

URL：`/slack?c=<会话>`、`view=threads|reply`、`tc=<会话>&t=<thread_ts>`（右栏 thread）。

## AI：每个 thread / 私信背后一个 skill agent

- **频道 thread → 帖子翻译助手**（skill `slack-post-translate`）：thread 面板默认是「AI 翻译」标签页。agent 找出要发的
  内容（根帖、链接卡片里的 X 帖、`1/N…N/N` 分段取最新版），走 `translate-post`（术语库），再出标题候选。
- **私信 → 回复助手**（skill `slack-dm-reply`）：打开私信时右栏是「AI 回复」。agent 用中文说清对方要什么，
  用 `slack-reply` 给 A/B/C 三版英文；选一版「复制并打开 Slack」，到 Slack 里粘贴发送（momo 从不发送）。
- 第一次打开 thread / 私信时自动启动；同一时间只跑一个 Slack agent（2 GB 内存），其余在页面上排队、每 15 秒重试。
- 绑定：skill-runner 的 run 带 `source = slack:<会话>[:<thread_ts>]`，同一个 source 只建一个对话；Claude 页的对话列表不显示这些。
- 上下文：`GET /api/slack-inbox/conversations/{id}/agent-context?thread_ts=` 导出 Markdown（作者标「（我）」、链接卡片全文）
  和 `history`（me/them）。前端把它们作为附件交给 agent。之后有新消息，右栏提示「让 AI 重新看」，把最新上下文发给同一个对话。
- 结果：skill 每次都重写运行目录里的 `result.json`，页面据此显示带「复制」按钮的结果卡片；格式见两个 SKILL.md。
- skill 源文件在仓库 `skill_runner/skills/`；`~/.agents/skills/<名字>` 软链接到 `~/skill-runner/src/skill_runner/skills/<名字>`，
  随 skill-runner 一起 `git pull` 更新。

后续：每条消息配中文、thread 中文标题和摘要、AI 速览、搜索。

## 接入方式

- 用个人网页会话凭证：`xoxc-` token + `d` cookie（`xoxd-`），不需要装 Slack App。
- 凭证存 `data/slack_credentials.json`（600，格式 `{"token": "...", "cookie_d": "..."}`）；失效时页面会弹出表单重新填写，只写不回显。
- 缓存：`data/slack_cache/`（用户名、已下载的附件）；会话/消息/thread 列表在内存里缓存 30 秒，`client.userBoot` 5 分钟。

## 企业版工作区的限制（2026-11 实测）

SemiAnalysis 是 Enterprise Grid：`conversations.list`、`users.conversations`、`usergroups.*` 返回
`enterprise_is_restricted` / `user_is_restricted`。会话清单用网页端自己的接口：

- `client.userBoot`：侧栏的完整频道列表和打开着的私信（`client.counts` 只给有动静的会话，不全）。拿不到时退回只用 `client.counts`。
- `client.counts`（`thread_counts_by_channel=true`）：每个会话的 `last_read`、未读、@我 数，以及按频道的 thread 未读 / @我 数。
- `subscriptions.thread.getView`：我参与的 thread，带 thread 的 `last_read`。没参与的 thread Slack 不记已读。

用户组名拿不到，`<!subteam^…>` 显示为「@用户组」。群聊私信名从「Group messaging with: @a @b @me」整理成「a, b」。

## 只读保证和唯一的写操作

`src/services/slack_inbox.py`：

- `ALLOWED_METHODS` 只读白名单：`auth.test`、`client.counts`、`client.userBoot`、`conversations.info/history/replies`、
  `subscriptions.thread.getView`、`users.info`。
- `MARK_METHODS`：`conversations.mark`、`subscriptions.thread.mark`——在 momo 里看过的会话/thread 同步标成 Slack 已读
  （2026-11-17 用户确认要同步）。只推进「我」自己的已读位置，后端拒绝往回退；不发送、不修改任何消息，别人不可见。
- 白名单外的方法直接抛错（有单测锁定，发送类方法永远不加）。附件只从 `*.slack.com` 下载。
- 前端只在页面可见时标已读，同一条消息只发一次请求。

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
| POST | `/conversations/{id}/mark` | `{"ts"}` 标记会话已读（只前进） |
| POST | `/conversations/{id}/threads/{ts}/mark` | `{"ts"}` 标记 thread 已读（只对我参与的 thread） |
| GET | `/conversations/{id}/export?format=md\|json` | 导出最近 200 条（含 thread） |
| GET | `/files/{id}` | 附件代理；只内联 png/jpeg/gif/webp，其余一律下载 |

⚠️ momo 目前没有登录，这些接口和页面对公网可见（2026-11-17 用户确认暂不加）；正式使用前要加鉴权。
