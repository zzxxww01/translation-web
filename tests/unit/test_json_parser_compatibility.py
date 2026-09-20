from src.api.utils.json_utils import parse_llm_json_response, parse_title_json_response

def test_general_json_parser_keeps_legacy_preamble_support():
    text = 'Here is the optimized result:\n{"optimized_text":"Improved text","improvements":["Clearer wording"],"confidence":0.95}'
    assert parse_llm_json_response(text)['optimized_text'] == 'Improved text'
    assert parse_title_json_response(text) == {}
