"""
翻译记忆服务 - 自学习翻译规则管理

规则以自然语言 markdown 条目存储，每条是一句可操作的翻译指令。
存储路径：
  - 项目级：data/memory/{project_id}.md
  - 全局：data/global_memory.md
"""

import asyncio
import difflib
import logging
import random
import threading
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# 全局记忆文件路径
GLOBAL_MEMORY_PATH = Path("data/global_memory.md")
PROJECT_MEMORY_DIR = Path("data/memory")

# diff 变化率阈值，低于此值跳过 LLM 提取
MIN_DIFF_RATIO = 0.05

# 每次成功保存规则后，以此概率触发规则库梳理
CONSOLIDATION_PROBABILITY = 0.05

# 注入 prompt 时的规则上限
MAX_RULES_IN_PROMPT = 20
MAX_RULES_CHARS = 600


class TranslationMemoryService:
    """翻译记忆服务 - 管理自学习翻译规则"""

    def __init__(self, llm_provider=None):
        self._llm = llm_provider
        self._cache: dict[str, list[str]] = {}
        self._lock = threading.RLock()
        self._llm_lock = threading.Lock()

    @property
    def llm(self):
        """懒加载规则提取专用 LLM provider（Flash 模型）。"""
        if self._llm is None:
            from src.llm.factory import create_llm_provider
            self._llm = create_llm_provider(model_type="flash")
        return self._llm

    # ============ 主入口方法 ============

    async def process_correction(
        self,
        source: str,
        ai_translation: str,
        user_translation: str,
        project_id: Optional[str] = None,
    ) -> List[str]:
        """从用户纠正中提取翻译规则。"""
        diff_ratio = self._compute_diff_ratio(ai_translation, user_translation)
        if diff_ratio < MIN_DIFF_RATIO:
            logger.debug("Diff ratio %.3f < threshold, skipping", diff_ratio)
            return []

        try:
            new_rules = await self._extract_rules(
                "longform/learning/correction_rule_extraction.v2",
                source=source,
                ai_translation=ai_translation,
                user_translation=user_translation,
            )
            if new_rules:
                self._append_rules(new_rules, project_id)
                logger.info("Extracted %d rules from correction", len(new_rules))
                self._maybe_consolidate(project_id)
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
        project_id: Optional[str] = None,
    ) -> List[str]:
        """从重翻指令中提取风格偏好规则。"""
        diff_ratio = self._compute_diff_ratio(before, after)
        if diff_ratio < MIN_DIFF_RATIO:
            return []

        try:
            new_rules = await self._extract_rules(
                "longform/learning/retranslation_rule_extraction.v2",
                instruction=instruction,
                source=source,
                before=before,
                after=after,
            )
            if new_rules:
                self._append_rules(new_rules, project_id)
                logger.info("Extracted %d rules from retranslation", len(new_rules))
                self._maybe_consolidate(project_id)
            return new_rules
        except Exception as e:
            logger.warning("Failed to extract rules from retranslation: %s", e)
            return []

    async def process_reflection_issues(
        self,
        issues: list,
        translations: List[str],
        project_id: Optional[str] = None,
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
                "longform/learning/reflection_rule_extraction.v2",
                issues_text=issues_text,
                translations_text=translations_text,
            )
            if new_rules:
                self._append_rules(new_rules, project_id)
                logger.info("Extracted %d rules from reflection", len(new_rules))
                self._maybe_consolidate(project_id)
            return new_rules
        except Exception as e:
            logger.warning("Failed to extract rules from reflection: %s", e)
            return []

    # ============ 规则读取 ============

    def get_rules_for_prompt(
        self,
        project_id: Optional[str] = None,
    ) -> List[str]:
        """获取用于注入翻译 prompt 的规则列表（截断到上限）。"""
        with self._lock:
            rules = self._load_rules(project_id)
            if not rules:
                return []
            selected = []
            total_chars = 0
            for rule in rules[:MAX_RULES_IN_PROMPT]:
                total_chars += len(rule)
                if total_chars > MAX_RULES_CHARS:
                    break
                selected.append(rule)
            return selected

    def get_all_rules(self, project_id: Optional[str] = None) -> List[str]:
        """获取所有规则（API 用）。"""
        with self._lock:
            return list(self._load_rules(project_id))

    def delete_rule(self, rule_text: str, project_id: Optional[str] = None) -> bool:
        """删除匹配的规则。"""
        with self._lock:
            rules = self._load_rules(project_id)
            original_count = len(rules)
            rules = [r for r in rules if r.strip() != rule_text.strip()]
            if len(rules) < original_count:
                self._save_rules(rules, project_id)
                return True
            return False

    def delete_rule_by_index(self, index: int, project_id: Optional[str] = None) -> bool:
        """按索引删除规则。"""
        with self._lock:
            rules = self._load_rules(project_id)
            if 0 <= index < len(rules):
                rules.pop(index)
                self._save_rules(rules, project_id)
                return True
            return False

    def add_rule_manually(self, rule_text: str, project_id: Optional[str] = None) -> None:
        """手动添加一条规则。"""
        rule = rule_text.strip().lstrip("- ").strip()
        if not rule:
            return
        self._append_rules([rule], project_id)

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

    def _append_rules(self, new_rules: List[str], project_id: Optional[str] = None) -> None:
        """追加规则，跳过精确重复。"""
        with self._lock:
            existing = self._load_rules(project_id)
            existing_set = {r.strip() for r in existing}
            added = 0
            for rule in new_rules:
                rule = rule.strip()
                if rule and rule not in existing_set:
                    existing.append(rule)
                    existing_set.add(rule)
                    added += 1
            if added:
                self._save_rules(existing, project_id)

        # 规则保存后尝试提取术语候选
        if project_id and new_rules:
            self._extract_term_candidates_from_rules(new_rules, project_id)

    def _extract_term_candidates_from_rules(self, rules: List[str], project_id: str) -> None:
        """从规则文本中用正则提取术语候选，保存到候选文件。"""
        import json
        import re

        patterns = [
            r'"(.+?)"\s*(?:翻译为|应译为|译为|统一翻译为)\s*"(.+?)"',
            r'(?:将|把)\s*"(.+?)"\s*(?:翻译为|译为)\s*"(.+?)"',
        ]
        candidates = []
        for rule in rules:
            for pat in patterns:
                for m in re.finditer(pat, rule):
                    candidates.append({
                        "term": m.group(1),
                        "translation": m.group(2),
                        "source_rule": rule,
                    })

        if not candidates:
            return

        candidates_path = PROJECT_MEMORY_DIR / f"{project_id}_term_candidates.json"
        existing = []
        if candidates_path.exists():
            try:
                existing = json.loads(candidates_path.read_text("utf-8"))
            except Exception:
                existing = []

        existing_keys = {c["term"].lower() for c in existing}
        for c in candidates:
            if c["term"].lower() not in existing_keys:
                existing.append(c)
                existing_keys.add(c["term"].lower())

        candidates_path.parent.mkdir(parents=True, exist_ok=True)
        candidates_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), "utf-8")

    def _maybe_consolidate(self, project_id: Optional[str] = None) -> None:
        """以 CONSOLIDATION_PROBABILITY 概率触发规则库梳理（异步非阻塞）。"""
        with self._lock:
            rules = self._load_rules(project_id)
            if len(rules) < 8:
                return
        if random.random() < CONSOLIDATION_PROBABILITY:
            logger.info("Triggering rule consolidation (%.0f%% chance) for project=%s",
                       CONSOLIDATION_PROBABILITY * 100, project_id)
            asyncio.create_task(self._consolidate_rules(project_id))

    async def _consolidate_rules(self, project_id: Optional[str] = None) -> None:
        """使用 LLM 梳理规则库：合并重复、解决矛盾、删除模糊规则。"""
        try:
            with self._lock:
                rules = self._load_rules(project_id)
                if not rules:
                    return
                rules_text = "\n".join(f"- {r}" for r in rules)

            from src.prompts import get_prompt_manager
            pm = get_prompt_manager()
            prompt = pm.get(
                "longform/learning/rules_consolidation.v2",
                rules_text=rules_text,
            )

            response = await asyncio.to_thread(self._generate, prompt)
            consolidated = self._parse_bullet_list(response)

            if not consolidated:
                logger.warning("Consolidation returned empty, skipping")
                return

            with self._lock:
                old_rules = self._load_rules(project_id)
                old_count = len(old_rules)
                self._save_rules(consolidated, project_id)

            logger.info("Consolidation complete: %d → %d rules", old_count, len(consolidated))

        except Exception as e:
            logger.warning("Rule consolidation failed: %s", e)

    # ============ 存储 ============

    def _memory_path(self, project_id: Optional[str] = None) -> Path:
        if not project_id:
            return GLOBAL_MEMORY_PATH
        cleaned = "".join(
            char if (char.isalnum() or char in ("-", "_")) else "_"
            for char in project_id.strip()
        )
        return PROJECT_MEMORY_DIR / f"{cleaned or 'global'}.md"

    def _load_rules(self, project_id: Optional[str] = None) -> List[str]:
        """加载规则列表（从缓存或磁盘）。"""
        path = self._memory_path(project_id)
        cache_key = str(path)
        if cache_key in self._cache:
            return self._cache[cache_key]

        rules: List[str] = []
        if path.exists():
            try:
                text = path.read_text(encoding="utf-8")
                rules = self._parse_bullet_list(text)
            except Exception as e:
                logger.warning("Failed to load rules from %s: %s", path, e)

        self._cache[cache_key] = rules
        return rules

    def _save_rules(self, rules: List[str], project_id: Optional[str] = None) -> None:
        """原子写入规则到 markdown 文件。"""
        path = self._memory_path(project_id)
        cache_key = str(path)
        self._cache[cache_key] = rules

        path.parent.mkdir(parents=True, exist_ok=True)
        content = "\n".join(f"- {r}" for r in rules) + "\n" if rules else ""
        temp_path = path.with_suffix(".md.tmp")
        temp_path.write_text(content, encoding="utf-8")
        temp_path.replace(path)

    # ============ 工具方法 ============

    @staticmethod
    def _compute_diff_ratio(text_a: str, text_b: str) -> float:
        if not text_a or not text_b:
            return 1.0
        matcher = difflib.SequenceMatcher(None, text_a, text_b)
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
