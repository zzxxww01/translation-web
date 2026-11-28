import { describe as group, expect, it } from 'vitest';
import { addDays, describe, diffFromBeijing, zonedToInstant } from './zones';

group('zones', () => {
  it('converts US Central wall time to Beijing, across daylight saving', () => {
    // 冬令时：美中 UTC-6，北京 UTC+8，差 14 小时
    const winter = zonedToInstant('2026-11-28', '09:00', 'America/Chicago')!;
    expect(winter.toISOString()).toBe('2026-11-28T15:00:00.000Z');
    expect(describe(winter, 'Asia/Shanghai', winter)).toMatchObject({ date: '11月28日', weekday: '周六', time: '23:00', relative: '今天' });
    expect(diffFromBeijing(winter, 'America/Chicago')).toBe('比北京晚 14 小时');
    // 夏令时：美中 UTC-5，差 13 小时
    const summer = zonedToInstant('2026-07-01', '21:30', 'America/Chicago')!;
    // 「明天」是相对北京的今天：美中 7/1 中午时北京还是 7/2 凌晨，北京那边是「今天」
    expect(describe(summer, 'Asia/Shanghai', zonedToInstant('2026-07-01', '08:00', 'Asia/Shanghai')!)).toMatchObject({ date: '7月2日', time: '10:30', relative: '明天' });
    expect(diffFromBeijing(summer, 'America/Chicago')).toBe('比北京晚 13 小时');
  });

  it('goes the other way and handles bad input', () => {
    const instant = zonedToInstant('2026-11-29', '08:00', 'Asia/Shanghai')!;
    expect(describe(instant, 'America/Los_Angeles', zonedToInstant('2026-11-29', '09:00', 'America/Los_Angeles')!)).toMatchObject({ date: '11月28日', time: '16:00', relative: '昨天' });
    expect(zonedToInstant('2026-11-29', '', 'UTC')).toBeNull();
    expect(addDays('2026-12-31', 1)).toBe('2027-01-01');
  });
});
