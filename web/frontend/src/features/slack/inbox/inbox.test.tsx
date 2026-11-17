// @vitest-environment jsdom
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { expect, it, vi } from 'vitest';
import { emojiFor, emojify, filterConversations, parseSlackView } from './lib';
import { SlackText } from './SlackText';
import type { SlackConversation } from './types';

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

it('splits conversations into channels and DMs', () => {
  const base = { latest_ts: null, latest_time: '', has_unreads: false, mention_count: 0 };
  const convs: SlackConversation[] = [
    { ...base, id: 'C1', kind: 'channel', name: 'social' },
    { ...base, id: 'G1', kind: 'private', name: 'secret' },
    { ...base, id: 'D1', kind: 'im', name: 'Alice' },
    { ...base, id: 'G2', kind: 'mpim', name: 'group' },
  ];
  expect(filterConversations(convs, 'channels').map(c => c.id)).toEqual(['C1', 'G1']);
  expect(filterConversations(convs, 'dms').map(c => c.id)).toEqual(['D1', 'G2']);
});

it('defaults unknown Slack sub-views to channels', () => {
  expect(parseSlackView('dms')).toBe('dms');
  expect(parseSlackView('reply')).toBe('reply');
  expect(parseSlackView('evil')).toBe('channels');
  expect(parseSlackView(null)).toBe('channels');
});
