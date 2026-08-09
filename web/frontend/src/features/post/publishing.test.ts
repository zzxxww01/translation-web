import { describe, expect, it } from 'vitest';

import {
  composeXiaohongshuPost,
  normalizeHashtag,
  splitPostContent,
  suggestSpecificHashtags,
} from './publishing';

describe('post publishing helpers', () => {
  it('separates a trailing hashtag block from the translated body', () => {
    expect(
      splitPostContent('正文第一段\n\n正文第二段\n\n#AI芯片 #英伟达\n#科技资讯')
    ).toEqual({
      body: '正文第一段\n\n正文第二段',
      hashtags: ['#AI芯片', '#英伟达'],
    });
  });

  it('rejects broad generic tags while preserving specific tags', () => {
    expect(normalizeHashtag('#科技资讯')).toBeNull();
    expect(normalizeHashtag(' NVIDIA Blackwell ')).toBe('#NVIDIABlackwell');
  });

  it('derives concrete tags only from matching content', () => {
    const tags = suggestSpecificHashtags(
      'NVIDIA announced the B200 Blackwell GPU for AI infrastructure.',
      '英伟达发布了用于 AI 基础设施的 B200。'
    );

    expect(tags).toEqual(
      expect.arrayContaining(['#NVIDIABlackwell', '#AI芯片', '#AI基础设施', '#英伟达', '#GPU', '#B200'])
    );
    expect(tags).not.toContain('#科技');
  });

  it('composes one copy-ready post without empty sections or duplicate tags', () => {
    expect(
      composeXiaohongshuPost('一个标题', '正文', ['#AI芯片', '#AI芯片'])
    ).toBe('一个标题\n\n正文\n\n#AI芯片');
  });
});
