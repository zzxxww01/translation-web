// @vitest-environment jsdom
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { expect, it, vi } from 'vitest';
import { buildStream, dayLabel, emojiFor, emojify, newestTs, stripLeadingMentions } from './lib';
import { SlackText } from './SlackText';
import type { SlackMessage } from './types';

it('renders segments as text, mentions and safe links only', async () => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
  const host = document.createElement('div');
  const root = createRoot(host);
  try {
    await act(async () => root.render(<SlackText segments={[
      { type: 'mention', text: '@social' },
      { type: 'text', text: ' alert :rotating_light: <b>x</b> ' },
      { type: 'link', url: 'https://x.com/a', text: 'x.com/a' },
      { type: 'link', url: 'javascript:alert(1)', text: 'bad' },
    ]} />));
    const links = host.querySelectorAll('a');
    expect(links).toHaveLength(1);
    expect(links[0].getAttribute('href')).toBe('https://x.com/a');
    expect(links[0].getAttribute('rel')).toContain('noopener');
    expect(host.querySelector('b')).toBeNull();
    expect(host.textContent).toContain('@social alert 🚨 <b>x</b> x.com/abad');
  } finally {
    await act(async () => root.unmount());
    vi.unstubAllGlobals();
  }
});

it('maps known emoji shortcodes and leaves unknown ones', () => {
  expect(emojify(':fire: :bufo-yay:')).toBe('🔥 :bufo-yay:');
  expect(emojiFor('thumbsup::skin-tone-3')).toBe('👍');
  expect(emojiFor('bufo-love')).toBe(':bufo-love:');
});

function msg(ts: number, user: string, extra: Partial<SlackMessage> = {}): SlackMessage {
  return {
    ts: ts.toFixed(6), time: '', user_id: user, user_name: user, is_me: false, mentions_me: false, subtype: null,
    segments: [], text: '', thread_ts: null, reply_count: 0, latest_reply: null, edited: false,
    files: [], attachments: [], reactions: [], permalink: '', ...extra,
  };
}

it('builds a Slack-like stream: day dividers, new-message line and grouped bursts', () => {
  const now = new Date(2026, 10, 17, 12, 0);
  const today = now.getTime() / 1000;
  const yesterday = today - 86400;
  const stream = buildStream([
    msg(yesterday, 'A'),
    msg(today - 600, 'A'),
    msg(today - 590, 'A'),          // 同一人 5 分钟内连发 -> 合并
    msg(today - 300, 'B'),          // 第一条未读
    msg(today - 200, 'B'),          // 未读线之后正常合并
  ], (today - 400).toFixed(6), now);
  expect(stream.map(i => i.day)).toEqual(['昨天', '今天', null, null, null]);
  expect(stream.map(i => i.firstUnread)).toEqual([false, false, false, true, false]);
  expect(stream.map(i => i.compact)).toEqual([false, false, true, false, true]);
  // 我自己发的消息不算未读
  const mine = buildStream([msg(today - 100, 'me', { is_me: true }), msg(today, 'B')], (today - 400).toFixed(6), now);
  expect(mine.map(i => i.firstUnread)).toEqual([false, true]);
  expect(buildStream([msg(today, 'B')], null, now)[0].firstUnread).toBe(false);
});

it('labels days and picks the newest ts', () => {
  const now = new Date(2026, 10, 17, 12, 0);
  expect(dayLabel((new Date(2026, 10, 14, 9).getTime() / 1000).toFixed(6), now)).toBe('11月14日 周六');
  expect(dayLabel((new Date(2025, 0, 2, 9).getTime() / 1000).toFixed(6), now)).toBe('2025年1月2日 周四');
  expect(newestTs([{ ts: '1700000000.000200' }, { ts: '1700000001.000100' }, { ts: '1699999999.9' }])).toBe('1700000001.000100');
  expect(newestTs([])).toBeNull();
});

it('drops leading @用户组 from titles, keeps named mentions and mention-only text', () => {
  expect(stripLeadingMentions('@用户组 Elon post')).toBe('Elon post');
  expect(stripLeadingMentions('@用户组 @用户组 hi')).toBe('hi');
  expect(stripLeadingMentions('@Daksh Malik can u RT')).toBe('@Daksh Malik can u RT');
  expect(stripLeadingMentions('Thanks @Felix Zhou')).toBe('Thanks @Felix Zhou');
  expect(stripLeadingMentions('@Felix')).toBe('@Felix');
});
