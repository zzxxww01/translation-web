"""
术语确认服务

管理用户确认流程，包括准备确认包、应用决策、删除确认包。
"""

import json
import uuid
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
from src.services.glossary_storage import GlossaryStorage
from src.services.term_extraction_service import TermCandidate
from src.services.term_conflict_detector import TermConflict
from src.models.terminology import Term, TermMetadata


class ConfirmationAction(Enum):
    """确认动作"""
    ACCEPT = "accept"  # 接受建议翻译
    MODIFY = "modify"  # 修改翻译
    SKIP = "skip"  # 跳过（本次不处理）
    USE_EXISTING = "use_existing"  # 使用已有术语
    REJECT = "reject"  # 拒绝（永久不添加）


@dataclass
class ConfirmationDecision:
    """确认决策"""
    candidate_index: int  # 候选术语索引
    action: ConfirmationAction  # 动作
    final_translation: Optional[str] = None  # 最终翻译（ACCEPT/MODIFY时需要）
    existing_term_id: Optional[str] = None  # 已有术语ID（USE_EXISTING时需要）


@dataclass
class ConfirmationPackage:
    """确认包"""
    package_id: str  # 包ID
    project_id: str  # 项目ID
    candidates: List[Dict[str, Any]]  # 候选术语列表（序列化）
    conflicts: List[Dict[str, Any]]  # 冲突列表（序列化）
    created_at: str  # 创建时间（ISO格式）
    expires_at: str  # 过期时间（ISO格式）


class TermConfirmationService:
    """术语确认服务"""

    PACKAGE_EXPIRATION_HOURS = 24  # 确认包过期时间（小时）

    def __init__(self, storage: GlossaryStorage):
        """
        初始化确认服务

        Args:
            storage: 术语存储
        """
        self.storage = storage

    def prepare_confirmation(
        self,
        candidates: List[TermCandidate],
        conflicts: List[TermConflict],
        project_id: str
    ) -> str:
        """
        准备确认包

        Args:
            candidates: 候选术语列表
            conflicts: 冲突列表
            project_id: 项目ID

        Returns:
            确认包ID
        """
        # 生成包ID
        package_id = str(uuid.uuid4())

        # 创建确认包
        now = datetime.now()
        expires_at = now + timedelta(hours=self.PACKAGE_EXPIRATION_HOURS)

        package = ConfirmationPackage(
            package_id=package_id,
            project_id=project_id,
            candidates=[self._serialize_candidate(c) for c in candidates],
            conflicts=[self._serialize_conflict(c) for c in conflicts],
            created_at=now.isoformat(),
            expires_at=expires_at.isoformat()
        )

        # 保存确认包
        self._save_package(package, project_id)

        return package_id

    def load_confirmation_package(
        self,
        package_id: str,
        project_id: str
    ) -> Optional[ConfirmationPackage]:
        """
        加载确认包

        Args:
            package_id: 包ID
            project_id: 项目ID

        Returns:
            确认包（如果存在且未过期）
        """
        package_path = self._get_package_path(package_id, project_id)

        if not package_path.exists():
            return None

        # 加载包数据
        package_data = json.loads(package_path.read_text(encoding='utf-8'))
        package = ConfirmationPackage(**package_data)

        # 检查是否过期
        expires_at = datetime.fromisoformat(package.expires_at)
        if datetime.now() > expires_at:
            # 删除过期包
            package_path.unlink()
            return None

        return package

    def apply_decision(
        self,
        package_id: str,
        decision: ConfirmationDecision,
        project_id: str
    ) -> None:
        """
        应用确认决策

        Args:
            package_id: 包ID
            decision: 确认决策
            project_id: 项目ID
        """
        # 加载确认包
        package = self.load_confirmation_package(package_id, project_id)
        if not package:
            raise ValueError(f"Confirmation package not found or expired: {package_id}")

        # 获取候选术语
        if decision.candidate_index >= len(package.candidates):
            raise ValueError(f"Invalid candidate index: {decision.candidate_index}")

        candidate_data = package.candidates[decision.candidate_index]

        # 根据动作处理
        if decision.action == ConfirmationAction.ACCEPT:
            self._apply_accept(candidate_data, decision, project_id)
        elif decision.action == ConfirmationAction.MODIFY:
            self._apply_modify(candidate_data, decision, project_id)
        elif decision.action == ConfirmationAction.SKIP:
            # 跳过，不做任何操作
            pass
        elif decision.action == ConfirmationAction.USE_EXISTING:
            # 使用已有术语，不添加新术语
            pass
        elif decision.action == ConfirmationAction.REJECT:
            # 拒绝，不做任何操作
            pass

    def delete_confirmation_package(
        self,
        package_id: str,
        project_id: str
    ) -> None:
        """
        删除确认包

        Args:
            package_id: 包ID
            project_id: 项目ID
        """
        package_path = self._get_package_path(package_id, project_id)
        if package_path.exists():
            package_path.unlink()

    def _apply_accept(
        self,
        candidate_data: Dict[str, Any],
        decision: ConfirmationDecision,
        project_id: str
    ) -> None:
        """应用 ACCEPT 决策"""
        if not decision.final_translation:
            raise ValueError("final_translation is required for ACCEPT action")

        self._add_term(candidate_data, decision.final_translation, project_id)

    def _apply_modify(
        self,
        candidate_data: Dict[str, Any],
        decision: ConfirmationDecision,
        project_id: str
    ) -> None:
        """应用 MODIFY 决策"""
        if not decision.final_translation:
            raise ValueError("final_translation is required for MODIFY action")

        self._add_term(candidate_data, decision.final_translation, project_id)

    def _add_term(
        self,
        candidate_data: Dict[str, Any],
        translation: str,
        project_id: str
    ) -> None:
        """添加术语到存储"""
        # 生成术语ID
        term_id = str(uuid.uuid4())

        # 推断策略
        strategy = "preserve" if candidate_data["original"] == translation else "translate"

        # 创建术语
        term = Term(
            id=term_id,
            original=candidate_data["original"],
            translation=translation,
            strategy=strategy,
            status="active"
        )

        # 创建元数据
        metadata = TermMetadata(
            term_id=term_id,
            scope="project",
            project_id=project_id,
            term_original=candidate_data["original"],
            term_translation=translation,
            context=candidate_data.get("context"),
            confidence=candidate_data.get("confidence")
        )

        # 添加到存储
        self.storage.add_term(term, metadata)

    def _serialize_candidate(self, candidate: TermCandidate) -> Dict[str, Any]:
        """序列化候选术语"""
        return {
            "original": candidate.original,
            "suggested_translation": candidate.suggested_translation,
            "confidence": candidate.confidence,
            "context": candidate.context,
            "occurrence_count": candidate.occurrence_count,
            "hit_title": candidate.hit_title,
            "sections": candidate.sections
        }

    def _serialize_conflict(self, conflict: TermConflict) -> Dict[str, Any]:
        """序列化冲突"""
        return {
            "original": conflict.original,
            "existing_term_id": conflict.existing_term_id,
            "existing_translation": conflict.existing_translation,
            "existing_scope": conflict.existing_scope,
            "suggested_translation": conflict.suggested_translation,
            "context": conflict.context,
            "conflict_type": conflict.conflict_type.value
        }

    def _save_package(self, package: ConfirmationPackage, project_id: str) -> None:
        """保存确认包"""
        package_path = self._get_package_path(package.package_id, project_id)
        package_path.parent.mkdir(parents=True, exist_ok=True)

        package_data = asdict(package)
        package_path.write_text(
            json.dumps(package_data, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )

    def _get_package_path(self, package_id: str, project_id: str) -> Path:
        """获取确认包路径"""
        return (
            self.storage.base_path /
            "projects" /
            project_id /
            "artifacts" /
            "term-confirmation" /
            f"{package_id}.json"
        )
