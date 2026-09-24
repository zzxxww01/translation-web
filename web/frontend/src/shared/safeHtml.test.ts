// @vitest-environment jsdom
import { describe, expect, it } from 'vitest';
import { sanitizeSourceHtml } from './safeHtml';

describe('imported table sanitization', () => {
  it('preserves table content without allowing event handlers or script URLs', () => {
    const html = '<table><tr><td colspan="2">42<img src="x" onerror="alert(1)"><a href="javascript:alert(1)">link</a><script>alert(1)</script></td></tr></table>';
    const root = document.createElement('div');
    root.innerHTML = sanitizeSourceHtml(html);
    expect(root.querySelector('td')?.getAttribute('colspan')).toBe('2');
    expect(root.textContent).toBe('42link');
    expect(root.querySelector('script')).toBeNull();
    expect(root.querySelector('img')?.hasAttribute('onerror')).toBe(false);
    expect(root.querySelector('a')?.hasAttribute('href')).toBe(false);
  });
  it('removes executable namespaces, forms and style overlays', () => {
    const clean = sanitizeSourceHtml('<svg onload="x()"></svg><iframe srcdoc="<script>x()</script>"></iframe><form><input autofocus></form><p style="position:fixed">text</p>');
    expect(clean).not.toMatch(/svg|iframe|onload|srcdoc|<form|<input|style=/i);
    expect(clean).toContain('text');
  });
});
