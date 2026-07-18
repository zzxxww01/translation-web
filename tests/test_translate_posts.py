import unittest
from unittest.mock import patch

from starlette.requests import Request

from src.api.routers import translate_posts
from src.api.routers.translate_models import PostOptimizeRequest, PostTranslateRequest


class TranslatePostRegressionTests(unittest.IsolatedAsyncioTestCase):
    def make_http_request(self) -> Request:
        return Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/api/translate/post",
                "headers": [],
                "client": ("testclient", 50000),
            }
        )

    async def test_translate_post_uses_post_translation_template(self) -> None:
        body = PostTranslateRequest(content="Hello world")

        with patch(
            "src.api.routers.translate_posts.build_glossary_context",
            return_value="term: glossary-term",
        ) as mock_glossary, patch.object(
            translate_posts.prompt_manager,
            "get",
            return_value="rendered-prompt",
        ) as mock_prompt_get, patch(
            "src.api.routers.translate_posts.generate_with_fallback",
            return_value="translated-result",
        ) as mock_generate:
            response = await translate_posts.translate_post(
                self.make_http_request(),
                body,
            )

        self.assertEqual(response.translation, "translated-result")
        mock_glossary.assert_called_once_with("Hello world")
        mock_prompt_get.assert_called_once_with(
            "post_translation",
            text="Hello world",
            dynamic_sections="term: glossary-term",
        )
        mock_generate.assert_called_once()
        self.assertEqual(mock_generate.call_args.args, ("rendered-prompt",))
        self.assertEqual(mock_generate.call_args.kwargs["task_type"], "post")

    async def test_translate_post_custom_prompt_bypasses_template_manager(self) -> None:
        body = PostTranslateRequest(
            content="Hello world",
            custom_prompt="Translate: {content}\n{glossary}",
        )

        with patch.dict("os.environ", {"ALLOW_CUSTOM_PROMPTS": "true"}), patch(
            "src.api.routers.translate_posts.build_glossary_context",
            return_value="term: glossary-term",
        ) as mock_glossary, patch.object(
            translate_posts.prompt_manager,
            "get",
            side_effect=AssertionError("prompt_manager.get should not be called"),
        ), patch(
            "src.api.routers.translate_posts.generate_with_fallback",
            return_value="translated-result",
        ) as mock_generate:
            response = await translate_posts.translate_post(
                self.make_http_request(),
                body,
            )

        self.assertEqual(response.translation, "translated-result")
        mock_glossary.assert_called_once_with("Hello world")
        mock_generate.assert_called_once()
        self.assertEqual(
            mock_generate.call_args.args,
            ("Translate: Hello world\nterm: glossary-term",),
        )
        self.assertEqual(mock_generate.call_args.kwargs["task_type"], "post")

    async def test_translate_post_preserves_token_and_adds_relevant_tags(self) -> None:
        body = PostTranslateRequest(
            content="NVIDIA says its LLM processes more token on new AI chips."
        )

        with patch(
            "src.api.routers.translate_posts.build_glossary_context",
            return_value="",
        ), patch.object(
            translate_posts.prompt_manager,
            "get",
            return_value="rendered-prompt",
        ), patch(
            "src.api.routers.translate_posts.generate_with_fallback",
            return_value="英伟达称，新AI芯片能处理更多词元。",
        ):
            response = await translate_posts.translate_post(
                self.make_http_request(),
                body,
            )

        self.assertIn("更多token", response.translation)
        self.assertNotIn("词元", response.translation)
        self.assertTrue(
            response.translation.endswith("#英伟达 #AI芯片 #大模型推理")
        )

    async def test_optimize_post_reapplies_token_and_tag_guards(self) -> None:
        body = PostOptimizeRequest(
            original_text="NVIDIA improved token throughput for its LLM chips.",
            current_translation="英伟达提升了大模型芯片的token吞吐量。",
            option_id="readable",
        )

        with patch(
            "src.api.routers.translate_posts.build_glossary_context",
            return_value="",
        ), patch.object(
            translate_posts.prompt_manager,
            "get",
            return_value="rendered-prompt",
        ), patch(
            "src.api.routers.translate_posts.generate_with_fallback",
            return_value="英伟达提升了大模型芯片的词元吞吐量。\n\n#大模型",
        ):
            response = await translate_posts.optimize_post_translation(
                self.make_http_request(),
                body,
            )

        self.assertNotIn("词元", response.optimized_translation)
        self.assertIn("token吞吐量", response.optimized_translation)
        self.assertTrue(
            response.optimized_translation.endswith("#大模型")
        )


if __name__ == "__main__":
    unittest.main()
