"""Parse complete model JSON; malformed responses must not masquerade as success."""
import json
import logging
from typing import Any, Dict, List
from src.prompts.contracts import object_response, parse_json, PromptContractError, json_decoder

def parse_llm_json_response(response: str) -> Dict[str, Any]:
    return object_response(response)

def parse_llm_json_array(response: str) -> List[Any]:
    result = parse_json(response)
    if not isinstance(result, list):
        raise PromptContractError("Expected a JSON array")
    return result

logger = logging.getLogger(__name__)

def parse_title_json_response(response: str) -> Dict[str, Any]:
    """
    解析 LLM 返回的 JSON 响应

    处理常见问题：
    - 移除完整的外层 markdown 代码块标记，不改动正文
    - 优先严格解析，仅容忍 JSON 字符串内未转义的控制字符
    - 拒绝非对象、截断数据和其他语法错误，不提取局部对象

    Args:
        response: LLM 返回的原始文本

    Returns:
        Dict: 解析后的 JSON 对象，解析失败返回空字典
    """
    if not isinstance(response, str):
        return {}
    text = response.strip(" \t\r\n")

    # 仅剥离完整的外层代码块；全局 replace 会破坏 JSON 字符串里的正文。
    opening, separator, remainder = text.partition("\n")
    if separator and opening.rstrip(" \t\r") in ("```json", "```"):
        body, closing_separator, closing = remainder.rpartition("\n")
        if closing_separator and closing.strip(" \t\r") == "```":
            text = body

    # 不截取首尾花括号：数组内的对象、带截断尾部的数据不能冒充完整对象。
    try:
        result = json_decoder().decode(text)
    except (json.JSONDecodeError, PromptContractError, ValueError):
        try:
            # strict=False 仅放宽字符串内 U+0000..U+001F，不补全数据，
            # 不修改空白、合法转义或正文；其他 JSON 语法规则仍然生效。
            result = json_decoder(strict=False).decode(text)
        except (json.JSONDecodeError, PromptContractError, ValueError):
            logger.warning("Title JSON rejected (characters=%d)", len(text))
            return {}
    return result if isinstance(result, dict) else {}
