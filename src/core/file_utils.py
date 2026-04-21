"""
文件操作工具模块

提供原子写入、重试逻辑等文件操作工具函数。
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Callable, TypeVar
from uuid import uuid4

from .limits import TranslationLimits

logger = logging.getLogger(__name__)

T = TypeVar('T')


def atomic_write_with_retry(
    path: Path,
    write_func: Callable[[Path], None],
    max_attempts: int = TranslationLimits.FILE_WRITE_MAX_RETRIES,
    retry_delay_base: float = TranslationLimits.FILE_WRITE_RETRY_DELAY_BASE
) -> None:
    """
    原子写入文件,支持重试机制

    Args:
        path: 目标文件路径
        write_func: 写入函数,接收临时文件路径作为参数
        max_attempts: 最大重试次数
        retry_delay_base: 重试延迟基数(秒)

    Raises:
        OSError: 所有重试失败后抛出
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.{uuid4().hex}.tmp")

    try:
        write_func(tmp_path)

        for attempt in range(max_attempts):
            try:
                os.replace(tmp_path, path)
                return
            except OSError as e:
                if attempt == max_attempts - 1:
                    logger.error(
                        f"Failed to write file after {max_attempts} attempts: {path}, error: {e}"
                    )
                    raise
                logger.warning(
                    f"File write attempt {attempt + 1} failed for {path}: {e}, retrying..."
                )
                time.sleep(retry_delay_base * (attempt + 1))
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {tmp_path}: {e}")


def write_text_atomic(path: Path, content: str, encoding: str = "utf-8") -> None:
    """
    原子写入文本文件

    Args:
        path: 目标文件路径
        content: 文本内容
        encoding: 文件编码
    """
    def _write(tmp_path: Path) -> None:
        with open(tmp_path, "w", encoding=encoding) as f:
            f.write(content)

    atomic_write_with_retry(path, _write)


def write_json_atomic(path: Path, payload: Any, **json_kwargs) -> None:
    """
    原子写入JSON文件

    Args:
        path: 目标文件路径
        payload: 要序列化的数据
        **json_kwargs: 传递给json.dump的额外参数
    """
    json_kwargs.setdefault('ensure_ascii', False)
    json_kwargs.setdefault('indent', 2)
    json_kwargs.setdefault('default', str)

    def _write(tmp_path: Path) -> None:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, **json_kwargs)

    atomic_write_with_retry(path, _write)


def read_json(path: Path) -> Any:
    """
    读取JSON文件

    Args:
        path: 文件路径

    Returns:
        解析后的JSON数据
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_text(path: Path, encoding: str = "utf-8") -> str:
    """
    读取文本文件

    Args:
        path: 文件路径
        encoding: 文件编码

    Returns:
        文件内容
    """
    with open(path, "r", encoding=encoding) as f:
        return f.read()
