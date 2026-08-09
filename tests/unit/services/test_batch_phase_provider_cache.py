from types import SimpleNamespace

from src.services.batch_translation_service import BatchTranslationService


class _ModelConfig:
    def get_model_for_phase(self, phase):
        models = {
            "phase0_prescan": "grok-model",
            "phase1_draft": "shared-model",
            "phase2_refine": "shared-model",
            "phase3_review": "review-model",
        }
        return {
            "model": models[phase],
            "temperature": 0.3,
        }


def test_phase_providers_are_reused_by_model_alias(monkeypatch) -> None:
    service = BatchTranslationService.__new__(BatchTranslationService)
    service.llm = SimpleNamespace(model_alias="base-model")
    service.user_model_override = None
    service.model_config = _ModelConfig()
    service._phase_provider_cache = {}
    created = []

    def create_provider(*, provider):
        result = SimpleNamespace(model_alias=provider)
        created.append(result)
        return result

    monkeypatch.setattr(
        "src.api.utils.llm_factory.create_llm_provider",
        create_provider,
    )

    draft = service._get_provider_for_phase("phase1_draft")
    refine = service._get_provider_for_phase("phase2_refine")

    assert draft is refine
    assert len(created) == 1


def test_matching_base_provider_is_cached_without_recreation(monkeypatch) -> None:
    service = BatchTranslationService.__new__(BatchTranslationService)
    service.llm = SimpleNamespace(model_alias="shared-model")
    service.user_model_override = None
    service.model_config = _ModelConfig()
    service._phase_provider_cache = {}

    monkeypatch.setattr(
        "src.api.utils.llm_factory.create_llm_provider",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("matching base provider must be reused")
        ),
    )

    assert service._get_provider_for_phase("phase1_draft") is service.llm
    assert service._get_provider_for_phase("phase2_refine") is service.llm
