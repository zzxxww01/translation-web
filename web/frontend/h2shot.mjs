import { chromium } from 'playwright';

const SCRATCH =
  'C:/Users/DELL/AppData/Local/Temp/claude/C--Users-DELL-Desktop-translation-agent/5f4eef3d-465f-434f-9d2c-bb10a1ad559d/scratchpad';

const MD = [
  '这说明，KDA 这类线性注意力虽然大幅降低了 KV 缓存的显存消耗。',
  '',
  '## 注意力残差',
  '',
  '## 残差连接',
  '',
  '残差连接是关键创新之一，它让我们得以不断扩展模型深度。',
  '',
  '### 三级标题长这样',
  '',
  '正文。',
].join('\n');

const browser = await chromium.launch({ channel: 'msedge' });
const page = await browser.newPage({ viewport: { width: 1200, height: 900 } });
await page.goto('http://localhost:8888/wechat', { waitUntil: 'networkidle' });
await page.getByLabel('Markdown 内容').fill(MD);
await page.getByRole('button', { name: '转换' }).click();
await page.waitForTimeout(3000);

const frame = page.frameLocator('iframe[title="微信排版预览"]');
const h2 = frame.locator('h2').first();
const box = await h2.boundingBox();
const styles = await h2.evaluate(el => {
  const s = getComputedStyle(el);
  return { display: s.display, width: s.width, background: s.backgroundColor, textAlign: s.textAlign };
});
console.log('预览里 h2 computed:', JSON.stringify(styles));
console.log('预览里 h2 宽度:', box ? Math.round(box.width) : 'n/a');

await page.screenshot({
  path: `${SCRATCH}/h2_preview.png`,
  clip: { x: 600, y: 120, width: 580, height: 420 },
});
console.log('shot ->', `${SCRATCH}/h2_preview.png`);
await browser.close();
