"""
Timezone Utils - 时区转换工具模块

提供美国时区与北京时间之间的转换功能。
使用 zoneinfo 实现精确的时区转换，包括夏令时自动处理。
"""

import re
from datetime import datetime
from typing import Optional, Tuple
from zoneinfo import ZoneInfo


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

def parse_datetime_input(input_str: str) -> Tuple[Optional[datetime], Optional[str]]:
    """
    解析多种时间格式

    支持格式:
    - M/D/YY at h:mm am/pm tz (如: 1/19/26 at 4:00 pm cdt)
    - M/D/YY h:mm am/pm tz (如: 1/15/26 2:00 pm cdt)
    - M/D/YY h am/pm tz (如: 1/26/26 4pm cdt) - 新支持的格式
    - M/D/YYYY h:mm am/pm tz (如: 1/15/2026 2:00 pm cst)
    - YYYY-MM-DD HH:mm tz (如: 2025-01-15 14:00 est)
    - MM/DD/YYYY h:mm am/pm (如: 01/15/2026 2:00 pm)
    - January 15, 2026 2:00 pm est
    - 今天下午3点
    - 明天上午9点

    默认时区: CDT (美中时间)

    Args:
        input_str: 时间字符串

    Returns:
        Tuple[datetime, str]: (解析后的日期时间, 检测到的时区缩写)
    """
    input_str = input_str.strip()

    # 处理中文相对时间表达
    if "今天" in input_str or "明天" in input_str:
        return parse_relative_chinese_time(input_str)

    input_lower = input_str.lower()

    # 尝试解析格式: 1/15/26 at 2:00 pm cdt 或 1/15/2026 2:00 pm cst
    # 添加了对 "at" 关键字的支持
    pattern1 = r'(\d{1,2})/(\d{1,2})/(\d{2,4})\s+(?:at\s+)?(\d{1,2}):(\d{2})\s*(am|pm)?\s*(est|edt|cst|cdt|mst|mdt|pst|pdt)?'
    match = re.search(pattern1, input_lower)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        year = int(match.group(3))
        if year < 100:
            year += 2000 if year >= 26 else 2100  # 假设 26-99 是 2026-2099
        hour = int(match.group(4))
        minute = int(match.group(5))
        ampm = match.group(6)
        tz_abbr = match.group(7)

        if ampm == "pm" and hour != 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0

        return datetime(year, month, day, hour, minute), tz_abbr

    # 尝试解析格式: M/D/YY h am/pm tz（不带分钟，支持4pm格式）
    pattern_no_minutes = r'(\d{1,2})/(\d{1,2})/(\d{2,4})\s+(?:at\s+)?(\d{1,2})\s*(am|pm)\s*(est|edt|cst|cdt|mst|mdt|pst|pdt)?'
    match = re.search(pattern_no_minutes, input_lower)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        year = int(match.group(3))
        if year < 100:
            year += 2000 if year >= 26 else 2100  # 假设 26-99 是 2026-2099
        hour = int(match.group(4))
        minute = 0  # 分钟设为0
        ampm = match.group(5)
        tz_abbr = match.group(6)

        if ampm == "pm" and hour != 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0

        return datetime(year, month, day, hour, minute), tz_abbr

    # 尝试解析格式: 2025-01-15 14:00 cst
    pattern2 = r'(\d{4})-(\d{1,2})-(\d{1,2})\s+(?:at\s+)?(\d{1,2}):(\d{2})\s*(est|edt|cst|cdt|mst|mdt|pst|pdt)?'
    match = re.search(pattern2, input_lower)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        hour = int(match.group(4))
        minute = int(match.group(5))
        tz_abbr = match.group(6)

        return datetime(year, month, day, hour, minute), tz_abbr

    # 尝试解析格式: January 15, 2026 2:00 pm est
    pattern3 = r'([a-zA-Z]+)\s+(\d{1,2}),?\s*(\d{4})\s+(?:at\s+)?(\d{1,2}):(\d{2})\s*(am|pm)?\s*(est|edt|cst|cdt|mst|mdt|pst|pdt)?'
    match = re.search(pattern3, input_lower)
    if match:
        months = {
            "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
            "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
        }
        month_name = match.group(1)
        month = months.get(month_name.lower())
        if month:
            day = int(match.group(2))
            year = int(match.group(3))
            hour = int(match.group(4))
            minute = int(match.group(5))
            ampm = match.group(6)
            tz_abbr = match.group(7)

            if ampm == "pm" and hour != 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0

            return datetime(year, month, day, hour, minute), tz_abbr

    return None, None


def parse_relative_chinese_time(input_str: str) -> Tuple[Optional[datetime], Optional[str]]:
    """
    解析中文相对时间表达

    支持格式:
    - 今天下午3点
    - 今天上午9点
    - 明天下午3点
    - 明天上午9:30
    """
    import datetime as dt

    now = dt.datetime.now()
    input_lower = input_str.lower().strip()

    # 解析上午/下午
    period_match = re.search(r'(上午|下午|am|pm)', input_lower)
    if period_match:
        period = period_match.group(1)
        is_pm = period in ['下午', 'pm']
    else:
        # 默认为24小时制
        is_pm = False

    # 解析时间
    time_match = re.search(r'(\d{1,2}):?(\d{0,2})\s*(点)?', input_str)
    if not time_match:
        return None, None

    hour = int(time_match.group(1))
    minute = int(time_match.group(2)) if time_match.group(2) else 0

    if is_pm and hour != 12:
        hour += 12
    elif not is_pm and hour == 12:
        hour = 0

    # 解析日期
    if '明天' in input_lower:
        target_date = now + dt.timedelta(days=1)
    elif '今天' in input_lower:
        target_date = now
    else:
        target_date = now

    result = datetime(target_date.year, target_date.month, target_date.day, hour, minute)

    # 尝试检测时区
    tz_match = re.search(r'(est|edt|cst|cdt|mst|mdt|pst|pdt)', input_lower)
    tz_abbr = tz_match.group(1) if tz_match else None

    return result, tz_abbr


# ============ 时区转换 ============

def get_zone_info(tz_name: str) -> ZoneInfo:
    """获取 ZoneInfo 对象，使用缓存"""
    return ZONE_INFO_CACHE.get(tz_name, ZoneInfo(tz_name))


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
    dt_with_tz = dt.replace(tzinfo=source_zone)

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
    # 如果用户指定了时区
    if source_timezone != "auto":
        # 如果是 IANA 标识符，直接返回
        if "/" in source_timezone:
            return source_timezone
        # 如果是缩写，转换为 IANA 标识符
        return US_TIMEZONE_NAMES.get(source_timezone.upper(), "America/Chicago")

    # 自动检测
    if detected_tz:
        return US_TIMEZONE_NAMES.get(detected_tz.upper(), "America/Chicago")

    return "America/Chicago"


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
    dt_with_tz = dt.replace(tzinfo=zone)
    offset = dt_with_tz.utcoffset()

    if offset is None:
        return "UTC"

    offset_seconds = int(offset.total_seconds())
    offset_hours = offset_seconds // 3600
    offset_minutes = (offset_seconds % 3600) // 60

    sign = "+" if offset_hours >= 0 else "-"
    return f"UTC{sign}{abs(offset_hours)}{f':{offset_minutes:02d}' if offset_minutes else ''}"


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
    dt_with_tz = dt.replace(tzinfo=zone)
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
    dt, detected_tz = parse_datetime_input(input_str)

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
    dt, detected_tz = parse_datetime_input(input_str)

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
    dt, detected_tz = parse_datetime_input(input_str)

    if dt is None:
        return {
            "success": False,
            "message": f"无法解析时间格式: {input_str}",
            "original": input_str
        }

    # 确定源时区
    if from_tz == "auto":
        # 检测输入中是否包含时区信息
        if detected_tz:
            source_tz = US_TIMEZONE_NAMES.get(detected_tz.upper(), "Asia/Shanghai")
        else:
            source_tz = "Asia/Shanghai"  # 默认为北京时间
    elif from_tz.lower() == "beijing":
        source_tz = "Asia/Shanghai"
    else:
        source_tz = US_TIMEZONE_NAMES.get(from_tz.upper(), "Asia/Shanghai")

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
        target_tz = target_tz_map.get(to_tz.lower(), "Asia/Shanghai")
        target_dt = convert_timezone(dt, source_tz, target_tz)
        return {
            "success": True,
            "original": input_str,
            "source_tz": TZ_DISPLAY_NAMES.get(source_tz, source_tz),
            "result": format_time(target_dt, target_tz)
        }
