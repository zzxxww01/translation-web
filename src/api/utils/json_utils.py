"""
JSON 解析工具函数

统一处理 LLM 返回的 JSON 响应。
"""

import json
from typing import Any, Dict, List, Union


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
