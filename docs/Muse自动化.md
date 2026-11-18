# Muse 自动化 CLI（translation-agent）

Felix 的个人助手 Muse 经 SSH 按需调用 momo：**检测自动，动作确认**。Muse 负责定时检测、通知、征求确认、
轮询、交付和保存水位线；momo 只提供能力，凭证不出服务器。

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
| `translate-article <slug 或 Substack 链接> [--target-lang zh]` | 导入（已导入复用）→ 四步法翻译，自动采用术语建议。`status`：`started` / `resumed`（上次停在一半，续译）/ `already_exists`（在跑、等术语或已译完，附 `translation_status`） |
| `status <project_id> [--with-markdown]` | `status`：`running`（附 `stage`）/ `done`（`result` 是 momo 链接）/ `failed`（`error`）/ `not_started`；带 `zh_title`、`zh_summary`；`--with-markdown` 完成时附中文 Markdown 全文 |
| `health` | `substack` / `slack` / `models` 各自 `ok` 或 `error: …`；`models` 只检查配置，不发请求 |
| `translate-slack`（二期） | 目前返回 `NOT_IMPLEMENTED` |

### updates 细节

- **watermark = 这次调用开始同步那一刻**（UTC ISO），不是数据里的最大时间：同步期间新到的下次还会出现，不漏；
  极少数会重复一次，Muse 按 `slug`、`conversation_id + message_ts` 去重。Slack 同步失败时 watermark 不前进（= since）。
- **mention_type**：`direct`（`<@U0A8T7U5D7A>`）> `group`（`<!subteam^ID>` 且 ID 在 `AUTOMATION_SLACK_GROUP_IDS` 里）>
  `channel`（`<!channel>` / `<!here>` / `<!everyone>`）；一条只返回一次，取最强的一类；自己发的不算；只在链接卡片里出现的不算。
  企业版工作区查不了 `usergroups.*`，用户组 ID 只能手填（逗号分隔，在 `.env` 里设），没填时 group 永远为空。
- 从本地副本 `slack.db` 查，所以 Felix 没参与、Slack 也没自动订阅的 thread 里的回复查不到（被 @ 时 Slack 一般会自动订阅）。
- **只读**：Slack 走现有只读白名单；不碰 momo 本地已读（`read_state`）；不导入、不翻译。

### translate-article 细节

- 后端一把锁串行处理，同一篇并发调用只会导入一个项目、起一次翻译；翻译槽被网页那边占了（409）也当 `already_exists`。
- 直接调 `start_longform_workflow`（绕过网页用的 3 次/分钟限流），参数等于网页「一键翻译」+ `auto_accept_terms`。
- Muse 起的翻译在跑时，momo 发版的 precheck 会拦住，和网页起的一样。

## SSH 受限密钥

给 Muse 单独一把密钥，在 `~/.ssh/authorized_keys` 里写成：

```
command="/home/zxw/bin/translation-agent --ssh",no-pty,no-port-forwarding,no-agent-forwarding,no-X11-forwarding,no-user-rc ssh-ed25519 AAAA... muse
```

`--ssh` 从 `SSH_ORIGINAL_COMMAND` 读子命令（开头的 `translation-agent` 可写可不写），只放行上面 5 个，
不允许 `--base-url`，也不认 `TRANSLATION_SERVICE_URL`。Muse 调用：`ssh -p 42022 zxw@<host> translation-agent updates --since ...`。

## 配置（`src/settings.py`）

- `AUTOMATION_SLACK_GROUP_IDS`：Felix 所在用户组 ID，逗号分隔。
- `AUTOMATION_PUBLIC_URL`：交付链接前缀，默认 `https://momo.beauty`。
