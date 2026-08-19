// 公众号排版体检：对每个主题渲染一份覆盖全元素的样张，再叠加"公众号降级"
// （剥掉公众号不支持的 CSS）截图，对比找出会崩的地方。
import fs from 'node:fs';
import { chromium } from 'playwright';

const SCRATCH =
  'C:/Users/DELL/AppData/Local/Temp/claude/C--Users-DELL-Desktop-translation-agent/5f4eef3d-465f-434f-9d2c-bb10a1ad559d/scratchpad';

const MD = [
  '# 一级标题',
  '',
  '正文段落，含 **粗体**、*斜体*、`行内代码`、[链接](https://example.com) 与行内公式 $E=mc^2$。',
  '',
  '## 二级标题',
  '',
  '### 三级标题',
  '',
  '#### 四级标题',
  '',
  '> 这是一段引用文字，用来检查引用块的边框与背景。',
  '> 第二行。',
  '',
  '- 无序列表第一项',
  '- 第二项',
  '  - 嵌套项',
  '',
  '1. 有序列表第一项',
  '2. 第二项',
  '',
  '| 列一 | 列二 | 列三 |',
  '| --- | --- | --- |',
  '| a | b | c |',
  '| d | e | f |',
  '',
  '```python',
  'def hello(name):',
  '    return f"hi {name}"',
  '```',
  '',
  '块级公式：',
  '',
  '$$',
  'E = \\sum_{i=1}^{n} m_i c^2',
  '$$',
  '',
  '---',
  '',
  '最后一段正文。',
].join('\n');

// 公众号不支持/不可靠的 CSS，一律打回默认值
// 只作用于普通 HTML 元素：SVG 内部有自己的显示模型，公众号不会去动它，
// 一并 revert 会把公式打散，造成假故障。
const DEGRADE_CSS = `
  :not(svg):not(svg *) {
    position: static !important;
    transform: none !important;
    transition: none !important;
    animation: none !important;
    box-shadow: none !important;
    float: none !important;
    filter: none !important;
  }
  :not(svg):not(svg *):not(.wx-heading-label) { display: revert !important; }
`;

const browser = await chromium.launch({ channel: 'msedge' });
const page = await browser.newPage({ viewport: { width: 1200, height: 1000 } });
await page.goto('http://localhost:8888/wechat', { waitUntil: 'networkidle' });
await page.getByLabel('Markdown 内容').fill(MD);

const report = {};

for (const theme of ['default', 'grace', 'simple']) {
  await page.getByRole('button', { name: '打开排版设置' }).click();
  await page.waitForTimeout(400);
  await page.locator('select').selectOption(theme);
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);
  await page.getByRole('button', { name: '转换' }).click();
  await page.waitForTimeout(4000);

  const frame = page.frameLocator('iframe[title="微信排版预览"]');
  const body = frame.locator('body');

  const measure = () =>
    body.evaluate(el => {
      const out = {};
      const pick = sel => {
        const node = el.querySelector(sel);
        if (!node) return null;
        const r = node.getBoundingClientRect();
        return { w: Math.round(r.width), h: Math.round(r.height) };
      };
      for (const sel of ['h1', 'h2', 'h3', 'blockquote', 'pre', 'table', 'ul', 'hr']) {
        out[sel] = pick(sel);
      }
      out.bodyHeight = Math.round(el.scrollHeight);
      out.overflowX = el.scrollWidth > el.clientWidth;
      return out;
    });

  const before = await measure();
  await page.screenshot({ path: `${SCRATCH}/wx_${theme}_normal.png`, fullPage: false, clip: { x: 600, y: 100, width: 590, height: 880 } });

  // 叠加降级
  await body.evaluate((el, css) => {
    const style = el.ownerDocument.createElement('style');
    style.id = 'wx-degrade';
    style.textContent = css;
    el.ownerDocument.head.appendChild(style);
  }, DEGRADE_CSS);
  await page.waitForTimeout(600);

  const after = await measure();
  await page.screenshot({ path: `${SCRATCH}/wx_${theme}_degraded.png`, fullPage: false, clip: { x: 600, y: 100, width: 590, height: 880 } });

  // 撤掉降级，供下一轮
  await body.evaluate(el => el.ownerDocument.getElementById('wx-degrade')?.remove());

  report[theme] = { before, after };
  const changed = Object.keys(before).filter(
    k => JSON.stringify(before[k]) !== JSON.stringify(after[k])
  );
  console.log(`[${theme}] 降级后发生变化: ${changed.join(', ') || '无'}`);
  for (const k of changed) {
    console.log(`    ${k}: ${JSON.stringify(before[k])} -> ${JSON.stringify(after[k])}`);
  }
}

fs.writeFileSync(`${SCRATCH}/wx_report.json`, JSON.stringify(report, null, 1));
await browser.close();
