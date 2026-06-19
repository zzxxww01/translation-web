"""回归测试：gemini provider 的错误分类与批翻输出清洗。

1. auth 错误（401/403/invalid key）是确定性失败，不应进入指数退避重试循环，
   否则坏 key 会空耗整个退避预算。但仍应被 _is_auth_error 识别（用于换 key 轮换）。
2. translate_section 的 JSON 输出可能畸形（字符串列表、缺键），_coerce_translation_items
   必须宽容丢弃畸形条目并对齐，让调用方的逐段回退干净接管，而非抛 KeyError 中断整章。
"""

from src.llm.gemini import GeminiProvider


class TestAuthErrorClassification:
    def test_auth_errors_are_detected(self):
        for msg in [
            "401 Unauthorized",
            "403 forbidden",
            "API key not valid",
            "permission denied",
            "unauthenticated request",
        ]:
            assert GeminiProvider._is_auth_error(msg) is True

    def test_auth_errors_are_not_retryable(self):
        # 关键回归点：auth 不再被判为 retryable，避免空耗退避预算
        for msg in ["401 Unauthorized", "403 forbidden", "invalid api key"]:
            assert GeminiProvider._is_retryable_error(msg) is False

    def test_transient_errors_still_retryable(self):
        for msg in [
            "503 service unavailable",
            "deadline exceeded",
            "connection reset",
            "429 rate limit",
        ]:
            assert GeminiProvider._is_retryable_error(msg) is True


class TestCoerceTranslationItems:
    def test_drops_non_dict_and_missing_keys(self):
        raw = [
            {"id": "p1", "translation": "译文1"},
            "纯字符串项",  # 畸形：非 dict
            {"id": "p2"},  # 畸形：缺 translation
            {"translation": "无 id"},  # 畸形：缺 id
            {"id": "p3", "translation": "译文3"},
        ]
        out = GeminiProvider._coerce_translation_items(raw, expected_count=5)
        assert out == [
            {"id": "p1", "translation": "译文1"},
            {"id": "p3", "translation": "译文3"},
        ]

    def test_non_list_returns_empty(self):
        assert GeminiProvider._coerce_translation_items({"foo": "bar"}) == []
        assert GeminiProvider._coerce_translation_items(None) == []

    def test_well_formed_passthrough(self):
        raw = [{"id": "a", "translation": "x"}, {"id": "b", "translation": "y"}]
        assert GeminiProvider._coerce_translation_items(raw, expected_count=2) == raw

    def test_id_coerced_to_string(self):
        raw = [{"id": 7, "translation": "数字 id"}]
        assert GeminiProvider._coerce_translation_items(raw) == [
            {"id": "7", "translation": "数字 id"}
        ]
