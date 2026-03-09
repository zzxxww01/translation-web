"""
翻译记忆服务 - 自学习翻译规则管理

功能:
1. 从用户纠正中提取可复用翻译规则
2. 从重翻指令中提取风格偏好规则
3. 从反思评分中提取质量规则
4. 为翻译提供相关规则注入
"""

import asyncio
import difflib
import json
import logging
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from src.core.models import (
    TranslationRule,
    TranslationMemory,
    RuleType,
    ErrorCategory,
)

logger = logging.getLogger(__name__)

# 全局记忆文件路径
GLOBAL_MEMORY_PATH = Path("data/global_memory.json")
PROJECT_MEMORY_DIR = Path("data/memory")

# diff 变化率阈值，低于此值跳过 LLM 提取
MIN_DIFF_RATIO = 0.05


class TranslationMemoryService:
    """翻译记忆服务 - 管理自学习翻译规则"""

    def __init__(self, llm_provider=None):
        """
        初始化翻译记忆服务

        Args:
            llm_provider: LLM Provider（用于规则提取，使用 Flash 模型）
        """
        self._llm = llm_provider
        self._memory_cache: Dict[str, TranslationMemory] = {}
        self._memory_lock = threading.RLock()
        self._llm_lock = threading.Lock()

    @property
    def llm(self):
        """懒加载规则提取专用 LLM provider。"""
        if self._llm is None:
            from src.llm.factory import create_llm_provider

            # 使用独立实例，避免切换共享 provider 的模型状态。
            self._llm = create_llm_provider(model_type="flash")
        return self._llm

    # ============ 主入口方法 ============

    async def process_correction(
        self,
        source: str,
        ai_translation: str,
        user_translation: str,
        project_id: Optional[str] = None,
    ) -> List[TranslationRule]:
        """
        处理用户纠正，提取翻译规则

        Args:
            source: 英文原文
            ai_translation: AI 译文
            user_translation: 用户确认的译文

        Returns:
            提取的规则列表
        """
        # 预过滤：diff 变化率太小则跳过
        diff_ratio = self._compute_diff_ratio(ai_translation, user_translation)
        if diff_ratio < MIN_DIFF_RATIO:
            logger.debug("Diff ratio %.3f < threshold %.3f, skipping rule extraction", diff_ratio, MIN_DIFF_RATIO)
            return []

        try:
            rules = await self._extract_rules_with_llm(
                "rule_extraction",
                source=source,
                ai_translation=ai_translation,
                user_translation=user_translation,
            )

            if rules:
                with self._memory_lock:
                    memory = self._load_memory(project_id)
                    for rule in rules:
                        rule.source_context = source[:200]
                        self._deduplicate_and_add(memory, rule)
                    self._save_memory(memory, project_id)
                logger.info("Extracted %d rules from correction", len(rules))

            return rules

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
    ) -> List[TranslationRule]:
        """
        从重翻指令中提取风格偏好规则

        Args:
            instruction: 用户的重翻指令（如"更简洁"、"去翻译腔"）
            source: 英文原文
            before: 重翻前译文
            after: 重翻后译文

        Returns:
            提取的规则列表
        """
        diff_ratio = self._compute_diff_ratio(before, after)
        if diff_ratio < MIN_DIFF_RATIO:
            return []

        try:
            rules = await self._extract_rules_with_llm(
                "retranslation_rule_extraction",
                instruction=instruction,
                source=source,
                before=before,
                after=after,
            )

            if rules:
                with self._memory_lock:
                    memory = self._load_memory(project_id)
                    for rule in rules:
                        rule.source_context = source[:200]
                        self._deduplicate_and_add(memory, rule)
                    self._save_memory(memory, project_id)
                logger.info("Extracted %d rules from retranslation instruction", len(rules))

            return rules

        except Exception as e:
            logger.warning("Failed to extract rules from retranslation: %s", e)
            return []

    async def process_reflection_issues(
        self,
        issues: list,
        translations: List[str],
        project_id: Optional[str] = None,
    ) -> List[TranslationRule]:
        """
        从四步法反思评分的 issues 中提取规则

        Args:
            issues: TranslationIssue 列表
            translations: 对应的译文列表

        Returns:
            提取的规则列表
        """
        if not issues:
            return []

        # 构建 issues 文本
        issues_text = "\n".join(
            f"- [{issue.issue_type}] 段落{issue.paragraph_index}: {issue.description}"
            + (f" 建议: {issue.suggestion}" if issue.suggestion else "")
            for issue in issues
        )

        # 构建相关译文文本
        translations_text = "\n".join(
            f"段落{i}: {t[:200]}"
            for i, t in enumerate(translations)
            if any(issue.paragraph_index == i for issue in issues)
        )

        if not translations_text:
            return []

        try:
            rules = await self._extract_rules_with_llm(
                "reflection_rule_extraction",
                issues_text=issues_text,
                translations_text=translations_text,
            )

            if rules:
                with self._memory_lock:
                    memory = self._load_memory(project_id)
                    for rule in rules:
                        self._deduplicate_and_add(memory, rule)
                    self._save_memory(memory, project_id)
                logger.info("Extracted %d rules from reflection issues", len(rules))

            return rules

        except Exception as e:
            logger.warning("Failed to extract rules from reflection: %s", e)
            return []

    # ============ 规则选取 ============

    def get_relevant_rules(
        self,
        source_text: str,
        max_rules: int = 5,
        project_id: Optional[str] = None,
    ) -> List[TranslationRule]:
        """
        为当前段落选取最相关的规则

        使用关键词子串匹配 + 置信度排序

        Args:
            source_text: 当前段落英文原文
            max_rules: 最大返回规则数

        Returns:
            相关规则列表
        """
        with self._memory_lock:
            memory = self._load_memory(project_id)
            if not memory.rules:
                return []

            scored_rules = []
            source_lower = source_text.lower()

            for rule in memory.rules:
                score = rule.confidence

                # 规则的英文上下文与当前原文有词汇重叠 → 加分
                if rule.source_context:
                    context_words = set(rule.source_context.lower().split())
                    source_words = set(source_lower.split())
                    overlap = len(context_words & source_words)
                    if overlap > 0:
                        score += min(overlap * 0.1, 0.3)

                # 命中次数加分（经验证的规则更可靠）
                score += min(rule.hit_count * 0.05, 0.2)

                # HARD_RULE 和 STRICT_PROHIBITION 优先
                if rule.rule_type in (RuleType.HARD_RULE, RuleType.STRICT_PROHIBITION):
                    score += 0.1

                scored_rules.append((score, rule))

            # 按分数降序排列
            scored_rules.sort(key=lambda x: x[0], reverse=True)

            # 返回 top N，并更新命中次数
            selected = []
            for _score, rule in scored_rules[:max_rules]:
                rule.hit_count += 1
                selected.append(rule)

            # 保存命中计数更新
            if selected:
                self._save_memory(memory, project_id)

            return selected

    def get_all_rules(self, project_id: Optional[str] = None) -> List[TranslationRule]:
        """获取所有已学习的规则"""
        with self._memory_lock:
            memory = self._load_memory(project_id)
            return list(memory.rules)

    def delete_rule(self, rule_id: str, project_id: Optional[str] = None) -> bool:
        """删除指定规则"""
        with self._memory_lock:
            memory = self._load_memory(project_id)
            original_count = len(memory.rules)
            memory.rules = [r for r in memory.rules if r.id != rule_id]
            if len(memory.rules) < original_count:
                self._save_memory(memory, project_id)
                return True
            return False

    def add_rule_manually(
        self,
        rule: TranslationRule,
        project_id: Optional[str] = None,
    ) -> TranslationRule:
        """手动添加规则"""
        with self._memory_lock:
            memory = self._load_memory(project_id)
            self._deduplicate_and_add(memory, rule)
            self._save_memory(memory, project_id)
            return rule

    # ============ 内部方法 ============

    async def _extract_rules_with_llm(
        self,
        template_name: str,
        **kwargs,
    ) -> List[TranslationRule]:
        """
        使用 LLM 从对比中提取结构化规则

        Args:
            template_name: prompt 模板名称
            **kwargs: 模板变量

        Returns:
            提取的规则列表
        """
        from src.prompts import get_prompt_manager

        pm = get_prompt_manager()
        prompt = pm.get(template_name, **kwargs)

        # 同步 SDK 调用放入线程池，避免阻塞事件循环。
        response = await asyncio.to_thread(self._generate_rules_json, prompt)

        # 解析 JSON 响应
        result = self._parse_json_response(response)

        if not result.get("has_meaningful_change", False):
            return []

        rules = []
        for rule_data in result.get("rules", []):
            try:
                rule = TranslationRule(
                    id=uuid.uuid4().hex[:12],
                    wrong=rule_data["wrong"],
                    right=rule_data["right"],
                    instruction=rule_data["instruction"][:20],
                    rule_type=RuleType(rule_data.get("rule_type", "soft_preference")),
                    category=ErrorCategory(rule_data.get("category", "fluency")),
                    created_at=datetime.now(),
                    confidence=0.5,
                )
                rules.append(rule)
            except (KeyError, ValueError) as e:
                logger.debug("Skipping invalid rule data: %s (%s)", rule_data, e)
                continue

        return rules

    def _generate_rules_json(self, prompt: str) -> str:
        """Thread-safe JSON rule generation."""
        with self._llm_lock:
            return self.llm.generate(prompt, response_format="json", temperature=0.3)

    def _deduplicate_and_add(self, memory: TranslationMemory, new_rule: TranslationRule) -> None:
        """
        去重并添加规则

        相同 wrong+right 的规则合并，增加 confidence
        """
        for existing in memory.rules:
            if existing.wrong == new_rule.wrong and existing.right == new_rule.right:
                # 合并：提升置信度
                existing.confidence = min(existing.confidence + 0.15, 1.0)
                existing.hit_count += 1
                logger.debug("Merged duplicate rule: %s → %s (confidence=%.2f)",
                           existing.wrong, existing.right, existing.confidence)
                return

        # 新规则，直接添加
        memory.rules.append(new_rule)
        memory.last_updated = datetime.now()

    @staticmethod
    def _compute_diff_ratio(text_a: str, text_b: str) -> float:
        """计算两段文本的差异率"""
        if not text_a or not text_b:
            return 1.0
        matcher = difflib.SequenceMatcher(None, text_a, text_b)
        return 1.0 - matcher.ratio()

    def _namespace(self, project_id: Optional[str]) -> str:
        """Resolve storage namespace."""
        if not project_id:
            return "global"
        cleaned = "".join(
            char if (char.isalnum() or char in ("-", "_")) else "_"
            for char in project_id.strip()
        )
        return cleaned or "global"

    def _memory_path(self, project_id: Optional[str]) -> Path:
        """Resolve on-disk memory path for a project namespace."""
        namespace = self._namespace(project_id)
        if namespace == "global":
            return GLOBAL_MEMORY_PATH
        return PROJECT_MEMORY_DIR / f"{namespace}.json"

    def _load_memory(self, project_id: Optional[str] = None) -> TranslationMemory:
        """加载翻译记忆（按项目隔离）。"""
        namespace = self._namespace(project_id)
        cached = self._memory_cache.get(namespace)
        if cached is not None:
            return cached

        memory_path = self._memory_path(project_id)
        if memory_path.exists():
            try:
                with open(memory_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                memory = TranslationMemory.model_validate(data)
            except Exception as e:
                logger.warning("Failed to load memory from %s: %s", memory_path, e)
                memory = TranslationMemory(last_updated=datetime.now())
        else:
            memory = TranslationMemory(last_updated=datetime.now())

        self._memory_cache[namespace] = memory
        return memory

    def _save_memory(
        self,
        memory: TranslationMemory,
        project_id: Optional[str] = None,
    ) -> None:
        """保存翻译记忆（按项目隔离，原子写入）。"""
        namespace = self._namespace(project_id)
        memory.last_updated = datetime.now()
        self._memory_cache[namespace] = memory

        memory_path = self._memory_path(project_id)
        memory_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = memory_path.with_suffix(memory_path.suffix + ".tmp")

        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(
                memory.model_dump(mode="json"),
                f,
                ensure_ascii=False,
                indent=2,
                default=str,
            )

        temp_path.replace(memory_path)

    @staticmethod
    def _parse_json_response(response: str) -> dict:
        """解析 JSON 响应"""
        text = response.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}
