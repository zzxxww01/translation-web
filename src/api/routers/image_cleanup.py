"""
图片段落处理API端点

提供以下功能：
1. 批量清理图片翻译错误
2. 标记图片段落
3. 防止图片段落被再次翻译
4. 获取图片段落统计信息
"""

from typing import List, Dict, Any, Optional
import json
import logging
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel

from src.core.models import ElementType, ParagraphStatus
from ..dependencies import ProjectManagerDep, get_project_manager
from ..middleware import NotFoundException, BadRequestException

router = APIRouter(prefix="/projects", tags=["image-cleanup"])
logger = logging.getLogger(__name__)


class ImageCleanupRequest(BaseModel):
    """图片清理请求"""
    dry_run: bool = False  # 是否为预览模式（不实际修改）
    clean_translations: bool = True  # 是否清理错误翻译
    mark_as_image: bool = True  # 是否标记为图片类型


class ImageCleanupResponse(BaseModel):
    """图片清理响应"""
    project_id: str
    total_image_paragraphs: int
    cleaned_translations: int
    marked_paragraphs: int
    affected_sections: List[Dict[str, Any]]
    dry_run: bool
    timestamp: str


class ImageStatsResponse(BaseModel):
    """图片统计响应"""
    project_id: str
    total_paragraphs: int
    image_paragraphs: int
    image_percentage: float
    sections_with_images: List[Dict[str, Any]]
    error_translations: int


def detect_image_content(source_text: str) -> bool:
    """检测内容是否为图片"""
    source = source_text.strip()

    # Markdown图片语法
    if source.startswith("![") and "](" in source:
        return True

    # HTML img标签
    if source.startswith("<img") and ">" in source:
        return True

    # 图片文件路径模式
    image_patterns = [
        "_files/",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".webp",
        "substackcdn.com/image/",
        "image/fetch/",
    ]

    if any(pattern in source.lower() for pattern in image_patterns):
        return True

    # 纯路径或URL（没有文字内容）
    if len(source.split()) <= 2 and ("/" in source or "http" in source):
        return True

    return False


def detect_image_translation_error(text: str) -> bool:
    """检测是否为图片翻译错误文本"""
    error_patterns = [
        "待翻译内容仅包含图片路径",
        "未检测到具体的英文文本",
        "请提供相应的英文原文",
        "符合SemiAnalysis专业水准的中文译文",
        "This appears to be an image",
        "Cannot translate image",
        "图片路径未检测到",
        "仅包含图片",
        "没有文本内容"
    ]

    return any(pattern in text for pattern in error_patterns)


@router.post("/{project_id}/cleanup-images", response_model=ImageCleanupResponse)
async def cleanup_image_paragraphs(
    project_id: str,
    request: ImageCleanupRequest,
    background_tasks: BackgroundTasks,
    pm: ProjectManagerDep
):
    """
    批量清理项目中的图片段落问题

    功能：
    - 识别并标记图片段落
    - 清理错误的图片翻译
    - 防止图片段落被再次翻译
    - 支持预览模式（dry_run）
    """
    try:
        logger.info(f"[Image Cleanup] 开始处理项目 {project_id}, dry_run={request.dry_run}")

        # 加载项目
        project = pm.get(project_id)
        sections = pm.get_sections(project_id)

        total_image_paragraphs = 0
        cleaned_translations = 0
        marked_paragraphs = 0
        affected_sections = []

        for section in sections:
            section_image_count = 0
            section_cleaned = 0
            section_marked = 0

            for paragraph in section.paragraphs:
                # 检查是否为图片内容
                if detect_image_content(paragraph.source):
                    total_image_paragraphs += 1
                    section_image_count += 1

                    # 标记为图片类型
                    if paragraph.element_type != ElementType.IMAGE:
                        if not request.dry_run and request.mark_as_image:
                            paragraph.element_type = ElementType.IMAGE
                            section_marked += 1
                            marked_paragraphs += 1

                    # 清理错误翻译
                    if paragraph.translations and request.clean_translations:
                        cleaned_translations_for_paragraph = {}

                        for trans_id, translation in paragraph.translations.items():
                            trans_text = translation.text if hasattr(translation, 'text') else str(translation)

                            # 如果是图片翻译错误
                            if detect_image_translation_error(trans_text):
                                if not request.dry_run:
                                    section_cleaned += 1
                                    cleaned_translations += 1
                                    logger.info(f"清理段落 {paragraph.id} 的图片翻译错误")
                                    continue

                            # 保留正常翻译
                            cleaned_translations_for_paragraph[trans_id] = translation

                        # 更新翻译记录
                        if not request.dry_run:
                            paragraph.translations = cleaned_translations_for_paragraph

                            # 如果清理后没有翻译了，重置状态
                            if not paragraph.translations:
                                paragraph.status = ParagraphStatus.PENDING

            # 保存修改的章节
            if not request.dry_run and (section_cleaned > 0 or section_marked > 0):
                pm.save_section(project_id, section)

            # 记录影响的章节
            if section_image_count > 0:
                affected_sections.append({
                    "section_id": section.section_id,
                    "section_title": section.title,
                    "image_paragraphs": section_image_count,
                    "cleaned_translations": section_cleaned,
                    "marked_paragraphs": section_marked
                })

        # 后台任务：更新项目统计和缓存清理
        background_tasks.add_task(
            update_project_after_cleanup,
            project_id,
            total_image_paragraphs,
            cleaned_translations
        )

        result = ImageCleanupResponse(
            project_id=project_id,
            total_image_paragraphs=total_image_paragraphs,
            cleaned_translations=cleaned_translations,
            marked_paragraphs=marked_paragraphs,
            affected_sections=affected_sections,
            dry_run=request.dry_run,
            timestamp=datetime.now().isoformat()
        )

        logger.info(
            f"[Image Cleanup] 完成 - 图片段落: {total_image_paragraphs}, "
            f"清理翻译: {cleaned_translations}, 标记段落: {marked_paragraphs}"
        )

        return result

    except Exception as e:
        logger.error(f"[Image Cleanup] 处理失败: {e}")
        raise BadRequestException(detail=f"图片清理失败: {str(e)}")


@router.get("/{project_id}/image-stats", response_model=ImageStatsResponse)
async def get_image_statistics(
    project_id: str,
    pm: ProjectManagerDep
):
    """
    获取项目的图片段落统计信息

    返回：
    - 总段落数和图片段落数
    - 图片段落百分比
    - 各章节的图片分布
    - 检测到的翻译错误数量
    """
    try:
        # 加载项目数据
        project = pm.get(project_id)
        sections = pm.get_sections(project_id)

        total_paragraphs = 0
        image_paragraphs = 0
        error_translations = 0
        sections_with_images = []

        for section in sections:
            section_total = len(section.paragraphs)
            section_images = 0
            section_errors = 0

            for paragraph in sections.paragraphs:
                total_paragraphs += 1

                # 检查是否为图片内容
                if (paragraph.element_type == ElementType.IMAGE or
                    detect_image_content(paragraph.source)):
                    image_paragraphs += 1
                    section_images += 1

                # 检查翻译错误
                if paragraph.translations:
                    for translation in paragraph.translations.values():
                        trans_text = translation.text if hasattr(translation, 'text') else str(translation)
                        if detect_image_translation_error(trans_text):
                            error_translations += 1
                            section_errors += 1

            if section_images > 0:
                sections_with_images.append({
                    "section_id": section.section_id,
                    "section_title": section.title,
                    "total_paragraphs": section_total,
                    "image_paragraphs": section_images,
                    "error_translations": section_errors,
                    "image_percentage": (section_images / section_total * 100) if section_total > 0 else 0
                })

        image_percentage = (image_paragraphs / total_paragraphs * 100) if total_paragraphs > 0 else 0

        return ImageStatsResponse(
            project_id=project_id,
            total_paragraphs=total_paragraphs,
            image_paragraphs=image_paragraphs,
            image_percentage=round(image_percentage, 2),
            sections_with_images=sections_with_images,
            error_translations=error_translations
        )

    except Exception as e:
        logger.error(f"[Image Stats] 获取统计失败: {e}")
        raise BadRequestException(detail=f"获取图片统计失败: {str(e)}")


@router.post("/{project_id}/prevent-image-translation")
async def prevent_image_translation(
    project_id: str,
    pm: ProjectManagerDep
):
    """
    为项目设置图片翻译预防机制

    功能：
    - 扫描并标记所有图片段落为IMAGE类型
    - 设置项目配置以跳过图片翻译
    - 返回预防效果统计
    """
    try:
        logger.info(f"[Image Prevention] 设置图片翻译预防机制: {project_id}")

        # 加载项目
        project = pm.get(project_id)
        sections = pm.get_sections(project_id)

        marked_count = 0
        processed_sections = 0

        for section in sections:
            section_modified = False

            for paragraph in section.paragraphs:
                # 检查是否为图片内容但未标记
                if (detect_image_content(paragraph.source) and
                    paragraph.element_type != ElementType.IMAGE):

                    # 标记为图片类型
                    paragraph.element_type = ElementType.IMAGE
                    marked_count += 1
                    section_modified = True

                    logger.debug(f"标记段落 {paragraph.id} 为图片类型")

            # 保存修改的章节
            if section_modified:
                pm.save_section(project_id, section)
                processed_sections += 1

        # 更新项目配置
        project_meta_path = Path(pm.projects_path) / project_id / "meta.json"
        if project_meta_path.exists():
            with open(project_meta_path, 'r', encoding='utf-8') as f:
                meta_data = json.load(f)

            # 添加图片翻译预防配置
            if "config" not in meta_data:
                meta_data["config"] = {}

            meta_data["config"]["skip_image_translation"] = True
            meta_data["config"]["image_detection_enabled"] = True
            meta_data["updated_at"] = datetime.now().isoformat()

            with open(project_meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta_data, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"[Image Prevention] 完成 - 标记了 {marked_count} 个图片段落")

        return {
            "project_id": project_id,
            "marked_paragraphs": marked_count,
            "processed_sections": processed_sections,
            "prevention_enabled": True,
            "message": f"已标记 {marked_count} 个图片段落，未来翻译将自动跳过这些内容",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"[Image Prevention] 设置失败: {e}")
        raise BadRequestException(detail=f"设置图片翻译预防失败: {str(e)}")


async def update_project_after_cleanup(
    project_id: str,
    image_count: int,
    cleaned_count: int
):
    """
    清理后的后台更新任务

    Args:
        project_id: 项目ID
        image_count: 图片段落数量
        cleaned_count: 清理的翻译数量
    """
    try:
        logger.info(
            f"[Post-Cleanup] 项目 {project_id} 后续处理: "
            f"图片段落 {image_count} 个, 清理翻译 {cleaned_count} 个"
        )

        # 这里可以添加更多后续处理，比如：
        # - 更新缓存
        # - 发送通知
        # - 记录审计日志

    except Exception as e:
        logger.error(f"[Post-Cleanup] 后续处理失败: {e}")
