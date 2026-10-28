# skill-runner

在服务器上用**本人的 Claude 订阅**跑 skill（four-step-translate、video-bilingual-subber、podcast-cn-dubber），
momo 的「Claude」页（`/skills`）负责触发和交互：选 skill、传文件或贴链接、在 skill 的关卡上作答、下载产出。
也可以不选 skill 直接对话（`skill` 留空，消息原样发给 Claude，它仍能按需调用已装的 skill）。
设计见 `docs/superpowers/specs/2026-10-24-skill-runner-design.md`。

```
浏览器 momo.beauty/skills
nginx ── /api/skills/* ──► skill-runner（127.0.0.1:18090，本目录，独立的 systemd 用户服务）
      └─ 其他 /api/*    ──► momo 后端（不变）
```

每次运行是一个 Claude Agent SDK 会话，工作目录 `$SKILL_RUNNER_HOME/runs/<run_id>/`。事件先落盘再推给页面，
所以关掉网页、断网、服务重启都不会丢记录；服务重启打断的任务，在页面上发一条「继续」就会按会话 ID 续跑。

**只能本人使用。** 订阅凭证按 Anthropic 条款只允许本人用官方 Claude Code 程序（SDK 驱动的就是它），
不要把口令给别人。服务启动时会删掉 `ANTHROPIC_API_KEY` / `ANTHROPIC_BASE_URL`，保证只走订阅额度。

## 首次部署

以下在服务器上以 zxw 执行。skill-runner 的代码用本仓库的一个独立 clone（`~/skill-runner/src`），
不放进 momo 的发布目录，两边各自更新、互不打断。

1. **系统依赖**：`sudo apt-get install -y bubblewrap socat`（沙箱必需；Ubuntu 24.04 还要给 bwrap 加 AppArmor 配置，见 PORTING.md）。
2. **代码和两个 venv**：
   ```bash
   mkdir -p ~/skill-runner && cd ~/skill-runner
   git clone https://github.com/zzxxww01/translation-web.git src
   python3 -m venv venv && venv/bin/pip install -r src/skill_runner/requirements.txt
   # skill 脚本用的 python（服务把它排在 PATH 最前面），各 skill 的依赖装在这里，见 PORTING.md
   python3 -m venv tools
   ```
3. **订阅凭证**：服务用户已经用自己的 Pro/Max 账号登录过 Claude Code 就直接复用；否则在自己电脑上运行
   `claude setup-token`，把 token 填进下一步的 env。
4. **配置**：
   ```bash
   mkdir -p ~/.config/skill-runner
   cp src/skill_runner/deploy/env.example ~/.config/skill-runner/env
   chmod 600 ~/.config/skill-runner/env   # 然后填口令、密钥、白名单路径
   ```
5. **自检**（真实起一个 Claude 会话，走提问→作答→沙箱内 Bash→写文件，消耗少量额度）：
   ```bash
   cd ~/skill-runner && set -a && . ~/.config/skill-runner/env && set +a
   PATH=~/skill-runner/tools/bin:$PATH PYTHONPATH=src venv/bin/python -m skill_runner.smoke
   ```
   输出「自检通过」才继续。沙箱起不来时这里会直接失败（`failIfUnavailable`），不会在沙箱外偷偷跑。
6. **常驻**：按 `deploy/skill-runner.service` 顶部的注释安装用户服务。
7. **nginx**：把 `deploy/nginx-skill-runner.conf` 加进 momo.beauty 的 443 server 块，`sudo nginx -t && sudo systemctl reload nginx`。
8. **前端**：Skill 页随 momo 正常发版上线（替换了原来的「终端」页，旧的 `/terminal` 链接会跳到 `/skills`）。
9. **迁 skill**：见 `PORTING.md`。

## 日常运维

| 要做的事 | 怎么做 |
| --- | --- |
| 看日志 | `journalctl --user -u skill-runner -f`（Claude 进程的 stderr 也在里面） |
| 更新 skill_runner 代码 | `git -C ~/skill-runner/src pull` 后 `systemctl --user restart skill-runner`。正在跑的任务会被打断，页面上发「继续」即可续跑 |
| 升级 SDK | 改 `requirements.txt` 的版本 → 本机跑 smoke → 服务器 `venv/bin/pip install -r src/skill_runner/requirements.txt` → 再跑 smoke → 重启 |
| 上传上限 | 公网入口是 Cloudflare Tunnel，免费版单个请求最大 100 MB，所以配置成 95 MB；更大的素材贴链接 |
| 清理空间 | 页面上删除只是把运行挪到 `~/skill-runner/deleted/`，仍占磁盘；要真正腾空间，先核对 `deleted/deleted.jsonl`，再手动删 `~/skill-runner/deleted/` 下的旧目录 |
| 改口令 | 改 env 文件后重启，所有旧登录立即失效 |
| 加 skill（= 页面上多一个 agent） | 装到 `~/.claude/skills/`，加进 `SKILL_RUNNER_SKILLS`，在 `skill_runner/agents.json` 写名片（中文名、图标、说明、输入提示、示例），开沙箱时按需补 `SKILL_RUNNER_EXTRA_WRITE` / `SKILL_RUNNER_ALLOWED_DOMAINS`，重启 |
| 改 agent 名片 | 编辑 `skill_runner/agents.json`（或 `SKILL_RUNNER_AGENTS_FILE` 指向的文件）后重启；图标可选 `chat`、`article`、`video`、`podcast` |

## Harness：Claude Code / Codex / Antigravity

新任务页可以选用哪个 harness，任务元数据记在 `harness` 字段里（旧任务没有这个字段，按 Claude 处理）。

- **Claude Code**：`sdk_session.py`，claude-agent-sdk，会话常驻；skill 用 `/<skill>` 派发，提问走 AskUserQuestion。
- **Codex**：`codex_session.py`，每一轮起一个 `codex exec --json`，之后的轮次 `codex exec resume <thread_id>`；
  关掉沙箱时带 `--dangerously-bypass-approvals-and-sandbox`（不需要确认）。提示词从 stdin 传，必须读完就关，
  否则 Codex 会停在「Reading additional input from stdin」。没有提问工具：要确认时它把内容写在回复里结束这一轮。
  skill 的派发是让它先读 `~/.agents/skills/<skill>/SKILL.md`。模型默认取 `~/.codex/models_cache.json` 里排第一的。
- **skill 目录**：真实文件在 `~/.agents/skills/`（Codex 原生读），`~/.claude/skills/<skill>` 是指向它的软链接。
  新加 skill：放进 `~/.agents/skills/`，再 `ln -s ~/.agents/skills/<名字> ~/.claude/skills/<名字>`。

- **Antigravity**：使用 Google 官方 `agy` CLI，每轮通过 stdin 传入 stream-json，输出映射到同一聊天界面。
  后续消息用已保存的 `--conversation <id>` 续聊，避免恢复到其他对话。使用 `--model` 指定型号。
  请按 [官方安装与登录文档](https://antigravity.google/docs/install?tab=cli) 在服务用户下登录；SSH 登录采用官方浏览器授权流程。
  设置 `SKILL_RUNNER_ANTIGRAVITY_BIN` 指向已安装的程序。不会自动切换到 Gemini API Key 计费。
  由于原生 `--sandbox` 在系统不支持时可能无效，此接入在沙箱配置开启时拒绝启动，生产现有明确关闭沙箱的模式可用。
  读取技能文件后按任务要求执行，产物仍放在本次运行目录。

## 选择具体模型与更新工具

长文的「译本 2 Agent」提供 Codex、Claude、Antigravity 三个单选项，选择本身不会启动任务。
点击开始或重新翻译后使用所选工具新建翻译会话；原来有会话时先调用 `/runs/{id}/stop`，
等待旧进程关闭、取消待确认问题和自动回复后再启动。停止失败不会启动替代任务。
旧会话及文件保留，并记为已中断，避免把未完成产物当成完成译文自动导入；新译文完成后更新所选工具的译本。

在「新对话」里先选 Claude、Codex 或 Antigravity，再用「具体模型」选择型号，也可以填写完整模型 ID。
浏览器分别记住每个 Agent、每种工具的选择；对话会保存所选模型，刷新或服务重启后续聊仍沿用它。
选择「默认模型」时使用服务器配置；对话标题下优先显示运行工具实际返回的模型。

Codex 清单来自服务用户的 `CODEX_HOME/models_cache.json`，Claude 清单来自 SDK 初始化握手，Antigravity 清单来自 `agy models`，均不提交推理请求。
「刷新模型」会绕过应用层缓存；Codex 仍依赖其 CLI 更新本地清单，其他工具返回的目录也不等于账号额度或权限验证。
清单不可用时页面说明原因，仍可使用默认模型或手填 ID。可用型号及权限由该账号决定，手填 ID 不保证账号有权使用。

登录后打开侧栏「工具与更新」，点击「检查更新」查看实际运行版本与官方稳定版本，再单独更新 Codex 或 Claude Code。
更新会拒绝运行中、等待确认或正在启动的对话；关闭空闲进程后安装，成功后核对实际版本。网页重新打开能继续查看进度，
但服务重启会清空更新记录，需要重新检查。失败信息会保留在窗口里，不会把安装失败报告为成功。

- Codex 网页更新支持服务用户有写权限的 npm 全局安装，并校验当前命令确实属于该安装。
  自定义命令或其他安装方式需在服务器手动更新。
- Claude 使用原生命令 `claude install <已检查的版本>` 更新。SDK 与模型发现统一优先使用 `~/.local/bin/claude`，
  其次 PATH 中的 Claude，最后回退到 SDK 自带程序。`SKILL_RUNNER_CLAUDE_BIN` 可显式指定路径；自定义路径不支持网页自动更新。
- 更新程序不会修改登录凭证、运行记录或 Python SDK 包。SDK 升级继续按上面的部署流程操作。
- Antigravity 版本与官方原生 manifest 比较；它使用官方 CLI 自带的自动更新，此处仅显示版本状态，不通过 npm 安装同名第三方包。

## 等确认超时自动继续

系统提示词要求：一轮结束时如果在等用户确认，回复最后单独一行写 `【等待确认】`（`runner.AWAIT_MARK`）。
带这个标记结束的一轮记为 `awaiting_reply=True`（是在等你，不是做完了）；文章工作台据此不去导入译文，而是提示去确认。

建任务时可以带 `auto_reply_minutes`（新任务页默认勾选 10 分钟，文章工作台交出去的任务固定 10 分钟，
和网页版术语确认一致）。等确认超过这么久没人回复：AskUserQuestion 自动选推荐选项（标了 Recommended / 推荐的，
没有就第一个）；带标记结束的一轮则自动发一条「按你推荐的方案确认、继续」。每个任务最多自动 3 次，
到时间点记在 `auto_reply_at`，服务重启后照旧接着排。

## 删除与找回

页面上「删除」对话是假删除：整个运行目录从 `~/skill-runner/runs/<id>` 原样挪到 `~/skill-runner/deleted/<id>`
（同名已存在时加 `-1`、`-2`），文件一个不少。每次删除往 `~/skill-runner/deleted/deleted.jsonl` 追加一行，
记着删除时间、原因（`user` 页面删除 / `upload_failed` 创建时上传失败）、标题、Agent、模型、上传和产出的文件清单、
存档路径和来源 IP；同一条也在服务日志里：`journalctl --user -u skill-runner | grep "deleted run"`。

找回：`mv ~/skill-runner/deleted/<存档目录名> ~/skill-runner/runs/<原 id>`（原 id 就是记录里的 `run_id`；存档目录名带 `-1`、`-2` 后缀时必须改回原 id）后 `systemctl --user restart skill-runner`。

## 安全边界

- 登录：单口令，`HttpOnly; Secure; SameSite=Strict` 的签名 cookie（记一年，每天第一次用时自动续期，一直在用就不用再输口令），连续 5 次输错锁 1 分钟；除登录外所有接口和事件流都校验。
- 权限：命令和改文件不逐条确认（这是选定的工作方式），默认由两层兜底：
  - Bash 及其子进程在沙箱里：只能写运行目录和 `SKILL_RUNNER_EXTRA_WRITE`，网络只放行白名单域名，不允许绕出沙箱；
  - Edit/Write 等文件工具不受沙箱约束，由 `policy.py` 按同一份白名单拦截，拦截会显示在页面上。
- `SKILL_RUNNER_SANDBOX=0` 是完全放开：没有沙箱，`policy.py` 也全部放行（Bash 已能写任何地方，单独拦文件工具没有意义）。
  只剩系统提示词里「不要动运行目录以外的东西」的约定。用户 2026-10-24 选定服务器用这个模式。
- 下载接口只给运行目录里的文件，`meta.json`、`events.jsonl` 和隐藏文件不可下载，符号链接越界会被拒绝。

## 本地开发

```bash
pip install -r skill_runner/requirements.txt
# Windows 没有沙箱，开发时关掉；cookie 走 http 要关 Secure
SKILL_RUNNER_PASSWORD=dev SKILL_RUNNER_SANDBOX=0 SKILL_RUNNER_COOKIE_SECURE=0 python -m skill_runner
cd web/frontend && npm run dev   # vite 已把 /api/skills 代理到 18090
```

测试：`pytest tests/unit/skill_runner`（不需要 SDK；装了 SDK 时会多跑消息映射那组），前端 `npx vitest run src/features/skills`。
在 Claude Code 里开发时，启动前先清掉 `CLAUDECODE` 环境变量（`env -u CLAUDECODE ...`），否则会被当成嵌套会话。
