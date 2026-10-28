# 文章工作台：Agent + 模型选择与界面重做（2026-10-28）

用户的两点要求：
1. 长文用 Agent 翻译（译本 2）时，三个 Agent（Claude / Codex / Antigravity）都要能选**具体模型**；
2. 「现在的界面已经太乱了」「所有都受不了，完全不符合美学」，工作台要整体重做。

这份文档定的是工作台（`/articles/:id`）和文章库「导入后怎么翻」两处。Agent 页（`/skills`）不在范围内。
设计过程中的线框图存在会话 scratchpad 里，不进仓库。下面的文字和 ASCII 示意以本文为准。

## 1. 现状问题（用户全部认定）

| # | 问题 |
|---|---|
| 1 | 状态说三遍：顶栏状态签、栏头进度、整页横幅；同一个 Codex 还会同时显示「已完成」和「翻译中」 |
| 2 | 导出有两个入口：顶栏「导出 ▾」加每栏的 ⤓ |
| 3 | 「译本 2 Agent」那一条一直占一整行：单选框、按钮、一长句说明挤在一起，翻完了也不消失 |
| 4 | 「⋯」菜单成了杂物间：「选择 / 更换 Agent」点了只会展开栏，Agent 对话、人工改动下载、旧版编辑器、原文链接都塞在里面 |
| 5 | 译本 2 有几版时靠栏头一个原生下拉框切换，看不出有几版、谁翻的、用的什么模型 |
| 6 | 没有阅读标记时也常驻一行提示文字 |
| 7 | 选不了模型：前端只传 `harness`，模型由服务器默认值决定；Agent 页记住的模型这里也不用 |

正文上方叠了 5 层：顶栏 → 横幅 → 阅读标记 → Agent 条 → 栏头。

## 2. 已定的决定

- **布局：方案 A「栏头就是控制台」**。译本 2 的切换、状态、翻译入口和提示都放在它自己那一栏。
- **选择框：先 Agent 后模型**。上面是 Claude / Codex / Antigravity 分段按钮，下面是模型下拉框。
- **每个 Agent 只留一版**。同一个 Agent 换模型重翻，会覆盖这个 Agent 的旧版（包括旧版上的人工修改），其他 Agent 的版本不动。
  所以译本 2 最多 3 版 Agent 译本，再加上以前留下的模型译本（argon 等）。
- **重翻期间旧版锁成只读**：翻完会整篇替换，期间的修改留不住，干脆不让改。
- **导入页**：原来四选一的单选改成「网页版」「Agent」两个勾选框。勾上 Agent 才展开同一个选择框，两个都不勾就是只导入。

## 3. 非目标

- 多个 Agent 同时翻同一篇。仍然是一篇文章同时只有一个 Agent 在跑（`claude_run_id` 只有一个），开始新的会先停掉旧的。
- 同一个 Agent 保留多个模型的版本。
- 改 Agent 页，或改服务器上的默认模型配置（`SKILL_RUNNER_*_MODEL`）。
- 恢复「换个模型再翻一版」（kind=model）的入口。已有的模型译本照常显示、能改、能导出、能补译。
- 定稿、逐段确认这类状态（10-26 用户已明确否掉）。
- 判断文章是否付费。Agent 翻的都是已经下载好的 HTML（`source-html`），不需要知道付费与否，
  也不存在「Claude 不能翻」的问题（用户 10-28 明确说的）。界面上所有跟付费有关、或说 Claude 不肯翻的提示都去掉，见 4.7。

## 4. 界面

### 4.1 整页

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ ☰  HBM4 的成本结构                          🔖 继续阅读   ✓ 已保存 14:20   导出 ▾   ⋯ │
│    HBM4 Cost Structure                                                               │
├──────────────────────┬───────────────────────────┬───────────────────────────────────┤
│ 英文               ‹ │ 译本 1 · 网页版 ●已完成  ⋯ ‹ │ ●Codex gpt-5.5-codex  ●Claude opus  ↻ 翻译 ⋯ ‹ │
├──────────────────────┼───────────────────────────┼───────────────────────────────────┤
│ 原文……               │ 网页版译文……               │ Codex 译文……                       │
```

正文上方只有两层：顶栏和栏头。

**顶栏**（从左到右）：
- 文章列表按钮（☰；窄屏是返回 ←）
- 标题（中文，衬线体）+ 英文原标题（小字，和中文相同时不显示）
- 「🔖 继续阅读」：有阅读标记时才出现。悬停显示标记处的文字；点了滚到标记处。
  清除标记仍然是在那一段上再点一次「看到这里」。原来那行「在段落上边缘点…」的提示文字去掉。
- 保存状态，同时也是保存按钮：`✓ 已保存 14:20` / `保存中…` / `⚠ 2 段没保存上`（红字）。点它立刻保存，快捷键 Ctrl/⌘+S 不变。
  两个中文栏的保存状态合并显示：有失败就显示失败数，有保存中就显示保存中，否则显示最后一次保存的时间。
- 「导出 ▾」：英文原文、译本 1 · 网页版、每个译本 2（写上模型，比如「译本 2 · Codex（gpt-5.5-codex）」）。这是唯一的导出入口。
- 「⋯」：原文链接、旧版编辑器（单段重译、质量报告）、下载全部文章的人工改动。

顶栏不再放状态签，状态只在栏头显示。

**栏头**：每栏最右边保留现在的收起按钮 ‹。它左边的「⋯」放这一栏自己的操作，不放导出（导出在顶栏），也不重复放「收起」。
- 英文：只有栏名。
- 译本 1 · 网页版：栏名 + 状态（彩色圆点 + 文字：翻译中 12/57、等你确认术语、缺 3 段、已完成、出错了、还没开始）。
  「⋯」里是：看我改了什么、补译（缺段时才有）。
- 译本 2：见 4.2。

### 4.2 译本 2 的栏头

```
●Codex gpt-5.5-codex   ●Claude opus   ●argon                ↻ 翻译  ⋯  ‹
```

- **标签页**：每一版一个标签，顺序是 Codex、Claude、Antigravity（与 `ARTICLE_HARNESSES` 一致），然后是以前留下的模型译本。
  标签上是 Agent 名 + 小字模型名 + 状态圆点。只有正在翻、还没有译本的 Agent（第一次用它）也有标签，小字写「翻译中」。
  没用过的 Agent 不出标签，要从「↻ 翻译」进去。
- **默认显示哪一版**：有 Agent 正在跑（或在等你确认）就显示它那一版；否则显示最近导入的那一版；都没有就显示第一个标签。
  页面内切换后保持，不跨页面记。
- **「↻ 翻译」**：打开选择框（4.4）。还没有任何译本 2 时栏头不显示这个按钮，选择框直接摆在这一栏中间（4.3「还没有译本 2」）。
- **「⋯」**：看我改了什么；看 {Agent} 的对话（有对话时）；补译（模型译本缺段时才有，同现在）。
- **窄栏**：这一栏宽度不足 420px 时，标签页收成一个下拉：`●Codex · gpt-5.5-codex ▾`，下拉里列各版和它们的状态。手机上始终是下拉。

### 4.3 栏内提示和各种状态

需要你处理或值得知道的事，在这一栏栏头下面用一条提示说明（和栏头一起固定在顶部）。整页横幅全部去掉。
提示分三种色调：进行中（蓝）、要你处理（黄）、出错（红）。

| 状态 | 标签 | 提示 | 正文 |
|---|---|---|---|
| 还没有译本 2 | 无（栏头只写「译本 2」） | 无 | 中间：「选一个 Agent 翻这篇」+ 一句说明 + 选择框 +「开始翻译」 |
| 第一次用某 Agent，翻译中 | ●(蓝) Antigravity 翻译中 | 蓝：「Antigravity（Gemini 3.8 Pro）正在翻译，完成后自动导入到这里」· 看对话 | 「译文还没出来」 |
| 换模型重翻中 | ●(蓝) Codex 重翻中 | 蓝：「Codex 正在用 gpt-5.5-codex 重翻；完成后替换这一版，翻完前这一版只读」· 看对话 | 旧版，**只读**、变淡 |
| 等你确认 | ●(黄) Codex 等你确认 | 黄：「Codex 在等你确认术语表 · 14:30 前不回复就按它的建议继续」· 去确认 | 有旧版就显示旧版（只读），没有就写「译文还没出来」 |
| 跑完了但没导入（没找到 zh.md / 对不上） | ●(红) Claude 没导入 | 红：原因（沿用现在的文案）· 看对话 · 重新翻译（打开选择框，可以换 Agent 或模型） | 有旧版就显示旧版（可改），没有就写「没有译文」 |
| 运行出错 / 中断（run 状态是 error，比如模型 ID 不存在、进程退出） | ●(红) Codex 出错了 | 红：run 的错误信息 · 看对话 · 重新翻译 | 同上 |
| 这个浏览器没登录 Agent 页 | 照常 | 黄：「要先登录一次 Agent 页，才能看进度和回复」· 去登录 | 照常 |
| 已完成 | ●(绿) | 无 | 可改 |

模型名的取法：已导入的版本用导入记录里的 `model`（见 6.2）；正在跑的用 run 的 `actual_model`，没有就用 `model`；
都没有就不写模型名（旧记录）。

译本 1 用同样的提示条：「网页版在等你确认术语，10 分钟内不确认会自动采用建议」· 去确认；「网页版出错了：…」。
网页版还没开始时，这一栏中间是「开始翻译」按钮（替代原来栏头里的小链接）。

「只读」的范围：这一栏的段落不能编辑；「整段采用」「补齐缺译」这类往这一栏写入的操作也禁用。
从这一栏采用到译本 1 不受影响。

### 4.4 选择框

```
┌ 重新翻译译本 2 ─────────────────────────┐
│ Agent                                   │
│ [ Claude |  Codex  | Antigravity ]      │
│ 用你的 ChatGPT 订阅（Codex）            │
│ 模型                                    │
│ [ gpt-5.5-codex                    ▾ ]  │
│ 上次用的。 刷新清单                      │
│ ⚠ 会替换现有的 Codex 版（gpt-5.5），     │
│   你改过的 12 段也会被替换。            │
│                        [取消] [开始翻译] │
└─────────────────────────────────────────┘
```

- 标题：没有这个 Agent 的版本时写「用 Agent 翻译译本 2」，有的时候写「重新翻译译本 2」。
- **Agent 分段按钮**下面一行写这个 Agent 的说明（`HARNESSES[].note`）。Codex 的说明去掉「付费文章也肯全文翻」，只留
  「用你的 ChatGPT 订阅（Codex）」。这份说明和 Agent 页共用，那边也跟着改。
- **模型下拉**：选项是「默认 · {default_model}」（服务端没给 default_model 时写「默认（账号默认）」）、服务端模型清单、「填写模型 ID…」。
  选了「填写模型 ID…」就出现一个输入框。下拉下面一行小字：「上次用的」/「默认」，和「刷新清单」链接。
  读清单失败时写「模型清单读取失败，仍可使用默认模型或填写模型 ID」。不显示 Agent 页里那段「来源：…CLI 本地缓存」的说明。
- **记住选择**：切到某个 Agent，模型下拉自动换成它上次用的模型。打开选择框时，如果当前显示的是 Agent 译本，就默认选中它的 Agent；
  显示的是模型译本或者还没有译本时，选上次用的 Agent，再没有就选 Codex。
  沿用 Agent 页的存储（`loadHarness` / `saveHarness` 和 `loadModel` / `saveModel`，Agent 名都用 `four-step-translate`），
  所以在这里选的和在 Agent 页给翻译 Agent 选的是同一份记忆。点「开始翻译」时才保存。
- **警告**（有几条显示几条，都在按钮上方）：
  - 这个 Agent 已有一版：「会替换现有的 {Agent} 版（{旧模型}），你改过的 N 段也会被替换。」N 来自 `GET /workbench/changes`，
    为 0 时不写后半句；读不到改动数时写「会替换现有的 {Agent} 版」。
  - 有 Agent 正在跑或在等确认：「会先停掉正在跑的 {Agent}。」
- 按 Esc、点「取消」或点框外面都会关掉。打开时焦点在 Agent 分段按钮上，分段按钮可以用左右方向键切换。

### 4.5 收起和手机

- 收起后的竖条上，在栏名上方显示这一栏的状态圆点（颜色同栏头），一眼看得出那一版在跑还是在等你。
- 手机：保持一次看一栏，顶部「英文 / 译本 1 / 译本 2」分段切换不变。译本 2 的标签页收成下拉，「↻」只显示图标；
  提示条和桌面一样，在栏头下面。

### 4.6 文章库「导入后怎么翻」

```
导入后怎么翻
☑ 译本 1 · 网页版
  网站自己的翻译流程
☑ 译本 2 · Agent
  在服务器上跑，关掉页面也不会停
  [ Claude |  Codex  | Antigravity ]
  [ 默认 · gpt-5.5                 ▾ ]
[            导入并翻译            ]           ← 两个都不勾时写「导入」
```

默认两个都勾上（等同原来的「两个都翻」）。选择框和 4.4 是同一个组件，只是没有标题、警告和按钮。

### 4.7 去掉的付费相关提示

Agent 翻的是下载好的 HTML，和文章是否付费无关。以下现有文案全部去掉，不换成别的说法：
- 导入页选 Claude 时的「付费文章 Claude 通常不肯全文翻译，只给导读」（`ArticlePreview.tsx`）；
- Codex 说明里的「付费文章也肯全文翻」（`skills/harness.ts`）；
- 没拿到译文时专门推荐「选择 Codex」的按钮（`Workbench.tsx` 里的 `claudeNote` 横幅），改成通用的「重新翻译」；
- 代码注释里「Claude 不肯翻付费文章所以默认 Codex」一类的说法（`skill_runner/agents.py`）。

默认 Agent 仍是 Codex。这只是默认值，不代表别的 Agent 不能翻。

保留的：文章库里的「付费」小标签，和导入付费文章时要求填订阅 cookie 的表单。下载付费原文需要 cookie，这和 Agent 无关。

## 5. 前端结构

目录是 `web/frontend/src/features/articles/`。

| 单元 | 做什么 | 依赖 |
|---|---|---|
| `lib/agentChoice.ts`（新） | `AgentChoice = { harness, model }`；`loadAgentChoice(preferred?)` / `saveAgentChoice(choice)`，内部调用 skills 的 `loadHarness/saveHarness/loadModel/saveModel`，Agent 名是 `CLAUDE_SKILL` | `skills/harness.ts`、`skills/models.ts` |
| `lib/agentTracks.ts`（新） | 纯函数：由 `variants` + 当前 `run` + 导入失败信息，算出译本 2 的标签列表（id、Agent、模型、状态色调、状态文字、是否只读、对应 variant），以及默认选中哪个标签 | `types.ts`、`skills/types.ts` |
| `components/AgentModelChooser.tsx`（新） | 分段按钮 + 模型下拉 + 自定义 ID 输入 + 刷新。受控组件：`value: AgentChoice`、`onChange` | `skillsApi.models` |
| `components/TranslatePopover.tsx`（新） | 4.4 的选择框：标题、`AgentModelChooser`、警告、取消 / 开始翻译 | 上面两个、`articlesApi.changes` |
| `components/AltPaneHeader.tsx`（新） | 4.2：标签页 / 窄栏下拉、「↻ 翻译」、栏内「⋯」 | `agentTracks` |
| `components/PaneNotice.tsx`（新） | 栏内提示条（busy / wait / error，最多两个按钮），替代 `Workbench.tsx` 里的 `Banner` | — |
| `components/SaveStatus.tsx`（新） | 顶栏的合并保存状态 + 点击保存 | `lib/edits.ts` |
| `components/PaneGrid.tsx` | `PaneColumn` 加 `notice?: ReactNode`（显示在栏头下面）、`readOnly?: boolean`、`tone?`（收起竖条上的状态圆点） | — |
| `components/EditableText.tsx` | 加 `readOnly`：只渲染、不能进入编辑，样式变淡 | — |
| `components/Workbench.tsx` | 去掉 `SecondVersionPrompt`、`StatusChip` 行、整页 `Banner`、阅读提示行、`VersionHeader` 里的导出和保存状态。只负责组装数据和回调。现在 602 行，目标 350 行以内 | 以上 |
| `components/ArticlePreview.tsx`、`lib/importFlow.ts` | 4.6：`importAndTranslate(article, { web: boolean, agent: AgentChoice \| null })`；去掉付费提示（4.7） | `AgentModelChooser` |
| `skills/harness.ts` | Codex 的 `note` 去掉付费那半句（4.7） | — |
| `lib/claude.ts` | `startClaudeTrack(projectId, choice, title)` 把 `model` 传给 `startRun`；`importClaudeTrack(projectId, run)` 带上 `agent: run.harness` 和 `model: run.actual_model ?? run.model ?? null` | — |
| 删除 | `components/ArticleAgentChoice.tsx`（被 `AgentModelChooser` 取代）；`lib/agentOptions.ts` 如果只剩排序，并进 `agentChoice.ts` | — |

样式用现有的设计变量（`primary-*`、`bg-*`、`text-*`、`success/warning/info/error`）和 `--font-display`。
弹层、下拉沿用 `components/ui/` 里已有的组件，不新增 UI 库。

## 6. 后端与 skill-runner

### 6.1 skill-runner：每次运行固定一个模型，并记下实际模型

- Codex：现在没指定模型时，**每一轮** `build_command` 都会重新取 `models_cache.json` 排第一的模型，同一个任务中途可能换模型，
  而且 `actual_model` 一直是空的。改成 `CodexSession` 打开时就把模型定下来（`spec.model or config.codex_model or latest_model(...)`），
  之后每一轮都用它；`CodexMapper` 发 `session` 事件时带上 `model`，这样 runner 会写进 `actual_model`。
- Claude、Antigravity：初始化事件里本来就带模型，`actual_model` 已经有值，不改。

### 6.2 主站：导入记录带上 Agent 和模型

- `ImportClaudeRequest` 加 `model: Optional[str] = Field(None, max_length=128)`。
- `import_claude_translation(..., agent, model)` 写导入记录（`artifacts/claude-import.json`）时加 `agent` 和 `model`。
- `GET /workbench` 原样返回导入记录；前端类型 `ClaudeImportRecord` 加 `agent?: Harness`、`model?: string | null`。
  旧记录没有 `agent` 时，前端用 label（Claude / Codex / Antigravity）反推。

不需要新接口。改动数用现有的 `GET /projects/{id}/workbench/changes?target=`。

## 7. 边界情况

- 读模型清单很慢或失败：下拉照常可用（默认 / 填写 ID），不挡「开始翻译」。
- 填了不存在的模型 ID：由 CLI 报错，错误显示在对话里；标签显示「出错了」（红），提示条里有「看对话」和「重新翻译」。
- 正在跑时刷新页面：标签、只读、提示都从 `run` 状态算出来，不依赖页面内存。
- 点「开始翻译」后、run 建好之前：选择框按钮显示「开始中…」并禁用，防止连点（沿用 `agentStartLock`）。
- 停掉旧 run 后，旧 run 的半成品不会被自动导入（沿用 `importTried` 逻辑）。
- 选择框打开期间 run 状态变了（比如刚好翻完）：警告文案跟着数据更新，不需要关掉重开。

## 8. 测试

- 单元（vitest）：
  - `agentTracks`：标签顺序；第一次用某 Agent 时的标签；重翻时只读；等确认、没导入、已完成的状态；默认选中哪个标签；旧导入记录反推 Agent。
  - `agentChoice`：按 Agent 记住模型；和 Agent 页共用存储键。
  - `AgentModelChooser`：切换 Agent 时模型跟着换；「默认 · X」的文案；自定义 ID；清单读取失败的提示。
  - `TranslatePopover`：改动数警告（N=0、N>0、读取失败）；会停掉正在跑的 Agent；开始时传出 `{ harness, model }`。
  - `importFlow`：四种勾选组合。
  - `articles.test.tsx`：按新结构更新——顶栏不再有状态签，提示在栏内，导出只在顶栏。
- 后端（pytest）：导入记录带 `agent`、`model`；请求里的 `model` 超长会被拒。
- skill-runner（pytest）：Codex 没指定模型时，第一轮和续聊轮用同一个模型；`session` 事件带 `model`。
- 端到端（Playwright，`tests/e2e/article-reading.spec.ts`）：桌面和手机各截图，人工检查正文上方只有顶栏和栏头两层、各状态的提示条、窄栏下拉。

## 9. 发布

按 `AGENTS.md` 和 `docs/production-release.md`：从最新 `origin/main` 开分支 → 合并前再拉一次远程并重跑检查 → 发布经过验证的那个提交 →
确认本机当前目录、GitHub main、服务器（主站发布目录和 `~/skill-runner/src`）三处 SHA 一致。
skill-runner 有改动，所以服务器上还要 `git pull` 并重启 `skill-runner` 用户服务。
