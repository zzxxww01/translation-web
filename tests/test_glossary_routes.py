import shutil
import unittest
import uuid
from pathlib import Path

from starlette.requests import Request

from src.api.routers import glossary as global_glossary_router
from src.api.routers import project_glossary
from src.core.glossary import GlossaryManager
from src.core.models import Glossary, GlossaryTerm, TranslationStrategy


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


if __name__ == "__main__":
    unittest.main()
