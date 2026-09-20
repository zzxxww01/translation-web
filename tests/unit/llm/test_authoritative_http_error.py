import httpx
import pytest
from openai import APIStatusError
from src.llm.errors import normalize_llm_transport_error


@pytest.mark.parametrize('status', [400, 401, 403, 404, 422])
def test_client_status_overrides_transient_sounding_body(status):
    response = httpx.Response(status, request=httpx.Request('POST', 'https://example.invalid'))
    error = APIStatusError('upstream timeout invalid argument', response=response, body={})
    normalized = normalize_llm_transport_error(error, provider_name='VectorEngine')
    assert normalized is None or not normalized.retryable
