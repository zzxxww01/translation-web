"""
翻译记忆服务 - 自学习翻译规则管理

规则以自然语言 markdown 条目存储，每条是一句可操作的翻译指令。
存储路径：data/global_memory.md（仅全局规则库）

规则 ≠ 术语。规则是关于翻译句式、风格、语气的全局偏好（如"避免被动句堆叠"），
跨项目通用；术语是特定项目中专业词汇的翻译，属于项目级术语库管辖。
"""

import asyncio
import difflib
import logging
import random
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import List

try:
    from filelock import FileLock, Timeout as FileLockTimeout
except ImportError:  # pragma: no cover - filelock 应已安装
    FileLock = None
    FileLockTimeout = ()

logger = logging.getLogger(__name__)

# 全局记忆文件路径
GLOBAL_MEMORY_PATH = Path("data/global_memory.md")

# diff 变化率阈值，低于此值跳过 LLM 提取
MIN_DIFF_RATIO = 0.05

# 每次成功保存规则后，以此概率触发规则库梳理
CONSOLIDATION_PROBABILITY = 0.05

# 注入 prompt 时的规则上限
MAX_RULES_IN_PROMPT = 20
MAX_RULES_CHARS = 600

# 规则库硬上限：超过即确定性触发一次梳理（不再仅靠 5% 概率），防止无界膨胀
MAX_RULES_HARD_CAP = 60

# 近似去重阈值：相似度高于此值视为语义重复，跳过写入
RULE_SIMILARITY_THRESHOLD = 0.85

# diff 比对的最大字符数，避免长段落 SequenceMatcher O(n^2) 阻塞
MAX_DIFF_CHARS = 2000

# 术语型规则的特征：这类规则应进术语库而非规则库，代码侧兜底过滤
_TERM_RULE_PATTERNS = (
    "翻译为",
    "译为",
    "翻译成",
    "应译作",
    "译作",
    "统一译为",
)


class TranslationMemoryService:
    """翻译记忆服务 - 管理自学习翻译规则"""

    # 进程级共享状态：多处会各自 new 一个实例（dependencies 单例 + batch /
    # confirmation 自建），但都读写同一个 global_memory.md。若每实例各持独立缓存与锁，
    # 会出现脏读（单例读盘后看不到其它实例追加的新规则）与丢写（跨实例 read-modify-write
    # 后写覆盖先写）。改为类级共享缓存 + 类级锁，使同进程内成为单一真相来源。
    # 配合 _load_rules 的 mtime 校验，跨进程/外部修改也能被感知并重读。
    _cache: dict[str, list[str]] = {}
    _cache_mtime: dict[str, "int | None"] = {}
    _lock = threading.RLock()
    # 后台学习任务强引用集合，防止未被引用的 Task 在完成前被 GC 回收（CPython 陷阱）
    _bg_tasks: set = set()
    # 主事件循环引用，供工作线程回投后台学习协程（见 register_loop / _spawn_background）
    _main_loop = None

    def __init__(self, llm_provider=None):
        self._llm = llm_provider
        self._llm_lock = threading.Lock()

    @property
    def llm(self):
        """懒加载规则提取专用 LLM provider（走 analysis 任务默认模型）。"""
        if self._llm is None:
            from src.llm.factory import create_llm_provider, get_task_model_alias

            self._llm = create_llm_provider(provider=get_task_model_alias("analysis"))
        return self._llm

    # ============ 主入口方法 ============

    async def process_correction(
        self,
        source: str,
        ai_translation: str,
        user_translation: str,
    ) -> List[str]:
        """从用户纠正中提取翻译规则。"""
        diff_ratio = self._compute_diff_ratio(ai_translation, user_translation)
        if diff_ratio < MIN_DIFF_RATIO:
            logger.debug("Diff ratio %.3f < threshold, skipping", diff_ratio)
            return []

        try:
            new_rules = await self._extract_rules(
                "longform/learning/correction_rule_extraction",
                source=source,
                ai_translation=ai_translation,
                user_translation=user_translation,
            )
            if new_rules:
                self._append_rules(new_rules)
                logger.info("Extracted %d rules from correction", len(new_rules))
                self._maybe_consolidate()
            return new_rules
        except Exception as e:
            logger.warning("Failed to extract rules from correction: %s", e)
            return []

    async def process_retranslation_instruction(
        self,
        instruction: str,
        source: str,
        before: str,
        after: str,
    ) -> List[str]:
        """从重翻指令中提取风格偏好规则。"""
        diff_ratio = self._compute_diff_ratio(before, after)
        if diff_ratio < MIN_DIFF_RATIO:
            return []

        try:
            new_rules = await self._extract_rules(
                "longform/learning/retranslation_rule_extraction",
                instruction=instruction,
                source=source,
                before=before,
                after=after,
            )
            if new_rules:
                self._append_rules(new_rules)
                logger.info("Extracted %d rules from retranslation", len(new_rules))
                self._maybe_consolidate()
            return new_rules
        except Exception as e:
            logger.warning("Failed to extract rules from retranslation: %s", e)
            return []

    async def process_reflection_issues(
        self,
        issues: list,
        translations: List[str],
    ) -> List[str]:
        """从四步法 critique 的 issues 中提取规则。"""
        if not issues:
            return []

        issues_text = "\n".join(
            f"- [{issue.issue_type}] 段落{issue.paragraph_index}: {issue.description}"
            + (f" 建议: {issue.suggestion}" if issue.suggestion else "")
            for issue in issues
        )
        translations_text = "\n".join(
            f"段落{i}: {t[:200]}"
            for i, t in enumerate(translations)
            if any(issue.paragraph_index == i for issue in issues)
        )
        if not translations_text:
            return []

        try:
            new_rules = await self._extract_rules(
                "longform/learning/reflection_rule_extraction",
                issues_text=issues_text,
                translations_text=translations_text,
            )
            if new_rules:
                self._append_rules(new_rules)
                logger.info("Extracted %d rules from reflection", len(new_rules))
                self._maybe_consolidate()
            return new_rules
        except Exception as e:
            logger.warning("Failed to extract rules from reflection: %s", e)
            return []

    # ============ 规则读取 ============

    def get_rules_for_prompt(self) -> List[str]:
        """获取用于注入翻译 prompt 的规则列表（截断到上限）。"""
        with self._lock:
            rules = self._load_rules()
            if not rules:
                return []
            # 新规则由 _append_rules 追加到列表末尾（最新在尾部）。
            # 注入 prompt 时应优先取最新规则，否则一旦规则总数超过上限，
            # 新学习成果永远排在上限之后、注入不进 prompt，自学习闭环失效。
            selected = []
            total_chars = 0
            for rule in reversed(rules):
                if len(selected) >= MAX_RULES_IN_PROMPT:
                    break
                total_chars += len(rule)
                if total_chars > MAX_RULES_CHARS:
                    break
                selected.append(rule)
            # 在选中的最新规则内恢复时间顺序（旧→新），读起来更自然
            selected.reverse()
            return selected

    def get_all_rules(self) -> List[str]:
        """获取所有规则（API 用）。"""
        with self._lock:
            return list(self._load_rules())

    def delete_rule_by_index(self, index: int) -> bool:
        """按索引删除规则。"""
        with self._lock:
            rules = self._load_rules()
            if 0 <= index < len(rules):
                rules.pop(index)
                self._save_rules(rules)
                return True
            return False

    def add_rule_manually(self, rule_text: str) -> None:
        """手动添加一条规则。"""
        rule = rule_text.strip().lstrip("- ").strip()
        if not rule:
            return
        self._append_rules([rule])

    # ============ 内部方法 ============

    async def _extract_rules(self, template_name: str, **kwargs) -> List[str]:
        """使用 LLM 提取规则，返回纯文本规则列表。"""
        from src.prompts import get_prompt_manager

        pm = get_prompt_manager()
        prompt = pm.get(template_name, **kwargs)

        response = await asyncio.to_thread(self._generate, prompt)
        return self._parse_bullet_list(response)

    def _generate(self, prompt: str) -> str:
        """Thread-safe LLM 调用。"""
        with self._llm_lock:
            return self.llm.generate(prompt, temperature=0.3)

    @staticmethod
    def _is_term_rule(rule: str) -> bool:
        """判断是否是术语型规则（应进术语库而非规则库）。"""
        return any(pat in rule for pat in _TERM_RULE_PATTERNS)

    @staticmethod
    def _is_near_duplicate(rule: str, existing: List[str]) -> bool:
        """与已有规则做轻量语义近似判断，避免措辞不同的重复无限累积。"""
        for other in existing:
            if difflib.SequenceMatcher(None, rule, other).ratio() >= RULE_SIMILARITY_THRESHOLD:
                return True
        return False

    def _append_rules(self, new_rules: List[str]) -> None:
        """追加规则：过滤术语型规则、跳过精确与近似重复。"""
        with self._file_lock(), self._lock:
            existing = self._load_rules()
            existing_set = {r.strip() for r in existing}
            added = 0
            for rule in new_rules:
                rule = rule.strip()
                if not rule or rule in existing_set:
                    continue
                if self._is_term_rule(rule):
                    # 术语型规则不进规则库（规则提取 prompt 已禁止，这里代码侧兜底）
                    logger.debug("Skip term-like rule from memory: %s", rule)
                    continue
                if self._is_near_duplicate(rule, existing):
                    continue
                existing.append(rule)
                existing_set.add(rule)
                added += 1
            if added:
                self._save_rules(existing)

    def _maybe_consolidate(self) -> None:
        """触发规则库梳理（异步非阻塞）。

        超过硬上限时确定性触发；否则按 CONSOLIDATION_PROBABILITY 概率触发。
        """
        with self._lock:
            rules = self._load_rules()
            if len(rules) < 8:
                return
            over_cap = len(rules) > MAX_RULES_HARD_CAP
        if over_cap or random.random() < CONSOLIDATION_PROBABILITY:
            logger.info(
                "Triggering rule consolidation (over_cap=%s)", over_cap
            )
            self._spawn_background(self._consolidate_rules())

    @classmethod
    def register_loop(cls) -> None:
        """登记当前主事件循环，供工作线程（asyncio.to_thread）回投后台学习协程。"""
        try:
            cls._main_loop = asyncio.get_running_loop()
        except RuntimeError:
            cls._main_loop = None

    @classmethod
    def _spawn_background(cls, coro) -> None:
        """调度后台协程并保留强引用，防止 Task 在完成前被 GC 回收。

        - 在事件循环线程内：create_task。
        - 在工作线程内（如四步法经 asyncio.to_thread 执行）：若已登记主循环，则用
          run_coroutine_threadsafe 回投到主循环；否则静默跳过（关闭协程避免告警）。
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None:
            task = loop.create_task(coro)
            cls._bg_tasks.add(task)
            task.add_done_callback(cls._bg_tasks.discard)
            return

        main_loop = getattr(cls, "_main_loop", None)
        if main_loop is not None and main_loop.is_running():
            fut = asyncio.run_coroutine_threadsafe(coro, main_loop)
            cls._bg_tasks.add(fut)
            fut.add_done_callback(cls._bg_tasks.discard)
            return

        coro.close()

    async def _consolidate_rules(self) -> None:
        """使用 LLM 梳理规则库：合并重复、解决矛盾、删除模糊规则。

        梳理期间（LLM 调用耗时数秒）可能有其它学习任务追加新规则。完成保存前
        会把这些窗口期新增规则并入 consolidated，避免被整表覆盖而丢失。
        """
        try:
            with self._lock:
                rules = self._load_rules()
                if not rules:
                    return
                snapshot = list(rules)
                rules_text = "\n".join(f"- {r}" for r in snapshot)

            from src.prompts import get_prompt_manager
            pm = get_prompt_manager()
            prompt = pm.get(
                "longform/learning/rules_consolidation",
                rules_text=rules_text,
            )

            response = await asyncio.to_thread(self._generate, prompt)
            consolidated = self._parse_bullet_list(response)

            if not consolidated:
                logger.warning("Consolidation returned empty, skipping")
                return

            with self._file_lock(), self._lock:
                current = self._load_rules()
                old_count = len(current)
                # 并入窗口期新增（在 current 中但不在送去梳理的 snapshot 里）的规则
                snapshot_set = set(snapshot)
                merged = list(consolidated)
                merged_set = set(consolidated)
                for rule in current:
                    if rule not in snapshot_set and rule not in merged_set:
                        merged.append(rule)
                        merged_set.add(rule)
                self._save_rules(merged)

            logger.info("Consolidation complete: %d → %d rules", old_count, len(merged))

        except Exception as e:
            logger.warning("Rule consolidation failed: %s", e)

    # ============ 存储 ============

    @contextmanager
    def _file_lock(self):
        """跨进程文件锁，保护 global_memory.md 的 read-modify-write 不被并发覆盖。

        类级 _lock 只能串行化同进程内的访问；多进程部署时需文件锁防止丢写。
        filelock 不可用或获取超时时降级为无锁（仍由 _lock 保证同进程安全）。
        """
        if FileLock is None:
            yield
            return
        lock_path = str(GLOBAL_MEMORY_PATH) + ".lock"
        lock = FileLock(lock_path, timeout=10)
        try:
            with lock:
                yield
        except FileLockTimeout:
            logger.warning("global_memory 文件锁获取超时，降级为进程内锁继续")
            yield

    @staticmethod
    def _current_mtime() -> "int | None":
        try:
            return GLOBAL_MEMORY_PATH.stat().st_mtime_ns
        except OSError:
            return None

    def _load_rules(self) -> List[str]:
        """加载规则列表（缓存有效则返回缓存，否则读盘）。

        缓存以文件 mtime 校验：mtime 未变才复用缓存，使其它实例/进程写入后能被感知，
        消除“缓存永不失效”导致的脏读。
        """
        cache_key = str(GLOBAL_MEMORY_PATH)
        mtime = self._current_mtime()
        if cache_key in self._cache and self._cache_mtime.get(cache_key) == mtime:
            return self._cache[cache_key]

        rules: List[str] = []
        if mtime is not None:
            try:
                text = GLOBAL_MEMORY_PATH.read_text(encoding="utf-8")
                rules = self._parse_bullet_list(text)
            except Exception as e:
                logger.warning("Failed to load rules from %s: %s", GLOBAL_MEMORY_PATH, e)

        self._cache[cache_key] = rules
        self._cache_mtime[cache_key] = mtime
        return rules

    def _save_rules(self, rules: List[str]) -> None:
        """原子写入规则到 markdown 文件，并刷新缓存 mtime。"""
        cache_key = str(GLOBAL_MEMORY_PATH)

        GLOBAL_MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        content = "\n".join(f"- {r}" for r in rules) + "\n" if rules else ""
        temp_path = GLOBAL_MEMORY_PATH.with_suffix(".md.tmp")
        temp_path.write_text(content, encoding="utf-8")
        temp_path.replace(GLOBAL_MEMORY_PATH)

        self._cache[cache_key] = rules
        self._cache_mtime[cache_key] = self._current_mtime()

    # ============ 工具方法 ============

    @staticmethod
    def _compute_diff_ratio(text_a: str, text_b: str) -> float:
        if not text_a or not text_b:
            return 1.0
        # 截断到 MAX_DIFF_CHARS，避免长段落 SequenceMatcher O(n^2) 阻塞事件循环
        a = text_a[:MAX_DIFF_CHARS]
        b = text_b[:MAX_DIFF_CHARS]
        matcher = difflib.SequenceMatcher(None, a, b)
        return 1.0 - matcher.ratio()

    @staticmethod
    def _parse_bullet_list(text: str) -> List[str]:
        """从 LLM 响应或 markdown 文件中解析 bullet list。"""
        if not text or text.strip() == "NONE":
            return []
        rules = []
        for line in text.strip().splitlines():
            line = line.strip()
            if line.startswith("- "):
                rule = line[2:].strip()
                if rule:
                    rules.append(rule)
        return rules
