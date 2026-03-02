"""
Dependencies - 依赖注入模块

使用 FastAPI 的依赖注入系统管理共享资源。
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from src.config import settings
from src.core.conversation import ConversationManager
from src.core.project import ProjectManager
from src.core.glossary import GlossaryManager
from src.llm.gemini import GeminiProvider
from src.services.confirmation_service import ConfirmationService
from src.services.batch_translation_service import BatchTranslationService
from src.services.version_import_service import VersionImportService


# ============ 管理器依赖（单例） ============

@lru_cache(maxsize=1)
def get_project_manager() -> ProjectManager:
    """获取 ProjectManager 实例（单例）"""
    return ProjectManager(projects_path=settings.projects_path)


@lru_cache(maxsize=1)
def get_glossary_manager() -> GlossaryManager:
    """获取 GlossaryManager 实例（单例）"""
    return GlossaryManager(projects_path=settings.projects_path)


@lru_cache(maxsize=1)
def get_conversation_manager() -> ConversationManager:
    """获取 ConversationManager 实例（单例）"""
    return ConversationManager(base_path=settings.conversations_path)


# ============ LLM Provider 依赖 ============

def get_llm_provider() -> GeminiProvider:
    """获取 LLM Provider（单例，通过 lru_cache 的 get_gemini_provider）"""
    from src.api.utils.llm_factory import get_gemini_provider
    try:
        return get_gemini_provider()
    except ValueError as e:
        from src.api.middleware import BadRequestException
        raise BadRequestException(detail=str(e))


# ============ 服务依赖 ============

def get_confirmation_service(
    pm: ProjectManager = Depends(get_project_manager),
    gm: GlossaryManager = Depends(get_glossary_manager)
) -> ConfirmationService:
    """获取 ConfirmationService 实例"""
    return ConfirmationService(
        project_manager=pm,
        glossary_manager=gm
    )


def get_batch_service(
    pm: ProjectManager = Depends(get_project_manager)
) -> BatchTranslationService:
    """获取 BatchTranslationService 实例"""
    from src.api.utils.llm_factory import get_gemini_provider

    try:
        llm = get_gemini_provider()
    except ValueError as e:
        from src.api.middleware import BadRequestException
        raise BadRequestException(detail=str(e))
    return BatchTranslationService(
        llm_provider=llm,
        project_manager=pm
    )


def get_version_service(
    pm: ProjectManager = Depends(get_project_manager)
) -> VersionImportService:
    """获取 VersionImportService 实例"""
    return VersionImportService(project_manager=pm)


# ============ 类型别名 ============

ProjectManagerDep = Annotated[ProjectManager, Depends(get_project_manager)]
GlossaryManagerDep = Annotated[GlossaryManager, Depends(get_glossary_manager)]
ConversationManagerDep = Annotated[ConversationManager, Depends(get_conversation_manager)]
LLMProviderDep = Annotated[GeminiProvider, Depends(get_llm_provider)]
ConfirmationServiceDep = Annotated[ConfirmationService, Depends(get_confirmation_service)]
BatchServiceDep = Annotated[BatchTranslationService, Depends(get_batch_service)]
VersionServiceDep = Annotated[VersionImportService, Depends(get_version_service)]
