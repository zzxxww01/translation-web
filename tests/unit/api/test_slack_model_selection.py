"""All Slack operations must honor the picker instead of silently using defaults."""
import json
import pytest
from src.api.routers import slack_process, slack_compose, slack_refine, slack_refine_version
from src.api.routers.slack_models import (SlackProcessRequest, SlackComposeRequest,
    SlackRefineRequest)

MODEL = 'gpt-6.1-sol'
VARIANTS = [{'version':v,'english':'Thanks.','chinese':'谢谢'} for v in 'ABC']

@pytest.mark.asyncio
@pytest.mark.parametrize('operation', ['process','compose','refine','refine-version'])
async def test_model_and_metadata(monkeypatch, operation):
    cases = {
        'process':(slack_process,slack_process.process_slack_message.__wrapped__,[None,SlackProcessRequest(message='Hi',model=MODEL)],json.dumps({'translation':'你好','suggested_replies':VARIANTS})),
        'compose':(slack_compose,slack_compose.compose_slack_message.__wrapped__,[None,SlackComposeRequest(content='谢谢',model=MODEL)],json.dumps({'versions':VARIANTS})),
        'refine':(slack_refine,slack_refine.refine_result.__wrapped__,[None,SlackRefineRequest(context_type='draft',original_result='Hi',adjustment_instruction='polite',model=MODEL)],'Hello'),
        'refine-version':(slack_refine_version,slack_refine_version.refine_version,['A','谢谢','简洁',MODEL],'Thanks'),
    }
    module, fn, args, result = cases[operation]
    async def generate(prompt, **kwargs):
        assert kwargs['model'] == MODEL
        assert kwargs['task_type'] == 'slack'
        kwargs['result_metadata'].update(model_used=MODEL,real_model_used=MODEL,provider_used='openai-official',fallback_used=False)
        return result
    monkeypatch.setattr(module,'generate_with_fallback_budget',generate)
    monkeypatch.setattr(module.prompt_manager,'get',lambda *a,**k:'rendered')
    value = await fn(*args)
    assert value.model_used == value.real_model_used == MODEL
    assert value.provider_used == 'openai-official' and value.fallback_used is False
