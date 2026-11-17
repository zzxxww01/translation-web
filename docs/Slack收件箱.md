# Slack 收件箱（只读）

momo 顶部「Slack」页：`频道` / `私信` 两个子页只读展示 Slack 消息，`回复工作台` 是原来的 Slack 回复助手。

## 接入方式

- 用个人网页会话凭证：`xoxc-` token + `d` cookie（`xoxd-`），不需要装 Slack App。
- 凭证存 `data/slack_credentials.json`（600，格式 `{"token": "...", "cookie_d": "..."}`）；失效时页面会弹出表单重新填写，只写不回显。
- 缓存：`data/slack_cache/`（用户名、已下载的附件）。

## 企业版工作区的限制（2026-11 实测）

SemiAnalysis 是 Enterprise Grid：`conversations.list`、`users.conversations`、`usergroups.*` 返回
`enterprise_is_restricted` / `user_is_restricted`。会话清单改用网页端自己的 `client.counts`，
再逐个 `conversations.info`。用户组名拿不到，`<!subteam^…>` 显示为「@用户组」。

## 只读保证

`src/services/slack_inbox.py` 的 `ALLOWED_METHODS` 白名单：`auth.test`、`client.counts`、
`conversations.info/history/replies`、`users.info`。白名单外的方法直接抛错（有单测锁定）；
不调 `conversations.mark`，不会改变 Slack 里的已读状态。附件只从 `*.slack.com` 下载。

## 展示范围

- 频道：`client.counts` 里我所在的全部频道。
- 私信：最近 `SLACK_DM_RECENT_DAYS`（默认 30）天内有消息的私信和群聊私信；隐藏 Slackbot、Slack 官方账号、自己和 bot。

## 接口（`/api/slack-inbox`）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/status` | 凭证是否有效、当前用户和工作区 |
| PUT | `/credentials` | 保存凭证（`token`、`cookie_d`） |
| GET | `/conversations?refresh=` | 会话列表（30 秒缓存） |
| GET | `/conversations/{id}/messages?limit=&cursor=` | 消息，新→旧，分页 |
| GET | `/conversations/{id}/replies/{ts}` | thread |
| GET | `/conversations/{id}/export?format=md\|json` | 导出最近 200 条（含 thread） |
| GET | `/files/{id}` | 附件代理；只内联 png/jpeg/gif/webp，其余一律下载 |

⚠️ momo 目前没有登录，这些接口和页面对公网可见；正式使用前要加鉴权。

## 后续

- 二阶段：识别频道里的帖子（根消息 @用户组 + 标题，thread 里 `*1/* … (1/N)` 编号串，取最新完整一版），送进帖子翻译。
- 三阶段：私信一键带入回复工作台生成草稿；始终不实现发送。
