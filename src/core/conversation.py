"""
Conversation Manager - 对话管理模块

基于文件夹结构管理 Slack 对话：
- conversations/{id}/config.json  # 配置信息
- conversations/{id}/history.json # 对话历史（永久保存）
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field


class Message(BaseModel):
    """单条消息"""

    role: str  # "them" | "me"
    content_en: str
    content_cn: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ConversationConfig(BaseModel):
    """对话配置"""

    id: str
    name: str
    style: str = "casual"  # casual | professional
    system_prompt: str = ""  # 长期记忆：角色描述
    is_pinned: bool = False  # 置顶标记，用于预设模板
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class Conversation(BaseModel):
    """完整对话（配置 + 历史）"""

    config: ConversationConfig
    history: List[Message] = Field(default_factory=list)

    @property
    def id(self) -> str:
        return self.config.id

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def system_prompt(self) -> str:
        return self.config.system_prompt

    def get_context_for_prompt(self, max_messages: int = 5) -> str:
        """生成用于 Prompt 的上下文（长期 + 短期记忆）"""
        parts = []

        # 长期记忆
        if self.config.system_prompt:
            parts.append(f"## 背景信息\n{self.config.system_prompt}")

        # 短期记忆：最近对话
        if self.history:
            recent = self.history[-max_messages:]
            lines = []
            for msg in recent:
                role_label = "对方" if msg.role == "them" else "我"
                lines.append(f"[{role_label}] {msg.content_en}")
            parts.append("## 最近对话\n" + "\n".join(lines))

        return "\n\n".join(parts)


class ConversationManager:
    """对话管理器（文件夹结构）"""

    def __init__(self, base_path: str = "conversations"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_folder(self, conv_id: str) -> Path:
        return self.base_path / conv_id

    def _get_config_path(self, conv_id: str) -> Path:
        return self._get_folder(conv_id) / "config.json"

    def _get_history_path(self, conv_id: str) -> Path:
        return self._get_folder(conv_id) / "history.json"

    def list_all(self) -> List[ConversationConfig]:
        """列出所有对话的配置"""
        configs = []
        for folder in self.base_path.iterdir():
            if folder.is_dir():
                config_path = folder / "config.json"
                if config_path.exists():
                    try:
                        with open(config_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            # Backwards compatibility for updated_at
                            if "updated_at" not in data:
                                data["updated_at"] = data["created_at"]
                            configs.append(ConversationConfig(**data))
                    except Exception as e:
                        print(f"Error loading {config_path}: {e}")
        # Sort: pinned first, then by updated_at desc within each group
        pinned = sorted(
            [c for c in configs if c.is_pinned],
            key=lambda c: c.updated_at,
            reverse=True,
        )
        unpinned = sorted(
            [c for c in configs if not c.is_pinned],
            key=lambda c: c.updated_at,
            reverse=True,
        )
        return pinned + unpinned

    def get(self, conv_id: str) -> Optional[Conversation]:
        """获取完整对话"""
        config_path = self._get_config_path(conv_id)
        history_path = self._get_history_path(conv_id)

        if not config_path.exists():
            return None

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
                if "updated_at" not in config_data:
                    config_data["updated_at"] = config_data.get("created_at", "")

            history = []
            if history_path.exists():
                with open(history_path, "r", encoding="utf-8") as f:
                    history_data = json.load(f)
                    history = [Message(**m) for m in history_data]

            return Conversation(
                config=ConversationConfig(**config_data), history=history
            )
        except Exception as e:
            print(f"Error loading conversation {conv_id}: {e}")
            return None

    def create(
        self,
        conv_id: str,
        name: str,
        style: str = "casual",
        system_prompt: str = "",
        is_pinned: bool = False,
    ) -> ConversationConfig:
        """创建新对话"""
        folder = self._get_folder(conv_id)
        folder.mkdir(parents=True, exist_ok=True)

        config = ConversationConfig(
            id=conv_id,
            name=name,
            style=style,
            system_prompt=system_prompt,
            is_pinned=is_pinned,
        )

        # 保存 config
        with open(self._get_config_path(conv_id), "w", encoding="utf-8") as f:
            json.dump(config.model_dump(), f, ensure_ascii=False, indent=2)

        # 创建空历史
        with open(self._get_history_path(conv_id), "w", encoding="utf-8") as f:
            json.dump([], f)

        return config

    def update_config(self, conv_id: str, **kwargs) -> Optional[ConversationConfig]:
        """更新对话配置"""
        config_path = self._get_config_path(conv_id)
        if not config_path.exists():
            return None

        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data.update(kwargs)
        # Always update updated_at
        data["updated_at"] = datetime.now().isoformat()

        config = ConversationConfig(**data)

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config.model_dump(), f, ensure_ascii=False, indent=2)

        return config

    def delete(self, conv_id: str) -> bool:
        """删除对话"""
        folder = self._get_folder(conv_id)
        if folder.exists():
            shutil.rmtree(folder)
            return True
        return False

    def add_message(
        self, conv_id: str, role: str, content_en: str, content_cn: str = ""
    ) -> Optional[Message]:
        """添加消息到历史（永久保存）"""
        # Auto-create __default__ if missing
        if conv_id == "__default__" and not self._get_config_path(conv_id).exists():
            self.create("__default__", "默认（无记忆）")

        history_path = self._get_history_path(conv_id)
        if not history_path.exists():
            return None

        msg = Message(role=role, content_en=content_en, content_cn=content_cn)

        # 读取现有历史
        with open(history_path, "r", encoding="utf-8") as f:
            history = json.load(f)

        # 追加新消息
        history.append(msg.model_dump())

        # 保存历史
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

        # 更新 update_time
        self.update_config(conv_id)

        return msg

    def update_message(
        self,
        conv_id: str,
        index: int,
        role: Optional[str] = None,
        content_en: Optional[str] = None,
        content_cn: Optional[str] = None,
    ) -> Optional[Message]:
        """更新消息"""
        history_path = self._get_history_path(conv_id)
        if not history_path.exists():
            return None

        # 读取现有历史
        with open(history_path, "r", encoding="utf-8") as f:
            history = json.load(f)

        if index < 0 or index >= len(history):
            return None

        # 更新字段
        msg_data = history[index]
        if role is not None:
            msg_data["role"] = role
        if content_en is not None:
            msg_data["content_en"] = content_en
        if content_cn is not None:
            msg_data["content_cn"] = content_cn

        # 重新保存
        history[index] = msg_data
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

        return Message(**msg_data)

    def get_history(self, conv_id: str) -> List[Message]:
        """获取对话历史"""
        history_path = self._get_history_path(conv_id)
        if not history_path.exists():
            return []

        try:
            with open(history_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [Message(**m) for m in data]
        except Exception:
            return []

    def get_history_count(self, conv_id: str) -> int:
        """获取历史消息数量（避免完整反序列化）。"""
        history_path = self._get_history_path(conv_id)
        if not history_path.exists():
            return 0

        try:
            with open(history_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return len(data) if isinstance(data, list) else 0
        except Exception:
            return 0
