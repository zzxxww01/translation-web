"""Dependency injection helpers."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from src.settings import settings
from src.core.glossary import GlossaryManager
from src.core.project import ProjectManager
from src.llm.base import LLMProvider
from src.llm.factory import get_task_model_alias
from src.services.batch_translation_service import BatchTranslationService
from src.services.confirmation_service import ConfirmationService
from src.services.memory_service import TranslationMemoryService
from src.services.version_import_service import VersionImportService


@lru_cache(maxsize=1)
def get_project_manager() -> ProjectManager:
    """Return the singleton project manager."""
    return ProjectManager(projects_path=settings.projects_path)


@lru_cache(maxsize=1)
def get_glossary_manager() -> GlossaryManager:
    """Return the singleton glossary manager."""
    return GlossaryManager(projects_path=settings.projects_path)


def get_llm_provider() -> LLMProvider:
    """Return the configured LLM provider."""
    from src.api.middleware import BadRequestException
    from src.api.utils.llm_factory import get_llm_provider as get_cached_llm_provider

    try:
        return get_cached_llm_provider()
    except ValueError as exc:
        raise BadRequestException(detail=str(exc)) from exc


def get_task_llm_provider(task_type: str) -> LLMProvider:
    """Return the LLM provider configured for a specific task type."""
    from src.api.middleware import BadRequestException
    from src.api.utils.llm_factory import get_llm_provider as get_cached_llm_provider

    try:
        model_alias = get_task_model_alias(task_type)
        return get_cached_llm_provider(model_alias)
    except ValueError as exc:
        raise BadRequestException(detail=str(exc)) from exc


def get_longform_llm_provider() -> LLMProvider:
    """Return the default LLM provider for long-form translation flows."""
    return get_task_llm_provider("longform")


def get_analysis_llm_provider() -> LLMProvider:
    """Return the default LLM provider for analysis flows."""
    return get_task_llm_provider("analysis")


def get_term_review_llm_provider() -> LLMProvider:
    """Return the LLM provider for terminology pre-review."""
    return get_task_llm_provider("term_review")


def get_confirmation_service(
    pm: ProjectManager = Depends(get_project_manager),
    gm: GlossaryManager = Depends(get_glossary_manager),
) -> ConfirmationService:
    """Return the confirmation service."""
    return ConfirmationService(project_manager=pm, glossary_manager=gm)


@lru_cache(maxsize=1)
def get_batch_service() -> BatchTranslationService:
    """Return the batch translation service."""
    from src.api.middleware import BadRequestException

    try:
        llm = get_longform_llm_provider()
        analysis_llm = get_analysis_llm_provider()
    except ValueError as exc:
        raise BadRequestException(detail=str(exc)) from exc

    pm = get_project_manager()
    return BatchTranslationService(
        llm_provider=llm,
        project_manager=pm,
        analysis_llm_provider=analysis_llm,
        user_model_override=None,  # 默认无覆盖，使用阶段化配置
    )


def get_version_service(
    pm: ProjectManager = Depends(get_project_manager),
) -> VersionImportService:
    """Return the version import service."""
    return VersionImportService(project_manager=pm)


@lru_cache(maxsize=1)
def get_memory_service() -> TranslationMemoryService:
    """Return the singleton translation memory service."""
    return TranslationMemoryService()


ProjectManagerDep = Annotated[ProjectManager, Depends(get_project_manager)]
GlossaryManagerDep = Annotated[GlossaryManager, Depends(get_glossary_manager)]
LLMProviderDep = Annotated[LLMProvider, Depends(get_llm_provider)]
LongformLLMProviderDep = Annotated[LLMProvider, Depends(get_longform_llm_provider)]
AnalysisLLMProviderDep = Annotated[LLMProvider, Depends(get_analysis_llm_provider)]
TermReviewLLMProviderDep = Annotated[LLMProvider, Depends(get_term_review_llm_provider)]
ConfirmationServiceDep = Annotated[ConfirmationService, Depends(get_confirmation_service)]
BatchServiceDep = Annotated[BatchTranslationService, Depends(get_batch_service)]
VersionServiceDep = Annotated[VersionImportService, Depends(get_version_service)]
MemoryServiceDep = Annotated[TranslationMemoryService, Depends(get_memory_service)]
