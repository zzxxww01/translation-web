from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from src.llm.errors import LLMError, LLMOutputTruncatedError
from src.llm.output_validation import ensure_complete_generation, gemini_response_text
from src.llm.vectorengine import VectorEngineProvider

@pytest.mark.parametrize('reason',['length','MAX_TOKENS','FinishReason.MAX_TOKENS'])
def test_truncated_output_is_not_success(reason):
    with pytest.raises(LLMOutputTruncatedError):ensure_complete_generation(reason)

@pytest.mark.parametrize('reason',['SAFETY','content_filter','RECITATION','OTHER'])
def test_blocked_or_unknown_finish_is_not_success(reason):
    with pytest.raises(LLMError):ensure_complete_generation(reason)

def test_rest_assembles_answer_parts_without_thoughts():
    data={'candidates':[{'finishReason':'STOP','content':{'parts':[{'thought':True,'text':'private'},{'text':'first '},{'text':'second'}]}}]}
    assert gemini_response_text(data)=='first second'
    data['candidates'][0]['finishReason']='MAX_TOKENS'
    with pytest.raises(LLMOutputTruncatedError):gemini_response_text(data)

def test_vectorengine_rejects_nonempty_truncated_text():
    provider=object.__new__(VectorEngineProvider)
    provider.default_model='test';provider.temperature=.5;provider.max_tokens=10;provider.timeout=1
    provider.client=Mock()
    provider.client.with_options.return_value.chat.completions.create.return_value=SimpleNamespace(
        choices=[SimpleNamespace(finish_reason='length',message=SimpleNamespace(content='unfinished'))],usage=None)
    with pytest.raises(LLMOutputTruncatedError):provider.generate('source')
    provider.client.with_options.return_value.chat.completions.create.assert_called_once()
