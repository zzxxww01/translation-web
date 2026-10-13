"""
Timezone Utils - 时区转换工具模块

提供美国时区与北京时间之间的转换功能。
使用 zoneinfo 实现精确的时区转换，包括夏令时自动处理。
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


# ============ 时区配置 ============

# 使用 IANA 时区标识符
US_TIMEZONE_NAMES = {
    "EST": "America/New_York",   # 美东
    "EDT": "America/New_York",
    "CST": "America/Chicago",    # 美中
    "CDT": "America/Chicago",
    "MST": "America/Denver",     # 美山
    "MDT": "America/Denver",
    "PST": "America/Los_Angeles", # 美西
    "PDT": "America/Los_Angeles",
}

# Legacy UI aliases represent geographic zones with automatic DST, not fixed offsets.
US_TIMEZONE_NAMES.update({
    "ET": "America/New_York", "CT": "America/Chicago",
    "MT": "America/Denver", "PT": "America/Los_Angeles",
    "EST5EDT": "America/New_York", "CST6CDT": "America/Chicago",
    "MST7MDT": "America/Denver", "PST8PDT": "America/Los_Angeles",
    "UTC": "UTC", "GMT": "UTC", "BEIJING": "Asia/Shanghai",
})

# 时区 ZoneInfo 对象缓存
ZONE_INFO_CACHE = {
    "America/New_York": ZoneInfo("America/New_York"),
    "America/Chicago": ZoneInfo("America/Chicago"),
    "America/Denver": ZoneInfo("America/Denver"),
    "America/Los_Angeles": ZoneInfo("America/Los_Angeles"),
    "Asia/Shanghai": ZoneInfo("Asia/Shanghai"),
}

# 显示名称映射
TZ_DISPLAY_NAMES = {
    "America/New_York": "美东时间",
    "America/Chicago": "美中时间",
    "America/Denver": "美山时间",
    "America/Los_Angeles": "美西时间",
    "Asia/Shanghai": "北京时间",
}

# 时区缩写
TZ_ABBREVS = {
    "America/New_York": "ET",
    "America/Chicago": "CT",
    "America/Denver": "MT",
    "America/Los_Angeles": "PT",
    "Asia/Shanghai": "北京",
}


# ============ 时间解析 ============

def _clock(hour: int, minute: int, period: Optional[str]) -> tuple[int, int]:
    if period:
        if not 1 <= hour <= 12:
            raise ValueError("12 小时制的小时必须在 1–12 之间")
        hour = hour % 12 + (12 if period.lower() in {"pm", "下午"} else 0)
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError("时间超出有效范围")
    return hour, minute


def _split_zone(value: str) -> tuple[str, Optional[str]]:
    # Only consume a complete suffix. Unknown abbreviations are not silently
    # accepted as the default zone or as trailing prose.
    match = re.search(r"\s+([A-Za-z][A-Za-z0-9_+./-]*)$", value)
    if match and match.group(1).lower() not in {"am", "pm"}:
        suffix = match.group(1)
        if suffix.upper() in US_TIMEZONE_NAMES or "/" in suffix:
            return value[:match.start()].strip(), suffix
    return value, None


def parse_datetime_input(
    input_str: str, source_timezone: str = "auto", *, now: Optional[datetime] = None,
) -> Tuple[Optional[datetime], Optional[str]]:
    """Parse a complete supported input; never accept a truncated valid prefix.

    Relative dates use the source zone, not the server's local calendar date.
    Explicit ISO offsets are accepted to disambiguate fall-back DST hours.
    """
    value, detected = _split_zone(input_str.strip())
    if "今天" in value or "明天" in value:
        return parse_relative_chinese_time(input_str, source_timezone, now=now)
    try:
        reference_zone = get_zone_info(resolve_timezone(source_timezone, detected))
        reference = now.astimezone(reference_zone) if now is not None else datetime.now(reference_zone)
        # datetime.fromisoformat accepts explicit numeric offsets and ISO dates.
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})", value):
            return datetime.fromisoformat(value.replace("Z", "+00:00")), detected
        patterns = (
            (r"(?P<month>\d{1,2})/(?P<day>\d{1,2})(?:/(?P<year>\d{2}|\d{4}))?\s+(?:at\s+)?(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<period>am|pm)?", "numeric"),
            (r"(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})[T ](?:at\s+)?(?P<hour>\d{1,2}):(?P<minute>\d{2})\s*(?P<period>am|pm)?", "numeric"),
            (r"(?P<month>[a-z]+)\s+(?P<day>\d{1,2}),?\s+(?P<year>\d{4})\s+(?:at\s+)?(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<period>am|pm)?", "month_name"),
        )
        months = {name.lower(): i for i, name in enumerate(("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"), 1)}
        months.update({name[:3]: i for name, i in list(months.items())})
        for pattern, kind in patterns:
            match = re.fullmatch(pattern, value, re.I)
            if not match:
                continue
            data = match.groupdict()
            year_text = data.get("year")
            year = int(year_text) if year_text else reference.year
            if year_text and len(year_text) == 2:
                year += reference.year // 100 * 100
                if year > reference.year + 20:
                    year -= 100
            month = months[data["month"].lower()] if kind == "month_name" else int(data["month"])
            hour, minute = _clock(int(data["hour"]), int(data.get("minute") or 0), data.get("period"))
            return datetime(year, month, int(data["day"]), hour, minute), detected
    except (ValueError, KeyError, ZoneInfoNotFoundError):
        return None, None
    return None, None


def parse_relative_chinese_time(
    input_str: str, source_timezone: str = "auto", *, now: Optional[datetime] = None,
) -> Tuple[Optional[datetime], Optional[str]]:
    value, detected = _split_zone(input_str.strip())
    match = re.fullmatch(
        r"(今天|明天)\s*(上午|下午|am|pm)?\s*(\d{1,2})(?:[:：](\d{1,2})|点(?:(\d{1,2})分?|半)?)\s*", value, re.I,
    )
    if not match:
        return None, None
    try:
        hour, minute = _clock(int(match.group(3)), 30 if value.endswith("半") else int(match.group(4) or match.group(5) or 0), match.group(2))
        zone = get_zone_info(resolve_timezone(source_timezone, detected))
        reference = now.astimezone(zone) if now is not None else datetime.now(zone)
        day = reference.date() + timedelta(days=int(match.group(1) == "明天"))
        return datetime(day.year, day.month, day.day, hour, minute), detected
    except (ValueError, ZoneInfoNotFoundError):
        return None, None


# ============ 时区转换 ============

def get_zone_info(tz_name: str) -> ZoneInfo:
    """获取 ZoneInfo 对象，使用缓存"""
    return ZONE_INFO_CACHE[tz_name] if tz_name in ZONE_INFO_CACHE else ZoneInfo(tz_name)


def convert_timezone(dt: datetime, source_tz: str, target_tz: str) -> datetime:
    """
    在时区之间转换时间（精确版本，处理夏令时）

    Args:
        dt: 源日期时间（无时区信息的 naive datetime）
        source_tz: 源时区名称 (IANA 标识符)
        target_tz: 目标时区名称 (IANA 标识符)

    Returns:
        datetime: 转换后的日期时间
    """
    source_zone = get_zone_info(source_tz)
    target_zone = get_zone_info(target_tz)

    # 将 naive datetime 视为源时区的时间
    if dt.tzinfo is not None:
        dt_with_tz = dt.astimezone(source_zone)
    else:
        dt_with_tz = dt.replace(tzinfo=source_zone)
        round_trip = dt_with_tz.astimezone(timezone.utc).astimezone(source_zone).replace(tzinfo=None)
        if round_trip != dt:
            raise ValueError("该本地时间因夏令时切换不存在，请选择有效时间")
        if dt.replace(tzinfo=source_zone, fold=0).utcoffset() != dt.replace(tzinfo=source_zone, fold=1).utcoffset():
            raise ValueError("该本地时间在夏令时切换时出现两次，请用带 UTC 偏移的 ISO 时间明确时刻")

    # 转换为目标时区
    return dt_with_tz.astimezone(target_zone).replace(tzinfo=None)


def convert_all_timezones(dt: datetime, source_tz: str) -> dict:
    """
    将给定时间转换为所有美国时区和北京时间
    使用精确的时区转换，自动处理夏令时

    Args:
        dt: 源日期时间
        source_tz: 源时区 (IANA 标识符，如 "America/New_York")

    Returns:
        dict: 包含各时区时间的字典
    """
    return {
        "est": convert_timezone(dt, source_tz, "America/New_York"),
        "cst": convert_timezone(dt, source_tz, "America/Chicago"),
        "mst": convert_timezone(dt, source_tz, "America/Denver"),
        "pst": convert_timezone(dt, source_tz, "America/Los_Angeles"),
        "beijing": convert_timezone(dt, source_tz, "Asia/Shanghai"),
    }


def format_time(dt: datetime, tz_name: str) -> str:
    """
    格式化时间为可读字符串

    Args:
        dt: 日期时间
        tz_name: 时区名称 (IANA 标识符)

    Returns:
        str: 格式化后的时间字符串，包含时区缩写
    """
    if dt.tzinfo is not None:
        dt = dt.astimezone(get_zone_info(tz_name))
    abbrev = TZ_ABBREVS.get(tz_name, tz_name.split("/")[-1])
    return f"{dt.strftime('%Y-%m-%d %H:%M')} ({abbrev})"


def resolve_timezone(source_timezone: str, detected_tz: Optional[str]) -> str:
    """
    解析并确定最终使用的时区

    Args:
        source_timezone: 用户指定的源时区
        detected_tz: 从输入中检测到的时区缩写

    Returns:
        str: 最终的时区 IANA 标识符 (如 America/New_York)
    """
    supplied = source_timezone.strip()
    name = (detected_tz or "America/Chicago") if supplied.lower() == "auto" else supplied
    resolved = US_TIMEZONE_NAMES.get(name.upper(), name)
    try:
        get_zone_info(resolved)
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise ValueError("未知时区，请使用有效的 IANA 时区或受支持的缩写") from exc
    return resolved


def get_timezone_offset_display(dt: datetime, tz_name: str) -> str:
    """
    获取时区偏移量显示（如 UTC-5, UTC+8）

    Args:
        dt: 日期时间
        tz_name: 时区名称

    Returns:
        str: UTC 偏移量
    """
    zone = get_zone_info(tz_name)
    dt_with_tz = dt.astimezone(zone) if dt.tzinfo is not None else dt.replace(tzinfo=zone)
    offset = dt_with_tz.utcoffset()

    if offset is None:
        return "UTC"

    offset_seconds = int(offset.total_seconds())
    hours, minutes = divmod(abs(offset_seconds) // 60, 60)
    sign = "+" if offset_seconds >= 0 else "-"
    return f"UTC{sign}{hours}{f':{minutes:02d}' if minutes else ''}"


def is_dst(dt: datetime, tz_name: str) -> bool:
    """
    判断给定时间是否为夏令时

    Args:
        dt: 日期时间
        tz_name: 时区名称

    Returns:
        bool: 是否为夏令时
    """
    zone = get_zone_info(tz_name)
    dt_with_tz = dt.astimezone(zone) if dt.tzinfo is not None else dt.replace(tzinfo=zone)
    return bool(dt_with_tz.dst())


# ============ 便捷转换函数 ============

def convert_us_to_beijing(
    input_str: str,
    source_timezone: str = "auto"
) -> dict:
    """
    将美国时区时间转换为北京时间

    支持多种格式输入:
    - 1/19/26 at 4:00 pm cdt
    - 1/23/26 8:00 am cst
    - 2026-01-19 16:00 est

    Args:
        input_str: 时间字符串
        source_timezone: 源时区 ("auto" 自动检测, 或指定 "est"/"cst"/"mst"/"pst")

    Returns:
        dict: {
            "success": bool,
            "message": str,
            "original": str,
            "source_tz": str,
            "beijing_time": str,
            "all_timezones": dict
        }
    """
    dt, detected_tz = parse_datetime_input(input_str, source_timezone)

    if dt is None:
        return {
            "success": False,
            "message": f"无法解析时间格式: {input_str}",
            "original": input_str
        }

    # 解析源时区
    source_tz = resolve_timezone(source_timezone, detected_tz)

    # 转换为北京时间
    beijing_dt = convert_timezone(dt, source_tz, "Asia/Shanghai")

    # 获取所有时区的时间
    all_timezones = convert_all_timezones(dt, source_tz)

    # 格式化输出
    return {
        "success": True,
        "message": "转换成功",
        "original": input_str,
        "original_parsed": dt.strftime("%Y-%m-%d %H:%M:%S"),
        "source_tz": f"{TZ_DISPLAY_NAMES.get(source_tz, source_tz)} ({get_timezone_offset_display(dt, source_tz)})",
        "beijing_time": f"{beijing_dt.strftime('%Y-%m-%d %H:%M')} (北京)",
        "beijing_time_full": format_time(beijing_dt, "Asia/Shanghai"),
        "is_dst": is_dst(dt, source_tz),
        "all_timezones": {
            "美东 (ET)": format_time(all_timezones["est"], "America/New_York"),
            "美中 (CT)": format_time(all_timezones["cst"], "America/Chicago"),
            "美山 (MT)": format_time(all_timezones["mst"], "America/Denver"),
            "美西 (PT)": format_time(all_timezones["pst"], "America/Los_Angeles"),
            "北京": format_time(all_timezones["beijing"], "Asia/Shanghai"),
        }
    }


def convert_beijing_to_us(
    input_str: str,
    target_timezone: str = "all"
) -> dict:
    """
    将北京时间转换为美国时区时间

    支持多种格式输入:
    - 2026-01-19 16:00
    - 1/19/26 at 4:00 pm
    - 2026年1月19日 下午4点

    Args:
        input_str: 时间字符串（北京时间）
        target_timezone: 目标时区 ("all" 返回所有时区, 或指定 "est"/"cst"/"mst"/"pst")

    Returns:
        dict: 转换结果
    """
    dt, detected_tz = parse_datetime_input(input_str, "Asia/Shanghai")

    if dt is None:
        return {
            "success": False,
            "message": f"无法解析时间格式: {input_str}",
            "original": input_str
        }

    # 获取所有美国时区的时间
    all_timezones = convert_all_timezones(dt, "Asia/Shanghai")

    # 格式化输出
    result = {
        "success": True,
        "message": "转换成功",
        "original": input_str,
        "original_parsed": dt.strftime("%Y-%m-%d %H:%M:%S"),
        "source_tz": f"北京时间 ({get_timezone_offset_display(dt, 'Asia/Shanghai')})",
    }

    if target_timezone == "all":
        result["all_timezones"] = {
            "美东 (ET)": format_time(all_timezones["est"], "America/New_York"),
            "美中 (CT)": format_time(all_timezones["cst"], "America/Chicago"),
            "美山 (MT)": format_time(all_timezones["mst"], "America/Denver"),
            "美西 (PT)": format_time(all_timezones["pst"], "America/Los_Angeles"),
        }
    else:
        target_tz_map = {
            "est": ("est", "America/New_York", "美东"),
            "cst": ("cst", "America/Chicago", "美中"),
            "mst": ("mst", "America/Denver", "美山"),
            "pst": ("pst", "America/Los_Angeles", "美西"),
        }
        if target_timezone.lower() in target_tz_map:
            key, iana_tz, display_name = target_tz_map[target_timezone.lower()]
            result["target_time"] = format_time(all_timezones[key], iana_tz)
            result["target_tz"] = f"{display_name}时间 ({get_timezone_offset_display(all_timezones[key], iana_tz)})"
            result["is_dst"] = is_dst(all_timezones[key], iana_tz)

    return result


def quick_convert(
    input_str: str,
    from_tz: str = "auto",
    to_tz: str = "beijing"
) -> dict:
    """
    快速时区转换 - 自动检测输入时区并转换

    Args:
        input_str: 时间字符串
        from_tz: 源时区 ("auto" 自动检测, "beijing", 或指定美国时区)
        to_tz: 目标时区 ("beijing", "all", 或指定美国时区)

    Returns:
        dict: 转换结果
    """
    _, suffix = _split_zone(input_str.strip())
    parse_zone = (suffix or "Asia/Shanghai") if from_tz.lower() == "auto" else from_tz
    dt, detected_tz = parse_datetime_input(input_str, parse_zone)

    if dt is None:
        return {
            "success": False,
            "message": f"无法解析时间格式: {input_str}",
            "original": input_str
        }

    # 确定源时区
    if from_tz.lower() == "auto":
        # 检测输入中是否包含时区信息
        if detected_tz:
            source_tz = resolve_timezone("auto", detected_tz)
        else:
            source_tz = "Asia/Shanghai"  # 默认为北京时间
    elif from_tz.lower() == "beijing":
        source_tz = "Asia/Shanghai"
    else:
        source_tz = resolve_timezone(from_tz, None)

    # 确定目标时区
    if to_tz.lower() == "beijing":
        target_dt = convert_timezone(dt, source_tz, "Asia/Shanghai")
        return {
            "success": True,
            "original": input_str,
            "source_tz": TZ_DISPLAY_NAMES.get(source_tz, source_tz),
            "result": format_time(target_dt, "Asia/Shanghai")
        }
    elif to_tz.lower() == "all":
        all_timezones = convert_all_timezones(dt, source_tz)
        return {
            "success": True,
            "original": input_str,
            "source_tz": TZ_DISPLAY_NAMES.get(source_tz, source_tz),
            "result": {
                "美东 (ET)": format_time(all_timezones["est"], "America/New_York"),
                "美中 (CT)": format_time(all_timezones["cst"], "America/Chicago"),
                "美山 (MT)": format_time(all_timezones["mst"], "America/Denver"),
                "美西 (PT)": format_time(all_timezones["pst"], "America/Los_Angeles"),
                "北京": format_time(all_timezones["beijing"], "Asia/Shanghai"),
            }
        }
    else:
        target_tz_map = {
            "est": "America/New_York",
            "cst": "America/Chicago",
            "mst": "America/Denver",
            "pst": "America/Los_Angeles",
        }
        target_tz = resolve_timezone(to_tz, None)
        target_dt = convert_timezone(dt, source_tz, target_tz)
        return {
            "success": True,
            "original": input_str,
            "source_tz": TZ_DISPLAY_NAMES.get(source_tz, source_tz),
            "result": format_time(target_dt, target_tz)
        }
