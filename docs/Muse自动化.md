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
| `translate-article <slug 或 Substack 链接> [--target-lang zh]` | 导入（已导入复用）→ 四步法翻译，自动采用术语建议。`status`：`started` / `resumed`（上次停在一半，续译）/ `already_exists`（在跑、等术语或已译完，附 `translation_status`） |
| `slack-todos` | **我要处理什么**：和网页 Slack 页「我的待办」同一份。`items` 是找我的事（私信、thread 里直接 @我），每条有 `task`（谁要我干什么）、`action`（`reply` 要回复 / `do` 要做事，多半是翻译 / `read` 看看就行）、`conversation_id`、`thread_ts`、`draft`（已有翻译稿时给 `draft_id`、`status`）；`fyi` 是只被群发 @ 到的，不用处理 |
| `drafts [--status draft\|done\|all] [--source slack\|manual] [--q 关键词] [--limit 50]` | **翻译记录**（网页「我翻译的」/「全部翻译记录」）。默认 `--status draft`：还没点「标记完成」的。每条有 `draft_id`、`title`、`preview`（译文开头）、`versions`（0 = 只提取了原文还没出译文）、`image_count`、`auto`（后台或 Muse 自动翻的） |
| `draft <draft_id> [--no-images]` | **一份翻译结果**：`source_text`（要翻的英文）、`translation`（当前版译文）、`titles` / `selected_title`、`slack.permalink`、`link`（网页打开这份稿子），`images` 按发帖顺序给**原图**：`n`、`name`、`mimetype`、`size`、`sha256`、`data_base64`（单张 >30MB 或合计 >100MB 的只给元数据和 `error`）。`--no-images` 只给元数据 |
| `translate-slack-post <conversation_id> <thread_ts> [--instruction 说明] [--no-images]` | 把一个 thread 当帖子翻，和网页「翻译这个帖子」同一条流程：提取原文和配图 → 翻译 → 生成标题，存成翻译稿（标成自动翻的），返回和 `draft` 一样的结果。已有稿子时追加新版本。`--instruction` 用在 AI 挑错了时（如「翻第二版文案」）。几十秒到两分钟 |
| `translate-slack <conversation_id> <message_ts> [--thread-ts T] [--with-thread]` | 翻译任意一条 Slack 消息的正文或它所在的整个 thread（不存翻译稿；翻帖子用上面的 `translate-slack-post`），**同步**返回 `translation`，`status` 为 `done`（新翻）或 `already_exists`（同样内容翻过，直接给缓存）；`project_id` 形如 `slack-<会话>-<ts>[-thread]` |
| `translate-post [原文] [--hashtags]` | **直接翻一段帖子原文**（推文、公众号段落……），和网页「帖子翻译」同一条链路（术语库、帖子翻译默认模型），同步返回 `translation`、`model`；不存翻译稿。默认不加话题标签，`--hashtags` 才在末尾加小红书标签。上限 10000 字符 |
| `slack-reply [内容] [--mode auto\|incoming\|compose] [--history JSON]` | **帮 Felix 回 Slack**，和网页「Slack 回复」同一套。对方的英文消息（`incoming`）→ `translation`（中文理解）+ `replies`（3 版英文回复）；Felix 的中文草稿（`compose`）→ `replies`（3 版英文）。每版有 `version`（A/B/C）、`style`、`english`、`chinese`。`auto` 按中文占比判断，返回的 `mode` 是实际用的。`--history` 给之前的对话：`[{"role":"them\|me","content":"..."}]` |
| `status <project_id> [--with-markdown]` | 文章：`running`（附 `stage`）/ `done`（`result` 是翻译服务链接）/ `failed`（`error`）/ `not_started`，带 `zh_title`、`zh_summary`，`--with-markdown` 完成时附中文 Markdown 全文。`slack-…`：`done`，`result` 是译文 |
| `health` | `substack` / `slack` / `models` 各自 `ok` 或 `error: …`（`models` 只检查配置，不发请求）；`slack_groups` 是自动识别 / 手配的用户组个数 |

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

### Muse 的典型用法

1. `slack-todos` → 知道要回谁、要翻哪些（`action: do` 且 `draft` 为空的 thread 还没翻）。
2. 要翻的：经 Felix 确认后 `translate-slack-post <conversation_id> <thread_ts>`。后台对「直接 @我」的 thread 本来就会自动翻，多数时候 `draft` 已经有了。
3. `drafts` → 还没点「标记完成」的翻译；`draft <draft_id>` 拿译文、标题和原图交付。Felix 在网页上改过译文，`draft` 拿到的就是改过的当前版。

**正文怎么传**：`translate-post`、`slack-reply` 的正文可以写在参数里，也可以不写、从标准输入传——长文本、带引号和换行的用 stdin 最省事：
`printf '%s' "$TEXT" | ssh -p 42022 zxw@<host> translation-agent translate-post`。

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

`--ssh` 从 `SSH_ORIGINAL_COMMAND` 读子命令（开头的 `translation-agent` 可写可不写），只放行上面 11 个，
不允许 `--base-url`，也不认 `TRANSLATION_SERVICE_URL`。Muse 调用：`ssh -p 42022 zxw@<host> translation-agent updates --since ...`。

## 配置（`src/settings.py`）

- `AUTOMATION_SLACK_GROUP_IDS`：Felix 所在用户组 ID，逗号分隔。
- `AUTOMATION_PUBLIC_URL`：交付链接前缀，默认 `https://momo.beauty`。

## 和仓库里其他命令行的关系

`translation-agent` 是本仓库唯一给外部调用的命令行入口（机器人、脚本都用它）。早期给人在终端用的
`translate-post`、`slack-reply` 两个脚本已删除（2026-11-23），功能就是这里的同名子命令。
`src/cli/cost_report.py`、`scripts/*` 是开发 / 运维工具，不给机器人。
