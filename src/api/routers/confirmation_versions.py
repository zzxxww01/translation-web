"""
Confirmation reference-version endpoints.
"""

from fastapi import APIRouter

from ..dependencies import ProjectManagerDep, VersionServiceDep
from ..middleware import NotFoundException, BadRequestException
from .confirmation_models import ImportVersionRequest, ManualAlignRequest


router = APIRouter()


@router.post("/{project_id}/import-version")
async def import_reference_version(
    project_id: str,
    request: ImportVersionRequest,
    pm: ProjectManagerDep,
    service: VersionServiceDep,
):
    try:
        version = await service.import_reference_translation(
            project_id,
            request.markdown_content,
            request.version_name,
        )

        project = pm.get(project_id)
        project.versions.append(version)
        pm.save_meta(project)

        return {
            "version_id": version.id,
            "name": version.name,
            "aligned_count": version.metadata.get("aligned_count", 0),
            "unaligned_count": version.metadata.get("unaligned_count", 0),
            "unaligned_items": version.metadata.get("unaligned_items", []),
        }

    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")
    except ValueError as e:
        raise BadRequestException(detail=str(e))
    except Exception as e:
        raise BadRequestException(detail=f"Failed to import: {str(e)}")


@router.post("/{project_id}/versions/{version_id}/align")
async def manual_align(
    project_id: str,
    version_id: str,
    request: ManualAlignRequest,
    service: VersionServiceDep,
):
    try:
        return await service.manual_align(
            project_id,
            version_id,
            request.ref_index,
            request.target_paragraph_id,
        )
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")
    except ValueError as e:
        raise BadRequestException(detail=str(e))
    except Exception as e:
        raise BadRequestException(detail=f"Failed to align: {str(e)}")


@router.post("/{project_id}/versions/{version_id}/skip")
async def skip_unaligned(
    project_id: str,
    version_id: str,
    ref_index: int,
    service: VersionServiceDep,
):
    try:
        return await service.skip_unaligned(
            project_id,
            version_id,
            ref_index,
        )
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")
    except ValueError as e:
        raise BadRequestException(detail=str(e))
    except Exception as e:
        raise BadRequestException(detail=f"Failed to skip: {str(e)}")


@router.get("/{project_id}/versions")
async def list_versions(
    project_id: str,
    pm: ProjectManagerDep,
):
    try:
        project = pm.get(project_id)
        return {
            "versions": [
                {
                    "id": v.id,
                    "name": v.name,
                    "source_type": v.source_type,
                    "created_at": v.created_at.isoformat(),
                    "metadata": v.metadata,
                }
                for v in project.versions
            ]
        }
    except FileNotFoundError:
        raise NotFoundException(detail="Project not found")
