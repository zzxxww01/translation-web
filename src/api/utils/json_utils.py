"""
JSON 解析工具函数

统一处理 LLM 返回的 JSON 响应。
"""

import json
import logging
import re
from typing import Any, Dict, List, Sequence, Union


logger = logging.getLogger(__name__)


def parse_llm_json_response(response: str) -> Dict[str, Any]:
    """
    解析 LLM 返回的 JSON 响应

    处理常见问题：
    - 移除 markdown 代码块标记
    - 提取 JSON 对象

    Args:
        response: LLM 返回的原始文本

    Returns:
        Dict: 解析后的 JSON 对象，解析失败返回空字典
    """
    text = response.strip()

    # 移除 markdown 代码块
    text = text.replace("```json", "").replace("```", "").strip()

    # 尝试提取 JSON 对象
    start_idx = text.find("{")
    end_idx = text.rfind("}") + 1
    if start_idx != -1 and end_idx > start_idx:
        text = text[start_idx:end_idx]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            # 中转/relay 常把未转义换行写进 JSON 字符串，有时连键名都被换行拆断。
            # strict=False 只放宽字符串内 U+0000..U+001F：不补造截断数据、不修改
            # 正文与合法转义，其他 JSON 语法错误仍然照旧失败。
            return json.loads(text, strict=False)
        except json.JSONDecodeError:
            # 解析失败仍返回 {}（调用方依赖该语义），但记录首段原文以便定位截断/赘述
            logger.warning("parse_llm_json_response failed, head=%r", text[:200])
            return {}


def parse_llm_json_array(response: str) -> List[Any]:
    """
    解析 LLM 返回的 JSON 数组响应

    Args:
        response: LLM 返回的原始文本

    Returns:
        List: 解析后的 JSON 数组，解析失败返回空列表
    """
    text = response.strip()

    # 移除 markdown 代码块
    text = text.replace("```json", "").replace("```", "").strip()

    # 尝试提取 JSON 数组
    start_idx = text.find("[")
    end_idx = text.rfind("]") + 1
    if start_idx != -1 and end_idx > start_idx:
        text = text[start_idx:end_idx]

    try:
        result = json.loads(text)
        return result if isinstance(result, list) else []
    except json.JSONDecodeError:
        return []

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
_RELAY_BREAK = re.compile(r"[ \t]*[\r\n]+[ \t]*")


def unwrap_relay_lines(text: str) -> str:
    """拼接中转在单个字符串值内部插入的折行。

    这些换行来自 relay 折行，不是消息本身的多行结构：中文之间直接拼回，
    ASCII 词之间补一个空格（避免把英文单词粘成一团），标点开头时不加空格。
    """
    if not isinstance(text, str) or not text:
        return text
    segments = _RELAY_BREAK.split(text)
    result = segments[0]
    for segment in segments[1:]:
        if not segment:
            continue
        prev = result[-1] if result else ""
        nxt = segment[0]
        if prev.isascii() and prev.isalnum() and nxt.isascii() and nxt.isalnum():
            result += " " + segment
        else:
            result += segment
    return result


def normalize_control_keys(value: Any, known_keys: Sequence[str]) -> Any:
    """Repair known keys that arrived with relay line wrapping inside them.

    Relay providers sometimes wrap long lines, so a key such as ``"english"``
    can come back as ``"english\n"`` (or ``"\nversion"``). Only keys whose
    cleaned form matches an explicit whitelist are rewritten; keys that are not
    on the list are returned exactly as received.
    """
    allowed = {key.casefold(): key for key in known_keys}

    def _walk(node: Any) -> Any:
        if isinstance(node, dict):
            repaired: Dict[Any, Any] = {}
            for key, item in node.items():
                if isinstance(key, str) and _CONTROL_CHARS.search(key):
                    cleaned = _CONTROL_CHARS.sub("", key).strip().casefold()
                    key = allowed.get(cleaned, key)
                repaired[key] = _walk(item)
            return repaired
        if isinstance(node, list):
            return [_walk(item) for item in node]
        return node

    return _walk(value)


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
    text = response.strip(" \t\r\n")

    # 仅剥离完整的外层代码块；全局 replace 会破坏 JSON 字符串里的正文。
    opening, separator, remainder = text.partition("\n")
    if separator and opening.rstrip(" \t\r") in ("```json", "```"):
        body, closing_separator, closing = remainder.rpartition("\n")
        if closing_separator and closing.strip(" \t\r") == "```":
            text = body

    # 不截取首尾花括号：数组内的对象、带截断尾部的数据不能冒充完整对象。
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        try:
            # strict=False 仅放宽字符串内 U+0000..U+001F，不补全数据，
            # 不修改空白、合法转义或正文；其他 JSON 语法规则仍然生效。
            result = json.loads(text, strict=False)
        except json.JSONDecodeError:
            logger.warning("parse_llm_json_response failed, head=%r", text[:200])
            return {}
    return result if isinstance(result, dict) else {}
