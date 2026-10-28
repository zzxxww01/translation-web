# 工作台重做：后端与 skill-runner 支撑 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给工作台重做准备好后端：主译本（存、解析、接口、列表进度）、Agent 导入记录带 Agent 和模型、导入时的对齐门槛、Codex 每次运行固定一个模型并上报、界面上 Antigravity 一律叫 Gemini。

**Architecture:** 主译本是主项目 meta 里的一个指针 `primary_target`，解析规则集中在新模块 `src/services/article_primary.py`，工作台接口和文章列表共用。导入门槛放在 `article_variants.import_claude_translation` 里，低于 80% 抛 `AlignmentTooLow`，路由转成 409。skill-runner 只改 Codex 会话的模型选取时机，以及对外文案。

**Tech Stack:** Python 3.12、FastAPI、Pydantic v2、pytest（pytest-asyncio）；前端只改 `skills/harness.ts` 等 Agent 页文案（vitest）。

设计文档：`docs/superpowers/specs/2026-10-28-workbench-agent-model-design.md`（4.2、8.2、9、10 节）。前端工作台部分见 `2026-10-28-workbench-frontend-redesign.md`，依赖本计划。

所有命令都在 worktree 根目录 `C:/Users/DELL/AppData/Local/Temp/ta-workbench-agent-model` 下执行。

---

## 文件

| 文件 | 改动 |
|---|---|
| `src/core/models/project.py` | `ProjectMeta.primary_target` |
| `src/core/project.py` | `ProjectListSummary.primary_target` 及解析 |
| `src/services/article_primary.py`（新） | `resolve_primary()` |
| `src/services/article_variants.py` | 导入带 agent/model、label Gemini、suffix 用 Agent id、`AlignmentTooLow`、`force` |
| `src/api/routers/workbench.py` | `GET /workbench` 返回主译本；`PUT /workbench/primary`；导入请求加 `model`/`force`，409 |
| `src/api/routers/substack.py` | `_translation_state` 只看主译本 |
| `skill_runner/codex_session.py` | 会话打开时定模型，`session` 事件带 `model` |
| `skill_runner/runner.py`、`antigravity_session.py`、`models.py`、`runtime_updates.py`、`agents.py`、`README.md` | Antigravity → Gemini 的对外文案；去掉付费注释 |
| `web/frontend/src/features/skills/harness.ts`、`components/ModelPicker.tsx`、`components/RuntimeUpdatesPanel.tsx`、`agents.test.tsx` | Agent 页文案 |
| 测试 | `tests/unit/services/test_article_variants.py`、`tests/unit/api/test_substack_router.py`、`tests/unit/skill_runner/test_skill_runner_codex.py`、`tests/unit/skill_runner/test_skill_runner_antigravity.py` |

---

### Task 1: 主译本字段

**Files:**
- Modify: `src/core/models/project.py:66`（`claude_run_id` 下面）
- Modify: `src/core/project.py:60-73`（`ProjectListSummary`）、`:615-628`（构造处）
- Test: `tests/unit/services/test_article_variants.py`

- [ ] **Step 1: 写失败的测试**（追加到 `tests/unit/services/test_article_variants.py` 末尾）

```python
def test_primary_target_is_stored_in_meta_and_list_summary(pm, main_id):
    variant = article_variants.create_variant(pm, main_id, kind="claude", label="Codex", suffix="codex")
    pm.merge_meta_fields(main_id, fields={"primary_target": variant})
    assert pm.get(main_id).primary_target == variant
    [summary] = pm.list_summaries()
    assert summary.primary_target == variant
```

- [ ] **Step 2: 跑测试，确认失败**

Run: `python -m pytest tests/unit/services/test_article_variants.py::test_primary_target_is_stored_in_meta_and_list_summary -q`
Expected: FAIL，`Unknown project metadata fields: primary_target`

- [ ] **Step 3: 实现**

`src/core/models/project.py`，在 `claude_run_id: Optional[str] = None` 下面加（必须放在前面：列表只解析 meta.json 开头一段）：

```python
    # 主项目：主译本是哪一版（主项目自己或某个孪生项目的 id）；None 按默认规则（services/article_primary.py）
    primary_target: Optional[str] = None
```

`src/core/project.py`，`ProjectListSummary` 末尾加字段：

```python
    # 主项目选定的主译本（ProjectMeta.primary_target）
    primary_target: Optional[str] = None
```

构造 `ProjectListSummary(...)` 的地方（`variant_of=...` 那行下面）加：

```python
            primary_target=data.get("primary_target") if isinstance(data.get("primary_target"), str) else None,
```

- [ ] **Step 4: 跑测试，确认通过**

Run: `python -m pytest tests/unit/services/test_article_variants.py -q`
Expected: 全部通过

- [ ] **Step 5: 提交**

```bash
git add src/core/models/project.py src/core/project.py tests/unit/services/test_article_variants.py
git commit -m "feat(workbench): store the primary version pointer on the main project"
```

---

### Task 2: 主译本解析规则

**Files:**
- Create: `src/services/article_primary.py`
- Test: `tests/unit/services/test_article_variants.py`

- [ ] **Step 1: 写失败的测试**（追加）

```python
from src.services import article_primary  # 放到文件顶部的 import 区


EN_FULL = ("# Demo Post\n\nFirst paragraph about wafer supply and the 2027 buildout of datacenters.\n\n"
           "## Second Section\n\nAnother paragraph explaining why HBM demand keeps outrunning supply.\n")
ZH_FULL = "# 演示文章\n\n关于晶圆供给和 2027 年数据中心建设的第一段。\n\n## 第二节\n\n解释 HBM 需求为何持续超过供给的一段。\n"


def test_primary_defaults_to_web_once_it_has_started(pm, main_id):
    variant = article_variants.import_claude_translation(
        pm, main_id, zh_markdown=ZH_FULL, en_markdown=EN_FULL, agent="codex")["variant_id"]
    resolve = article_primary.resolve_primary
    assert resolve(pm, main_id, [variant], primary_target=None, main_started=True) == main_id
    assert resolve(pm, main_id, [variant], primary_target=None, main_started=False) == variant
    assert resolve(pm, main_id, [], primary_target=None, main_started=False) == main_id


def test_primary_default_picks_latest_import_and_honours_explicit_choice(pm, main_id, monkeypatch):
    records = {f"{main_id}--codex": "2026-10-28T10:00:00", f"{main_id}--claude": "2026-10-28T11:00:00"}
    monkeypatch.setattr(article_variants, "read_import_record",
                        lambda _pm, vid: {"imported_at": records[vid]} if vid in records else None)
    ids = list(records) + [f"{main_id}--argon"]
    resolve = article_primary.resolve_primary
    assert resolve(pm, main_id, ids, primary_target=None, main_started=False) == f"{main_id}--claude"
    assert resolve(pm, main_id, ids, primary_target=f"{main_id}--argon", main_started=True) == f"{main_id}--argon"
    assert resolve(pm, main_id, ids, primary_target=main_id, main_started=False) == main_id
    # 指向已经不存在的版本：退回默认规则
    assert resolve(pm, main_id, ids, primary_target=f"{main_id}--gone", main_started=True) == main_id
```

- [ ] **Step 2: 跑测试，确认失败**

Run: `python -m pytest tests/unit/services/test_article_variants.py -q -k primary`
Expected: FAIL，`cannot import name 'article_primary'`

- [ ] **Step 3: 实现** `src/services/article_primary.py`：

```python
"""主译本：文章工作台中间那一栏、「导出主译本」和文章列表进度看的那一版。

用户在工作台点「设为主译本」时存进主项目 meta 的 primary_target；没选过（或指向的版本已经没了）时按默认规则：
网页版有译文或正在翻 → 网页版；否则最近导入的 Agent 版；都没有 → 网页版。默认值只用来显示，不写回 meta。
设计见 docs/superpowers/specs/2026-10-28-workbench-agent-model-design.md 4.2。
"""

from __future__ import annotations

from typing import Iterable, Optional

from src.core.project import ProjectManager
from src.services import article_variants


def resolve_primary(pm: ProjectManager, main_id: str, variant_ids: Iterable[str], *,
                    primary_target: Optional[str], main_started: bool) -> str:
    ids = list(variant_ids)
    if primary_target and (primary_target == main_id or primary_target in ids):
        return primary_target
    if main_started:
        return main_id
    imported = []
    for vid in ids:
        record = article_variants.read_import_record(pm, vid)
        if record and isinstance(record.get("imported_at"), str):
            imported.append((record["imported_at"], vid))
    return max(imported)[1] if imported else main_id
```

- [ ] **Step 4: 跑测试，确认通过**

Run: `python -m pytest tests/unit/services/test_article_variants.py -q -k primary`
Expected: 3 passed

- [ ] **Step 5: 提交**

```bash
git add src/services/article_primary.py tests/unit/services/test_article_variants.py
git commit -m "feat(workbench): resolve which version is the primary one"
```

---

### Task 3: 导入记录带 Agent 和模型、Gemini 的 label、对齐门槛

**Files:**
- Modify: `src/services/article_variants.py`（`import_claude_translation`，约第 124–148 行）
- Test: `tests/unit/services/test_article_variants.py`（改 `test_agent_import_gets_its_own_variant`，加新测试）

- [ ] **Step 1: 改 / 写测试**

把 `test_agent_import_gets_its_own_variant` 整个换成（原来只给了半篇英文，门槛上线后会被拒）：

```python
@pytest.mark.parametrize(("agent", "label"), [("claude", "Claude"), ("codex", "Codex"), ("antigravity", "Gemini")])
def test_agent_import_gets_its_own_variant(pm, main_id, agent, label):
    body = workbench.ImportClaudeRequest(run_id="r1", zh_markdown=ZH_FULL, en_markdown=EN_FULL, agent=agent, model="m-1")
    result = article_variants.import_claude_translation(
        pm, main_id, zh_markdown=body.zh_markdown, en_markdown=body.en_markdown, agent=body.agent, model=body.model)
    assert result["variant_id"] == f"{main_id}--{agent}"
    assert pm.get(result["variant_id"]).variant_label == label
    record = article_variants.read_import_record(pm, result["variant_id"])
    assert (record["agent"], record["model"], record["run_id"]) == (agent, "m-1", None)


def test_import_refuses_an_english_draft_that_does_not_match_the_download(pm, main_id):
    half_en = "First paragraph about wafer supply and the 2027 buildout of datacenters.\n"
    half_zh = "关于晶圆供给和 2027 年数据中心建设的第一段。\n"
    with pytest.raises(article_variants.AlignmentTooLow) as caught:
        article_variants.import_claude_translation(pm, main_id, zh_markdown=half_zh, en_markdown=half_en, agent="codex")
    assert (caught.value.aligned, caught.value.total) == (1, 3)  # 两段正文 + 一个章节标题
    assert "1/3" in str(caught.value)
    assert article_variants.list_variants(pm, main_id) == []  # 没建孪生项目

    result = article_variants.import_claude_translation(
        pm, main_id, zh_markdown=half_zh, en_markdown=half_en, agent="codex", force=True)
    assert result["aligned"] >= 1
```

（`test_claude_import_aligns_text_into_its_own_variant` 不用改：它本来就给的全文。）

- [ ] **Step 2: 跑测试，确认失败**

Run: `python -m pytest tests/unit/services/test_article_variants.py -q -k "import"`
Expected: FAIL：`ImportClaudeRequest` 没有 `model` 字段 / 没有 `AlignmentTooLow`

- [ ] **Step 3: 实现**

`src/services/article_variants.py`，在 `_EXPORT_SUFFIXES` 下面加：

```python
# Agent 的 en.md 和项目从同一份 source.html 解析出的正文段落，对上不到这个比例就不自动导入：
# 多半不是这篇下载的原文（设计文档 8.2）。10-25 Codex 那次是 61/61 全对上。
MIN_ALIGNED_RATIO = 0.8
AGENT_LABELS = {"claude": "Claude", "codex": "Codex", "antigravity": "Gemini"}


class AlignmentTooLow(ValueError):
    def __init__(self, aligned: int, total: int):
        self.aligned, self.total = aligned, total
        super().__init__(f"Agent 的英文稿只对上 {aligned}/{total} 段，可能不是这篇下载的原文")
```

`import_claude_translation` 换成：

```python
def import_claude_translation(pm: ProjectManager, main_id: str, *, zh_markdown: str, en_markdown: str,
                              run_id: Optional[str] = None, agent: str = "claude",
                              model: Optional[str] = None, force: bool = False) -> Dict:
    """把 four-step-translate 产出的 zh.md 对齐后写进该 Agent 对应的孪生项目
    （已有就整篇替换），返回对齐统计。英文稿对不上下载的原文时抛 AlignmentTooLow，force=True 时照样导入。"""
    sections = pm.get_sections(main_id)
    targets = alignment_targets(sections)
    alignment: Alignment = align_claude_translation(en_markdown, zh_markdown, targets)
    if not alignment.texts:
        raise ValueError("Agent 的译文和这篇文章对不上，可能不是同一篇")
    total = sum(1 for target in targets if target.kind != "image")
    aligned = total - alignment.stats["unaligned"]
    if not force and total and aligned < MIN_ALIGNED_RATIO * total:
        raise AlignmentTooLow(aligned, total)
    # id 后缀用 Agent id：claude / codex 和以前一样，Gemini 版是 {主id}--antigravity
    new_id = create_variant(pm, main_id, kind="claude", label=AGENT_LABELS[agent], suffix=agent, replace=True)

    for section in pm.get_sections(new_id):
        title = alignment.texts.get(f"section:{section.section_id}")
        if title:
            section.title_translation = title.split("\n")[0].strip()
        for paragraph in section.paragraphs:
            text = alignment.texts.get(f"{section.section_id}/{paragraph.id}")
            if text and paragraph.element_type.value != "image" and paragraph.status != ParagraphStatus.APPROVED:
                paragraph.add_translation(text, "claude")
                paragraph.status = ParagraphStatus.TRANSLATED
        pm._save_section(new_id, section)

    meta = pm.get(new_id)
    if alignment.title:
        meta.title_translation = alignment.title
    meta.update_progress(pm.get_sections(new_id))
    meta.status = ProjectStatus.REVIEWING
    pm.save_meta(meta)
    _write_import_record(pm, new_id, {"run_id": run_id, "agent": agent, "model": model, **alignment.stats})
    return {"variant_id": new_id, "title": alignment.title, **alignment.stats}
```

`src/api/routers/workbench.py`，`ImportClaudeRequest` 加两个字段：

```python
    model: Optional[str] = Field(None, max_length=128)  # 实际跑的模型（run 的 actual_model / model），只用来显示
    force: bool = False  # 英文稿和下载的原文对不上时也导入
```

- [ ] **Step 4: 跑测试，确认通过**

Run: `python -m pytest tests/unit/services/test_article_variants.py -q`
Expected: 全部通过（已核对：测试 HTML 的对齐目标是 `00-intro/p000`、`section:01-second-section`、`01-second-section/p000` 三个，半篇英文只对上 1 个）。

- [ ] **Step 5: 提交**

```bash
git add src/services/article_variants.py src/api/routers/workbench.py tests/unit/services/test_article_variants.py
git commit -m "feat(workbench): record agent and model on import and refuse mismatched drafts"
```

---

### Task 4: 工作台接口：返回主译本、设主译本、导入 409

**Files:**
- Modify: `src/api/routers/workbench.py`（`get_workbench` 约 147–194 行；新增 `set_primary`；`import_claude_variant` 约 302–313 行）
- Test: `tests/unit/services/test_article_variants.py`

- [ ] **Step 1: 写失败的测试**（追加；顶部 import 加 `from src.api.middleware import ConflictException, NotFoundException`）

```python
@pytest.mark.asyncio
async def test_workbench_reports_and_changes_the_primary_version(pm, main_id):
    variant = article_variants.import_claude_translation(
        pm, main_id, zh_markdown=ZH_FULL, en_markdown=EN_FULL, agent="codex", model="gpt-5.5")["variant_id"]

    data = await workbench.get_workbench(main_id, pm, FakeStatus())
    assert data["project"]["primary_target"] is None
    assert data["project"]["primary"] == variant  # 网页版没开始，默认是刚导入的 Agent 版
    assert data["variants"][0]["import"]["model"] == "gpt-5.5"

    saved = await workbench.set_primary(main_id, workbench.PrimaryRequest(target=main_id), pm)
    assert saved == {"ok": True, "primary_target": main_id}
    data = await workbench.get_workbench(main_id, pm, FakeStatus())
    assert (data["project"]["primary_target"], data["project"]["primary"]) == (main_id, main_id)


@pytest.mark.asyncio
async def test_primary_must_be_this_article_or_its_variant(pm, main_id, tmp_path):
    other_source = tmp_path / "other.html"
    other_source.write_text(HTML.replace("Demo Post", "Other Post"), encoding="utf-8")
    other = pm.create("other", str(other_source)).id
    with pytest.raises(BadRequestException):
        await workbench.set_primary(main_id, workbench.PrimaryRequest(target=other), pm)
    with pytest.raises(NotFoundException):
        await workbench.set_primary(main_id, workbench.PrimaryRequest(target=f"{main_id}--nope"), pm)
    variant = article_variants.create_variant(pm, main_id, kind="model", label="argon", suffix="argon")
    with pytest.raises(BadRequestException):
        await workbench.set_primary(variant, workbench.PrimaryRequest(target=variant), pm)


@pytest.mark.asyncio
async def test_import_endpoint_reports_mismatched_draft_as_conflict(pm, main_id):
    body = workbench.ImportClaudeRequest(
        zh_markdown="关于晶圆供给和 2027 年数据中心建设的第一段。\n",
        en_markdown="First paragraph about wafer supply and the 2027 buildout of datacenters.\n", agent="codex")
    with pytest.raises(ConflictException) as caught:
        await workbench.import_claude_variant(_request("POST"), main_id, body, pm)
    assert caught.value.error_code == "ALIGNMENT_LOW" and "可能不是这篇下载的原文" in caught.value.detail
    forced = await workbench.import_claude_variant(_request("POST"), main_id, body.model_copy(update={"force": True}), pm)
    assert forced["variant_id"] == f"{main_id}--codex"
```

- [ ] **Step 2: 跑测试，确认失败**

Run: `python -m pytest tests/unit/services/test_article_variants.py -q -k "primary or conflict"`
Expected: FAIL，`KeyError: 'primary_target'` / `module ... has no attribute 'PrimaryRequest'`

- [ ] **Step 3: 实现** `src/api/routers/workbench.py`

import 区：`from src.services import article_edits, article_primary, article_variants`；
`from ..middleware import BadRequestException, ConflictException, NotFoundException, ServiceUnavailableException`（`ConflictException` 已在列表里就不用动）。

请求模型区加：

```python
class PrimaryRequest(BaseModel):
    target: str = Field(..., min_length=1, max_length=200)  # 主项目或孪生项目 id
```

`get_workbench` 里 `return {...}` 的 `"project"` 字典加两项（放在 `"claude_run_id"` 后面），并在 return 前算出 `primary`：

```python
    main_started = main_status["active"] or any(row["web"] for row in rows)
    primary = article_primary.resolve_primary(
        pm, project_id, [v.id for v in variant_metas], primary_target=meta.primary_target, main_started=main_started)
```

```python
            "primary_target": meta.primary_target,
            "primary": primary,
```

`set_reading_mark` 前面加新接口：

```python
@router.put("/projects/{project_id}/workbench/primary")
async def set_primary(project_id: str, body: PrimaryRequest, pm: ProjectManagerDep):
    """「设为主译本」：存进主项目 meta，换设备也一样。"""
    _check_id(project_id)

    def save():
        if pm.get(project_id).variant_of:
            raise BadRequestException(detail="主译本只能设在文章的主项目上", error_code="IS_VARIANT")
        _check_target(pm, project_id, body.target)
        pm.merge_meta_fields(project_id, fields={"primary_target": body.target})

    try:
        await run_blocking(save)
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")
    return {"ok": True, "primary_target": body.target}
```

`import_claude_variant` 的调用和异常处理换成：

```python
    try:
        result = await run_blocking(
            article_variants.import_claude_translation, pm, project_id,
            zh_markdown=body.zh_markdown, en_markdown=body.en_markdown, run_id=body.run_id, agent=body.agent,
            model=body.model, force=body.force)
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")
    except article_variants.AlignmentTooLow as error:
        raise ConflictException(detail=str(error), error_code="ALIGNMENT_LOW")
    except ValueError as error:
        raise BadRequestException(detail=str(error))
    return result
```

（`AlignmentTooLow` 是 `ValueError` 的子类，必须排在 `except ValueError` 前面。）

- [ ] **Step 4: 跑测试，确认通过**

Run: `python -m pytest tests/unit/services/test_article_variants.py -q`
Expected: 全部通过

- [ ] **Step 5: 提交**

```bash
git add src/api/routers/workbench.py tests/unit/services/test_article_variants.py
git commit -m "feat(workbench): primary version endpoints and alignment conflict"
```

---

### Task 5: 文章列表进度只看主译本

**Files:**
- Modify: `src/api/routers/substack.py:159-177`（`_translation_state`）、`:193`（调用处）
- Test: `tests/unit/api/test_substack_router.py:235-247`

- [ ] **Step 1: 改测试**

把 `test_list_articles_progress_takes_the_further_version` 整个换成：

```python
@pytest.mark.asyncio
async def test_list_articles_progress_follows_the_primary_version(tmp_path, pm, monkeypatch):
    project_id = await _import(tmp_path, pm)
    variant = article_variants.create_variant(pm, project_id, kind="claude", label="Codex", suffix="codex")
    done = {project_id: 1, variant: 4}
    monkeypatch.setattr(pm, "get_translation_summary", lambda pid: ProjectTranslationSummary(
        status=ProjectStatus.IN_PROGRESS, total_sections=1, total_paragraphs=4,
        translated_sections=0, translated_paragraphs=done[pid],
    ))
    library = _library(tmp_path)
    # 没选过主译本、网页版已经开始 → 看网页版
    article = (await _list(pm, library)).articles[0]
    assert (article.status, article.progress) == ("partial", 25)
    # 选了 Codex 版作主译本 → 看它
    pm.merge_meta_fields(project_id, fields={"primary_target": variant})
    article = (await _list(pm, library)).articles[0]
    assert (article.project_id, article.status, article.progress) == (project_id, "translated", 100)
    assert (await _list(pm, library)).counts["imported"] == 1  # 孪生项目不算一篇
```

- [ ] **Step 2: 跑测试，确认失败**

Run: `python -m pytest tests/unit/api/test_substack_router.py -q -k "primary"`
Expected: FAIL，第一处断言得到 `("translated", 100)`（旧逻辑取最高的那版）

- [ ] **Step 3: 实现** `src/api/routers/substack.py`

import 区加 `from src.services import article_primary`（和已有的 services import 放一起）。

`_translation_state` 换成：

```python
def _translation_state(pm: ProjectManager, project_id: str, variant_ids: List[str],
                       primary_target: Optional[str] = None) -> Tuple[ArticleStatus, int]:
    """只看主译本（services/article_primary.py）；主译本是网页版时，在跑或在等术语确认照旧显示。"""
    main = _percent(pm, project_id)
    if main is None:
        return "not_imported", 0  # 列清单和这里之间项目被删了
    main_active = translation_run_registry.get_active_run(project_id) is not None
    primary = article_primary.resolve_primary(
        pm, project_id, variant_ids, primary_target=primary_target, main_started=bool(main) or main_active)
    percent = main if primary == project_id else (_percent(pm, primary) or 0)
    active = translation_run_registry.get_active_run(primary)
    if active is not None:
        return ("awaiting_terms" if _awaiting_terms(pm, primary, active.run_id) else "translating"), percent
    if percent >= 100:
        return "translated", 100
    if percent:
        return "partial", percent
    return "imported", 0
```

调用处换成：

```python
        status, progress = _translation_state(pm, project.id, variant_ids, project.primary_target)
```

（`project` 是 `ProjectListSummary`，Task 1 已经加了 `primary_target`。）

- [ ] **Step 4: 跑测试，确认通过**

Run: `python -m pytest tests/unit/api/test_substack_router.py -q`
Expected: 全部通过（`test_list_articles_shows_running_workflow_and_term_confirmation` 里网页版在跑，主译本默认是网页版，行为不变）

- [ ] **Step 5: 提交**

```bash
git add src/api/routers/substack.py tests/unit/api/test_substack_router.py
git commit -m "feat(articles): list progress follows the primary version"
```

---

### Task 6: Codex 每次运行固定一个模型并上报

**Files:**
- Modify: `skill_runner/codex_session.py`（`CodexMapper.__init__` 约 65 行、`map` 的 `thread.started` 约 88 行、`CodexSession.__init__` 约 164 行、`_turn` 约 216 行）
- Test: `tests/unit/skill_runner/test_skill_runner_codex.py`

- [ ] **Step 1: 写失败的测试**（追加）

```python
FAKE_CODEX_ECHO_MODEL = textwrap.dedent('''
    import json, sys
    args = sys.argv[1:]
    sys.stdin.buffer.read()
    model = args[args.index("-m") + 1] if "-m" in args else "none"
    thread = args[-2] if "resume" in args else "thread-1"
    def emit(event): print(json.dumps(event), flush=True)
    emit({"type": "thread.started", "thread_id": thread})
    emit({"type": "turn.started"})
    emit({"type": "item.completed", "item": {"id": "m", "type": "agent_message", "text": "model=" + model}})
    emit({"type": "turn.completed", "usage": {}})
''')


@pytest.mark.asyncio
async def test_default_model_is_fixed_for_the_whole_run_and_reported(tmp_path):
    script = tmp_path / "fake_codex.py"
    script.write_text(FAKE_CODEX_ECHO_MODEL, encoding="utf-8")

    def top(slug):
        (tmp_path / "models_cache.json").write_text(json.dumps(
            {"models": [{"slug": slug, "visibility": "list", "priority": 1}]}), encoding="utf-8")

    top("gpt-6.1-sol")
    config = make_config(tmp_path, sandbox=False, codex_bin=f'"{sys.executable}" "{script}"'.replace("\\", "/"),
                         codex_home=tmp_path)

    async def deny(*_args):
        raise AssertionError("Codex 不走权限回调")

    spec = SessionSpec(run_id="r1", cwd=tmp_path, resume=None, on_permission=deny, harness="codex")
    session = await CodexSession.open(config, spec)
    seen = []

    async def collect(until: int):
        async for event in session.events():
            seen.append(event)
            if sum(e["type"] == "result" for e in seen) == until:
                return

    await session.send("第一轮")
    await asyncio.wait_for(collect(1), 30)
    top("gpt-7-new")  # 任务中途 Codex 更新了清单
    await session.send("第二轮")
    await asyncio.wait_for(collect(2), 30)
    await session.close()

    assert [e["text"] for e in seen if e["type"] == "text"] == ["model=gpt-6.1-sol", "model=gpt-6.1-sol"]
    assert [e.get("model") for e in seen if e["type"] == "session"] == ["gpt-6.1-sol", "gpt-6.1-sol"]
```

- [ ] **Step 2: 跑测试，确认失败**

Run: `python -m pytest tests/unit/skill_runner/test_skill_runner_codex.py -q -k fixed`
Expected: FAIL：第二轮是 `model=gpt-7-new`，且 session 事件没有 `model`

- [ ] **Step 3: 实现** `skill_runner/codex_session.py`

`CodexMapper.__init__` 加一行：

```python
        self.model: str | None = None  # 这次运行定下的模型，随 session 事件上报
```

`map` 里 `thread.started` 分支换成：

```python
        if kind == "thread.started":
            self.thread_id = event.get("thread_id") or self.thread_id
            session = {"type": "session", "session_id": self.thread_id}
            if self.model:
                session["model"] = self.model  # runner 据此写 actual_model
            return [session]
```

`CodexSession.__init__` 里 `self._mapper.thread_id = spec.resume` 下面加：

```python
        # 没指定模型时开局就定下清单里排第一的那个，之后每一轮都用它：中途清单更新也不换模型
        self._model = spec.model or config.codex_model or latest_model(config.codex_home)
        self._mapper.model = self._model
```

`_turn` 第一行换成：

```python
        command = build_command(self._config, self._mapper.thread_id, self._model)
```

- [ ] **Step 4: 跑 Codex 测试**

Run: `python -m pytest tests/unit/skill_runner/test_skill_runner_codex.py -q`
Expected: 全部通过（`test_session_runs_one_process_per_turn_and_resumes` 的 `codex_home` 下没有清单，`_model` 为 None，行为不变）

- [ ] **Step 5: 提交**

```bash
git add skill_runner/codex_session.py tests/unit/skill_runner/test_skill_runner_codex.py
git commit -m "fix(skill-runner): pin Codex default model per run and report it"
```

---

### Task 7: 界面上 Antigravity 改叫 Gemini（skill-runner）

**Files:**
- Modify: `skill_runner/runner.py:134-135`、`skill_runner/antigravity_session.py`、`skill_runner/models.py:202`、`skill_runner/runtime_updates.py:43,96,113,135`、`skill_runner/agents.py:52`、`skill_runner/README.md`
- Test: `tests/unit/skill_runner/test_skill_runner_antigravity.py:60`

- [ ] **Step 1: 改测试**

`test_skill_runner_antigravity.py` 第 60 行改为：

```python
    assert harness_label("antigravity") == "Gemini"
```

再在该文件末尾加一条扫描测试：

```python
def test_user_facing_text_calls_it_gemini():
    import inspect
    from skill_runner import antigravity_session, models, runner, runtime_updates
    for module in (antigravity_session, models, runner, runtime_updates):
        for line in inspect.getsource(module).splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or "Antigravity" not in stripped:
                continue
            # 只允许类名、文档字符串、英文日志/异常，以及写给模型看的运行环境说明里出现 Antigravity
            assert any(token in stripped for token in (
                "class Antigravity", "Antigravity CLI backend", "AntigravityMapper", "AntigravitySession",
                "Antigravity model output", "Antigravity model discovery", "Antigravity 的审阅界面",
            )), f"{module.__name__}: {stripped}"
```

- [ ] **Step 2: 跑测试，确认失败**

Run: `python -m pytest tests/unit/skill_runner/test_skill_runner_antigravity.py -q`
Expected: FAIL，`harness_label` 返回 `Antigravity`，扫描测试列出含中文的那些行

- [ ] **Step 3: 实现**（逐条替换；`antigravity`、`agy`、`ANTIGRAVITY_*`、类名一律不动）

`skill_runner/runner.py`：

```python
def harness_label(harness: str) -> str:
    # 界面上第三个 Agent 叫 Gemini；内部 id 仍是 antigravity（官方 agy CLI）
    return {"claude": "Claude", "codex": "Codex", "antigravity": "Gemini"}.get(harness, harness)
```

`skill_runner/antigravity_session.py` 里的字符串：

| 原文 | 改成 |
|---|---|
| `"Antigravity 输出的事件不是 JSON 对象"` | `"Gemini 输出的事件不是 JSON 对象"` |
| `f"Antigravity 状态：{status or 'UNKNOWN'}"` | `f"Gemini 状态：{status or 'UNKNOWN'}"` |
| `"Antigravity 输出错误事件"` | `"Gemini 输出错误事件"` |
| `"AntigravityTool"` | `"GeminiTool"` |
| `"Antigravity CLI 无法保证服务器沙箱隔离；当前 SKILL_RUNNER_SANDBOX 要求沙箱，拒绝启动"` | `"Gemini（agy CLI）无法保证服务器沙箱隔离；当前 SKILL_RUNNER_SANDBOX 要求沙箱，拒绝启动"` |
| `"Antigravity 会话已关闭"` | `"Gemini 会话已关闭"` |
| `f"Antigravity 进程出错：{message}"` | `f"Gemini 进程出错：{message}"` |
| `"Antigravity 输出了无效的 JSON 事件"` | `"Gemini 输出了无效的 JSON 事件"` |
| `f"Antigravity 退出码 {code}：…"` | `f"Gemini 退出码 {code}：…"`（后半句不变） |

文件第一行文档字符串 `"""Official Google Antigravity CLI backend, …` 保持英文不动；第 29 行写给模型的运行环境说明
（「看不到终端或 Antigravity 的审阅界面」）也不动，页面上不显示，而且对模型来说是准确的。两处扫描测试都已放行。

`skill_runner/models.py:202` 的提示改为：
`"暂时读不到 Gemini 模型清单；请检查服务器 agy CLI 的安装和登录状态。仍可使用默认模型或填写模型 ID。"`

`skill_runner/runtime_updates.py`：
- 第 43 行 `"当前平台无法查询 Antigravity 官方版本"` → `"当前平台无法查询 Gemini（agy CLI）官方版本"`
- 第 96 行 `("antigravity", "Antigravity")` → `("antigravity", "Gemini")`
- 第 113 行 `"未配置 Antigravity 可执行程序"` → `"未配置 Gemini（agy CLI）可执行程序"`
- 第 135 行 `"Antigravity 使用官方 CLI 的自动更新；此处仅检查版本。"` → `"Gemini（agy CLI）使用官方自动更新；此处仅检查版本。"`

`skill_runner/agents.py:52` 注释改为：

```python
        # 新对话默认用哪个运行工具跑（翻译 Agent 默认 Codex，只是默认值）；页面上可以改
```

`skill_runner/README.md`：标题 `## Harness：Claude Code / Codex / Antigravity` 改为 `## Harness：Claude Code / Codex / Gemini（Antigravity CLI）`；
第 87、92 行里给用户看的「Antigravity」改成「Gemini」，并在该节开头加一句「界面上叫 Gemini，内部 id、环境变量和 CLI 仍是 antigravity / `SKILL_RUNNER_ANTIGRAVITY_*` / `agy`。」

- [ ] **Step 4: 跑 skill-runner 全部测试**

Run: `python -m pytest tests/unit/skill_runner -q`
Expected: 全部通过。若有测试断言了旧中文文案（例如 runtime_updates 的标签），按新文案更新断言。

- [ ] **Step 5: 提交**

```bash
git add skill_runner tests/unit/skill_runner
git commit -m "feat(skill-runner): call the Antigravity harness Gemini in user-facing text"
```

---

### Task 8: Agent 页前端文案（Gemini、Codex 说明）

**Files:**
- Modify: `web/frontend/src/features/skills/harness.ts:4-8`
- Modify: `web/frontend/src/features/skills/components/ModelPicker.tsx:65`
- Modify: `web/frontend/src/features/skills/components/RuntimeUpdatesPanel.tsx:39`
- Test: `web/frontend/src/features/skills/agents.test.tsx`

- [ ] **Step 1: 改测试**

`agents.test.tsx`：
- 第 23 行用例名改为 `'preserves an antigravity default and labels it Gemini'`，第 25 行改为 `expect(harnessLabel('antigravity')).toBe('Gemini');`
- 第 177、207 行用例名里的 `Antigravity` 改成 `Gemini`；第 178、186、189、192、211 行 `radio('模型', 'Antigravity')` 和 `'Antigravity'` 都改成 `'Gemini'`。
- 再加一条：

```tsx
  it('describes each harness without mentioning paid articles', () => {
    for (const item of HARNESSES) expect(item.note).not.toMatch(/付费/);
    expect(HARNESSES.map(item => item.label)).toEqual(['Claude', 'Codex', 'Gemini']);
  });
```

（import 里加 `HARNESSES`：`import { HARNESSES, harnessLabel } from './harness';`）

- [ ] **Step 2: 跑测试，确认失败**

Run（`web/frontend`）：`npx vitest run src/features/skills/agents.test.tsx`
Expected: FAIL，label 还是 `Antigravity`

- [ ] **Step 3: 实现**

`harness.ts` 的 `HARNESSES` 换成：

```ts
export const HARNESSES: { id: Harness; label: string; note: string }[] = [
  { id: 'claude', label: 'Claude', note: '用你的 Claude 订阅（Claude Code）' },
  { id: 'codex', label: 'Codex', note: '用你的 ChatGPT 订阅（Codex）' },
  // 内部 id 仍是 antigravity（服务器上的 agy CLI），界面上叫 Gemini
  { id: 'antigravity', label: 'Gemini', note: '用服务器上登录的 Google 账号（Gemini）' },
];
```

`ModelPicker.tsx:65` 的 `'Antigravity'` 改为 `'Gemini（agy）'`。
`RuntimeUpdatesPanel.tsx:39` 的「Codex、Claude Code 和 Antigravity 版本」改为「Codex、Claude Code 和 Gemini（agy CLI）版本」。

- [ ] **Step 4: 跑测试**

Run（`web/frontend`）：`npx vitest run src/features/skills && npx tsc -b`
Expected: 全部通过

- [ ] **Step 5: 提交**

```bash
git add web/frontend/src/features/skills
git commit -m "feat(agents): show the third harness as Gemini and drop paid-article notes"
```

---

### Task 9: 整体验证

- [ ] **Step 1:** `python -m pytest tests/unit -q -x --ignore=tests/unit/regression` → 和基线比，没有新增失败（Windows 上已知的软链接类失败照旧）
- [ ] **Step 2:** `python -m ruff check src skill_runner` → 无新增问题（CI 有 F821）
- [ ] **Step 3:**（`web/frontend`）`npm test && npx tsc -b && npm run lint` → 全部通过
- [ ] **Step 4:** `rg -n "Antigravity" skill_runner web/frontend/src --glob '!*.test.*'` → 只剩类名、英文文档字符串 / 日志、README 里说明内部 id 的那一句、`harness.ts` 注释
