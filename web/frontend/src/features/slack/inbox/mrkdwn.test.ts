// @vitest-environment jsdom
import { expect, it } from 'vitest';
import { renderSlackSegments, renderSlackText, stripMrkdwn } from './mrkdwn';

function dom(html: string) {
  const host = document.createElement('div');
  host.innerHTML = html;
  return host;
}

it('renders Slack mrkdwn inline styles', () => {
  const host = dom(renderSlackText('a *bold* b _it_ c ~gone~ d `x = 1` e **md bold**'));
  expect([...host.querySelectorAll('strong')].map(n => n.textContent)).toEqual(['bold', 'md bold']);
  expect(host.querySelector('em')?.textContent).toBe('it');
  expect(host.querySelector('del')?.textContent).toBe('gone');
  expect(host.querySelector('code')?.textContent).toBe('x = 1');
});

it('leaves snake_case, lone asterisks and math alone', () => {
  const host = dom(renderSlackText('use some_var_name and 2 * 3 * 4'));
  expect(host.querySelector('em, strong')).toBeNull();
  expect(host.textContent).toContain('some_var_name');
  expect(host.textContent).toContain('2 * 3 * 4');
});

it('renders bullets, numbered lists, quotes and code blocks', () => {
  const host = dom(renderSlackText('Plan:\n• one\n• two\n1. first\n2. second\n> quoted\n```\nconst *a* = `b`;\n```'));
  expect([...host.querySelectorAll('ul li')].map(n => n.textContent)).toEqual(['one', 'two']);
  expect([...host.querySelectorAll('ol li')].map(n => n.textContent)).toEqual(['first', 'second']);
  expect(host.querySelector('blockquote')?.textContent).toContain('quoted');
  // 代码块里的记号原样保留
  expect(host.querySelector('pre code')?.textContent).toBe('const *a* = `b`;\n');
});

it('keeps links, mentions and formatting together and stays safe', () => {
  const host = dom(renderSlackSegments([
    { type: 'text', text: '*see ' },
    { type: 'link', url: 'https://x.com/a_(b)', text: 'the *post*' },
    { type: 'text', text: '* by ' },
    { type: 'mention', text: '@<img src=x onerror=alert(1)>' },
    { type: 'text', text: ' <script>alert(1)</script> [x](javascript:alert(1))' },
    { type: 'link', url: 'javascript:alert(2)', text: 'bad' },
  ]));
  const link = host.querySelector('strong a');
  expect(link?.getAttribute('href')).toBe('https://x.com/a_%28b%29');
  expect(link?.getAttribute('target')).toBe('_blank');
  expect(link?.textContent).toBe('the *post*');
  expect(host.querySelector('.slack-mention')?.textContent).toBe('@<img src=x onerror=alert(1)>');
  expect(host.querySelector('img, script')).toBeNull();
  expect(host.querySelectorAll('a')).toHaveLength(1);
  expect(host.textContent).toContain('<script>alert(1)</script>');
});

it('strips markers for one-line previews', () => {
  expect(stripMrkdwn('*Hot* take: `code` and ~old~ _it_ **md**')).toBe('Hot take: code and old it md');
  expect(stripMrkdwn('> quote\n- item\n# Title')).toBe('quote\n• item\nTitle');
  expect(stripMrkdwn('2 * 3 and some_var')).toBe('2 * 3 and some_var');
});
