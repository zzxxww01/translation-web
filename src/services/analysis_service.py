"""
Analysis Service — perform project and section content analysis via LLM.

Extracted from translate_projects.py router to keep FastAPI endpoints thin.
"""

import json
import os
from typing import Any, Dict

from src.api.utils.json_utils import parse_llm_json_response
from src.api.utils.llm_factory import generate_with_fallback


class AnalysisService:
    """Generate LLM-based analysis for projects and sections."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_project(self, project_id: str) -> Dict[str, Any]:
        """
        Analyze an entire project's source content.

        Returns:
            Dict with keys ``summary``, ``notes``, ``key_terms``.

        Raises:
            FileNotFoundError: if the source file does not exist.
        """
        project_dir = f"projects/{project_id}"
        source_path = f"{project_dir}/source.md"
        if not os.path.exists(source_path):
            raise FileNotFoundError("Source file not found")

        with open(source_path, "r", encoding="utf-8") as file:
            content = file.read()

        preview_content = content[:8000]
        prompt = self._build_project_prompt(preview_content)
        response_text = generate_with_fallback(prompt, task_type="analysis")
        data = parse_llm_json_response(response_text)

        # Persist analysis result
        analysis_path = f"{project_dir}/analysis.json"
        with open(analysis_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

        return data

    def analyze_section(self, project_id: str, section_id: str) -> Dict[str, Any]:
        """
        Analyze a single section's source content.

        Returns:
            Dict with keys ``summary``, ``tips``.

        Raises:
            FileNotFoundError: if the section source file does not exist.
        """
        section_dir = f"projects/{project_id}/sections/{section_id}"
        source_path = f"{section_dir}/source.md"
        if not os.path.exists(source_path):
            raise FileNotFoundError("Section source file not found")

        with open(source_path, "r", encoding="utf-8") as file:
            content = file.read()

        prompt = self._build_section_prompt(content[:5000])
        response_text = generate_with_fallback(prompt, task_type="analysis")
        data = parse_llm_json_response(response_text)

        # Persist analysis result
        analysis_path = f"{section_dir}/analysis.json"
        with open(analysis_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

        return data

    # ------------------------------------------------------------------
    # Prompt builders (private)
    # ------------------------------------------------------------------

    @staticmethod
    def _build_project_prompt(preview_content: str) -> str:
        return f"""You are a senior technical editor. Analyze the following article content and provide a translation guide.

## Content Preview
{preview_content}

## Task
1. **Summary**: A concise abstract of the article (in Chinese).
2. **Translation Notes**: 3-5 bullet points on tone, audience, or potential translation pitfalls (in Chinese).
3. **Key Terms**: Extract 5-10 key technical terms that need consistent translation (keep English).

## Output Format (Strict JSON)
{{
    "summary": "文章摘要...",
    "notes": ["注意...", "语气..."],
    "key_terms": ["Wafer", "Lithography"]
}}
"""

    @staticmethod
    def _build_section_prompt(content: str) -> str:
        return f"""You are a technical translator. Analyze the following section content.

## Section Content
{content}

## Task
1. **Summary**: A very concise summary of this section (in Chinese, 2-3 sentences).
2. **Translation Tips**: 2-3 specific tips for translating this section (e.g., specific terms, complex sentence structure).

## Output Format (Strict JSON)
{{
    "summary": "本章主要讨论...",
    "tips": ["注意...", "处理..."]
}}
"""
