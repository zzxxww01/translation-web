import { describe, expect, it } from 'vitest';
import type { WorkbenchRow } from '../types';
import { articleImages, COVER_KEY } from './images';

const row = (key: string, kind: string, source: string, image?: string): WorkbenchRow => ({
  key, kind, section_id: 's', paragraph_id: null, source, image, web: null, alt: {},
});

describe('articleImages', () => {
  const rows = [
    row('section:a', 'section', 'Intro'),
    row('a/1', 'image', 'x', 'https://cdn/x.png'),
    row('a/2', 'image', 'broken'), // 没有可显示的地址：不算
    row('section:b', 'section', 'Supply'),
    row('b/1', 'image', 'y', 'https://cdn/y.png'),
  ];

  it('numbers images in reading order and labels each with its section', () => {
    expect(articleImages(rows, null, item => (item.source === 'Intro' ? '引言' : ''))).toEqual([
      { key: 'a/1', src: 'https://cdn/x.png', label: '图 1 · 引言' },
      { key: 'b/1', src: 'https://cdn/y.png', label: '图 2' },
    ]);
  });

  it('puts the cover first unless the body already shows the same picture', () => {
    expect(articleImages(rows, 'https://cdn/cover.png', item => item.source)[0]).toEqual(
      { key: COVER_KEY, src: 'https://cdn/cover.png', label: '封面', cover: true });
    expect(articleImages(rows, 'https://cdn/x.png', item => item.source).map(image => image.key)).toEqual(['a/1', 'b/1']);
  });
});
