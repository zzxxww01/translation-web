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
                self._queue_candidates(new_rules, "human_correction", {"source":source, "before":ai_translation, "after":user_translation})
                logger.info("Queued %d correction rule candidates", len(new_rules))
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
                self._queue_candidates(new_rules, "model_retranslation", {"instruction":instruction, "source":source, "before":before, "after":after})
                logger.info("Queued %d retranslation rule candidates", len(new_rules))
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
                self._queue_candidates(new_rules, "model_reflection", {"issues":issues_text, "translations":translations_text})
                logger.info("Queued %d reflection rule candidates", len(new_rules))
            return new_rules
        except Exception as e:
            logger.warning("Failed to extract rules from reflection: %s", e)
            return []

    def _candidate_store(self):
        from .memory_candidates import RuleCandidates
        return RuleCandidates(GLOBAL_MEMORY_PATH)

    def _queue_candidates(self, rules, source_kind, evidence):
        filtered = [r for r in rules if isinstance(r, str) and r.strip() and not self._is_term_rule(r)]
        return self._candidate_store().add(filtered, source_kind, evidence)

    def get_rule_candidates(self):
        return self._candidate_store().list()

    def decide_rule_candidate(self, candidate_id: str, action: str):
        return self._candidate_store().decide(candidate_id, action, self._append_rules)

    # ============ 规则读取 ============

    def get_rules_for_prompt(self) -> List[str]:
        """获取用于注入翻译 prompt 的规则列表（截断到上限）。"""
        from src.prompts import active_rule_snapshot
        frozen = active_rule_snapshot()
        if frozen is not None:
            return list(frozen)
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
                if total_chars + len(rule) > MAX_RULES_CHARS:
                    continue
                total_chars += len(rule)
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
        with self._file_lock(), self._lock:
            rules = list(self._load_rules())
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
        # A one-character negation can reverse the meaning of otherwise similar
        # rules. Only ignore whitespace/terminal punctuation, never semantic text.
        import re
        canonical = lambda text: re.sub(r"\s+", "", text).rstrip("。.!！?？;；")
        return any(canonical(rule) == canonical(other) for other in existing)

    def _append_rules(self, new_rules: List[str]) -> None:
        """追加规则：过滤术语型规则、跳过精确与近似重复。"""
        with self._file_lock(), self._lock:
            existing = list(self._load_rules())
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
        """登记承载本次翻译的事件循环，供工作线程（asyncio.to_thread）回投后台学习协程。

        仅在尚未登记、或已登记的循环**已关闭或已停止运行**时才写入。无条件覆盖
        会把仍在服务中的循环换成随即销毁的临时子循环；而只判 ``is_closed()`` 又会
        让引用长期停在一个已经跑完、只是尚未关闭的循环上，导致后续 run 的后台学习
        协程被 :meth:`_spawn_background` 静默丢弃。

        已知限制：并发多个 run 时只保留先登记的那个循环，后来者的后台学习协程会
        回投到前者（memory service 是单例，功能上等价）；若前者已结束，后来者的
        协程会被丢弃并记 warning。
        """
        existing = getattr(cls, "_main_loop", None)
        if existing is not None and not existing.is_closed() and existing.is_running():
            return

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

        # 没有可回投的循环时协程被丢弃——这会静默吃掉一次反思学习，必须留痕，
        # 否则「规则库不增长」这类问题无从排查。
        logger.warning(
            "No live event loop to run background learning task; coroutine dropped."
        )
        coro.close()

    async def _consolidate_rules(self) -> None:
        """Consolidation proposes candidates only; it cannot erase approved rules."""
        rules = self.get_all_rules()
        if not rules:
            return
        try:
            from src.prompts import get_prompt_manager
            prompt = get_prompt_manager().render("longform/learning/rules_consolidation", rules_text="\n".join("- " + r for r in rules))
            response = await asyncio.to_thread(self._generate, prompt)
            candidates = self._parse_bullet_list(response)
            self._queue_candidates(candidates, "consolidation", {"rules": "\n".join(rules)})
        except Exception as exc:
            logger.warning("Rule consolidation proposal failed: %s", exc)

    # ============ 存储 ============

    @contextmanager
    def _file_lock(self):
        """Fail closed on lock timeout; every writer uses the same process lock."""
        import portalocker
        GLOBAL_MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with portalocker.Lock(str(GLOBAL_MEMORY_PATH) + ".lock", timeout=10):
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
                logger.error("Failed to load rules from %s: %s", GLOBAL_MEMORY_PATH, e)
                raise

        self._cache[cache_key] = rules
        self._cache_mtime[cache_key] = mtime
        return rules

    def _save_rules(self, rules: List[str]) -> None:
        """原子写入规则到 markdown 文件，并刷新缓存 mtime。"""
        cache_key = str(GLOBAL_MEMORY_PATH)

        GLOBAL_MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        content = "\n".join(f"- {r}" for r in rules) + "\n" if rules else ""
        from src.core.file_utils import write_text_atomic
        write_text_atomic(GLOBAL_MEMORY_PATH, content)
        self._cache[cache_key] = list(rules)
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
