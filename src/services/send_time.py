"""Slack 帖子的建议发送时间：模型从 thread 里摘出「哪天几点、写的什么时区」，这里换算成上海时间。

换算不交给模型：时区缩写对照、夏令时都在这里用 zoneinfo 算。没写时区按美中时间（同事排期的习惯）。
"""
from __future__ import annotations

import re
from datetime import date as Date, datetime
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

DEFAULT_TZ = "America/Chicago"
SHANGHAI = ZoneInfo("Asia/Shanghai")

# 美国语境下 CST 是美中（不是中国标准时间）；EST / EDT 写哪个都按当天实际的美东时间算
_ALIASES = {
    "ET": "America/New_York", "EST": "America/New_York", "EDT": "America/New_York", "EASTERN": "America/New_York",
    "CT": "America/Chicago", "CST": "America/Chicago", "CDT": "America/Chicago", "CENTRAL": "America/Chicago",
    "MT": "America/Denver", "MST": "America/Denver", "MDT": "America/Denver", "MOUNTAIN": "America/Denver",
    "PT": "America/Los_Angeles", "PST": "America/Los_Angeles", "PDT": "America/Los_Angeles", "PACIFIC": "America/Los_Angeles",
    "UTC": "UTC", "GMT": "UTC", "Z": "UTC",
    "BJT": "Asia/Shanghai", "BEIJING": "Asia/Shanghai", "CHINA": "Asia/Shanghai", "SHANGHAI": "Asia/Shanghai",
    "HKT": "Asia/Hong_Kong", "SGT": "Asia/Singapore", "JST": "Asia/Tokyo", "KST": "Asia/Seoul",
    "BST": "Europe/London", "LONDON": "Europe/London", "CET": "Europe/Paris", "CEST": "Europe/Paris",
}
_LABELS = {
    "America/New_York": "美东", "America/Chicago": "美中", "America/Denver": "美山", "America/Los_Angeles": "美西",
    "UTC": "UTC", "Asia/Shanghai": "北京",
}
_WEEKDAYS = "一二三四五六日"


def resolve_tz(value: Any) -> tuple[str, bool]:
    """(IANA 时区, 是不是原文写明的)；认不出或没写 → 美中。"""
    text = str(value or "").strip()
    if not text:
        return DEFAULT_TZ, False
    key = re.sub(r"[^A-Za-z]", "", text).upper()
    if key in _ALIASES:
        return _ALIASES[key], True
    try:
        ZoneInfo(text)
        return text, True
    except (KeyError, ValueError):
        return DEFAULT_TZ, False


def _label(moment: datetime) -> str:
    return f"{moment.month}月{moment.day}日 周{_WEEKDAYS[moment.weekday()]} {moment:%H:%M}"


def resolve_send_time(raw: Any) -> Optional[Dict[str, Any]]:
    """模型给的 {text, message_id, date, time, tz} → 换算好的建议发送时间；没有日期（或日期不合法）返回 None。"""
    if not isinstance(raw, dict):
        return None
    try:
        day = Date.fromisoformat(str(raw.get("date") or "").strip())
    except ValueError:
        return None
    tz_name, explicit = resolve_tz(raw.get("tz"))
    zone = ZoneInfo(tz_name)
    clock = re.fullmatch(r"(\d{1,2}):(\d{2})", str(raw.get("time") or "").strip())
    result: Dict[str, Any] = {
        "text": str(raw.get("text") or "").strip()[:200],
        "source_tz": tz_name,
        "source_label": _LABELS.get(tz_name, tz_name),
        "tz_assumed": not explicit,
    }
    if not clock or int(clock[1]) > 23 or int(clock[2]) > 59:
        # 只说了哪天（「sch 11/18」）：只给日期，不换算钟点
        return {**result, "date_only": True, "source_local": day.isoformat(),
                "shanghai": None, "shanghai_label": f"{day.month}月{day.day}日（{result['source_label']}日期，没说几点）"}
    local = datetime(day.year, day.month, day.day, int(clock[1]), int(clock[2]), tzinfo=zone)
    shanghai = local.astimezone(SHANGHAI)
    return {**result, "date_only": False, "source_local": f"{local:%Y-%m-%d %H:%M}",
            "shanghai": shanghai.isoformat(), "shanghai_label": _label(shanghai)}
