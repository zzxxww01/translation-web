"""
Data Loader - 数据加载模块

从文件系统或数据库加载项目数据
"""

from typing import List, Optional
import json
from pathlib import Path

from ..core.models import Section, Glossary, Paragraph, ProjectMeta


class DataLoader:
    """数据加载器"""

    def __init__(self, base_dir: str = "projects"):
        self.base_dir = base_dir

    def load_project_sections(self, project_id: str) -> List[Section]:
        """
        加载项目章节

        Args:
            project_id: 项目ID

        Returns:
            章节列表
        """
        project_dir = Path(self.base_dir) / project_id
        sections_file = project_dir / "sections.json"

        if not sections_file.exists():
            return []

        with open(sections_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            sections = [Section(**s) for s in data]
            return sections

    def save_project_sections(self, project_id: str, sections: List[Section]) -> None:
        """
        保存项目章节

        Args:
            project_id: 项目ID
            sections: 章节列表
        """
        project_dir = Path(self.base_dir) / project_id
        project_dir.mkdir(parents=True, exist_ok=True)

        sections_file = project_dir / "sections.json"

        with open(sections_file, "w", encoding="utf-8") as f:
            data = [s.model_dump(mode="json") for s in sections]
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_project_glossary(self, project_id: str) -> Optional[Glossary]:
        """
        加载项目术语表

        Args:
            project_id: 项目ID

        Returns:
            术语表或None
        """
        project_dir = Path(self.base_dir) / project_id
        glossary_file = project_dir / "glossary.json"

        if not glossary_file.exists():
            return None

        try:
            with open(glossary_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return Glossary(**data)
        except Exception:
            return None

    def save_project_glossary(self, project_id: str, glossary: Glossary) -> None:
        """保存项目术语表"""
        project_dir = Path(self.base_dir) / project_id
        project_dir.mkdir(parents=True, exist_ok=True)

        glossary_file = project_dir / "glossary.json"

        with open(glossary_file, "w", encoding="utf-8") as f:
            json.dump(glossary.model_dump(mode="json"), f, ensure_ascii=False, indent=2)

    def load_project_meta(self, project_id: str) -> Optional[ProjectMeta]:
        """加载项目元信息"""
        project_dir = Path(self.base_dir) / project_id
        meta_file = project_dir / "meta.json"

        if not meta_file.exists():
            return None

        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return ProjectMeta(**data)
        except Exception:
            return None

    def save_project_meta(self, project_id: str, meta: ProjectMeta) -> None:
        """保存项目元信息"""
        project_dir = Path(self.base_dir) / project_id
        project_dir.mkdir(parents=True, exist_ok=True)

        meta_file = project_dir / "meta.json"

        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta.model_dump(mode="json"), f, ensure_ascii=False, indent=2)

    def load_paragraph(self, project_id: str, paragraph_id: str) -> Optional[Paragraph]:
        """加载单个段落"""
        sections = self.load_project_sections(project_id)

        for section in sections:
            for paragraph in section.paragraphs:
                if paragraph.id == paragraph_id:
                    return paragraph

        return None

    def save_paragraph(self, project_id: str, paragraph: Paragraph) -> None:
        """保存单个段落（更新对应的section）"""
        sections = self.load_project_sections(project_id)

        for section in sections:
            for i, p in enumerate(section.paragraphs):
                if p.id == paragraph.id:
                    section.paragraphs[i] = paragraph
                    break

        self.save_project_sections(project_id, sections)


# 全局实例
_data_loader = DataLoader()


# 辅助函数
def load_sections(project_id: str) -> List[Section]:
    """快捷函数：加载章节"""
    return _data_loader.load_project_sections(project_id)


def save_sections(project_id: str, sections: List[Section]) -> None:
    """快捷函数：保存章节"""
    _data_loader.save_project_sections(project_id, sections)


def load_glossary(project_id: str) -> Optional[Glossary]:
    """快捷函数：加载术语表"""
    return _data_loader.load_project_glossary(project_id)


def save_glossary(project_id: str, glossary: Glossary) -> None:
    """快捷函数：保存术语表"""
    _data_loader.save_project_glossary(project_id, glossary)
