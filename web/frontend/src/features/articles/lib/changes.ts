import type { ChangesReport } from '../types';

const savedAtFormat = new Intl.DateTimeFormat('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' });

/** 服务器给的 ISO 时间 → 「10/26 14:02」 */
export function savedAtText(iso: string): string {
  const time = Date.parse(iso);
  return Number.isFinite(time) ? savedAtFormat.format(time) : iso;
}

/** 人工改动导出成 Markdown：每段原文、初稿、改后。 */
export function changesMarkdown(title: string, report: ChangesReport): string {
  const lines = [`# 人工改动：${title}`, '', `共 ${report.total} 段，改了 ${report.changed} 段。`, ''];
  report.changes.forEach((change, index) => {
    lines.push(
      `## ${index + 1}. ${change.section_title || change.section_id} / ${change.paragraph_id}`,
      '',
      `原文：${change.source}`,
      '',
      `初稿：${change.before ?? '（没有，人工写的）'}`,
      '',
      `改后：${change.after}`,
      '',
    );
  });
  return lines.join('\n');
}
