// CI 的前端依赖审计：npm audit 必须干净，只放行下面列出的、上游还没有修复版的公告。
// 每条都带复查日期，过期就让 CI 失败，逼着回来看看有没有修复版了。用法：node scripts/check-npm-audit.mjs <npm-audit.json>
import fs from 'node:fs';

const ALLOWED = {
  // picomatch 扩展 glob 的 ReDoS：影响 <= 4.0.7（全部版本），2026-11 时没有修复版。
  // 只经 vite / vitest / typescript-eslint / tinyglobby 等开发和构建工具引入，线上运行时不含 picomatch。
  'https://github.com/advisories/GHSA-fc5q-39xc-vjpf': '2027-01-31',
};

const audit = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
if (audit.error) {
  console.error('npm audit 本身出错：', audit.error);
  process.exit(1);
}

const vulns = audit.vulnerabilities ?? {};
const today = new Date().toISOString().slice(0, 10);

/** 一个包的漏洞最终来自哪些公告（via 里的字符串是另一个有漏洞的包名，要顺着找下去） */
function advisories(name, seen = new Set()) {
  if (seen.has(name)) return [];
  seen.add(name);
  return (vulns[name]?.via ?? []).flatMap(via => (typeof via === 'string' ? advisories(via, seen) : [via.url]));
}

let failed = false;
for (const name of Object.keys(vulns)) {
  const sources = advisories(name);
  const blocking = sources.filter(url => !(ALLOWED[url] && today <= ALLOWED[url]));
  if (sources.length === 0 || blocking.length) {
    failed = true;
    console.error(`✗ ${name} (${vulns[name].severity}): ${blocking.join(', ') || '找不到来源公告'}`);
  } else {
    console.log(`放行 ${name}：${sources.join(', ')}`);
  }
}
for (const [url, until] of Object.entries(ALLOWED)) {
  if (today > until) console.error(`放行已过期（${until}），去看看有没有修复版：${url}`);
}
process.exit(failed ? 1 : 0);
