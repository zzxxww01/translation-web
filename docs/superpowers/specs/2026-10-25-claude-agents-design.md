# Claude 页：一个聊天 + 多个专职 agent

2026-10-25 与用户讨论确定。前身见 `2026-10-24-skill-runner-design.md`。

## 为什么改

用户反馈交互不方便。原来的新建页像填表（先选方式、再写要求），skill 名字和简介是英文，
选了 skill 也不知道该给什么。用户的心智模型是：**一个 skill 就是一个 agent，页面提供多个
agent 加一个聊天**。

## 定下来的设计

- **结构**：💬 Claude（通用聊天）+ 📄 文章精翻、🎬 视频字幕、🎙 播客配音三个专职 agent。
  **每个任务只属于一个 agent**，中途不换；想换就开新任务。
- **新任务页**：居中一个大输入框「今天要做什么？」，下面一排 agent 按钮。不点 = 和 Claude 聊；
  点了 = 输入框上挂 agent 标签（可 × 取消）、占位文字提示该给什么、下方给示例（点一下填入）。
  附件、发送都在输入框里。
- **左边列表**：「＋新任务」、按 agent 筛选（全部 / 各 agent 图标），每条带 agent 图标、标题、状态。
- **对话页**：顶部标题旁显示 agent；提问按钮、进度、文件、中断照旧。
- **Claude 聊天里**：用户要做的正好是某个专职 agent 的活时，Claude 提醒用户开对应 agent 的
  新任务，不自己跑那个 skill（系统提示词约定，不做硬拦截）。
- **不做**：切换模型、为每个 agent 定制表单、对话中途交接给别的 agent。

## 实现

- `skill_runner/agents.json`：每个 agent 的名片（中文名、图标名、说明、输入提示、示例），
  `skill` 为空串的那条是 Claude 聊天。哪些 skill 启用仍由 `SKILL_RUNNER_SKILLS` 决定；
  没写名片的 skill 回退到 skill 名和 SKILL.md 的简介。文件位置可用 `SKILL_RUNNER_AGENTS_FILE` 覆盖。
- `skill_runner/agents.py`：读名片、拼目录（聊天在第一位）、按任务给系统提示词追加说明
  （聊天任务列出专职 agent 并要求转介；skill 任务不加）。
- `GET /api/skills/catalog` 返回 `{name, title, icon, description, hint, examples, available}`，
  保留 `name` 字段兼容旧页面。
- 会话规格 `SessionSpec` 增加 `prompt_note`，由 runner 起会话时按任务填入。
- 前端：新任务页重写；列表加图标和筛选；对话页顶部显示 agent；界面文字统一叫「任务」。
  图标用 lucide（`chat`、`article`、`video`、`podcast`，未知回退为通用图标）。
