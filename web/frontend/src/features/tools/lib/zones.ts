/** 时区换算（浏览器本地算，夏令时由 Intl 时区库处理）：「某时区的某天几点」→ 时刻 → 各时区的钟点。 */

export interface Zone {
  id: string;
  label: string;
  /** 短名，用在按钮上 */
  short: string;
}

export const ZONES: Zone[] = [
  { id: 'Asia/Shanghai', label: '北京时间', short: '北京' },
  { id: 'America/New_York', label: '美东时间', short: '美东' },
  { id: 'America/Chicago', label: '美中时间', short: '美中' },
  { id: 'America/Denver', label: '美山时间', short: '美山' },
  { id: 'America/Los_Angeles', label: '美西时间', short: '美西' },
  { id: 'UTC', label: 'UTC', short: 'UTC' },
];

export const BEIJING = 'Asia/Shanghai';

const WEEKDAYS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];

function parts(instant: Date, timeZone: string) {
  const values: Record<string, number> = {};
  for (const part of new Intl.DateTimeFormat('en-US', {
    timeZone, hourCycle: 'h23', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit',
  }).formatToParts(instant)) {
    if (part.type !== 'literal') values[part.type] = Number(part.value);
  }
  return values as { year: number; month: number; day: number; hour: number; minute: number; second: number };
}

/** 这个时刻在 timeZone 里比 UTC 快多少分钟（美中冬天是 -360） */
export function offsetMinutes(instant: Date, timeZone: string): number {
  const p = parts(instant, timeZone);
  const asUtc = Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute, p.second);
  return Math.round((asUtc - Math.floor(instant.getTime() / 1000) * 1000) / 60000);
}

/** 「timeZone 里 date（YYYY-MM-DD）的 time（HH:MM）」是哪个时刻 */
export function zonedToInstant(date: string, time: string, timeZone: string): Date | null {
  const d = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date);
  const t = /^(\d{1,2}):(\d{2})$/.exec(time);
  if (!d || !t) return null;
  const wall = Date.UTC(+d[1], +d[2] - 1, +d[3], +t[1], +t[2]);
  let instant = wall - offsetMinutes(new Date(wall), timeZone) * 60000;
  // 夏令时切换附近，第一次猜的偏移可能不对：按算出来的时刻再取一次
  const second = offsetMinutes(new Date(instant), timeZone);
  instant = wall - second * 60000;
  return new Date(instant);
}

/** timeZone 里的日期 YYYY-MM-DD */
export function dateIn(instant: Date, timeZone: string): string {
  const p = parts(instant, timeZone);
  return `${p.year}-${String(p.month).padStart(2, '0')}-${String(p.day).padStart(2, '0')}`;
}

export function addDays(date: string, days: number): string {
  const [y, m, d] = date.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d + days)).toISOString().slice(0, 10);
}

function dayDiff(a: string, b: string): number {
  const toDay = (s: string) => Date.UTC(+s.slice(0, 4), +s.slice(5, 7) - 1, +s.slice(8, 10)) / 86400000;
  return toDay(a) - toDay(b);
}

const RELATIVE: Record<number, string> = { [-1]: '昨天', 0: '今天', 1: '明天', 2: '后天' };

/** 在 timeZone 里怎么写这个时刻：11月29日 周六 23:00，外加相对那个时区今天是「今天 / 明天…」 */
export function describe(instant: Date, timeZone: string, now = new Date()) {
  const p = parts(instant, timeZone);
  const date = dateIn(instant, timeZone);
  const weekday = WEEKDAYS[new Date(Date.UTC(p.year, p.month - 1, p.day)).getUTCDay()];
  return {
    date: `${p.month}月${p.day}日`,
    weekday,
    time: `${String(p.hour).padStart(2, '0')}:${String(p.minute).padStart(2, '0')}`,
    relative: RELATIVE[dayDiff(date, dateIn(now, timeZone))] ?? '',
  };
}

/** 和北京差几小时：「比北京晚 14 小时」 */
export function diffFromBeijing(instant: Date, timeZone: string): string {
  const diff = (offsetMinutes(instant, timeZone) - offsetMinutes(instant, BEIJING)) / 60;
  if (diff === 0) return '和北京同一时间';
  const hours = Number.isInteger(diff) ? String(Math.abs(diff)) : Math.abs(diff).toFixed(1);
  return diff < 0 ? `比北京晚 ${hours} 小时` : `比北京早 ${hours} 小时`;
}
