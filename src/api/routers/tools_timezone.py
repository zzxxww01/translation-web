"""
Tools timezone-convert endpoint.
"""

from fastapi import APIRouter

from ..middleware import BadRequestException
from ..utils.timezone import (
    convert_all_timezones,
    format_time,
    parse_datetime_input,
    resolve_timezone,
)
from .tools_models import TimezoneConvertRequest, TimezoneConvertResponse


router = APIRouter()


@router.post("/timezone-convert", response_model=TimezoneConvertResponse)
async def convert_timezone_api(request: TimezoneConvertRequest):
    """
    时区转换 API

    支持美国各时区与北京时间的互转
    使用 zoneinfo 实现精确的时区转换，自动处理夏令时
    默认时区: CDT (美中时间)
    """
    if not request.input.strip():
        raise BadRequestException(detail="请输入时间")

    dt, detected_tz = parse_datetime_input(request.input)
    if dt is None:
        raise BadRequestException(
            detail="无法解析时间格式。支持的格式示例: 1/26/26 4pm cdt, 1/15/26 2:00 pm cdt, 2025-01-15 14:00 est, 今天下午3点"
        )

    source_tz = resolve_timezone(request.source_timezone, detected_tz)
    times = convert_all_timezones(dt, source_tz)
    original_formatted = format_time(dt, source_tz)

    return TimezoneConvertResponse(
        original=original_formatted,
        est=format_time(times["est"], "America/New_York"),
        cst=format_time(times["cst"], "America/Chicago"),
        mst=format_time(times["mst"], "America/Denver"),
        pst=format_time(times["pst"], "America/Los_Angeles"),
        beijing=format_time(times["beijing"], "Asia/Shanghai"),
    )
