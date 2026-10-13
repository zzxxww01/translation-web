"""Title endpoint regressions: no real provider calls, matching router test style."""
import asyncio
import json
import unittest
from unittest.mock import patch

from starlette.requests import Request

from src.api.middleware.error_handlers import ServiceUnavailableException
from src.api.routers import translate_posts
from src.api.routers.translate_models import GenerateTitleRequest


class TitleFormatRetryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.request = Request({
            "type": "http", "method": "POST", "path": "/api/generate/title",
            "headers": [], "client": ("title-test", 50000),
        })
        self.body = GenerateTitleRequest(content="Source content", model="pro-official")
        self.prompt_patch = patch.object(translate_posts.prompt_manager, "get", return_value="original prompt")
        self.prompt_patch.start()
        self.addCleanup(self.prompt_patch.stop)
        # Do not consume global rate-limit quotas in the regression suite.
        self.limit_patch = patch.object(translate_posts.limiter, "enabled", False)
        self.limit_patch.start()
        self.addCleanup(self.limit_patch.stop)

    async def call(self):
        return await translate_posts.generate_title(self.request, self.body)

    async def test_valid_first_result_uses_all_eight_keys_without_retry(self):
        keys = ["suspense", "data", "counter_intuitive", "pain_point", "minimal", "contrast", "free_1", "free_2"]
        with patch.object(translate_posts, "generate_with_fallback", return_value=json.dumps(dict(zip(keys, keys)))) as generate:
            response = await self.call()
        self.assertEqual(response.title, "\n".join(keys))
        generate.assert_called_once()
        self.assertEqual(generate.call_args.kwargs["model"], "pro-official")

    async def test_control_char_keys_and_multiline_values_are_normalized(self):
        data = {"sus\npense": " First\r\n title ", "data\t": "Second\u2028title", "free_\x001": "Third", "free 2": "unknown"}
        with patch.object(translate_posts, "generate_with_fallback", return_value=json.dumps(data)) as generate:
            response = await self.call()
        self.assertEqual(response.title, "First title\nSecond title\nThird")
        generate.assert_called_once()

    async def test_raw_newlines_in_json_keys_and_values_do_not_need_retry(self):
        # Integration with json_utils' narrow unescaped-control-character repair.
        raw = '{"sus\npense": "First\n title", "free_2": "Second"}'
        with patch.object(translate_posts, "generate_with_fallback", return_value=raw) as generate:
            response = await self.call()
        self.assertEqual(response.title, "First title\nSecond")
        generate.assert_called_once()

    async def test_wrong_types_and_blank_values_are_not_stringified(self):
        data = {"suspense": ["bad"], "data": None, "counter_intuitive": 42,
                "pain_point": True, "minimal": {}, "contrast": " \n\t", "free_1": " Valid ", "unknown": "ignored"}
        with patch.object(translate_posts, "generate_with_fallback", return_value=json.dumps(data)) as generate:
            response = await self.call()
        self.assertEqual(response.title, "Valid")
        generate.assert_called_once()

    async def test_canonical_key_wins_over_repaired_alias(self):
        data = {"suspense": "canonical", "sus\npense": "alias"}
        with patch.object(translate_posts, "generate_with_fallback", return_value=json.dumps(data)):
            self.assertEqual((await self.call()).title, "canonical")

    async def test_format_failure_retries_same_model_and_returns_success_metadata(self):
        for invalid in ['not JSON', '{}', '[]', 'null', '{"suspense": ["bad"], "data": null}', None]:
            with self.subTest(invalid=invalid):
                def result(prompt, **kwargs):
                    if prompt == "original prompt":
                        kwargs["result_metadata"].update(model_used="old", provider_used="old", fallback_used=True)
                        return invalid
                    # A new metadata dict prevents stale fallback flags leaking.
                    self.assertEqual(kwargs["result_metadata"], {})
                    kwargs["result_metadata"].update(model_used="pro-official", provider_used="gemini", fallback_used=False)
                    return '{"minimal":"Recovered"}'
                with patch.object(translate_posts, "generate_with_fallback", side_effect=result) as generate:
                    response = await self.call()
                self.assertEqual(response.title, "Recovered")
                self.assertEqual(response.model_used, "pro-official")
                self.assertEqual(response.provider_used, "gemini")
                self.assertFalse(response.fallback_used)
                self.assertEqual(generate.call_count, 2)
                self.assertIn("original prompt", generate.call_args.args[0])
                self.assertIn("JSON", generate.call_args.args[0])
                for call in generate.call_args_list:
                    self.assertEqual(call.kwargs["model"], "pro-official")
                    self.assertEqual(call.kwargs["task_type"], "title")

    async def test_successful_retry_reports_its_actual_fallback_metadata(self):
        self.body.model = "deepseek-relay"
        count = 0

        def result(prompt, **kwargs):
            nonlocal count
            count += 1
            if count == 1:
                kwargs["result_metadata"].update(model_used="deepseek-relay", provider_used="relay", fallback_used=False)
                return "invalid"
            kwargs["result_metadata"].update(model_used="flash-official", provider_used="gemini", fallback_used=True)
            return '{"minimal":"Recovered"}'

        with patch.object(translate_posts, "generate_with_fallback", side_effect=result) as generate:
            response = await self.call()
        self.assertEqual(response.model_used, "flash-official")
        self.assertEqual(response.provider_used, "gemini")
        self.assertTrue(response.fallback_used)
        self.assertEqual(generate.call_count, 2)
        self.assertTrue(all(call.kwargs["model"] == "deepseek-relay" for call in generate.call_args_list))

    async def test_two_format_failures_stop_at_two_calls(self):
        with patch.object(translate_posts, "generate_with_fallback", return_value='{"suspense":null}') as generate:
            with self.assertRaises(ServiceUnavailableException) as error:
                await self.call()
        self.assertEqual(error.exception.status_code, 503)
        self.assertEqual(generate.call_count, 2)

    async def test_unicode_20_boundary_and_21_semantic_rewrite(self):
        for title in ["中" * 20, "A" * 20, "😀" * 20, "中A1 !😀" + "文" * 14]:
            self.assertEqual(len(title), 20)
            with patch.object(translate_posts, "generate_with_fallback", return_value=json.dumps({"minimal": title})) as generate:
                self.assertEqual((await self.call()).title, title)
                generate.assert_called_once()
            with patch.object(translate_posts, "generate_with_fallback", side_effect=[json.dumps({"minimal": title + "!"}), '{"minimal":"品牌良率超过80%"}']) as generate:
                self.assertEqual((await self.call()).title, "品牌良率超过80%")
                self.assertEqual(generate.call_count, 2)
                self.assertIn("语义改写", generate.call_args.args[0])
                self.assertIn("不能直接截断", generate.call_args.args[0])
                self.assertIn("品牌名", generate.call_args.args[0])

    async def test_overlong_is_not_filtered_or_truncated(self):
        response = json.dumps({"minimal": "合规", "data": "长" * 21})
        with patch.object(translate_posts, "generate_with_fallback", return_value=response) as generate:
            with self.assertRaises(ServiceUnavailableException) as error:
                await self.call()
        self.assertIn("20", error.exception.detail)
        self.assertEqual(generate.call_count, 2)

    async def test_rewrite_cannot_omit_overlong_key(self):
        responses = [json.dumps({"minimal": "合规", "data": "长" * 21}), '{"minimal":"合规"}', '{"minimal":"合规"}']
        with patch.object(translate_posts, "generate_with_fallback", side_effect=responses) as generate:
            with self.assertRaises(ServiceUnavailableException) as error:
                await self.call()
        self.assertIn("缺少", error.exception.detail)
        self.assertEqual(generate.call_count, 3)

    async def test_format_repair_and_length_rewrite_share_three_call_cap(self):
        long_json = json.dumps({"minimal": "长" * 21})
        # Both orders work, including raw controls in the successful JSON.
        for responses in [["invalid", long_json, '{"mini\nmal":"品牌\n良率超过80%"}'],
                          [long_json, "invalid", '{"minimal":"品牌良率超过80%"}']]:
            with patch.object(translate_posts, "generate_with_fallback", side_effect=responses) as generate:
                self.assertEqual((await self.call()).title, "品牌良率超过80%")
                self.assertEqual(generate.call_count, 3)

    async def test_length_and_format_repairs_share_remaining_deadline(self):
        timeouts = []
        async def fake_run(func, prompt, **kwargs):
            timeouts.append(kwargs["timeout"])
            await asyncio.sleep(0.02)
            if len(timeouts) == 1:
                return json.dumps({"minimal": "长" * 21})
            if len(timeouts) == 2:
                return "invalid"
            await asyncio.Event().wait()

        with patch.object(translate_posts, "_resolve_timeouts", return_value=(0.12, 0.12)), patch.object(
            translate_posts, "run_llm_blocking", side_effect=fake_run
        ):
            with self.assertRaises(ServiceUnavailableException) as error:
                await self.call()
        self.assertIn("timed out", error.exception.detail)
        self.assertEqual(len(timeouts), 3)
        self.assertGreater(timeouts[0], timeouts[1])
        self.assertGreater(timeouts[1], timeouts[2])

    async def test_transport_errors_are_not_format_retried(self):
        for exc in [RuntimeError("transport down"), TimeoutError("upstream timeout")]:
            with self.subTest(exc=exc), patch.object(translate_posts, "generate_with_fallback", side_effect=exc) as generate:
                with self.assertRaises(ServiceUnavailableException) as error:
                    await self.call()
                self.assertEqual(error.exception.status_code, 503)
                generate.assert_called_once()

    async def test_retry_transport_error_does_not_start_third_call(self):
        with patch.object(translate_posts, "generate_with_fallback", side_effect=["invalid", RuntimeError("down")]) as generate:
            with self.assertRaises(ServiceUnavailableException) as error:
                await self.call()
        self.assertEqual(error.exception.status_code, 503)
        self.assertEqual(generate.call_count, 2)

    async def test_two_generations_share_one_outer_timeout_and_remaining_attempt_budget(self):
        real_wait_for = asyncio.wait_for
        timeouts = []
        cancelled = []

        async def fake_run(func, prompt, **kwargs):
            self.assertIs(func, translate_posts.generate_with_fallback)
            self.assertEqual(kwargs["model"], "pro-official")
            timeouts.append(kwargs["timeout"])
            if len(timeouts) == 1:
                await asyncio.sleep(0.04)
                return "bad JSON"
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.append(True)
                raise

        with patch.object(translate_posts, "_resolve_timeouts", return_value=(0.12, 0.12)), patch.object(
            translate_posts, "run_llm_blocking", side_effect=fake_run
        ), patch.object(translate_posts.asyncio, "wait_for", wraps=real_wait_for) as wait_for:
            with self.assertRaises(ServiceUnavailableException) as error:
                await self.call()
        self.assertEqual(error.exception.status_code, 503)
        self.assertEqual(len(timeouts), 2)
        self.assertLess(timeouts[1], timeouts[0] - 0.02)
        self.assertTrue(cancelled)
        wait_for.assert_called_once()
        self.assertEqual(wait_for.call_args.kwargs["timeout"], 0.12)


if __name__ == "__main__":
    unittest.main()
