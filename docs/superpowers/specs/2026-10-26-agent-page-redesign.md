# Agent 页重新设计（2026-10-26）

用户反馈：「agent 页现在使用难度有点高，不太看得懂，对话、任务、skill……这些概念和图标也不太理解，要设计的尽可能简单易用。」
用户的心智模型：**每个 skill 就是一个 Agent**（翻译 Agent、字幕 Agent、播客 Agent……）。

## 页面上只留两个概念

- **Agent**：谁来做。通用 Agent（直接对话，什么都能问、能在服务器上动手）+ 各专职 Agent（一个 skill 一个）。
  每个 Agent 一个固定颜色的头像，名字一律带「Agent」，在卡片、对话记录、对话页里长得一样。
- **对话**：一次活就是和某个 Agent 的一次对话。不再出现「任务」「skill」「运行」「harness」这些词。

Claude Code / Codex 降为次要选项「模型」（输入框右下角），每个 Agent 有默认值（翻译默认 Codex：Claude 不肯全文翻付费文章），
改了按 Agent 记住（localStorage `momo.agent.model`）。

## 三块界面

1. **新对话**（`NewRunForm`）：标题「找哪个 Agent 帮忙？」→ Agent 卡片（单选，带一句话说明，没装的置灰写明）→ 输入框（上方写「交给 X Agent」，
   提示语是这个 Agent 要什么输入）→ 附件 / 模型 / 开始 → 「等你确认时 10 分钟没回就按建议继续」→「可以这样说」示例。
2. **对话记录**（`RunList`）：顶部大按钮「新对话」；每条 = 头像 + 标题 + 「X Agent · 时间」+ 状态文字。去掉了只有图标的筛选按钮。
3. **对话页**（`RunPanel`）：头部 = 头像 + 标题 + 「X Agent · 模型 · 状态」+ 删除；中间是对话（工具调用折叠成「做了 N 步操作」，
   每轮结束只写用时）；Agent 停下来等你确认时，输入框上方一条黄色提示 + **「按建议继续」一键按钮**（替你发「确认，按你的建议继续。」），
   并写明几点会自动继续；右栏「结果文件」放最上面，「步骤」有才显示，「你上传的」在最下。窄屏右栏收进「结果文件」抽屉。

## 状态只说四种

进行中 / 等你确认 / 完成 / 已中断（`state.ts` 的 `displayStatus`）。「等你确认」= 提问挂着，或一轮结束时回复末尾带 `【等待确认】`
（服务端的 status 事件带 `awaiting`，对话里不显示这行标记）。之前「一轮结束」显示成「等你回复」，做完了的活也像在等人，容易误解。

## 标题

建对话时可以传 `title`（文章工作台传文章中文标题）；不传就取消息第一句（长句只留第一个「。」之前）。旧对话的长标题在页面上同样只显示第一句。

## 代码位置

- 名片：`skill_runner/agents.json`（标题、图标 general / translate / subtitle / podcast、说明、提示、示例、默认模型 `harness`）
- 前端：`web/frontend/src/features/skills/`（`components/NewRunForm.tsx`、`RunList.tsx`、`RunPanel.tsx`、`AgentIcon.tsx` 的 `AgentAvatar`）
