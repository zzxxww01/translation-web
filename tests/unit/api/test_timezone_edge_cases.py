from datetime import datetime, timezone
import pytest
from src.api.utils.timezone import (
    parse_datetime_input, parse_relative_chinese_time, resolve_timezone,
    get_timezone_offset_display, convert_timezone,
)

@pytest.mark.parametrize('text,hour,minute', [
    ('今天12点',12,0), ('今天上午12点',0,0), ('今天下午12点',12,0),
    ('明天上午9:30',9,30), ('明天下午3点30分',15,30), ('今天下午3点半',15,30),
])
def test_relative_clock(text,hour,minute):
    result,_ = parse_relative_chinese_time(text, 'Asia/Shanghai')
    assert result is not None and (result.hour,result.minute)==(hour,minute)

@pytest.mark.parametrize('text', ['今天25点','今天上午9:90','今天上午13点','1/15/26 13am','1/15/26 0pm','2026-01-01 12:999','1/15/26 2pm junk','2026-02-30 09:00','今天1230点'])
def test_invalid_clock_rejected_without_raising(text):
    assert parse_datetime_input(text)==(None,None)

def test_relative_date_is_in_source_timezone():
    now=datetime(2026,1,1,2,tzinfo=timezone.utc)
    result,_=parse_datetime_input('今天12点', 'PST8PDT',now=now)
    assert result==datetime(2025,12,31,12)

@pytest.mark.parametrize('alias,expected', [('PST8PDT','America/Los_Angeles'),('EST5EDT','America/New_York'),('UTC','UTC'),('PT','America/Los_Angeles')])
def test_advertised_aliases(alias,expected):
    assert resolve_timezone(alias,None)==expected

def test_unknown_zone_is_not_silently_chicago():
    with pytest.raises(ValueError):resolve_timezone('unknown',None)

@pytest.mark.parametrize('zone,expected', [('America/St_Johns','UTC-3:30'),('Asia/Kathmandu','UTC+5:45'),('UTC','UTC+0')])
def test_fractional_offsets(zone,expected):
    assert get_timezone_offset_display(datetime(2026,1,20),zone)==expected

@pytest.mark.parametrize('dt', [datetime(2026,3,8,2,30),datetime(2026,11,1,1,30)])
def test_ambiguous_or_nonexistent_dst_time_needs_clarification(dt):
    with pytest.raises(ValueError):convert_timezone(dt,'America/New_York','UTC')

def test_explicit_offset_keeps_the_instant():
    dt,_=parse_datetime_input('2026-11-01T01:30-04:00')
    assert convert_timezone(dt,'America/Chicago','UTC')==datetime(2026,11,1,5,30)

@pytest.mark.parametrize('text', ['1/19/26 at 4:00 pm cdt','January 19, 2026 4:00 pm CDT','1/19/2026 4pm CDT','2026-01-19 16:00 cdt'])
def test_existing_formats(text):
    dt,tz=parse_datetime_input(text)
    assert dt==datetime(2026,1,19,16)
    assert tz.upper()=='CDT'

def test_aware_source_display_converts_before_labelling():
    from datetime import datetime
    from src.api.utils.timezone import format_time
    assert format_time(datetime.fromisoformat('2026-01-01T00:00:00+00:00'), 'America/Los_Angeles') == '2025-12-31 16:00 (PT)'

def test_quick_convert_uses_detected_zone_for_relative_parser(monkeypatch):
    from src.api.utils import timezone as tz
    original=tz.parse_datetime_input
    seen=[]
    def parse(text, zone):
        seen.append(zone)
        return original(text, zone)
    monkeypatch.setattr(tz,'parse_datetime_input',parse)
    assert tz.quick_convert('今天12点 PST')['success']
    assert seen==['PST']
