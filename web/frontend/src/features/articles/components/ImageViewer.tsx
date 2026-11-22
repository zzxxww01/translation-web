import { useRef, type KeyboardEvent } from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { ChevronLeft, ChevronRight, ExternalLink, LocateFixed, Maximize2, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
import type { ArticleImage } from '../lib/images';
import { FOCUS_RING, STROKE } from '../lib/ui';

const VIEWER_BUTTON = `inline-flex h-8 shrink-0 items-center gap-1.5 rounded-lg px-2.5 text-[12.5px] text-white/85 transition-colors hover:bg-white/10 hover:text-white ${FOCUS_RING}`;
const STEP_BUTTON = `absolute top-1/2 flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full bg-black/45 text-white transition-colors hover:bg-black/70 ${FOCUS_RING}`;

/**
 * 看大图：整屏深色底，图按窗口大小完整显示。←/→ 换上一张/下一张，Esc 或点空白处关掉。
 * 正文里的图可以「在文中定位」：关掉大图，三栏滚到这张图。
 */
export function ImageViewer({ images, index, onIndex, onClose, onLocate }: {
  images: ArticleImage[];
  /** null = 没打开 */
  index: number | null;
  onIndex: (index: number) => void;
  onClose: () => void;
  onLocate: (key: string) => void;
}) {
  const image = index === null ? undefined : images[index];
  const content = useRef<HTMLDivElement>(null);
  const step = (delta: number) => {
    if (index !== null && images.length > 1) onIndex((index + delta + images.length) % images.length);
  };
  const onKeyDown = (event: KeyboardEvent) => {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
    event.preventDefault();
    step(event.key === 'ArrowLeft' ? -1 : 1);
  };

  return (
    <DialogPrimitive.Root open={Boolean(image)} onOpenChange={open => { if (!open) onClose(); }}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/90 backdrop-blur-sm" />
        {/* 打开时焦点放在整个弹框上（方向键直接能用），不落到第一个按钮上把它高亮 */}
        <DialogPrimitive.Content ref={content} aria-describedby={undefined} onKeyDown={onKeyDown}
          onOpenAutoFocus={event => { event.preventDefault(); content.current?.focus(); }} className="fixed inset-0 z-50 flex flex-col outline-none">
          <DialogPrimitive.Title className="sr-only">查看图片{image ? `：${image.label}` : ''}</DialogPrimitive.Title>
          {image && index !== null && (
            <>
              <div className="flex h-14 shrink-0 items-center gap-2 px-3 text-[13px] text-white/80 md:px-4">
                <span className="shrink-0 tabular-nums">{index + 1} / {images.length}</span>
                <span className="min-w-0 truncate">{image.label}</span>
                <span className="min-w-0 flex-1" />
                {!image.cover && (
                  <button type="button" className={VIEWER_BUTTON} onClick={() => onLocate(image.key)}>
                    <LocateFixed aria-hidden className="h-4 w-4" strokeWidth={STROKE} /><span className="hidden sm:inline">在文中定位</span>
                  </button>
                )}
                <a href={image.src} target="_blank" rel="noreferrer" className={VIEWER_BUTTON} title="新标签页打开原图">
                  <ExternalLink aria-hidden className="h-4 w-4" strokeWidth={STROKE} /><span className="hidden sm:inline">原图</span>
                </a>
                <DialogPrimitive.Close aria-label="关闭" className={cn(VIEWER_BUTTON, 'w-8 justify-center px-0')}>
                  <X aria-hidden className="h-4 w-4" strokeWidth={STROKE} />
                </DialogPrimitive.Close>
              </div>
              {/* 点图片以外的地方关掉 */}
              <div className="relative flex min-h-0 flex-1 items-center justify-center px-3 pb-6 md:px-16"
                onClick={event => { if (event.target === event.currentTarget) onClose(); }}>
                {/* 白底：透明背景的图表在深色底上也看得清 */}
                <img key={image.src} src={image.src} alt={image.label} className="max-h-full max-w-full rounded-md bg-white object-contain" />
                {images.length > 1 && (
                  <>
                    <button type="button" aria-label="上一张" className={cn(STEP_BUTTON, 'left-2 md:left-4')} onClick={() => step(-1)}>
                      <ChevronLeft aria-hidden className="h-5 w-5" strokeWidth={STROKE} />
                    </button>
                    <button type="button" aria-label="下一张" className={cn(STEP_BUTTON, 'right-2 md:right-4')} onClick={() => step(1)}>
                      <ChevronRight aria-hidden className="h-5 w-5" strokeWidth={STROKE} />
                    </button>
                  </>
                )}
              </div>
            </>
          )}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

/** 文中图片一览：从右边滑出。点缩略图跳到文中位置（封面没有位置，直接放大），右上角按钮放大。 */
export function ImageGallery({ images, open, onClose, onLocate, onZoom }: {
  images: ArticleImage[];
  open: boolean;
  onClose: () => void;
  onLocate: (key: string) => void;
  onZoom: (index: number) => void;
}) {
  return (
    <Sheet open={open} onOpenChange={next => { if (!next) onClose(); }}>
      <SheetContent side="right" aria-describedby={undefined} className="flex w-[360px] flex-col gap-0 bg-bg-primary p-0 sm:max-w-[360px]">
        <div className="shrink-0 border-b border-border-subtle px-4 pb-3 pt-4">
          <SheetTitle className="text-sm font-medium text-text-primary">文中图片 <span className="font-normal text-text-muted">{images.length}</span></SheetTitle>
          <p className="mt-1 text-xs text-text-muted">点图片跳到文中位置，点右上角放大</p>
        </div>
        <ul className="grid min-h-0 flex-1 auto-rows-min grid-cols-2 gap-x-3 gap-y-4 overflow-y-auto p-4">
          {images.map((image, index) => (
            <li key={image.key} className="relative min-w-0">
              <button type="button" onClick={() => (image.cover ? onZoom(index) : onLocate(image.key))}
                title={image.cover ? '放大封面' : '跳到文中这张图'} className={cn('block w-full rounded-md text-left', FOCUS_RING)}>
                <img src={image.src} alt="" loading="lazy" className="aspect-[4/3] w-full rounded-md border border-border-subtle bg-white object-cover" />
                <span className="mt-1.5 line-clamp-2 text-[11.5px] leading-snug text-text-secondary">{image.label}</span>
              </button>
              <button type="button" aria-label={`放大${image.label}`} title="放大" onClick={() => onZoom(index)}
                className={cn('absolute right-1.5 top-1.5 flex h-7 w-7 items-center justify-center rounded-md bg-black/55 text-white transition-colors hover:bg-black/75', FOCUS_RING)}>
                <Maximize2 aria-hidden className="h-3.5 w-3.5" strokeWidth={STROKE} />
              </button>
            </li>
          ))}
        </ul>
      </SheetContent>
    </Sheet>
  );
}
