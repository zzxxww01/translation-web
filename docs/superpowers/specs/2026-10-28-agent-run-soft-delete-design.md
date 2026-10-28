# Agent 页对话的假删除（2026-10-28）

用户要求：「agent 页的会话记录需要支持删除，但是只能是假删除，后台直接查机器要能查到，同时日志记录删了什么。」

## 现状

- 只有对话页顶部有「删除」，确认框写「对话记录、上传的文件和结果文件都会从服务器上删掉，无法恢复」。
- 后端是真删：`RunStore.delete` 直接 `shutil.rmtree(runs/<id>)`（`skill_runner/store.py`），没有任何记录。
- 新建对话时附件上传失败，`create_run` 也会调 `runner.delete` 清掉刚建的目录。

## 设计

### 磁盘

- 删除 = 把整个目录从 `~/skill-runner/runs/<id>` 原样移到 `~/skill-runner/deleted/<id>`（同一文件系统上的 `os.rename`，不复制、不删任何文件）。
  `deleted/` 不在 `runs/` 里面，`list_meta`、`load_meta`、文件下载、事件读取自然都找不到它，不需要在每个接口里加过滤。
- 目标已存在（理论上不会，id 带时间和随机串）时，在后面加 `-1`、`-2`。
- 每次删除往 `~/skill-runner/deleted/deleted.jsonl` 追加一行 JSON：

  ```json
  {"deleted_at": "2026-10-28T23:40:12+08:00", "reason": "user",
   "run_id": "20261028-232435-1dc860", "title": "…", "skill": "four-step-translate",
   "harness": "antigravity", "model": null, "actual_model": "…",
   "created_at": "…", "status": "idle",
   "inputs": [{"path": "input/x.html", "bytes": 240394}],
   "outputs": [{"path": "output/zh.md", "bytes": 51234}],
   "moved_to": "/home/zxw/skill-runner/deleted/20261028-232435-1dc860",
   "client_ip": "…"}
  ```

  `reason` 是 `user`（页面上删的）或 `upload_failed`（创建时上传失败的自动清理）。`client_ip` 取 `X-Forwarded-For` 第一个，没有就取连接地址。
  文件清单列 `input/` 和其余文件的相对路径和大小，最多列 500 个，超过的写 `"truncated": true`。
- 同一条也写服务日志（`logger.info("deleted run …")`），用 `journalctl --user -u skill-runner` 能查到。
- 写日志失败不影响删除（目录已经挪走），但会在服务日志里记一条 error。
- 找回：把目录挪回 `runs/`，重启服务。写进 `skill_runner/README.md`。

### 接口

`DELETE /api/skills/runs/{id}` 不变，语义变成假删除。规则不变：正在跑或在等确认的对话不能删（409「任务还在运行，先中断再删除」）。

### 界面（Agent 页）

- 对话列表每一条右侧，鼠标悬停（手机上常显）时出现一个垃圾桶图标按钮；对话页顶部的「删除」保留。
- 确认框：标题「删除这个对话？」；说明改成「从列表里删掉。服务器上会保留存档，需要时可以找回。」；按钮「删除」。
- 正在跑的对话，列表里的删除按钮置灰，悬停提示「先停止再删除」。
- 删掉当前打开的对话后回到新对话页（和现在一样）。

### 和文章工作台的关系

文章项目里记着 `claude_run_id`。对应的对话被删后，`GET /runs/{id}` 返回 404：工作台把它当作「没有对话」，
已导入的 Agent 版不受影响（存在主站），「看对话」入口不显示，也不报错。

## 测试

- `RunStore`：删除后目录在 `deleted/` 下且文件完整；`runs/` 下没有了；`list_meta` 不再列出；`deleted.jsonl` 追加一行且字段齐全；同名冲突加后缀。
- `Runner.delete`：运行中拒绝；上传失败的清理写 `reason=upload_failed`。
- 前端：列表删除按钮、确认框文案、删掉当前对话后的跳转；工作台遇到 404 的对话不报错。
