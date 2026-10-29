# 文章工作台：主译本、Agent + 模型与界面重做（2026-10-28）

用户的要求：
1. 长文用 Agent 翻译时，三个 Agent 都要能选**具体模型**；
2. 「现在的界面已经太乱了」「所有都受不了，完全不符合美学」：工作台整体重做，而且要优雅好看；
3. 要有一个地方选**主译本**：「我就是基于这个版本改，最终也大概率导出这个，所以需要有一个标记」；
4. 只有 Agent 版需要「重新翻译」；网页版只有没翻完时才能「继续翻译」；
5. 第三个 Agent 从 Antigravity 改名为 **Gemini**，前端所有显示都改；
6. 真的检查 Agent，确保它翻的是下载好的 HTML。下载在 skill 外层做，skill 的输入就是下载好的 HTML；不需要感知文章是否付费，
   也不存在 Claude 不能翻的问题。

范围：文章工作台（`/articles/:id`）和文章库「导入后怎么翻」。Agent 页只改 Gemini 改名和 Codex 说明文案（见第 9 节）；
Agent 页对话的假删除另见 `2026-10-28-agent-run-soft-delete-design.md`。
设计过程中的线框图和高保真稿存在会话 scratchpad 里，不进仓库。以本文的文字和示意为准。

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

- **三栏改成「英文 | 主译本 | 对照」**。中间永远是主译本；右边「对照」放其余所有版本，用标签切换。
- **主译本**：在对照栏点「☆ 设为主译本」，两版对调位置。主译本记在服务器上；导出默认导出它；文章列表的进度只看它。
- **各版本按来源命名**：网页版、Codex、Claude、Gemini，以及以前留下的模型版（argon 等）。不再用「译本 1 / 译本 2」。
- **翻译按钮看这一栏显示的是哪一版**：Agent 版只有「↻ 重新翻译」（只换模型，不换 Agent）；网页版只在没翻完时有「▶ 继续翻译」；
  还没用过的 Agent 从对照栏标签末尾的「＋」加。
- **每个 Agent 只留一版**。重新翻译会整篇替换这个 Agent 的旧版，包括旧版上的人工修改；**重翻期间旧版只读**。
- **视觉方向 A「书页」**（第 5 节）：安静、像在读一本排好的书。
- **状态写在版本名下面那一行**，不用横幅，也不用栏内提示框。
- **导入页**：四选一改成「网页版」「Agent」两个勾选，勾上 Agent 才展开 Agent 和模型的选择。
- **不感知付费**：去掉所有付费相关、或说 Claude 不肯翻的提示（第 8.3 节）。
- **Antigravity 在界面上一律叫 Gemini**（第 9 节）。

## 3. 非目标

- 多个 Agent 同时翻同一篇。仍然是一篇文章同时只有一个 Agent 在跑（`claude_run_id` 只有一个），开始新的会先停掉旧的。
- 同一个 Agent 保留多个模型的版本。
- 改服务器上的默认模型配置（`SKILL_RUNNER_*_MODEL`）。
- 恢复「换个模型再翻一版」（kind=model）的入口。已有的模型版照常显示、能改、能导出、能继续翻译。
- 定稿、逐段确认这类状态（10-26 用户已明确否掉）。主译本只是一个指针：不锁定、不需要确认，随时可以换。
- 新做暗色模式。沿用项目现有的主题变量。

## 4. 信息结构

### 4.1 三栏

```
英文（原文）  │  ★ 主译本（某一版）  │  对照（其余各版，标签切换）
```

- **英文**：原文，不能改。
- **主译本**：当前主译本那一版，能改、自动保存。
- **对照**：其余各版，标签顺序是 网页版、Codex、Claude、Gemini、模型版（只列存在的，主译本那版不出现在这里），末尾一个「＋」。
  对照栏的版本也能改（和现在一样）。
- 两个中文栏都支持「整段采用」：从另一栏把这一段整段拿过来，和现在一样。

### 4.2 主译本

- **存在哪**：主项目 meta 加 `primary_target: Optional[str]`，值是主项目 id（网页版）或某个孪生项目 id（Agent 版 / 模型版）。
  孪生项目 id 是确定的（`{主id}--codex` 等），同一 Agent 重新翻译后 id 不变，主译本跟着不变。
- **默认**（`primary_target` 为空，或指向的版本已不存在）：网页版有译文或正在翻 → 网页版；否则最近导入的那一版 Agent 版；
  都没有 → 网页版。有了第一版 Agent 译文时把当时显示的那一版写进 meta（导入时；已经有 Agent 版的旧文章在第一次打开工作台时），之后再加 Agent 版、在网页版里写字都不会让主译本自己换，只有「设为主译本」能改。（10-29 修订：原先默认值不写回 meta，最终审查发现在网页版里写一段、或再加一个 Agent 版，主译本会自己跳。）
- **换主译本**：对照栏当前显示的那一版，栏头右侧有「☆ 设为主译本」。点了以后两版对调位置，原来的主译本进对照栏并成为当前标签。
  马上生效，不用确认。
- **影响**：
  - 顶栏「导出主译本」直接下载它的中文 Markdown；
  - 文章列表的进度和状态只看它；
  - 手机上顶部切换写「英文 / 主译本 / 对照」。

### 4.3 翻译按钮规则

主译本栏和对照栏用同一套规则，看这一栏**当前显示的是哪一版**：

| 显示的是 | 栏头的翻译按钮 |
|---|---|
| 网页版：翻完了 / 正在翻 / 在等确认术语 | 没有 |
| 网页版：缺段、出错停下、还没开始 | 「▶ 继续翻译」 |
| Agent 版（Codex / Claude / Gemini） | 「↻ 重新翻译」：只换模型，不换 Agent |
| 模型版（argon 等） | 缺段时「▶ 继续翻译」，否则没有 |
| 对照栏标签末尾 | 「＋」：只列还没有译本的 Agent；三个都有了就不显示 |

- **继续翻译**：还没开始时就是从头翻（`startWorkflow`）；已经翻了一部分时重译缺段所在的章节，也就是原来的「补译」。
  开始前确认一次，确认框沿用现在的文案：「重译缺译段落所在的 N 章：…这几章里已有的译文（包括你改过的）会被新译文替换」。
- **想换一个 Agent**：用「＋」加一版，再「设为主译本」。
- 一个 Agent 正在跑时，别的「重新翻译」和「＋」照样能点，弹框里会写「会先停掉正在跑的 Codex」。

## 5. 视觉方向 A「书页」

关键词：安静、留白、排版感。颜色、圆角、阴影都克制，信息靠字号、字重和灰度分层，不靠彩色标签和框线。

### 5.1 设计变量

全部用项目已有的主题变量（`fluid-theme.css`、`index.css`），不另起一套：

| 用途 | 变量 / 值 |
|---|---|
| 页面底色 | `--color-bg-primary`（暖白 `#fbf8f6`）；顶栏和底色融为一体，不画边框 |
| 纸张 | `--color-bg-secondary`（白）；圆角 14px；阴影 `0 1px 2px rgba(43,39,48,.05), 0 10px 30px rgba(43,39,48,.06)` |
| 分隔线 | `--color-border-subtle`（`#efe7ea`），只用在三栏之间、栏头与正文之间 |
| 主色 | `--color-primary-500`（`#a33d70`）：主按钮、主译本细线和小标题、选中态；不大面积使用 |
| 主译本底色 | 比白色略暖的极浅底（约 `#fdfaf9`），栏头顶部一道 2px 梅红渐变细线（`primary-300` → `primary-500`） |
| 文字 | `--color-text-primary` / `secondary` / `muted`；小标题用更浅一级 |
| 状态色 | `--color-success` / `warning` / `info` / `error`，只用在 6px 圆点和状态行文字上 |

### 5.2 字体

- 中文正文和版本名：`--font-display`（思源宋体，已自托管），正文 15.5px / 行高 1.95。
- 英文原文：新增衬线体 **Source Serif 4**（和思源宋体一样自托管、按需加载），14.5px / 行高 1.78，颜色比中文浅一级。
- 界面文字（按钮、状态行、小标题）：`--font-body`（Inter + 苹方 / 雅黑），12–13px。
- 小标题（「原文」「★ 主译本」「对照」）：11px，字距 0.14em。

### 5.3 图标与按钮

- 图标统一用 lucide（项目已在用），描边 1.75。不再用 ☰ ↻ ⋯ ⤓ 这类字符。
- 栏头操作默认只放图标按钮（32×32，圆角 8，悬停有浅底）；文字按钮只有两个：「☆ 设为主译本」（梅红文字、无边框，悬停浅底）
  和状态行里的行动链接（「继续翻译」「去确认 →」）。
- 主按钮（「导出主译本」、弹框里的确认）用梅红实心胶囊，带一层很淡的同色阴影。

### 5.4 动效

只在三处：弹框淡入并微微上移（150ms）；对调主译本时两栏内容交叉淡入（200ms）；标签切换没有动效。
用户开了「减少动态效果」时全部关掉。

## 6. 界面细节

### 6.1 整页

```
 ▢  HBM4 的成本结构                                 ✓ 已保存   🔖   ( ⤓ 导出主译本 | ▾ )   ⋯
    HBM4 Cost Structure: Logic Base Dies…  (英文斜体小字)
╭──────────────────────┬────────────────────────────┬──────────────────────────────╮
│ 原文               ‹ │━━━━━━━━━━━━━━━━━━━━━━━━━━━━│ 对照            ☆ 设为主译本 ⋯ │
│ English              │ ★ 主译本            ↻  ⋯   │ ( 网页版 | Claude | ＋ )        │
│ SemiAnalysis · 4,180 词│ Codex                      │ ● 缺 3 段 · 继续翻译           │
│                      │ ● 已完成 · gpt-5.5-codex   │                              │
├──────────────────────┼────────────────────────────┼──────────────────────────────┤
│ The base die moves…  │ 基底裸片改用逻辑工艺        │ 基底裸片转向逻辑工艺          │
│ HBM4 moves the base… │ HBM4 把基底裸片从 DRAM…     │ HBM4 将基底裸片由 DRAM…       │
╰──────────────────────┴────────────────────────────┴──────────────────────────────╯
```

正文上方只有两层：顶栏和栏头。三栏是一张浮起的白纸，左右各留 22px 页边。

**顶栏**（从左到右）：
- 文章列表按钮（panel-left 图标；窄屏是返回）。
- 标题：中文宋体 19px；下面一行英文原标题，衬线斜体 13px（和中文相同时不显示）。
- 「✓ 已保存 14:20」：保存状态，同时也是保存按钮，点它立刻保存，Ctrl/⌘+S 不变。保存中写「保存中…」，有失败写「⚠ 2 段没保存上」（红字）。
  两个中文栏的状态合并：有失败就显示失败数，有保存中就显示保存中，否则显示最后一次保存的时间。
- 书签图标（实心、梅红）：有阅读标记时才出现。点开是一张小卡片：标记处的文字、「继续阅读」（每个展开的栏都滚到标记处）、
  「清除」。原来那行「在段落上边缘点…」的提示文字去掉。
- 「⤓ 导出主译本 | ▾」：左半边直接下载主译本；▾ 里是英文原文和其余各版（写上模型，比如「Claude（opus）」）。这是唯一的导出入口。
- 「⋯」：原文链接、旧版编辑器（单段重译、质量报告）、下载全部文章的人工改动。

顶栏不放任何状态签。

### 6.2 栏头

每个栏头是一个三行的排版块，三栏一样高：

1. **小标题**：「原文」/「★ 主译本」（梅红）/「对照」。
2. **版本名**：宋体 16px。原文栏写「English」；主译本栏写版本名（网页版 / Codex / …）；
   对照栏这一行换成分段标签 `( 网页版 | Claude | ＋ )`：浅灰胶囊底，选中的那个是白底加一点阴影。
3. **状态行**：12px 灰字，格式是「● 状态 · 模型 · 行动」，见 6.3。原文栏写「SemiAnalysis · N 词」。

右上角操作：
- 原文：收起 ‹。
- 主译本：翻译按钮（按 4.3，图标按钮：↻ 重新翻译；继续翻译写在状态行里）、⋯（看我改了什么；看 {Agent} 的对话）、收起 ‹。
- 对照：「☆ 设为主译本」、⋯（同上）、收起 ‹。

对照栏宽度不足 420px 时，分段标签收成一个下拉：`网页版 ▾`。手机上始终是下拉。

### 6.3 状态行

所有状态都写在版本名下面这一行，不再有横幅和栏内提示框。行动链接是梅红文字，点了就去做。

| 状态 | 状态行（示例） | 色调 |
|---|---|---|
| 已完成 | ● 已完成 · gpt-5.5-codex | 绿点、灰字 |
| 翻译中（网页版） | ● 翻译中 32/57 | 蓝点 |
| 等你确认术语（网页版） | ● 等你确认术语 · 14:30 自动采用建议 · 去确认 → | 黄点、黄字 |
| 缺段 / 出错停下（网页版、模型版） | ● 缺 3 段 · 继续翻译 | 黄点、黄字 |
| 还没开始（网页版） | ● 还没开始 · 开始翻译 | 灰点 |
| 第一次用某 Agent，翻译中 | ● 翻译中 · Gemini 3.8 Pro · 看对话 → | 蓝点 |
| Agent 重翻中 | ● 重翻中 · gpt-5.5-codex · 翻完前只读 · 看对话 → | 蓝点 |
| Agent 等你确认 | ● 等你确认术语表 · 14:30 自动按建议继续 · 去确认 → | 黄点、黄字 |
| Agent 跑完但没导入 | ● 没导入：没找到 zh.md · 看对话 → | 红点、红字 |
| Agent 译文和原文对不上 | ● 没导入：英文稿只对上 40/57 段 · 看对话 → · 仍然导入 | 红点、红字（见 8.2） |
| Agent 运行出错 / 中断 | ● 出错了：模型 ID 不存在 · 看对话 → | 红点、红字 |
| 这个浏览器没登录 Agent 页 | ● 要先登录一次 Agent 页才能看进度 · 去登录 → | 黄点 |

- 文案太长时截断，悬停显示全文。
- 网页版的「去确认」打开现在的术语确认抽屉；Agent 的「去确认」「看对话」打开现在的对话抽屉。
- 模型名的取法：已导入的版本用导入记录里的 `model`（6.2 节技术部分）；正在跑的用 run 的 `actual_model`，没有就用 `model`；
  都没有（旧记录）就不写模型名。

**第一次用某个 Agent 时**，这个 Agent 的标签在它开始跑时就出现在对照栏，并自动切过去，正文写「译文还没出来」（浅灰）。

### 6.4 正文

- **保持 10-27 定的连续阅读**（`docs/plans/2026-10-27-continuous-reading.md`）：三栏各自是一篇连续文章、各自滚动，
  不强求同一段等高。高保真稿里画成了逐行对齐，以本条为准。悬停时只有这一栏的这一段出现极浅的梅红底纹。
- 阅读标记沿用 10-27 的交互：段落上边缘的「看到这里」小工具条，悬停或聚焦时出现，再点一次取消；
  顶栏书签按钮跳到标记处（每个展开的栏都跳）。被标记的段落改成左侧一道 2px 梅红细线，工具条里的书签常显，
  替代现在的整块浅底加描边。
- 缺译的段落写「还没有译文」（浅灰），能直接点进去写。
- **只读**：重翻中的那一版，段落不能编辑，文字变浅；「整段采用」这类往这一栏写入的操作也禁用。从这一版采用到另一栏不受影响。

### 6.5 选择框

两种弹框都锚在触发它的按钮下面，宽 320px，圆角 14px，阴影比纸张深一级。

**重新翻译（Agent 版）**

```
重新翻译 Codex 版
在服务器上跑，关掉页面也不会停
模型
 ○ 默认                  gpt-5.5
 ● gpt-5.5-codex         上次用
 ○ gpt-5.4-mini
 ◌ 填写模型 ID…
⚠ 翻完会整篇替换现在的 Codex 版，你改过的 12 段也会被替换；翻完前这一版只读。
                                  取消  ( 重新翻译 )
```

**＋（再加一个 Agent 版）**

```
用 Agent 再翻一版
只列出还没有译本的 Agent
 [ C  Codex  ChatGPT 订阅 ]  [ G  Gemini  Google 账号 ]
模型
 ● 默认                  gpt-5.5
 ○ gpt-5.5-codex
 ◌ 填写模型 ID…
                                  取消  ( 开始翻译 )
```

- **模型列表**是单选列表，不用原生下拉框。选项依次是：
  - 「默认」，右侧写服务端给的 `default_model`；没有就写「账号默认」；
  - 服务端模型清单；
  - 「填写模型 ID…」，选中后变成输入框。
  - 列表超过 6 项时内部滚动。
  - 列表下方一行小字：「上次用 X · 刷新清单」。读清单失败时写「模型清单读取失败，仍可使用默认模型或填写模型 ID」。
  - 不显示 Agent 页那段「来源：…CLI 本地缓存」的说明。
- **Agent 卡片**：首字母方块头像 + 名字 + 一句说明（`HARNESSES[].note`，见第 9 节），单选；切换 Agent 时，模型列表换成它上次用的模型。
  只有一个可选时也显示卡片（单张，已选中）。
- **记住选择**：沿用 Agent 页的存储（`loadHarness` / `saveHarness`、`loadModel` / `saveModel`，Agent 名用 `four-step-translate`），
  所以这里和 Agent 页给翻译 Agent 选的是同一份记忆。点确认按钮时才保存。
- **警告**（有几条显示几条）：
  - 重新翻译时：「翻完会整篇替换现在的 {Agent} 版，你改过的 N 段也会被替换；翻完前这一版只读。」N 来自 `GET /workbench/changes`；
    为 0 时去掉「你改过的…」，读不到时写「翻完会整篇替换现在的 {Agent} 版」。
  - 有 Agent 正在跑或在等确认：「会先停掉正在跑的 {Agent}。」
- 按 Esc、点「取消」或点框外面都会关掉。打开时焦点在第一个可选项上，方向键在选项间移动。
- 确认后按钮变成「开始中…」并禁用，直到 run 建好（沿用 `agentStartLock`）。

### 6.6 收起和手机

- 收起后的竖条：栏名竖排，上方一个状态圆点（颜色同状态行）。
- 手机：一次看一栏，顶部分段切换「英文 / 主译本 / 对照」。对照栏的标签收成下拉；栏头的状态行照常显示。

### 6.7 文章库「导入后怎么翻」

```
导入后怎么翻
☑ 网页版
  网站自己的翻译流程
☑ Agent
  在服务器上跑，关掉页面也不会停
  [ Codex ] [ Claude ] [ Gemini ]      ← 同 6.5 的 Agent 卡片（三个都可选）
  模型  ● 默认 gpt-5.5  ○ …            ← 同 6.5 的模型列表
( 导入并翻译 )                          ← 两个都不勾时写「导入」
```

默认两个都勾上（等同原来的「两个都翻」）。

## 7. 前端结构

目录是 `web/frontend/src/features/articles/`。

| 单元 | 做什么 |
|---|---|
| `lib/versions.ts`（新） | 纯函数：由 `variants`、`project`、`primary_target`、当前 `run`、导入失败信息算出所有版本（id、来源、显示名、模型、状态色调、状态行文字和行动、是否只读、翻译按钮类型），以及主译本是哪一版、对照栏默认显示哪一版 |
| `lib/agentChoice.ts`（新） | `AgentChoice = { harness, model }`；读写记忆（包装 skills 的 `loadHarness/saveHarness/loadModel/saveModel`） |
| `components/ModelList.tsx`（新） | 6.5 的模型单选列表（含默认、填写 ID、刷新、读取失败提示），受控 |
| `components/AgentCards.tsx`（新） | 6.5 的 Agent 卡片单选，受控；可以传入可选的 Agent 子集 |
| `components/TranslatePopovers.tsx`（新） | 6.5 的两种弹框（`RetranslatePopover`、`AddAgentPopover`，共用外壳） |
| `components/ColumnMenu.tsx`（新） | 栏头「⋯」：用 Popover（点击打开），不用 DropdownMenu |
| `components/VersionHeader.tsx`（重写） | 6.2 的三行栏头：小标题、版本名或分段标签、状态行、右上角操作 |
| `components/StatusLine.tsx`（新） | 6.3 的状态行 |
| `components/SaveStatus.tsx`（新） | 顶栏合并保存状态 + 点击保存 |
| `components/PaneGrid.tsx` | 栏 id 改成 `source / main / compare`；`PaneColumn` 加 `readOnly`、`tone`（收起竖条上的圆点）；纸张样式、悬停整行底纹、阅读标记书签 |
| `components/EditableText.tsx` | 加 `readOnly` |
| `components/Workbench.tsx` | 只负责取数据和组装回调。去掉 `SecondVersionPrompt`、`StatusChip`、`Banner`、阅读提示行。现在 602 行，目标 350 行以内 |
| `components/ArticlePreview.tsx`、`lib/importFlow.ts` | 6.7；`importAndTranslate(article, { web: boolean, agent: AgentChoice \| null })` |
| `lib/claude.ts` | `startClaudeTrack(projectId, choice, title)` 把 `model` 传给 `startRun`；`importClaudeTrack(projectId, run, { force? })` 带上 `agent` 和 `model` |
| `lib/panes.ts` | 收起状态的 localStorage 键从 `web/alt` 迁到 `main/compare`（读到旧键时换算一次） |
| 字体 | Source Serif 4 子集按 `--font-display` 的方式自托管，新增 `--font-source-serif` |
| 删除 | `ArticleAgentChoice.tsx`、`lib/agentOptions.ts`（并进 `agentChoice.ts`） |

弹层沿用 `components/ui/` 里已有的 popover / dropdown，不新增 UI 库。

## 8. Agent 的输入：确实是下载好的 HTML

### 8.1 链路（现状，已核对代码）

1. 文章库导入：`substack_service.fetch_article` 带订阅 cookie 下载整页 HTML；页面里有付费墙标记就报错，不会存半篇（`src/services/substack_service.py:240`）。
2. 存成项目目录里的 `source.html`（`project_lifecycle_service.py:118`）；网页版也是从这份文件解析的。
3. 工作台发起 Agent 翻译：前端取 `GET /projects/{id}/source-html`（就是这份 `source.html`），作为附件上传给 skill-runner，
   消息是「精翻附件里的这篇文章…」。
4. four-step-translate 的第一步是 `html2md.py <附件> → en.md`，之后翻译 en.md。

下载在 skill 外层做，skill 只拿到这份 HTML，不需要知道文章是否付费。

### 8.2 常设保险：导入时核对英文稿

导入 Agent 译文时，`align_claude_translation` 拿 Agent 的 en.md 和项目从同一份 `source.html` 解析出的段落逐段比对。
现在只有一段都对不上时才拒绝；改成**非图片段落对上不到 80% 就不自动导入**，状态行显示「没导入：英文稿只对上 N/M 段 · 看对话 → · 仍然导入」。
点「仍然导入」时带 `force=true` 照常导入。80% 是保守值：10-25 Codex 那次是 61/61 全对上。

### 8.3 去掉的付费相关提示

以下现有文案全部去掉，不换成别的说法：
- 导入页选 Claude 时的「付费文章 Claude 通常不肯全文翻译，只给导读」（`ArticlePreview.tsx`）；
- Codex 说明里的「付费文章也肯全文翻」（`skills/harness.ts`）；
- 没拿到译文时专门推荐「选择 Codex」的按钮（`Workbench.tsx` 的 `claudeNote` 横幅），统一成状态行里的「看对话」；
- 代码注释里「Claude 不肯翻付费文章所以默认 Codex」一类的说法（`skill_runner/agents.py`）。

默认 Agent 仍是 Codex，这只是默认值。保留的：文章库里的「付费」小标签和导入付费文章时填订阅 cookie 的表单，那是下载要用的。

### 8.4 实测

2026-10-28 用金丝雀 HTML 实测三个 Agent：复制一篇已下载的文章，在正文第一段后插一句网上不存在的话
（「Canary check 7Q4Z: in our fictional Aurora-9 scenario…」），三个 Agent 依次用默认模型跑 four-step-translate。
检查三点：en.md 和 zh.md 里有没有这句、过程中有没有联网抓原文、实际用了哪个模型。
结果记录在服务器 `~/backups/agent-canary-20261028/report.json`。

**结论（2026-10-29）**：用的是付费文章 `intel-should-raise-capital`（`audience: only_paid`）。三个 Agent 都只用了上传的 HTML。

| Agent | 范围 | 用时 | 金丝雀 | 联网抓原文 | actual_model |
|---|---|---|---|---|---|
| Gemini | 全文，QA 通过 | 16 分钟 | en.md、zh.md 都有 | 无 | 空（默认模型不上报） |
| Codex | 全文，QA 通过 | 12 分钟 | en.md、zh.md 都有 | 无 | 空（10.1 节修） |
| Claude | 只翻第一章（用户额度不够，只验链路） | 2 分钟 | en.md、zh-part1.md 都有 | 无 | claude-opus-5-5 |

Gemini、Codex 的 `html2md.py` 都是对 `input/intel-should-raise-capital.html` 跑的。Claude 的工具摘要只写用途、不写命令，但它的 en.md 含金丝雀句，只可能来自上传的文件。三个都没有拒绝翻译这篇付费文章。

## 9. Gemini 改名

- 界面上所有「Antigravity」改成「Gemini」：`skills/harness.ts` 的 `label`，`ModelPicker`、`RuntimeUpdatesPanel` 里的文案，
  文章工作台的版本名和弹框。skill-runner 返回给页面的文字也改（`harness_label()`、模型清单读取失败的提示、
  「Antigravity 会话已关闭」等错误信息）。
- 不改的：内部 id `antigravity`（API 参数、localStorage 里存的值、run meta）、环境变量 `SKILL_RUNNER_ANTIGRAVITY_*`、
  CLI 命令 `agy`、孪生项目 id 后缀。
- 导入时孪生项目的 label 从 `"Antigravity"` 改为 `"Gemini"`。`create_variant` 的 `suffix` 改用 Agent id（`claude / codex / antigravity`），
  这样 Claude、Codex 的孪生项目 id 不变，Gemini 版的 id 是 `{主id}--antigravity`。已有 label 为「Antigravity」的版本，前端按 Agent id 显示成 Gemini。
- Codex 的说明改成「用你的 ChatGPT 订阅（Codex）」；Gemini 的说明改成「用服务器上登录的 Google 账号（Gemini）」；Claude 不变。

## 10. 后端与 skill-runner

### 10.1 skill-runner：每次运行固定一个模型，并记下实际模型

- Codex：现在没指定模型时，**每一轮** `build_command` 都会重新取 `models_cache.json` 排第一的模型，同一个任务中途可能换模型，
  而且 `actual_model` 一直是空的。改成 `CodexSession` 打开时就把模型定下来（`spec.model or config.codex_model or latest_model(...)`），
  之后每一轮都用它；`CodexMapper` 发 `session` 事件时带上 `model`，runner 就会写进 `actual_model`。
- Claude、Gemini（Antigravity）：初始化事件里带模型时会写进 `actual_model`，不改。Gemini 没指定模型时，初始化事件可能不带模型名，
  这时状态行就不写模型名。
- 第 9 节的文案改名。

### 10.2 主站

- `ProjectMeta` 加 `primary_target: Optional[str] = None`；新接口 `PUT /projects/{id}/workbench/primary`，
  body `{ "target": "<主项目或孪生项目 id>" }`，校验 target 是主项目自己或它的孪生项目。`GET /workbench` 返回 `project.primary_target`。
- 文章列表（`substack.py` 的 `_translation_state`）：进度和状态只看主译本（`primary_target`，为空时按 4.2 的默认规则），
  不再取各版本里最高的那个。Agent 正在跑的状态主站不知道（在 skill-runner 里），列表照旧只反映段落进度。
- `ImportClaudeRequest` 加 `model: Optional[str] = Field(None, max_length=128)` 和 `force: bool = False`；
  导入记录（`artifacts/claude-import.json`）加 `agent`、`model`；对上不到 80% 且没有 `force` 时返回 409，
  错误里带 `aligned` / `total`，前端据此显示 6.3 的那一行。
- 第 9 节的 label 和 suffix。

## 11. 边界情况

- 读模型清单很慢或失败：列表照常能选「默认」和「填写模型 ID」，不挡确认按钮。
- 填了不存在的模型 ID：CLI 报错，状态行显示「出错了：…」+ 看对话。
- 正在跑时刷新页面：标签、只读、状态行都从 `run` 的状态算出来，不依赖页面内存。
- 停掉旧 run 后，旧 run 的半成品不会被自动导入（沿用 `importTried` 逻辑）。
- 主译本那版正在重翻：中间栏只读，状态行写「重翻中」；导出主译本照常导出现在这版。
- `primary_target` 指向的孪生项目被删：按默认规则显示，下次「设为主译本」时覆盖。
- 弹框打开期间 run 的状态变了：警告文案跟着数据更新。

## 12. 测试

- 单元（vitest）：
  - `versions`：版本顺序；主译本默认规则；对调；各状态的状态行文字和行动；只读；翻译按钮类型（4.3 每一行）；
    「＋」只列没有译本的 Agent；旧导入记录用 label 反推 Agent；Antigravity 显示成 Gemini。
  - `agentChoice`：按 Agent 记住模型；和 Agent 页共用存储键。
  - `ModelList`：默认项文案、上次用、填写 ID、读取失败提示。
  - `RetranslatePopover` / `AddAgentPopover`：警告（N=0、N>0、读取失败、会停掉正在跑的）；确认时传出 `{ harness, model }`。
  - `importFlow`：四种勾选组合。
  - `lib/panes`：旧收起键迁移。
  - `articles.test.tsx`：按新结构更新。
- 后端（pytest）：`primary_target` 读写和校验；列表进度只看主译本；导入记录带 `agent`、`model`；对上不到 80% 返回 409，`force` 时导入；
  Gemini 的 label / suffix。
- skill-runner（pytest）：Codex 没指定模型时第一轮和续聊轮用同一个模型；`session` 事件带 `model`；对外文案里没有 Antigravity。
- 端到端（Playwright）：桌面 1440 和手机 390 两种宽度截图，人工对照第 5、6 节检查：正文上方只有两层；三栏栏头一样高；状态行各状态；
  对调主译本；只读；对照栏窄栏下拉。
- 前端文案扫描：`rg -i antigravity web/frontend/src` 只剩内部 id 和类型定义。

## 13. 发布

按 `AGENTS.md` 和 `docs/production-release.md`：从最新 `origin/main` 开分支 → 合并前再拉一次远程并重跑检查 → 发布经过验证的那个提交 →
确认本机当前目录、GitHub main、服务器（主站发布目录和 `~/skill-runner/src`）三处 SHA 一致。
skill-runner 有改动，服务器上还要 `git pull` 并重启 `skill-runner` 用户服务。
