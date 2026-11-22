import type { WorkbenchRow } from '../types';

/** 封面不是正文里的一行，用这个 key 区分 */
export const COVER_KEY = 'cover';

export interface ArticleImage {
  /** 正文图片是行的 key（用来在三栏里定位），封面是 COVER_KEY */
  key: string;
  src: string;
  /** 「图 3 · 章节名」或「封面」 */
  label: string;
  cover?: boolean;
}

/**
 * 这篇文章的全部图片，按文中顺序；封面放第一张（正文里已有同一张图就不重复）。
 * sectionTitle 取章节标题的显示文字（一般是主译本的译文，没有就用原文）。
 */
export function articleImages(rows: WorkbenchRow[], cover: string | null | undefined,
  sectionTitle: (row: WorkbenchRow) => string): ArticleImage[] {
  const images: ArticleImage[] = [];
  let section = '';
  for (const row of rows) {
    if (row.kind === 'section') section = sectionTitle(row).trim();
    else if (row.kind === 'image' && row.image) {
      const number = images.length + 1;
      images.push({ key: row.key, src: row.image, label: section ? `图 ${number} · ${section}` : `图 ${number}` });
    }
  }
  if (cover && !images.some(image => image.src === cover)) images.unshift({ key: COVER_KEY, src: cover, label: '封面', cover: true });
  return images;
}
