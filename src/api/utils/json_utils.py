"""
JSON 解析工具函数

统一处理 LLM 返回的 JSON 响应。
"""

import json
import logging
from typing import Any, Dict, List, Union


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
