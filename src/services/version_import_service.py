"""
参考译文导入和对齐服务

功能:
1. 解析markdown参考译文
2. 自动对齐参考译文与原文段落
3. 提供手动对齐功能
"""

from typing import List, Dict, Optional
from difflib import SequenceMatcher
import re

from src.core.models import ProjectMeta, TranslationVersion
from src.core.project import ProjectManager


class VersionImportService:
    """参考译文导入和对齐服务"""

    def __init__(self, project_manager: ProjectManager):
        self.project_manager = project_manager

    def _load_project_with_sections(self, project_id: str) -> ProjectMeta:
        """加载项目并附带章节数据。"""
        project = self.project_manager.get(project_id)
        project.sections = self.project_manager.get_sections(project_id)
        return project

    def _find_version(self, project: ProjectMeta, version_id: str) -> TranslationVersion:
        """从项目中查找指定译文版本。"""
        for version in project.versions:
            if version.id == version_id:
                return version
        raise ValueError(f"Version {version_id} not found")

    def _get_unaligned_items(self, version: TranslationVersion) -> List[Dict]:
        """获取版本元数据中的未对齐条目。"""
        metadata = version.metadata
        if not metadata or "unaligned_items" not in metadata:
            raise ValueError("No unaligned items found")

        unaligned_items = metadata["unaligned_items"]
        if not isinstance(unaligned_items, list):
            raise ValueError("No unaligned items found")

        return unaligned_items

    def _validate_ref_index(self, ref_index: int, unaligned_items: List[Dict]) -> None:
        """验证未对齐索引范围。"""
        if ref_index < 0 or ref_index >= len(unaligned_items):
            raise ValueError(f"ref_index {ref_index} out of range")

    def _update_alignment_counters(self, version: TranslationVersion) -> None:
        """同步更新对齐统计字段。"""
        if version.metadata is None:
            version.metadata = {}

        unaligned_items = version.metadata.get("unaligned_items", [])
        version.metadata["aligned_count"] = len(
            [text for text in version.paragraphs.values() if text is not None]
        )
        version.metadata["unaligned_count"] = len(unaligned_items)

    async def import_reference_translation(
        self,
        project_id: str,
        markdown_content: str,
        version_name: str
    ) -> TranslationVersion:
        """
        导入并解析参考译文

        流程:
        1. 解析markdown为段落列表
        2. 加载项目原文段落
        3. 自动匹配对齐
        4. 返回对齐结果

        Args:
            project_id: 项目ID
            markdown_content: markdown格式的参考译文
            version_name: 版本名称，如 "网友翻译v1.0"

        Returns:
            TranslationVersion: 导入的版本对象
        """
        # 解析markdown
        ref_paragraphs = self._parse_markdown(markdown_content)

        # 加载项目
        project = self._load_project_with_sections(project_id)
        source_paragraphs = self._get_all_source_paragraphs(project)

        # 自动对齐
        aligned = self._auto_align(ref_paragraphs, source_paragraphs)

        # 检查未对齐的段落
        unaligned = self._find_unaligned(aligned, ref_paragraphs, source_paragraphs)

        # 创建版本对象
        version = TranslationVersion(
            id=f"ref_{version_name.replace(' ', '_').lower()}",
            name=version_name,
            source_type="imported",
            paragraphs=aligned,
            metadata={
                "unaligned_count": len(unaligned),
                "unaligned_items": unaligned,
                "total_ref_paragraphs": len(ref_paragraphs),
                "aligned_count": len([v for v in aligned.values() if v is not None])
            }
        )

        return version

    def _parse_markdown(self, content: str) -> List[Dict[str, str]]:
        """
        解析markdown内容为段落列表

        保留段落类型（h1, h2, h3, p等）以便更好地对齐

        Args:
            content: markdown内容

        Returns:
            List of dicts with 'text' and 'type' keys
        """
        lines = content.split('\n')
        paragraphs = []
        current_paragraph = []
        current_type = "p"

        for line in lines:
            stripped = line.strip()

            # 空行 - 结束当前段落
            if not stripped:
                if current_paragraph:
                    paragraphs.append({
                        'text': ' '.join(current_paragraph),
                        'type': current_type
                    })
                    current_paragraph = []
                    current_type = "p"
                continue

            # 标题行
            if stripped.startswith('#'):
                # 保存之前的段落
                if current_paragraph:
                    paragraphs.append({
                        'text': ' '.join(current_paragraph),
                        'type': current_type
                    })
                    current_paragraph = []

                # 提取标题级别
                match = re.match(r'^(#{1,6})\s+(.*)$', stripped)
                if match:
                    level = len(match.group(1))
                    current_type = f"h{level}"
                    current_paragraph = [match.group(2)]
                    continue

            # 普通文本行
            current_paragraph.append(stripped)

        # 保存最后一个段落
        if current_paragraph:
            paragraphs.append({
                'text': ' '.join(current_paragraph),
                'type': current_type
            })

        return paragraphs

    def _get_all_source_paragraphs(
        self,
        project: ProjectMeta
    ) -> List[Dict]:
        """
        获取项目所有原文段落

        Args:
            project: 项目元信息

        Returns:
            List of dicts with 'id', 'index', 'source', 'element_type' keys
        """
        paragraphs = []

        for section in project.sections:
            for para in section.paragraphs:
                paragraphs.append({
                    'id': para.id,
                    'index': len(paragraphs),
                    'source': para.source,
                    'element_type': para.element_type.value
                })

        return paragraphs

    def _auto_align(
        self,
        ref_paragraphs: List[Dict[str, str]],
        source_paragraphs: List[Dict]
    ) -> Dict[str, Optional[str]]:
        """
        自动对齐参考译文和原文段落

        策略:
        1. 使用文本相似度匹配（考虑英文原文和中文译文）
        2. 优先匹配段落类型（h1-h1, h2-h2等）
        3. 使用贪婪算法确保一一对应
        4. 返回段落ID到译文的映射

        Args:
            ref_paragraphs: 参考译文段落列表
            source_paragraphs: 原文段落列表

        Returns:
            Dict mapping paragraph_id to translation text
        """
        alignment: Dict[str, Optional[str]] = {}
        used_sources = set()

        for ref_para in ref_paragraphs:
            best_match = None
            best_similarity = 0.0

            for source_para in source_paragraphs:
                if source_para['id'] in used_sources:
                    continue

                # 优先匹配相同类型的段落
                if ref_para['type'] != source_para['element_type']:
                    # 如果类型不匹配，降低相似度权重
                    similarity = self._calculate_similarity(
                        ref_para['text'],
                        source_para['source']
                    ) * 0.7
                else:
                    similarity = self._calculate_similarity(
                        ref_para['text'],
                        source_para['source']
                    )

                # 相似度阈值（30%）
                if similarity > best_similarity and similarity > 0.3:
                    best_similarity = similarity
                    best_match = source_para

            if best_match:
                alignment[best_match['id']] = ref_para['text']
                used_sources.add(best_match['id'])

        # 为未匹配的原文段落填充None
        for source_para in source_paragraphs:
            if source_para['id'] not in alignment:
                alignment[source_para['id']] = None

        return alignment

    def _calculate_similarity(
        self,
        text1: str,
        text2: str
    ) -> float:
        """
        计算两个文本的相似度

        使用SequenceMatcher的ratio()方法，基于最长公共子序列

        Args:
            text1: 文本1
            text2: 文本2

        Returns:
            float: 相似度 (0.0 - 1.0)
        """
        # 对于跨语言文本（英文原文 vs 中文译文），
        # 我们主要依赖数字、专有名词等共同特征
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    def _find_unaligned(
        self,
        alignment: Dict[str, Optional[str]],
        ref_paragraphs: List[Dict[str, str]],
        source_paragraphs: List[Dict]
    ) -> List[Dict]:
        """
        找出未对齐的参考段落

        Args:
            alignment: 对齐结果
            ref_paragraphs: 参考译文段落列表
            source_paragraphs: 原文段落列表

        Returns:
            List of unaligned items with recommendations
        """
        unaligned = []

        # 建立 text -> [indices] 映射，支持重复文本
        text_to_indices: Dict[str, List[int]] = {}
        for index, ref_para in enumerate(ref_paragraphs):
            text = ref_para["text"]
            if text not in text_to_indices:
                text_to_indices[text] = []
            text_to_indices[text].append(index)

        # 找出所有已匹配的参考段落索引
        aligned_indices = set()
        for _para_id, translation in alignment.items():
            if translation is not None:
                indices = text_to_indices.get(translation, [])
                if indices:
                    aligned_indices.add(indices.pop(0))

        # 为未对齐的参考段落创建条目
        for i, ref_para in enumerate(ref_paragraphs):
            if i not in aligned_indices:
                recommendations = self._get_recommendations(
                    ref_para['text'],
                    source_paragraphs,
                    alignment
                )

                unaligned.append({
                    'ref_index': i,
                    'ref_text': ref_para['text'],
                    'ref_type': ref_para['type'],
                    'recommendations': recommendations
                })

        return unaligned

    def _get_recommendations(
        self,
        ref_text: str,
        source_paragraphs: List[Dict],
        alignment: Dict[str, Optional[str]]
    ) -> List[Dict]:
        """
        获取相似度推荐

        为未对齐的参考段落推荐可能的原文段落

        Args:
            ref_text: 参考译文文本
            source_paragraphs: 原文段落列表
            alignment: 当前对齐结果

        Returns:
            List of recommended source paragraphs with similarity scores
        """
        recommendations = []

        # 找出所有未使用的原文段落
        unused_sources = [
            sp for sp in source_paragraphs
            if alignment.get(sp['id']) is None
        ]

        # 计算相似度
        for source_para in unused_sources:
            similarity = self._calculate_similarity(ref_text, source_para['source'])
            if similarity > 0.2:  # 最低阈值
                recommendations.append({
                    'paragraph_id': source_para['id'],
                    'source_preview': source_para['source'][:100] + '...' if len(source_para['source']) > 100 else source_para['source'],
                    'similarity': round(similarity * 100, 1),
                    'element_type': source_para['element_type']
                })

        # 按相似度排序
        recommendations.sort(key=lambda x: x['similarity'], reverse=True)

        # 返回Top 5推荐
        return recommendations[:5]

    async def manual_align(
        self,
        project_id: str,
        version_id: str,
        ref_index: int,
        target_paragraph_id: str
    ) -> Dict:
        """
        手动对齐单个参考段落

        Args:
            project_id: 项目ID
            version_id: 版本ID
            ref_index: 参考段落索引
            target_paragraph_id: 目标段落ID

        Returns:
            Updated alignment info
        """
        project = self._load_project_with_sections(project_id)
        version = self._find_version(project, version_id)
        unaligned_items = self._get_unaligned_items(version)
        self._validate_ref_index(ref_index, unaligned_items)

        if target_paragraph_id not in version.paragraphs:
            raise ValueError(f"Target paragraph {target_paragraph_id} not found")

        unaligned_item = unaligned_items[ref_index]
        ref_text = unaligned_item.get("ref_text")
        if not isinstance(ref_text, str) or not ref_text.strip():
            raise ValueError("Invalid unaligned item: missing ref_text")

        # 更新对齐
        version.paragraphs[target_paragraph_id] = ref_text

        # 从未对齐列表中移除
        unaligned_items.pop(ref_index)
        self._update_alignment_counters(version)

        # 保存项目
        self.project_manager.save_meta(project)

        return {
            'version_id': version_id,
            'paragraph_id': target_paragraph_id,
            'aligned_count': version.metadata["aligned_count"],
            'unaligned_count': version.metadata["unaligned_count"]
        }

    async def skip_unaligned(
        self,
        project_id: str,
        version_id: str,
        ref_index: int
    ) -> Dict:
        """
        跳过未对齐的参考段落

        Args:
            project_id: 项目ID
            version_id: 版本ID
            ref_index: 参考段落索引

        Returns:
            Updated alignment info
        """
        project = self._load_project_with_sections(project_id)
        version = self._find_version(project, version_id)
        unaligned_items = self._get_unaligned_items(version)
        self._validate_ref_index(ref_index, unaligned_items)

        # 从未对齐列表中移除
        unaligned_items.pop(ref_index)
        self._update_alignment_counters(version)

        # 保存项目
        self.project_manager.save_meta(project)

        return {
            'version_id': version_id,
            'unaligned_count': version.metadata["unaligned_count"]
        }
