"""
术语提取服务

从源文档中提取候选术语（Phase 0）。
"""

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from src.models.terminology import Term
from src.services.glossary_storage import GlossaryStorage
from src.services.term_matcher.matcher import TermMatcher


@dataclass
class TermCandidate:
    """候选术语"""
    original: str
    suggested_translation: str
    confidence: float  # 0.0-1.0
    context: str  # 首次出现的上下文
    occurrence_count: int
    hit_title: bool  # 是否出现在标题中
    sections: List[str]  # 出现在哪些章节


class TermExtractionService:
    """术语提取服务"""

    def __init__(self, llm_provider, storage: GlossaryStorage):
        """
        初始化服务

        Args:
            llm_provider: LLM 提供者（需要有 generate 方法）
            storage: 术语存储服务
        """
        self.llm = llm_provider
        self.storage = storage

    async def extract_all(self, project_id: str) -> List[TermCandidate]:
        """
        提取项目中的所有候选术语（Phase 0）

        Args:
            project_id: 项目 ID

        Returns:
            候选术语列表，按重要性排序
        """
        # 1. 加载项目元数据
        project = self._load_project(project_id)

        # 2. 收集所有文本
        all_text = self._collect_text(project)

        # 3. 调用 LLM 提取术语
        prompt = self._build_extraction_prompt(all_text, project)
        response = await self.llm.generate(prompt)
        raw_candidates = self._parse_extraction_response(response)

        # 4. 使用 TermMatcher 统计出现次数
        existing_terms = self.storage.load_terms("project", project_id)
        matcher = TermMatcher(existing_terms) if existing_terms else None

        candidates = []
        for raw in raw_candidates:
            # 统计出现次数
            count = self._count_occurrences(raw["original"], all_text)

            # 检查是否在标题中
            hit_title = self._check_title_hit(raw["original"], project)

            # 找出出现的章节
            sections = self._find_sections(raw["original"], project)

            candidates.append(TermCandidate(
                original=raw["original"],
                suggested_translation=raw["translation"],
                confidence=raw.get("confidence", 0.8),
                context=raw["context"],
                occurrence_count=count,
                hit_title=hit_title,
                sections=sections
            ))

        # 5. 按重要性排序（标题 > 出现次数 > 置信度）
        candidates.sort(key=lambda c: (
            -int(c.hit_title),
            -c.occurrence_count,
            -c.confidence
        ))

        # 6. 保存提取结果
        self._save_extraction_result(project_id, candidates)

        return candidates

    def _load_project(self, project_id: str) -> dict:
        """
        加载项目元数据

        Args:
            project_id: 项目 ID

        Returns:
            项目元数据字典
        """
        project_path = self.storage.base_path / "projects" / project_id / "meta.json"
        if not project_path.exists():
            raise FileNotFoundError(f"Project metadata not found: {project_path}")

        return json.loads(project_path.read_text(encoding='utf-8'))

    def _collect_text(self, project: dict) -> str:
        """
        收集项目所有文本

        Args:
            project: 项目元数据

        Returns:
            合并后的文本
        """
        texts = []

        # 标题
        texts.append(f"# {project['title']}")

        # 各章节
        for section in project['sections']:
            source_path = Path(section['source_path'])
            if source_path.exists():
                texts.append(source_path.read_text(encoding='utf-8'))

        return "\n\n".join(texts)

    def _build_extraction_prompt(self, text: str, project: dict) -> str:
        """
        构建提取 prompt

        Args:
            text: 文档文本
            project: 项目元数据

        Returns:
            提取 prompt
        """
        return f"""
你是一个专业的术语提取专家。请从以下技术文档中提取所有重要的专业术语。

文档主题：{project['title']}
文档领域：半导体、芯片、存储技术

要求：
1. 提取所有专业术语（技术名词、产品名、公司名、缩写）
2. 为每个术语提供准确的中文翻译
3. 提供术语首次出现的上下文（前后各 20 字符）
4. 评估翻译置信度（0.0-1.0）

输出格式（JSON）：
[
  {{
    "original": "HBM",
    "translation": "高带宽内存",
    "confidence": 0.95,
    "context": "...using HBM memory for..."
  }},
  ...
]

文档内容：
{text[:10000]}
"""

    def _parse_extraction_response(self, response: str) -> List[dict]:
        """
        解析 LLM 响应

        Args:
            response: LLM 响应文本

        Returns:
            术语字典列表
        """
        try:
            # 尝试直接解析 JSON
            return json.loads(response)
        except json.JSONDecodeError:
            # 如果失败，尝试提取 JSON 块
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return []

    def _count_occurrences(self, term: str, text: str) -> int:
        """
        统计术语出现次数

        Args:
            term: 术语
            text: 文本

        Returns:
            出现次数
        """
        # 简单的大小写不敏感计数
        return text.lower().count(term.lower())

    def _check_title_hit(self, term: str, project: dict) -> bool:
        """
        检查术语是否在标题中

        Args:
            term: 术语
            project: 项目元数据

        Returns:
            是否在标题中
        """
        title = project['title'].lower()
        return term.lower() in title

    def _find_sections(self, term: str, project: dict) -> List[str]:
        """
        找出术语出现的章节

        Args:
            term: 术语
            project: 项目元数据

        Returns:
            章节 ID 列表
        """
        sections = []
        for section in project['sections']:
            source_path = Path(section['source_path'])
            if source_path.exists():
                text = source_path.read_text(encoding='utf-8')
                if term.lower() in text.lower():
                    sections.append(section['id'])
        return sections

    def _save_extraction_result(self, project_id: str, candidates: List[TermCandidate]):
        """
        保存提取结果

        Args:
            project_id: 项目 ID
            candidates: 候选术语列表
        """
        output_path = self.storage.base_path / "projects" / project_id / "artifacts" / "term-extraction" / "latest.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = [asdict(c) for c in candidates]
        output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
