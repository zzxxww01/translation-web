import asyncio
from types import SimpleNamespace

import pytest
from starlette.requests import Request

from src.api.routers import confirmation_translation
from src.api.routers.translate_models import LongformWorkflowStartRequest
from src.services.terminology_review_job_service import TerminologyReviewJobStore
from src.services.terminology_review_service import TerminologyReviewService


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/projects/demo/translation-workflow",
            "headers": [],
            "client": ("127.0.0.1", 50000),
        }
    )


@pytest.mark.asyncio
async def test_start_workflow_returns_while_server_task_keeps_ownership(
    monkeypatch,
):
    allow_finish = asyncio.Event()
    started = asyncio.Event()
    active_updates = []

    class WorkflowService:
        project_manager = SimpleNamespace(
            get=lambda _project_id: object(),
            glossary_manager=object(),
        )
        llm = object()

        async def claim_translation_slot(self, project_id):
            return {
                "status": "acquired",
                "project_id": project_id,
                "run_id": None,
                "lease_id": "lease-1",
            }

        def _set_active_run(self, project_id, **kwargs):
            active_updates.append((project_id, kwargs))

        def _release_active_run(self, *_args, **_kwargs):
            pass

    async def fake_ensure_job(**_kwargs):
        return {"job_id": "a" * 32}

    async def fake_run_workflow(**_kwargs):
        started.set()
        await allow_finish.wait()

    base_service = SimpleNamespace(
        project_manager=SimpleNamespace(get=lambda _project_id: object())
    )
    monkeypatch.setattr(
        confirmation_translation,
        "_build_longform_service",
        lambda _base, _body: WorkflowService(),
    )
    monkeypatch.setattr(
        confirmation_translation,
        "inspect_translation_resume",
        lambda *_args: SimpleNamespace(resumable=False),
    )
    monkeypatch.setattr(
        confirmation_translation,
        "ensure_term_review_job",
        fake_ensure_job,
    )
    monkeypatch.setattr(
        confirmation_translation,
        "_run_longform_workflow",
        fake_run_workflow,
    )

    response = await confirmation_translation.start_longform_workflow(
        _request(),
        "demo",
        base_service,
        LongformWorkflowStartRequest(method="four-step"),
    )

    assert response["status"] == "started"
    assert response["term_review_job_id"] == "a" * 32
    assert response["term_review_timeout_seconds"] == (
        confirmation_translation.settings.term_review_confirmation_timeout_seconds
    )
    assert response["resumed"] is False
    assert response["resume_checkpoint"] is None
    assert active_updates == [
        (
            "demo",
            {
                "run_id": "a" * 32,
                "status": "starting",
                "current_step": "术语预检中",
            },
        )
    ]
    assert await asyncio.wait_for(started.wait(), timeout=1)
    assert confirmation_translation._longform_workflow_tasks

    allow_finish.set()
    for _ in range(100):
        if not confirmation_translation._longform_workflow_tasks:
            break
        await asyncio.sleep(0.01)
    assert not confirmation_translation._longform_workflow_tasks


@pytest.mark.asyncio
async def test_start_workflow_resumes_persisted_checkpoint_without_term_review(
    monkeypatch,
):
    allow_finish = asyncio.Event()
    started = asyncio.Event()
    active_updates = []
    checkpoint = SimpleNamespace(
        resumable=True,
        translated_paragraphs=70,
        total_paragraphs=75,
        to_dict=lambda: {
            "resumable": True,
            "translated_paragraphs": 70,
            "total_paragraphs": 75,
            "remaining_paragraphs": 5,
        },
    )

    class WorkflowService:
        project_manager = SimpleNamespace(
            get=lambda _project_id: object(),
            glossary_manager=object(),
        )
        llm = object()

        async def claim_translation_slot(self, project_id):
            return {
                "status": "acquired",
                "project_id": project_id,
                "run_id": None,
                "lease_id": "lease-resume",
            }

        def _set_active_run(self, project_id, **kwargs):
            active_updates.append((project_id, kwargs))

        def _release_active_run(self, *_args, **_kwargs):
            pass

    async def fake_resume_workflow(**kwargs):
        assert kwargs["translated_paragraphs"] == 70
        assert kwargs["total_paragraphs"] == 75
        started.set()
        await allow_finish.wait()

    monkeypatch.setattr(
        confirmation_translation,
        "_build_longform_service",
        lambda _base, _body: WorkflowService(),
    )
    monkeypatch.setattr(
        confirmation_translation,
        "inspect_translation_resume",
        lambda *_args: checkpoint,
    )
    monkeypatch.setattr(
        confirmation_translation,
        "ensure_term_review_job",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("resume must bypass terminology preparation")
        ),
    )
    monkeypatch.setattr(
        confirmation_translation,
        "_run_longform_resume_workflow",
        fake_resume_workflow,
    )
    base_service = SimpleNamespace(
        project_manager=SimpleNamespace(get=lambda _project_id: object())
    )

    response = await confirmation_translation.start_longform_workflow(
        _request(),
        "demo",
        base_service,
        LongformWorkflowStartRequest(method="four-step"),
    )

    assert response["status"] == "started"
    assert response["resumed"] is True
    assert response["term_review_job_id"] is None
    assert response["term_review_timeout_seconds"] == 0
    assert response["resume_checkpoint"]["remaining_paragraphs"] == 5
    assert response["run_id"].startswith("resume-")
    assert active_updates[0][1]["current_step"] == (
        "断点续译：已完成 70/75 段"
    )
    assert await asyncio.wait_for(started.wait(), timeout=1)

    allow_finish.set()
    for _ in range(100):
        if not confirmation_translation._longform_workflow_tasks:
            break
        await asyncio.sleep(0.01)
    assert not confirmation_translation._longform_workflow_tasks


class _WorkflowTranslationService:
    def __init__(self, projects_path, *, cancelled=False):
        self.project_manager = SimpleNamespace(
            projects_path=projects_path,
            glossary_manager=object(),
        )
        self.cancelled = cancelled
        self.translated = 0
        self.cleared = []
        self.released = []
        self.active_updates = []

    def _is_cancelled(self, _project_id):
        return self.cancelled

    def _clear_cancelled(self, project_id):
        self.cleared.append(project_id)

    def _release_active_run(self, project_id, **kwargs):
        self.released.append((project_id, kwargs))

    def _set_active_run(self, project_id, **kwargs):
        self.active_updates.append((project_id, kwargs))

    async def translate_project(self, _project_id):
        self.translated += 1
        return {"status": "completed"}


@pytest.mark.asyncio
async def test_resume_workflow_keeps_server_ownership_until_translation_finishes(
    tmp_path,
):
    service = _WorkflowTranslationService(tmp_path)

    await confirmation_translation._run_longform_resume_workflow(
        project_id="demo",
        lease_id="lease-resume",
        workflow_run_id="resume-demo",
        translation_service=service,
        translated_paragraphs=7,
        total_paragraphs=10,
    )

    assert service.translated == 1
    assert service.active_updates == [
        (
            "demo",
            {
                "run_id": "resume-demo",
                "status": "starting",
                "current_step": "断点续译：已完成 7/10 段",
            },
        )
    ]
    assert service.cleared == ["demo"]
    assert service.released == [
        ("demo", {"lease_id": "lease-resume"})
    ]


@pytest.mark.asyncio
async def test_workflow_auto_accepts_terms_then_translates_without_browser(
    tmp_path,
    monkeypatch,
):
    store = TerminologyReviewJobStore(tmp_path)
    job = store.create("demo")
    review = {
        "artifact_id": job["job_id"],
        "project_id": "demo",
        "review_required": True,
        "total_candidates": 1,
        "sections": [
            {
                "candidates": [
                    {
                        "term": "chiplet",
                        "suggested_translation": "芯粒",
                        "first_occurrence": "first",
                    }
                ]
            }
        ],
    }
    store.mark_succeeded("demo", job["job_id"], review)
    applied = []

    def fake_apply(_self, project_id, decisions, *, artifact_id=None):
        applied.append((project_id, decisions, artifact_id))
        return {"applied_count": len(decisions)}

    monkeypatch.setattr(TerminologyReviewService, "apply_review", fake_apply)
    service = _WorkflowTranslationService(tmp_path)

    await confirmation_translation._run_longform_workflow(
        project_id="demo",
        lease_id="lease-1",
        term_review_job_id=job["job_id"],
        translation_service=service,
        confirmation_timeout_seconds=0.02,
        poll_interval_seconds=0.005,
    )

    assert applied == [
        (
            "demo",
            [
                {
                    "term": "chiplet",
                    "action": "accept",
                    "translation": "芯粒",
                    "first_occurrence": "first",
                }
            ],
            job["job_id"],
        )
    ]
    assert store.get("demo", job["job_id"])["confirmation_status"] == "auto_accepted"
    assert service.translated == 1
    assert service.cleared == ["demo"]
    assert service.released == [("demo", {"lease_id": "lease-1"})]


@pytest.mark.asyncio
async def test_human_term_submission_releases_gate_before_timeout(
    tmp_path,
    monkeypatch,
):
    store = TerminologyReviewJobStore(tmp_path)
    job = store.create("demo")
    store.mark_succeeded(
        "demo",
        job["job_id"],
        {
            "artifact_id": job["job_id"],
            "project_id": "demo",
            "review_required": True,
            "total_candidates": 1,
            "sections": [
                {
                    "candidates": [
                        {
                            "term": "CPO",
                            "suggested_translation": "共封装光学",
                        }
                    ]
                }
            ],
        },
    )
    monkeypatch.setattr(
        TerminologyReviewService,
        "apply_review",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("human submission must prevent auto-accept")
        ),
    )
    service = _WorkflowTranslationService(tmp_path)
    task = asyncio.create_task(
        confirmation_translation._run_longform_workflow(
            project_id="demo",
            lease_id="lease-1",
            term_review_job_id=job["job_id"],
            translation_service=service,
            confirmation_timeout_seconds=60,
            poll_interval_seconds=0.005,
        )
    )

    for _ in range(100):
        if store.get("demo", job["job_id"])["confirmation_status"] == "waiting":
            break
        await asyncio.sleep(0.005)
    store.mark_confirmation_resolved(
        "demo",
        job["job_id"],
        "submitted",
    )

    await asyncio.wait_for(task, timeout=1)
    assert service.translated == 1
    assert store.get("demo", job["job_id"])["confirmation_status"] == "submitted"


@pytest.mark.asyncio
async def test_explicit_cancellation_stops_workflow_before_translation(tmp_path):
    store = TerminologyReviewJobStore(tmp_path)
    job = store.create("demo")
    service = _WorkflowTranslationService(tmp_path, cancelled=True)

    await confirmation_translation._run_longform_workflow(
        project_id="demo",
        lease_id="lease-1",
        term_review_job_id=job["job_id"],
        translation_service=service,
        confirmation_timeout_seconds=60,
        poll_interval_seconds=0.005,
    )

    assert service.translated == 0
    assert store.get("demo", job["job_id"])["confirmation_status"] == "cancelled"
    assert service.released == [("demo", {"lease_id": "lease-1"})]
