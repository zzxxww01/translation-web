import unittest
from unittest.mock import patch

from src.api.routers import translate_posts
from src.api.routers.translate_models import PostTranslateRequest


class TranslatePostRegressionTests(unittest.IsolatedAsyncioTestCase):
    async def test_translate_post_uses_post_translation_template(self) -> None:
        request = PostTranslateRequest(content="Hello world")

        with patch(
            "src.api.routers.translate_posts.build_glossary_context",
            return_value="term: glossary-term",
        ), patch.object(
            translate_posts.prompt_manager,
            "get",
            return_value="rendered-prompt",
        ) as mock_prompt_get, patch(
            "src.api.routers.translate_posts.generate_with_fallback",
            return_value="translated-result",
        ) as mock_generate:
            response = await translate_posts.translate_post(request)

        self.assertEqual(response.translation, "translated-result")
        mock_prompt_get.assert_called_once_with(
            "post_translation",
            text="Hello world",
            dynamic_sections="term: glossary-term",
        )
        mock_generate.assert_called_once_with("rendered-prompt")

    async def test_translate_post_custom_prompt_bypasses_template_manager(self) -> None:
        request = PostTranslateRequest(
            content="Hello world",
            custom_prompt="Translate: {content}\n{glossary}",
        )

        with patch(
            "src.api.routers.translate_posts.build_glossary_context",
            return_value="term: glossary-term",
        ), patch.object(
            translate_posts.prompt_manager,
            "get",
            side_effect=AssertionError("prompt_manager.get should not be called"),
        ), patch(
            "src.api.routers.translate_posts.generate_with_fallback",
            return_value="translated-result",
        ) as mock_generate:
            response = await translate_posts.translate_post(request)

        self.assertEqual(response.translation, "translated-result")
        mock_generate.assert_called_once_with("Translate: Hello world\nterm: glossary-term")


if __name__ == "__main__":
    unittest.main()
