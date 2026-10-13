"""Canonical, versioned quick-edit instructions shared with the web frontend."""
import json
from pathlib import Path

OPTION_PATH = Path(__file__).resolve().parents[2] / "config" / "editing_options.json"
_payload = json.loads(OPTION_PATH.read_text(encoding="utf-8"))
OPTION_VERSION = _payload["version"]
EDITING_OPTIONS = _payload["options"]
OPTIONS_BY_ID = {item["id"]: item for item in EDITING_OPTIONS}
POST_OPTIMIZE_OPTIONS = {key: item["instruction"] for key, item in OPTIONS_BY_ID.items()}
OPTION_SUMMARIES = {key: item["description"] for key, item in OPTIONS_BY_ID.items()}

def history_option_summary(option_id: str, version: str | None = None) -> str:
    if version == OPTION_VERSION and option_id in OPTIONS_BY_ID:
        return f"历史操作（{version}）：{OPTION_SUMMARIES[option_id]}。仅供参考，当前要求优先。"
    # Old IDs are not proof of the new instruction text; never resurrect legacy rules.
    return f"历史操作：{option_id}（旧版或版本未知；仅记录操作类型，不作为当前指令）"
