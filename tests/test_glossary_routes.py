import asyncio
import shutil
import threading
import time
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pydantic import ValidationError
from starlette.requests import Request

from src.api.middleware import ConflictException
from src.api.routers import glossary as global_glossary_router
from src.api.routers import project_glossary
from src.core.file_utils import read_json, write_json_atomic
from src.core.glossary import GlossaryManager
from src.core.models import Glossary, GlossaryTerm, TranslationStrategy
from src.services.batch_translation_service import BatchTranslationService
from src.services.confirmation_service import ConfirmationService
from src.services.term_review_artifact import (
    SUBMISSION_PENDING,
    TERM_REVIEW_SCHEMA,
    TERM_REVIEW_SCHEMA_VERSION,
)
from src.services.terminology_review_job_service import TerminologyReviewJobStore
from src.services.terminology_review_service import TerminologyReviewService


class GlossaryRouteTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        temp_root = Path(__file__).resolve().parent / ".tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.tempdir = temp_root / f"glossary-routes-{uuid.uuid4().hex}"
        self.tempdir.mkdir(parents=True, exist_ok=True)
        root = self.tempdir
        self.gm = GlossaryManager(
            global_path=str(root / "glossary"),
            projects_path=str(root / "projects"),
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.tempdir, ignore_errors=True)

    @staticmethod
    def _request() -> Request:
        return Request({"type": "http", "method": "POST", "path": "/", "headers": []})

    async def test_update_global_term_updates_tags(self) -> None:
        glossary = Glossary(
            terms=[
                GlossaryTerm(
                    original="HBM",
                    translation="HBM",
                    strategy=TranslationStrategy.PRESERVE,
                    tags=["memory"],
                    scope="global",
                )
            ]
        )
        self.gm.save_global(glossary)

        response = await global_glossary_router.update_global_term(
            self._request(),
            "HBM",
            global_glossary_router.TermUpdateRequest(
                tags=["memory", "stack"],
                status="disabled",
            ),
            gm=self.gm,
        )

        saved = self.gm.load_global()
        saved_term = saved.get_term("HBM")
        self.assertEqual(response["term"]["tags"], ["memory", "stack"])
        self.assertIsNotNone(saved_term)
        self.assertEqual(saved_term.tags, ["memory", "stack"])
        self.assertEqual(saved_term.status, "disabled")

    async def test_project_batch_add_tags_updates_all_selected_terms(self) -> None:
        glossary = Glossary(
            terms=[
                GlossaryTerm(original="chiplet", translation="芯粒", tags=["arch"]),
                GlossaryTerm(original="HBM", translation="HBM", strategy=TranslationStrategy.PRESERVE),
            ]
        )
        self.gm.save_project("demo", glossary)

        response = await project_glossary.batch_update_project_glossary(
            "demo",
            project_glossary.BatchGlossaryRequest(
                originals=["chiplet", "HBM"],
                action="add_tags",
                tags=["priority", "memory"],
            ),
            gm=self.gm,
        )

        saved = self.gm.load_project("demo")
        chiplet = saved.get_term("chiplet")
        hbm = saved.get_term("HBM")
        self.assertEqual(response["matched_count"], 2)
        self.assertEqual(chiplet.tags, ["arch", "priority", "memory"])
        self.assertEqual(hbm.tags, ["memory", "priority"])

    async def test_global_batch_add_tags_uses_body_action(self) -> None:
        glossary = Glossary(
            terms=[
                GlossaryTerm(original="chiplet", translation="芯粒", tags=["arch"], scope="global"),
                GlossaryTerm(original="HBM", translation="HBM", strategy=TranslationStrategy.PRESERVE, scope="global"),
            ]
        )
        self.gm.save_global(glossary)

        response = await global_glossary_router.batch_update_global_glossary(
            self._request(),
            global_glossary_router.BatchGlossaryRequest(
                originals=["chiplet", "HBM"],
                action="add_tags",
                tags=["priority", "memory"],
            ),
            gm=self.gm,
        )

        saved = self.gm.load_global()
        chiplet = saved.get_term("chiplet")
        hbm = saved.get_term("HBM")
        self.assertEqual(response["action"], "add_tags")
        self.assertEqual(response["matched_count"], 2)
        self.assertEqual(chiplet.tags, ["arch", "priority", "memory"])
        self.assertEqual(hbm.tags, ["memory", "priority"])

    async def test_concurrent_global_adds_do_not_lose_updates(self) -> None:
        class SlowGlossaryManager(GlossaryManager):
            def load_global(self):
                glossary = super().load_global()
                time.sleep(0.03)
                return glossary

        managers = [
            SlowGlossaryManager(
                global_path=str(self.tempdir / "glossary"),
                projects_path=str(self.tempdir / "projects"),
            )
            for _ in range(2)
        ]
        barrier = threading.Barrier(2)
        errors = []

        def add_term(manager: GlossaryManager, original: str) -> None:
            try:
                barrier.wait()
                asyncio.run(
                    global_glossary_router.add_global_term(
                        self._request(),
                        global_glossary_router.TermRequest(
                            original=original,
                            translation=original,
                        ),
                        gm=manager,
                    )
                )
            except Exception as exc:  # noqa: BLE001 - collect thread failures
                errors.append(exc)

        threads = [
            threading.Thread(target=add_term, args=(managers[0], "CPO")),
            threading.Thread(target=add_term, args=(managers[1], "HBM")),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertFalse(errors)
        saved = self.gm.load_global()
        self.assertIsNotNone(saved.get_term("CPO"))
        self.assertIsNotNone(saved.get_term("HBM"))

    async def test_concurrent_confirmation_term_updates_do_not_lose_changes(
        self,
    ) -> None:
        class SlowGlossaryManager(GlossaryManager):
            def load_project(self, project_id: str):
                glossary = super().load_project(project_id)
                time.sleep(0.03)
                return glossary

        self.gm.save_project(
            "demo",
            Glossary(
                terms=[
                    GlossaryTerm(original="CPO", translation="旧 CPO"),
                    GlossaryTerm(original="HBM", translation="旧 HBM"),
                ]
            ),
        )
        managers = [
            SlowGlossaryManager(
                global_path=str(self.tempdir / "glossary"),
                projects_path=str(self.tempdir / "projects"),
            )
            for _ in range(2)
        ]
        barrier = threading.Barrier(2)
        errors = []

        def update_term(
            manager: GlossaryManager,
            original: str,
            translation: str,
        ) -> None:
            try:
                barrier.wait()
                service = ConfirmationService(
                    project_manager=SimpleNamespace(),
                    glossary_manager=manager,
                )
                asyncio.run(
                    service.update_terms(
                        "demo",
                        [
                            {
                                "term": original,
                                "new_translation": translation,
                            }
                        ],
                    )
                )
            except Exception as exc:  # noqa: BLE001 - collect thread failures
                errors.append(exc)

        threads = [
            threading.Thread(
                target=update_term,
                args=(managers[0], "CPO", "共封装光学"),
            ),
            threading.Thread(
                target=update_term,
                args=(managers[1], "HBM", "高带宽内存"),
            ),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertFalse(errors)
        saved = self.gm.load_project("demo")
        self.assertEqual(saved.get_term("CPO").translation, "共封装光学")
        self.assertEqual(saved.get_term("HBM").translation, "高带宽内存")

    async def test_save_global_normalizes_scope_and_infers_tags(self) -> None:
        glossary = Glossary(
            terms=[
                GlossaryTerm(
                    original=" TSMC ",
                    translation="台积电",
                    strategy=TranslationStrategy.FIRST_ANNOTATE,
                    scope="project",
                    tags=[],
                )
            ]
        )
        self.gm.save_global(glossary)

        self.assertTrue((self.tempdir / "glossary" / "global_glossary_semi.json").exists())
        self.assertFalse((self.tempdir / "glossary" / "semiconductor.json").exists())

        loaded = self.gm.load_global()
        term = loaded.get_term("TSMC")

        self.assertIsNotNone(term)
        self.assertEqual(term.original, "TSMC")
        self.assertEqual(term.scope, "global")
        self.assertEqual(term.tags, ["company"])

    async def test_project_glossary_keeps_term_visible_when_only_tags_differ(self) -> None:
        global_glossary = Glossary(
            terms=[
                GlossaryTerm(
                    original="HBM",
                    translation="HBM",
                    strategy=TranslationStrategy.PRESERVE,
                    scope="global",
                )
            ]
        )
        project_terms = Glossary(
            terms=[
                GlossaryTerm(
                    original="HBM",
                    translation="HBM",
                    strategy=TranslationStrategy.PRESERVE,
                    tags=["project-specific"],
                    scope="project",
                )
            ]
        )
        self.gm.save_global(global_glossary)
        self.gm.save_project("demo", project_terms)

        response = await project_glossary.get_project_glossary("demo", gm=self.gm)

        self.assertEqual(len(response["terms"]), 1)
        self.assertEqual(response["terms"][0]["tags"], ["project-specific"])

    async def test_term_review_submit_reports_every_decision(self) -> None:
        latest_path = (
            self.tempdir
            / "projects"
            / "demo"
            / "artifacts"
            / "term-review"
            / "latest.json"
        )
        write_json_atomic(
            latest_path,
            {
                "project_id": "demo",
                "sections": [
                    {
                        "candidates": [
                            {
                                "term": "chiplet",
                                "suggested_translation": "系统建议",
                                "reasons": ["high_frequency"],
                                "occurrence_count": 2,
                            },
                            {
                                "term": "CPO",
                                "suggested_translation": "共封装光学",
                                "reasons": ["title"],
                                "occurrence_count": 1,
                            },
                        ]
                    }
                ],
            },
        )

        class FakeProjectManager:
            projects_path = self.tempdir / "projects"

            @staticmethod
            def get(project_id: str):
                if project_id != "demo":
                    raise FileNotFoundError(project_id)
                return object()

        pm = FakeProjectManager()
        request = project_glossary.SubmitTermReviewRequest(
            decisions=[
                {
                    "term": "chiplet",
                    "action": "accept",
                    "translation": "芯粒",
                },
                {
                    "term": "CPO",
                    "action": "skip",
                },
            ]
        )

        response = await project_glossary.submit_term_review(
            "demo",
            request,
            pm=pm,
            gm=self.gm,
        )

        self.assertEqual(response["applied_count"], 1)
        self.assertEqual(response["skipped_count"], 1)
        self.assertEqual(response["skipped_terms"], ["CPO"])
        self.assertEqual(self.gm.load_project("demo").get_term("chiplet").translation, "芯粒")
        persisted = read_json(latest_path)
        self.assertEqual(len(persisted["decisions"]), 2)

        batch_service = BatchTranslationService.__new__(BatchTranslationService)
        batch_service.project_manager = pm
        seed_terms = batch_service._load_term_review_seed_terms("demo")
        self.assertEqual([term.original for term in seed_terms], ["chiplet"])
        self.assertEqual(seed_terms[0].translation, "芯粒")

    def test_term_review_submit_rejects_empty_or_incomplete_decisions(self) -> None:
        with self.assertRaises(ValidationError):
            project_glossary.SubmitTermReviewRequest(decisions=[])

        with self.assertRaises(ValidationError):
            project_glossary.SubmitTermReviewRequest(
                decisions=[
                    {
                        "term": "chiplet",
                        "action": "custom",
                        "translation": " ",
                    }
                ]
            )

    async def test_term_review_background_job_persists_result(self) -> None:
        payload = {
            "project_id": "demo",
            "project_title": "Demo",
            "review_required": False,
            "generated_at": "2026-07-19T00:00:00",
            "total_candidates": 0,
            "sections": [],
        }

        class FakeProjectManager:
            projects_path = self.tempdir / "projects"

            @staticmethod
            def get(project_id: str):
                if project_id != "demo":
                    raise FileNotFoundError(project_id)
                return object()

        pm = FakeProjectManager()
        with patch.object(
            TerminologyReviewService,
            "prepare_review",
            return_value=payload,
        ) as prepare_mock:
            job = await project_glossary.start_term_review_job(
                "demo",
                pm=pm,
                gm=self.gm,
                llm=object(),
                request=project_glossary.PrepareTermReviewRequest(),
            )

            for _ in range(100):
                status = await project_glossary.get_term_review_job(
                    "demo",
                    uuid.UUID(job["job_id"]),
                    pm=pm,
                )
                if status["status"] == "succeeded":
                    break
                await asyncio.sleep(0.01)

        self.assertEqual(status["status"], "succeeded")
        self.assertEqual(status["result"], payload)
        self.assertEqual(
            prepare_mock.call_args.kwargs["artifact_id"],
            job["job_id"],
        )

    async def test_term_review_job_rejects_different_active_model(self) -> None:
        class FakeProjectManager:
            projects_path = self.tempdir / "projects"

            @staticmethod
            def get(project_id: str):
                if project_id != "demo":
                    raise FileNotFoundError(project_id)
                return object()

        pm = FakeProjectManager()
        store = TerminologyReviewJobStore(pm.projects_path)
        active = store.create("demo", "model-a")

        with self.assertRaises(ConflictException) as raised:
            await project_glossary.start_term_review_job(
                "demo",
                pm=pm,
                gm=self.gm,
                llm=object(),
                request=project_glossary.PrepareTermReviewRequest(
                    model="model-b"
                ),
            )

        self.assertEqual(
            raised.exception.error_code,
            "TERM_REVIEW_MODEL_CONFLICT",
        )
        self.assertEqual(
            raised.exception.__cause__.active_job["job_id"],
            active["job_id"],
        )

    async def test_term_review_submit_rejects_replaced_artifact(self) -> None:
        latest_path = (
            self.tempdir
            / "projects"
            / "demo"
            / "artifacts"
            / "term-review"
            / "latest.json"
        )
        write_json_atomic(
            latest_path,
            {
                "schema": TERM_REVIEW_SCHEMA,
                "schema_version": TERM_REVIEW_SCHEMA_VERSION,
                "submission_status": SUBMISSION_PENDING,
                "artifact_id": "artifact-b",
                "project_id": "demo",
                "sections": [],
            },
        )

        class FakeProjectManager:
            projects_path = self.tempdir / "projects"

            @staticmethod
            def get(project_id: str):
                if project_id != "demo":
                    raise FileNotFoundError(project_id)
                return object()

        request = project_glossary.SubmitTermReviewRequest(
            artifact_id="artifact-a",
            decisions=[
                {
                    "term": "chiplet",
                    "action": "accept",
                    "translation": "芯粒",
                }
            ],
        )

        with self.assertRaises(ConflictException) as raised:
            await project_glossary.submit_term_review(
                "demo",
                request,
                pm=FakeProjectManager(),
                gm=self.gm,
            )

        self.assertEqual(
            raised.exception.error_code,
            "TERM_REVIEW_ARTIFACT_CONFLICT",
        )
        self.assertIsNone(self.gm.load_project("demo").get_term("chiplet"))


if __name__ == "__main__":
    unittest.main()
