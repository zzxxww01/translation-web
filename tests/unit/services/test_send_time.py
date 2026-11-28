import pytest

from src.services.send_time import resolve_send_time, resolve_tz
from src.services.slack_ai import parse_extraction


@pytest.mark.parametrize("raw,shanghai,label,assumed", [
    # 没写时区：按美中算；11 月是冬令时，美中 UTC-6，北京晚 14 小时
    ({"date": "2026-11-29", "time": "09:00", "tz": None}, "2026-11-29T23:00:00+08:00", "11月29日 周日 23:00", True),
    # 夏令时：美东 UTC-4
    ({"date": "2026-07-01", "time": "21:30", "tz": "ET"}, "2026-07-02T09:30:00+08:00", "7月2日 周四 09:30", False),
    # EST 写错季节也按当天实际时间算
    ({"date": "2026-07-01", "time": "08:00", "tz": "EST"}, "2026-07-01T20:00:00+08:00", "7月1日 周三 20:00", False),
    ({"date": "2026-11-30", "time": "16:00", "tz": "PT"}, "2026-12-01T08:00:00+08:00", "12月1日 周二 08:00", False),
    ({"date": "2026-11-30", "time": "10:00", "tz": "Beijing"}, "2026-11-30T10:00:00+08:00", "11月30日 周一 10:00", False),
    ({"date": "2026-11-30", "time": "10:00", "tz": "UTC"}, "2026-11-30T18:00:00+08:00", "11月30日 周一 18:00", False),
])
def test_converts_to_shanghai(raw, shanghai, label, assumed):
    result = resolve_send_time({"text": "post at 9am", **raw})
    assert result["shanghai"] == shanghai
    assert result["shanghai_label"] == label
    assert result["tz_assumed"] is assumed
    assert result["date_only"] is False


def test_date_only_unknown_tz_and_bad_input():
    only = resolve_send_time({"text": "sch 11/18", "date": "2026-11-18", "time": None, "tz": None})
    assert only["date_only"] and only["shanghai"] is None
    assert only["shanghai_label"] == "11月18日（美中日期，没说几点）"
    assert resolve_tz("CST") == ("America/Chicago", True)  # 美国语境的 CST 是美中
    assert resolve_tz("Mars time") == ("America/Chicago", False)
    assert resolve_send_time({"date": "tomorrow", "time": "09:00"}) is None
    assert resolve_send_time(None) is None
    assert resolve_send_time({"date": "2026-11-29", "time": "25:00"})["date_only"] is True


def test_extraction_keeps_send_time_only_for_posts():
    data = {"has_post": True, "source_text": "Hello", "message_ids": [2], "image_ids": [], "candidates": [],
            "send_time": {"text": "post tmw 9am", "message_id": "3", "date": "2026-11-29", "time": "09:00", "tz": None}}
    assert parse_extraction(data, [])["send_time"]["message_id"] == 3
    assert parse_extraction({**data, "send_time": None}, [])["send_time"] is None
    assert parse_extraction({**data, "has_post": False, "source_text": "", "note": "讨论"}, [])["send_time"] is None
