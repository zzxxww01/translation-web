"""
Model configuration manager for phase-based translation.
支持按阶段配置不同模型，或用户覆盖使用单一模型。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml


class ModelConfig:
    """Manages model selection for different translation phases."""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "translation_models.yaml"

        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

    def get_model_for_phase(
        self,
        phase: str,
        model_override: Optional[str] = None,
        profile: str = "default"
    ) -> dict:
        """
        Get model configuration for a specific phase.

        Args:
            phase: Translation phase (phase0_prescan, phase1_draft, phase2_refine, phase3_review)
            model_override: User-specified model to use for all phases (e.g., "deepseek-v3")
            profile: Configuration profile (default, fast, premium)

        Returns:
            dict with keys: model, temperature, description
        """
        # User override takes precedence
        if model_override:
            if model_override in self.config.get("model_overrides", {}):
                return self.config["model_overrides"][model_override]["all_phases"]
            # If override model not in config, use it directly with default settings
            return {
                "model": model_override,
                "temperature": 0.3,
                "description": f"User-specified model: {model_override}"
            }

        # Use profile configuration
        profile_config = self.config.get(profile, self.config["default"])

        # Check if profile has all_phases (single model for all phases)
        if "all_phases" in profile_config:
            return profile_config["all_phases"]

        # Return phase-specific configuration
        if phase in profile_config:
            return profile_config[phase]

        # Fallback to default phase0 config
        return self.config["default"]["phase0_prescan"]

    def get_available_models(self) -> list[str]:
        """Get list of available model overrides."""
        return list(self.config.get("model_overrides", {}).keys())

    def get_available_profiles(self) -> list[str]:
        """Get list of available configuration profiles."""
        return [k for k in self.config.keys() if k != "model_overrides"]


# Global instance
_model_config: Optional[ModelConfig] = None


def get_model_config() -> ModelConfig:
    """Get or create global ModelConfig instance."""
    global _model_config
    if _model_config is None:
        _model_config = ModelConfig()
    return _model_config
