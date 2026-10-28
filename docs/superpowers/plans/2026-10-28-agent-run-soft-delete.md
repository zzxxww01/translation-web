# Agent 页对话假删除 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agent 页删除对话改成假删除：目录原样挪到 `~/skill-runner/deleted/`，每次删除追加一条 JSONL 记录并写服务日志；对话列表也能删。

**Architecture:** `RunStore.archive()` 取代 `RunStore.delete()`（真删的方法整个去掉，保证没有第二条路径能真删）。`Runner.delete()` 规则不变，只是最后调用 `archive()` 并带上删除原因和来源 IP。前端抽一个 `DeleteRunDialog`，对话页和对话列表共用。

**Tech Stack:** Python 3.12 + FastAPI（skill_runner）、pytest；React 19 + TanStack Query + Radix AlertDialog、vitest（jsdom）。

设计文档：`docs/superpowers/specs/2026-10-28-agent-run-soft-delete-design.md`。

---

## 文件

| 文件 | 改动 |
|---|---|
| `skill_runner/store.py` | 去掉 `delete`，新增 `archive`、`_file_manifest`、`deleted_dir` |
| `skill_runner/runner.py` | `Runner.delete(run_id, *, reason, client_ip)` 调 `store.archive` |
| `skill_runner/app.py` | `_client_ip()`；删除接口和上传失败清理传原因和 IP |
| `skill_runner/README.md` | 「删除与找回」一节 |
| `tests/unit/skill_runner/test_skill_runner_soft_delete.py`（新） | store 层测试 |
| `tests/unit/skill_runner/test_skill_runner_lifecycle.py` | 改 `test_delete_requires_inactive_run_and_removes_directory` |
| `tests/unit/skill_runner/test_skill_runner_api.py` | 删除接口记录 IP；上传失败记 `upload_failed` |
| `web/frontend/src/features/skills/components/DeleteRunDialog.tsx`（新） | 共用的确认框 |
| `web/frontend/src/features/skills/components/RunPanel.tsx` | 改用 `DeleteRunDialog` |
| `web/frontend/src/features/skills/components/RunList.tsx` | 每条加删除按钮 |
| `web/frontend/src/features/skills/index.tsx` | 列表删除的回调 |
| `web/frontend/src/features/skills/runList.test.tsx`（新） | 列表删除 |

所有命令都在 worktree 根目录 `C:/Users/DELL/AppData/Local/Temp/ta-workbench-agent-model` 下执行（前端命令在 `web/frontend` 下）。

---

### Task 1: RunStore.archive

**Files:**
- Modify: `skill_runner/store.py`
- Create: `tests/unit/skill_runner/test_skill_runner_soft_delete.py`

- [ ] **Step 1: 写失败的测试**

`tests/unit/skill_runner/test_skill_runner_soft_delete.py`：

```python
import json

import pytest

from skill_runner import store as store_module
from skill_runner.store import RunStore


def _run_with_files(store: RunStore) -> str:
    meta = store.create("four-step-translate", "精翻 HBM4", "codex", model="gpt-5.5")
    run_dir = store.run_dir(meta.id)
    (run_dir / "input" / "a.html").write_text("<p>hi</p>", encoding="utf-8")
    (run_dir / "output").mkdir()
    (run_dir / "output" / "zh.md").write_text("译文", encoding="utf-8")
    store.append_event(meta.id, {"seq": 1, "type": "user", "text": "go"})
    return meta.id


def _log(store: RunStore) -> list[dict]:
    lines = (store.deleted_dir / "deleted.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


def test_archive_moves_the_whole_run_and_logs_what_was_deleted(tmp_path):
    store = RunStore(tmp_path / "runs")
    run_id = _run_with_files(store)

    record = store.archive(run_id, reason="user", client_ip="203.0.113.7")

    assert not store.exists(run_id)
    assert [m.id for m in store.list_meta()] == []
    moved = store.deleted_dir / run_id
    assert moved == tmp_path / "deleted" / run_id
    assert (moved / "meta.json").is_file() and (moved / "events.jsonl").is_file()
    assert (moved / "input" / "a.html").read_text(encoding="utf-8") == "<p>hi</p>"
    assert (moved / "output" / "zh.md").read_text(encoding="utf-8") == "译文"
    [logged] = _log(store)
    assert logged == record
    assert logged["reason"] == "user" and logged["client_ip"] == "203.0.113.7"
    assert logged["run_id"] == run_id and logged["title"] == "精翻 HBM4"
    assert (logged["skill"], logged["harness"], logged["model"]) == ("four-step-translate", "codex", "gpt-5.5")
    assert logged["inputs"] == [{"path": "input/a.html", "bytes": 9}]
    assert logged["outputs"] == [{"path": "output/zh.md", "bytes": len("译文".encode("utf-8"))}]
    assert logged["moved_to"] == str(moved)
    assert "truncated" not in logged
    for key in ("deleted_at", "created_at", "status", "actual_model"):
        assert key in logged


def test_archive_never_overwrites_an_earlier_archive(tmp_path):
    store = RunStore(tmp_path / "runs")
    run_id = _run_with_files(store)
    (store.deleted_dir / run_id).mkdir(parents=True)

    record = store.archive(run_id, reason="user")

    assert record["moved_to"] == str(store.deleted_dir / f"{run_id}-1")
    assert (store.deleted_dir / f"{run_id}-1" / "meta.json").is_file()


def test_archive_still_moves_the_run_when_the_log_cannot_be_written(tmp_path):
    store = RunStore(tmp_path / "runs")
    run_id = _run_with_files(store)
    (store.deleted_dir / "deleted.jsonl").mkdir(parents=True)  # 目录挡住了日志文件

    store.archive(run_id, reason="user")

    assert not store.exists(run_id)
    assert (store.deleted_dir / run_id / "meta.json").is_file()


def test_long_file_lists_are_truncated_in_the_log(tmp_path, monkeypatch):
    monkeypatch.setattr(store_module, "MAX_LOGGED_FILES", 1)
    store = RunStore(tmp_path / "runs")
    run_id = _run_with_files(store)

    record = store.archive(run_id, reason="user")

    assert len(record["inputs"]) + len(record["outputs"]) == 1
    assert record["truncated"] is True


def test_hard_delete_is_gone(tmp_path):
    assert not hasattr(RunStore(tmp_path / "runs"), "delete")


@pytest.mark.parametrize("bad", ["../x", "20261028-000000-zzzzzz"])
def test_archive_rejects_ids_that_are_not_run_ids(tmp_path, bad):
    with pytest.raises(KeyError):
        RunStore(tmp_path / "runs").archive(bad, reason="user")
```

- [ ] **Step 2: 跑测试，确认失败**

Run: `python -m pytest tests/unit/skill_runner/test_skill_runner_soft_delete.py -q`
Expected: FAIL，`AttributeError: 'RunStore' object has no attribute 'archive'`

- [ ] **Step 3: 实现**

`skill_runner/store.py`：

文件头文档字符串的目录说明末尾加一行：

```python
    deleted/<run_id>/            删除的对话原样挪到这里（假删除），deleted/deleted.jsonl 记着删了什么
```

import 区：去掉 `import shutil`，加上：

```python
import logging
from datetime import datetime
```

常量区（`CHUNK = ...` 下面）加：

```python
DELETED_LOG = "deleted.jsonl"
# 删除记录里最多列这么多个文件；运行目录里装过虚拟环境时文件会很多
MAX_LOGGED_FILES = 500

logger = logging.getLogger(__name__)
```

`RunStore.__init__` 换成：

```python
    def __init__(self, runs_dir: Path, deleted_dir: Path | None = None):
        self.runs_dir = runs_dir
        # 和 runs/ 平级，list_meta / run_dir 都找不到这里，删掉的对话自然从页面上消失
        self.deleted_dir = deleted_dir or runs_dir.parent / "deleted"
        self.runs_dir.mkdir(parents=True, exist_ok=True)
```

把原来的

```python
    def delete(self, run_id: str) -> None:
        shutil.rmtree(self.run_dir(run_id))
```

整个换成：

```python
    def archive(self, run_id: str, *, reason: str, client_ip: str | None = None) -> dict[str, Any]:
        """假删除：整个运行目录原样挪到 deleted/，再追加一条删除记录。返回这条记录。

        只是同一文件系统上的改名，不复制、不删除任何文件；要找回就挪回 runs/ 再重启服务。
        """
        source = self.run_dir(run_id)
        meta = self.load_meta(run_id)
        manifest = self._file_manifest(source)
        self.deleted_dir.mkdir(parents=True, exist_ok=True)
        target, n = self.deleted_dir / run_id, 0
        while target.exists():
            n += 1
            target = self.deleted_dir / f"{run_id}-{n}"
        os.rename(source, target)
        record: dict[str, Any] = {
            "deleted_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "reason": reason,
            "run_id": run_id,
            "title": meta.title if meta else None,
            "skill": meta.skill if meta else None,
            "harness": meta.harness if meta else None,
            "model": meta.model if meta else None,
            "actual_model": meta.actual_model if meta else None,
            "created_at": meta.created_at if meta else None,
            "status": meta.status if meta else None,
            **manifest,
            "moved_to": str(target),
            "client_ip": client_ip,
        }
        try:
            with open(self.deleted_dir / DELETED_LOG, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError:
            # 目录已经挪走了，删除本身算成功；日志写不进去要在服务日志里留痕
            logger.exception("deleted run %s but could not append %s", run_id, DELETED_LOG)
        logger.info("deleted run %s (%s) -> %s: %s", run_id, reason, target, json.dumps(record, ensure_ascii=False))
        return record

    def _file_manifest(self, root: Path) -> dict[str, Any]:
        """删除记录里的文件清单：input/ 下是上传的，其余是产出；meta/events 不列。"""
        inputs: list[dict[str, Any]] = []
        outputs: list[dict[str, Any]] = []
        truncated = False
        for path in sorted(p for p in root.rglob("*") if p.is_file() and not p.is_symlink()):
            rel = path.relative_to(root).as_posix()
            if rel in INTERNAL_FILES:
                continue
            if len(inputs) + len(outputs) >= MAX_LOGGED_FILES:
                truncated = True
                break
            entry = {"path": rel, "bytes": path.stat().st_size}
            (inputs if rel.startswith(f"{INPUT_DIR}/") else outputs).append(entry)
        manifest: dict[str, Any] = {"inputs": inputs, "outputs": outputs}
        if truncated:
            manifest["truncated"] = True
        return manifest
```

- [ ] **Step 4: 跑测试，确认通过**

Run: `python -m pytest tests/unit/skill_runner/test_skill_runner_soft_delete.py -q`
Expected: 7 passed

- [ ] **Step 5: 提交**

```bash
git add skill_runner/store.py tests/unit/skill_runner/test_skill_runner_soft_delete.py
git commit -m "feat(skill-runner): archive deleted runs instead of removing them"
```

---

### Task 2: Runner.delete 和接口带上删除原因、来源 IP

**Files:**
- Modify: `skill_runner/runner.py`（`async def delete`，约第 507 行）
- Modify: `skill_runner/app.py`（`create_run` 约第 181 行、`delete_run` 约第 231 行）
- Modify: `tests/unit/skill_runner/test_skill_runner_lifecycle.py:214-224`
- Modify: `tests/unit/skill_runner/test_skill_runner_api.py`

- [ ] **Step 1: 改 / 加测试**

`tests/unit/skill_runner/test_skill_runner_lifecycle.py` 里把 `test_delete_requires_inactive_run_and_removes_directory` 整个换成：

```python
async def test_delete_requires_inactive_run_and_archives_directory(runner, store, factory):
    run_id = await start(runner)
    with pytest.raises(Conflict):
        await runner.delete(run_id)
    factory.last.push({"type": "result", "session_id": "s"})
    await settle()
    backlog, queue = runner.subscribe(run_id)
    await runner.delete(run_id, client_ip="198.51.100.2")
    assert not store.exists(run_id)
    assert (store.deleted_dir / run_id / "meta.json").is_file()
    record = json.loads((store.deleted_dir / "deleted.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert (record["run_id"], record["reason"], record["client_ip"]) == (run_id, "user", "198.51.100.2")
    assert factory.last.closed
    assert queue.get_nowait() is None  # SSE 订阅者收到结束信号
```

（文件顶部现在只有 `import asyncio` / `import pytest`，加上 `import json`。）

`tests/unit/skill_runner/test_skill_runner_api.py`：

1. 在 `test_oversized_upload_is_rejected_and_run_discarded` 的 `assert client.get(f"{PREFIX}/runs").json() == []` 后面加：

```python
        log = (config.home / "deleted" / "deleted.jsonl").read_text(encoding="utf-8").splitlines()
        assert json.loads(log[-1])["reason"] == "upload_failed"
```

2. 文件末尾加：

```python
def test_delete_endpoint_archives_and_records_the_caller(setup):
    client, factory, runner = setup
    login(client)
    run_id = client.post(f"{PREFIX}/runs", data={"skill": "four-step-translate", "message": "go"}).json()["id"]
    assert client.post(f"{PREFIX}/runs/{run_id}/stop").json()["status"] == "error"  # 停下来才能删

    response = client.delete(f"{PREFIX}/runs/{run_id}", headers={"X-Forwarded-For": "203.0.113.9, 10.0.0.1"})

    assert response.status_code == 200
    assert client.get(f"{PREFIX}/runs/{run_id}").status_code == 404
    assert run_id not in [r["id"] for r in client.get(f"{PREFIX}/runs").json()]
    record = json.loads((runner.store.deleted_dir / "deleted.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert (record["run_id"], record["client_ip"]) == (run_id, "203.0.113.9")
```

- [ ] **Step 2: 跑测试，确认失败**

Run: `python -m pytest tests/unit/skill_runner/test_skill_runner_lifecycle.py tests/unit/skill_runner/test_skill_runner_api.py -q`
Expected: FAIL：`delete() got an unexpected keyword argument 'client_ip'`，以及上传失败那条找不到 `deleted.jsonl`（Task 1 之后 `store.delete` 已不存在，旧调用会报 `AttributeError`）。

- [ ] **Step 3: 实现**

`skill_runner/runner.py`，`delete` 换成：

```python
    async def delete(self, run_id: str, *, reason: str = "user", client_ip: str | None = None) -> None:
        """从页面上删掉对话：会话先关干净，目录挪进 deleted/ 存档（见 RunStore.archive）。"""
        run = self._get(run_id)
        if run.meta.status in ACTIVE_STATUSES or self._session_busy(run):
            raise Conflict("任务还在运行，先中断再删除")
        self._cancel_auto_reply(run)
        try:
            await self._close_session(run, strict=True)
        except Exception as exc:
            raise SessionFailed(f"会话未能关闭，暂时无法删除：{exc}") from exc
        for queue in list(run.subscribers):
            queue.put_nowait(None)
        self._runs.pop(run_id, None)
        self.store.archive(run_id, reason=reason, client_ip=client_ip)
```

`skill_runner/app.py`：

在 `create_app` 前（模块级函数区）加：

```python
def _client_ip(request: Request) -> str | None:
    """经 Cloudflare / nginx 转发时真实来源在 X-Forwarded-For 第一个。"""
    first = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    return first or (request.client.host if request.client else None)
```

`create_run` 的参数表第一行加 `request: Request,`，里面上传失败的清理改成：

```python
        except HTTPException:
            await runner.delete(meta.id, reason="upload_failed", client_ip=_client_ip(request))
            raise
```

`delete_run` 换成：

```python
    @api.delete("/runs/{run_id}")
    async def delete_run(run_id: str, request: Request):
        await runner.delete(run_id, client_ip=_client_ip(request))
        return {"ok": True}
```

- [ ] **Step 4: 跑 skill-runner 全部测试**

Run: `python -m pytest tests/unit/skill_runner -q`
Expected: 全部通过（`test_runtime_maintenance.py` 里两处 `runner.delete(meta.id)` 不用改：默认 `reason="user"`）

- [ ] **Step 5: 提交**

```bash
git add skill_runner/runner.py skill_runner/app.py tests/unit/skill_runner/test_skill_runner_lifecycle.py tests/unit/skill_runner/test_skill_runner_api.py
git commit -m "feat(skill-runner): record reason and caller when a run is deleted"
```

---

### Task 3: README 写明删除与找回

**Files:**
- Modify: `skill_runner/README.md`

- [ ] **Step 1: 在 README 的运行目录 / 运维说明附近加一节**

```markdown
## 删除与找回

页面上「删除」对话是假删除：整个运行目录从 `~/skill-runner/runs/<id>` 原样挪到 `~/skill-runner/deleted/<id>`
（同名已存在时加 `-1`、`-2`），文件一个不少。每次删除往 `~/skill-runner/deleted/deleted.jsonl` 追加一行，
记着删除时间、原因（`user` 页面删除 / `upload_failed` 创建时上传失败）、标题、Agent、模型、上传和产出的文件清单、
存档路径和来源 IP；同一条也在服务日志里：`journalctl --user -u skill-runner | grep "deleted run"`。

找回：`mv ~/skill-runner/deleted/<id> ~/skill-runner/runs/` 后 `systemctl --user restart skill-runner`。
```

- [ ] **Step 2: 提交**

```bash
git add skill_runner/README.md
git commit -m "docs(skill-runner): explain soft delete and recovery"
```

---

### Task 4: 前端共用的删除确认框，对话页改用它

**Files:**
- Create: `web/frontend/src/features/skills/components/DeleteRunDialog.tsx`
- Modify: `web/frontend/src/features/skills/components/RunPanel.tsx`（约第 50–75 行的 `remove`、约第 122–138 行的 `AlertDialog`）

- [ ] **Step 1: 写组件**

`DeleteRunDialog.tsx`：

```tsx
import { useState, type ReactNode } from 'react';
import { toast } from 'sonner';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';

/** 删除对话的确认框。服务器上是假删除（目录挪进存档），所以文案不说「无法恢复」。 */
export function DeleteRunDialog({ onConfirm, children }: {
  onConfirm: () => Promise<void>;
  /** 触发按钮，会被包进 AlertDialogTrigger asChild */
  children: ReactNode;
}) {
  const [busy, setBusy] = useState(false);
  const confirm = async () => {
    setBusy(true);
    try {
      await onConfirm();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '删除失败');
    } finally {
      setBusy(false);
    }
  };
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>{children}</AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>删除这个对话？</AlertDialogTitle>
          <AlertDialogDescription>从列表里删掉。服务器上会保留存档，需要时可以找回。</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>取消</AlertDialogCancel>
          <AlertDialogAction disabled={busy} onClick={() => void confirm()}>删除</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
```

- [ ] **Step 2: RunPanel 改用它**

`RunPanel.tsx`：

- 删掉 `const [deleting, setDeleting] = useState(false);`。
- `remove` 换成：

```tsx
  const remove = async () => {
    await skillsApi.remove(run.id);
    await queryClient.invalidateQueries({ queryKey: skillKeys.runs });
    onDeleted();
  };
```

- 头部那段 `<AlertDialog>…</AlertDialog>` 换成：

```tsx
        <DeleteRunDialog onConfirm={remove}>
          <Button variant="ghost" size="sm" disabled={active} title={active ? '先停止再删除' : '从列表里删掉这个对话'}>
            删除
          </Button>
        </DeleteRunDialog>
```

- import 里去掉不再用到的 `AlertDialog*`，加 `import { DeleteRunDialog } from './DeleteRunDialog';`。

- [ ] **Step 3: 类型检查和现有测试**

Run（在 `web/frontend` 下）：`npx tsc -b && npx vitest run src/features/skills`
Expected: 无类型错误，测试全部通过

- [ ] **Step 4: 提交**

```bash
git add web/frontend/src/features/skills/components/DeleteRunDialog.tsx web/frontend/src/features/skills/components/RunPanel.tsx
git commit -m "feat(agents): shared delete dialog that says runs are archived"
```

---

### Task 5: 对话列表每条可删除

**Files:**
- Modify: `web/frontend/src/features/skills/components/RunList.tsx`
- Modify: `web/frontend/src/features/skills/index.tsx:78`
- Create: `web/frontend/src/features/skills/runList.test.tsx`

- [ ] **Step 1: 写失败的测试**

`runList.test.tsx`：

```tsx
// @vitest-environment jsdom
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { RunList } from './components/RunList';
import { normalizeCatalog } from './agents';
import type { RunMeta } from './types';

vi.mock('sonner', () => ({ toast: { error: vi.fn() } }));

const run = (id: string, status: RunMeta['status']): RunMeta => ({
  id, skill: 'four-step-translate', title: `对话 ${id}`, status, created_at: 1_793_000_000, updated_at: 1_793_000_000,
  session_id: null, error: null, harness: 'codex', awaiting_reply: false,
} as RunMeta);

describe('RunList delete', () => {
  let root: Root;
  let host: HTMLDivElement;
  beforeEach(() => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    host = document.createElement('div');
    document.body.appendChild(host);
    root = createRoot(host);
  });
  afterEach(() => {
    act(() => root.unmount());
    host.remove();
    document.body.innerHTML = '';
  });

  const render = (onDelete: (id: string) => Promise<void>) => act(() => root.render(
    <RunList runs={[run('20261028-000000-aaaaaa', 'idle'), run('20261028-000001-bbbbbb', 'running')]}
      catalog={normalizeCatalog([])} selectedId={null} onSelect={vi.fn()} onNew={vi.fn()} onDelete={onDelete} />,
  ));
  const deleteButtons = () => Array.from(host.querySelectorAll<HTMLButtonElement>('button[aria-label^="删除对话"]'));

  it('confirms before deleting and passes the run id', async () => {
    const onDelete = vi.fn(async () => undefined);
    render(onDelete);
    const [idle] = deleteButtons();
    await act(async () => { idle.click(); });
    expect(document.body.textContent).toContain('服务器上会保留存档');
    const confirm = Array.from(document.querySelectorAll('button')).find(b => b.textContent === '删除')!;
    await act(async () => { confirm.click(); });
    expect(onDelete).toHaveBeenCalledWith('20261028-000000-aaaaaa');
  });

  it('does not let a running conversation be deleted', () => {
    render(vi.fn());
    const [, running] = deleteButtons();
    expect(running.disabled).toBe(true);
    expect(running.title).toBe('先停止再删除');
  });
});
```

- [ ] **Step 2: 跑测试，确认失败**

Run（`web/frontend`）：`npx vitest run src/features/skills/runList.test.tsx`
Expected: FAIL，找不到 `aria-label^="删除对话"` 的按钮

- [ ] **Step 3: 实现**

`RunList.tsx`：

- import 改为 `import { Plus, Trash2 } from 'lucide-react';`，加 `import { DeleteRunDialog } from './DeleteRunDialog';`。
- `RunListProps` 加 `onDelete: (id: string) => Promise<void>;`，函数参数解构加 `onDelete`。
- `runs.map` 里的 `<li>` 换成（主按钮不变，右侧叠一个删除按钮；按钮不能嵌在按钮里，所以 `li` 设 `relative group`）：

```tsx
            <li key={run.id} className="group relative">
              <button
                type="button"
                onClick={() => onSelect(run.id)}
                aria-current={run.id === selectedId ? 'true' : undefined}
                className={cn(
                  'flex w-full items-start gap-2.5 rounded-lg py-2.5 pl-2.5 pr-9 text-left transition-colors',
                  run.id === selectedId ? 'bg-primary-50' : 'hover:bg-bg-hover'
                )}
              >
                <AgentAvatar icon={agent.icon} size="sm" className="mt-0.5" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm text-text-primary">{runTitle(run.title)}</span>
                  <span className="mt-0.5 flex items-center gap-2 text-xs text-text-muted">
                    <span className="truncate">{agent.title} · {formatTime(run.created_at)}</span>
                    <StatusPill status={displayStatus(run.status, run.awaiting_reply)} className="ml-auto" />
                  </span>
                </span>
              </button>
              <DeleteRunDialog onConfirm={() => onDelete(run.id)}>
                <button
                  type="button"
                  aria-label={`删除对话：${runTitle(run.title)}`}
                  title={active ? '先停止再删除' : '删除这个对话'}
                  disabled={active}
                  className="absolute right-1.5 top-2 rounded-md p-1.5 text-text-muted opacity-100 transition-opacity hover:bg-bg-hover hover:text-text-primary focus-visible:opacity-100 disabled:cursor-not-allowed disabled:opacity-30 md:opacity-0 md:group-hover:opacity-100"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </DeleteRunDialog>
            </li>
```

其中 `active` 在 `const agent = …` 下面定义：

```tsx
          const active = run.status === 'running' || run.status === 'waiting';
```

`index.tsx` 第 78 行的 `<RunList … />` 加 `onDelete={removeRun}`，并在 `backToList` 下面加：

```tsx
  const removeRun = async (id: string) => {
    await skillsApi.remove(id);
    await queryClient.invalidateQueries({ queryKey: skillKeys.runs });
    if (id === selectedId) backToList();
  };
```

- [ ] **Step 4: 跑测试和类型检查**

Run（`web/frontend`）：`npx vitest run src/features/skills && npx tsc -b && npx eslint src/features/skills`
Expected: 全部通过、无类型和 lint 错误

- [ ] **Step 5: 提交**

```bash
git add web/frontend/src/features/skills/components/RunList.tsx web/frontend/src/features/skills/index.tsx web/frontend/src/features/skills/runList.test.tsx
git commit -m "feat(agents): delete conversations from the list"
```

---

### Task 6: 工作台遇到被删的对话不报错（核对，不改代码）

文章项目的 `claude_run_id` 指向的对话被删后，`useClaudeRun`（`web/frontend/src/features/articles/hooks.ts`）拿到 404：`run` 为 `undefined`，
`claudeNeedsLogin` 只认 401，所以现有工作台不显示任何横幅，「看对话」也不出现。工作台重做（另一份计划）里 `lib/versions.ts`
要保持这一点：run 查询报 404 时当作没有 run。

- [ ] **Step 1: 手动核对**：在 dev 环境删掉一个关联了文章的对话，打开那篇文章的工作台，确认没有报错、已导入的 Agent 版照常显示。

---

### Task 7: 整体验证

- [ ] **Step 1:** `python -m pytest tests/unit/skill_runner -q` → 全部通过
- [ ] **Step 2:**（`web/frontend`）`npm test && npx tsc -b && npm run lint` → 全部通过
- [ ] **Step 3:** 本机起 skill-runner（`python -m skill_runner`，环境变量按 `skill_runner/deploy/env.example`）和前端，在 Agent 页从列表删一个已结束的对话，
  确认：列表里消失；`<SKILL_RUNNER_HOME>/deleted/<id>/` 下文件完整；`deleted.jsonl` 多一行且字段齐全。
