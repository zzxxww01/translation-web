"""Parse complete model JSON; malformed responses must not masquerade as success."""
from typing import Any, Dict, List
from src.prompts.contracts import object_response, parse_json, PromptContractError

def parse_llm_json_response(response: str) -> Dict[str, Any]:
    return object_response(response)

def parse_llm_json_array(response: str) -> List[Any]:
    result = parse_json(response)
    if not isinstance(result, list):
        raise PromptContractError("Expected a JSON array")
    return result
