# Skill 运行页（skill-runner）设计

日期：2026-10-24 · 状态：已确认第 1 段，其余按讨论方向定稿，先实现

## 目标

在 momo.beauty 里新增「Skill」页，用**本人的 Claude 订阅额度**在服务器上跑 skill（首期：
four-step-translate、video-bilingual-subber、podcast-cn-dubber），全程网页触发与交互：选 skill、
传文件或贴链接、在 skill 的关卡（术语确认、字幕审校、稿件审核）上作答、下载产出。替换现有的
`/terminal` 远程终端页。

## 约束（已确认）

- **只有本人使用。** 订阅 OAuth 只允许本人、官方 Claude Code 程序使用（Agent SDK 驱动的就是它）；
  不得让他人经由 momo 使用本订阅。服务环境里**不设** `ANTHROPIC_API_KEY` / `ANTHROPIC_BASE_URL`，
  否则会改走 API 计费。
- **必须在 momo 里交互**（不用 claude.ai/code 的 Remote Control）。
- **通用对话页**：一个页面适用所有 skill，不为单个 skill 定制界面。
- **权限**：命令和改文件自动执行，靠沙箱兜底；只在 skill 关卡停下等人。
- **素材**：主要贴链接（服务器自己下载），本地上传偶尔、单个文件 ≤ 1 GB。
- momo 现有页面和后端不动，不给整个 momo 加登录。

## 架构

```
浏览器 momo.beauty/skills（同一个前端 SPA，替换「终端」导航）
   │
nginx ── /api/skills/*  ──► skill-runner（127.0.0.1:18090，独立 systemd 用户服务）
      └─ 其他 /api/*     ──► momo 后端（54321，不动）

skill-runner = FastAPI + claude-agent-sdk（pip 包自带 Claude Code 程序）
磁盘：$SKILL_RUNNER_HOME/runs/<run_id>/{meta.json, events.jsonl, input/, ...产出}
```

- 代码在本仓库 `skill_runner/`，有自己的依赖文件和 systemd unit；momo 发版不重启它。
- 每次运行 = 一个 `ClaudeSDKClient` 流式会话，`cwd` = 运行目录，`setting_sources=["user"]`
  （加载服务用户的 `~/.claude/skills`）。
- Claude 认证：服务器上 `claude setup-token` 生成的 `CLAUDE_CODE_OAUTH_TOKEN`，写在服务的 env 文件。

## 模块划分

| 模块 | 职责 | 依赖 |
| --- | --- | --- |
| `config.py` | 从环境变量读配置（路径、口令、并发上限、沙箱、白名单） | 无 |
| `auth.py` | 单用户口令登录、签名 cookie、登录失败限速 | 无 |
| `store.py` | 运行目录、`meta.json` 原子写、`events.jsonl` 追加与回放、文件列表与安全路径解析 | 无 |
| `policy.py` | 工具权限决策（写路径白名单、沙箱外命令拒绝） | 无 |
| `runner.py` | 运行生命周期、状态机、提问挂起与作答、并发上限、空闲回收、重启恢复、SSE 订阅 | `store`、`policy`、会话工厂 |
| `sdk_session.py` | 唯一 import SDK 的地方：建 `ClaudeSDKClient`、把 SDK 消息映射成页面事件 | `claude_agent_sdk` |
| `app.py` | HTTP 接口、上传、下载、SSE | 以上全部 |

`runner` 通过「会话工厂」协议拿到会话，测试用假会话，不需要装 SDK；只有 `sdk_session` 的
映射测试依赖 SDK（CI 未装时跳过）。

## 运行生命周期

状态：`running`（一轮进行中）· `waiting`（有待回答的提问）· `idle`（本轮结束，等你发消息）·
`error`（出错或服务重启中断；发消息即从会话断点续跑）。

1. 新建：`POST /api/skills/runs`（multipart：skill、message、files）→ 建目录、存文件到 `input/`，
   首条消息为 `/<skill> <message>` 加附件清单，起会话。`skill` 留空即直接对话：消息原样发出，
   不派发 skill（2026-10-24 补充；导航改名「Claude」）。
2. 事件：SDK 消息 → 页面事件（`user`、`text`、`tool`、`tool_result`、`question`、`answer`、
   `todos`、`status`、`result`、`error`、`notice`），带递增 `seq`，追加写 `events.jsonl`，
   推给 SSE 订阅者。工具结果截断到 2000 字；子代理的工具调用带 `parent` 字段，页面折叠显示。
   进度来自任务清单工具：新模型默认不带，会话环境里设 `CLAUDE_CODE_ENABLE_TODO_TOOLS=1` 打开；
   `TodoWrite`（全量）和 `TaskCreate`/`TaskUpdate`（增量，编号取自结构化结果 `tool_use_result.task.id`）都认，
   这些工具和 `AskUserQuestion` 的调用与结果不进工具流。
3. 提问：`can_use_tool` 收到 `AskUserQuestion` → 发 `question` 事件、状态 `waiting`、挂起等待；
   `POST /runs/{id}/answer` 作答后放行，带回 `answers`。
4. 插话：`POST /runs/{id}/messages` 随时可发（运行中会排进对话）；会话已回收或出错时，用
   `resume=session_id` 重连再发。
5. 中断：`POST /runs/{id}/interrupt` → `client.interrupt()`，挂起的提问按「用户中断」拒绝。
6. 回收：`idle` 超过 10 分钟断开 SDK 进程（状态仍是 `idle`，下次发消息自动续接）。
7. 重启恢复：服务启动时把 `running`/`waiting` 的运行标成 `error`（「服务重启导致中断」）。
8. 并发：`running`+`waiting` 的运行最多 2 个（可配置），超出返回 429。
9. 删除：`DELETE /runs/{id}`，只允许非活动运行，删整个目录。

## 权限与沙箱

- `permission_mode="default"`，所有需批准的调用都进 `can_use_tool`：
  - `AskUserQuestion` → 页面作答。
  - `Edit`/`Write`/`MultiEdit`/`NotebookEdit` → 目标在运行目录或 `SKILL_RUNNER_EXTRA_WRITE`
    白名单内放行，否则拒绝并说明原因。
  - `Bash` 到这里说明要在沙箱外执行 → 拒绝（沙箱关闭的开发模式下放行）。
  - 其他工具放行。
- 沙箱（经 `settings` JSON 传入）：`enabled`、`autoAllowBashIfSandboxed`、
  `allowUnsandboxedCommands=false`、`failIfUnavailable=true`；写路径 = 运行目录 + 白名单；
  网络 `allowedDomains` 默认放行 Gemini、DashScope/OSS、YouTube 相关域名（可配置）；
  `excludedCommands` 可配置（给不认代理环境变量的程序，如 websocket TTS 脚本）。
- 服务器需装 `bubblewrap`、`socat`；Ubuntu 24.04 需按官方文档放开 AppArmor 的 userns 限制。

## 登录

- 单口令（env `SKILL_RUNNER_PASSWORD`），常量时间比较；成功后发 `HttpOnly; Secure; SameSite=Strict;
  Path=/api/skills` 的签名 cookie（HMAC，30 天）。
- 连续 5 次失败锁 1 分钟。所有 `/api/skills/*`（除 `login`）都校验 cookie，SSE 也是。

## 页面（`/skills`）

- 未登录 → 口令框。
- 左栏：运行列表（skill、首条消息摘要、状态、时间）+「新建」。
- 新建：选「直接对话」（默认）或某个 skill（目录接口返回名称和简介）、写说明、附文件 → 开始。
- 主区：对话流（Markdown 用 `marked` 渲染 + DOMPurify 消毒）、工具调用折叠、提问卡片（单选/多选/
  「其他」自由输入）、底部输入框（发送、附件、中断）。
- 右栏：进度（Claude 的 todo 清单）、产出文件（可下载，运行中定时刷新）。
- SSE 断线自动重连（`Last-Event-ID`），重新打开页面从头回放。
- 窄屏：列表和内容二选一（`?run=<id>` 看运行、`?new=1` 新建），进度与文件放进右侧抽屉。

## 实现中确认的事实（2026-10-24 本地真实会话验证）

- SDK 0.2.174 自带 Claude Code 2.1.310；`setting_sources=["user"]` 能加载 `~/.claude/skills`。
- `can_use_tool` 能拿到 `AskUserQuestion` 并无限期挂起等页面作答；服务重启后按 `session_id` 续接，上下文完整。
- 模型可能跳过「先展示再提问」：系统提示里已明确要求要审阅的内容先在正文完整展示，问题文字也按 Markdown 渲染。

## 部署（需要服务器权限，代码里给出脚本与说明）

1. 装 `bubblewrap socat ffmpeg`，建 `$SKILL_RUNNER_HOME`。
2. 服务器上 `claude setup-token`，把 token 和口令、密钥写入 `~/.config/skill-runner/env`（600）。
3. 把三个 skill 同步到服务器 `~/.claude/skills`，改掉写死的 Windows 路径（见 `skill_runner/PORTING.md`）。
4. 装 `skill-runner.service`（用户 unit，linger），nginx 加 `/api/skills/` 段（SSE 不缓冲、1 GB 上传）。

## 错误处理

- SDK 连接失败 / 认证失败 / 进程崩溃 → `error` 事件 + `error` 状态，正文写明原因；可重试。
- 额度限制（`RateLimitEvent`）→ `notice` 事件提示窗口和重置时间。
- 上传超限 → 413；路径越界 → 404；未登录 → 401；并发满 → 429。

## 测试

- 后端（`tests/skill_runner/`，不依赖 SDK）：口令与 cookie、限速、存储与回放、安全路径、
  权限策略、生命周期（假会话：提问作答、插话、中断、回收、续接、重启恢复、并发上限）、HTTP 接口。
- SDK 映射测试：`importorskip("claude_agent_sdk")`。
- 前端：事件归并逻辑与 Markdown 消毒的 vitest。
- 真实冒烟：本地用 SDK 跑一次短会话（含 AskUserQuestion）验证端到端。

## 不做（YAGNI）

模型选择、多用户、按 skill 定制界面、视频分片上传、给 momo 整站加登录。
