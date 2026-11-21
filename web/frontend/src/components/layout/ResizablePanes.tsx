import { Fragment, useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface PaneSpec {
  id: string;
  title: string;
  /** 栏头标题右边的小字（例如「v3」「3 张图」） */
  meta?: ReactNode;
  /** 栏头右侧的按钮（✕ 之前） */
  actions?: ReactNode;
  content: ReactNode;
  /** 初始宽度（px）；不填的那一栏占剩余空间 */
  width?: number;
  minWidth?: number;
  /** 默认收起 */
  closed?: boolean;
}

interface Layout {
  closed: string[];
  widths: Record<string, number>;
}

const STRIP = 34;
const DEFAULT_MIN = 240;

function loadLayout(key: string, panes: PaneSpec[]): Layout {
  const fallback: Layout = {
    closed: panes.filter(p => p.closed).map(p => p.id),
    widths: Object.fromEntries(panes.filter(p => p.width).map(p => [p.id, p.width as number])),
  };
  try {
    const saved = JSON.parse(localStorage.getItem(key) || 'null') as Layout | null;
    if (!saved || !Array.isArray(saved.closed) || typeof saved.widths !== 'object') return fallback;
    return { closed: saved.closed, widths: { ...fallback.widths, ...saved.widths } };
  } catch {
    return fallback;
  }
}

/**
 * 并排的几栏：每栏右上角 ✕ 收起成一条竖条（点竖条恢复），栏之间的分隔线可以拖动调宽度。
 * 开合和宽度按 storageKey 记在浏览器里。窄屏（< 1024px）改成顶部标签，一次看一栏。
 */
export function ResizablePanes({ panes, storageKey, className, mobileDefault }: {
  panes: PaneSpec[];
  storageKey: string;
  className?: string;
  /** 窄屏上默认显示哪一栏（默认第一栏） */
  mobileDefault?: string;
}) {
  const [layout, setLayout] = useState<Layout>(() => loadLayout(storageKey, panes));
  const [narrow, setNarrow] = useState(() => typeof window !== 'undefined' && window.innerWidth < 1024);
  const [mobilePane, setMobilePane] = useState(mobileDefault ?? panes[0]?.id);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onResize = () => setNarrow(window.innerWidth < 1024);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const save = useCallback((next: Layout) => {
    setLayout(next);
    localStorage.setItem(storageKey, JSON.stringify(next));
  }, [storageKey]);

  const open = panes.filter(p => !layout.closed.includes(p.id));
  // 占剩余空间的那一栏：没写 width 的那栏；都写了（或它被收起）就是最后一个打开的
  const flexId = (open.find(p => !p.width) ?? open[open.length - 1])?.id ?? null;

  const toggle = (id: string) => {
    const closed = layout.closed.includes(id)
      ? layout.closed.filter(x => x !== id)
      : [...layout.closed, id];
    // 至少留一栏开着
    if (closed.length >= panes.length) return;
    save({ ...layout, closed });
  };

  const startDrag = (leftId: string, rightId: string) => (event: React.PointerEvent) => {
    event.preventDefault();
    const leftEl = containerRef.current?.querySelector<HTMLElement>(`[data-pane="${leftId}"]`);
    const rightEl = containerRef.current?.querySelector<HTMLElement>(`[data-pane="${rightId}"]`);
    if (!leftEl || !rightEl) return;
    const startX = event.clientX;
    const startLeft = leftEl.getBoundingClientRect().width;
    const startRight = rightEl.getBoundingClientRect().width;
    const leftMin = panes.find(p => p.id === leftId)?.minWidth ?? DEFAULT_MIN;
    const rightMin = panes.find(p => p.id === rightId)?.minWidth ?? DEFAULT_MIN;
    let latest = layout;
    const onMove = (e: PointerEvent) => {
      const dx = Math.max(leftMin - startLeft, Math.min(startRight - rightMin, e.clientX - startX));
      const widths = { ...latest.widths, [leftId]: Math.round(startLeft + dx) };
      if (rightId !== flexId) widths[rightId] = Math.round(startRight - dx);
      latest = { ...latest, widths };
      setLayout(latest);
    };
    const onUp = () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      save(latest);
    };
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
  };

  if (narrow) {
    const current = panes.find(p => p.id === mobilePane) ?? panes[0];
    return (
      <div className={cn('flex min-h-0 flex-1 flex-col', className)}>
        <div className="flex shrink-0 gap-1 overflow-x-auto border-b border-border-subtle bg-white/70 px-2 py-1.5" role="tablist">
          {panes.map(p => (
            <button
              key={p.id}
              type="button"
              role="tab"
              aria-selected={p.id === current.id}
              onClick={() => setMobilePane(p.id)}
              className={cn(
                'shrink-0 rounded-full px-3 py-1 text-xs transition-colors',
                p.id === current.id ? 'bg-primary-500 text-white' : 'text-text-secondary hover:bg-bg-hover'
              )}
            >
              {p.title}
            </button>
          ))}
        </div>
        <div className="min-h-0 flex-1 overflow-auto">{current.content}</div>
      </div>
    );
  }

  return (
    <div ref={containerRef} className={cn('flex min-h-0 flex-1', className)}>
      {panes.map((p, i) => {
        const closed = layout.closed.includes(p.id);
        const next = panes.slice(i + 1).find(x => !layout.closed.includes(x.id));
        if (closed) {
          return (
            <button
              key={p.id}
              type="button"
              onClick={() => toggle(p.id)}
              title={`展开「${p.title}」`}
              className="group flex shrink-0 flex-col items-center gap-2 border-r border-border-subtle bg-bg-tertiary/60 py-3 text-text-muted transition-colors hover:bg-primary-50 hover:text-primary-700"
              style={{ width: STRIP }}
            >
              <span className="text-xs font-medium [writing-mode:vertical-rl]">{p.title}</span>
            </button>
          );
        }
        const isFlex = p.id === flexId;
        const width = layout.widths[p.id];
        return (
          <Fragment key={p.id}>
            <section
              data-pane={p.id}
              aria-label={p.title}
              className="flex min-w-0 flex-col bg-white/40"
              style={isFlex ? { flex: '1 1 0%', minWidth: p.minWidth ?? DEFAULT_MIN } : { width: width ?? 360, flex: 'none' }}
            >
              <header className="flex h-9 shrink-0 items-center gap-2 border-b border-border-subtle bg-white/60 px-3">
                <h2 className="truncate text-xs font-medium tracking-wide text-text-secondary" style={{ fontFamily: 'var(--font-sans, inherit)' }}>{p.title}</h2>
                {p.meta && <span className="truncate text-xs text-text-muted">{p.meta}</span>}
                <div className="ml-auto flex shrink-0 items-center gap-1">
                  {p.actions}
                  <button
                    type="button"
                    onClick={() => toggle(p.id)}
                    className="rounded-md p-1 text-text-muted transition-colors hover:bg-bg-hover hover:text-text-primary"
                    title={`收起「${p.title}」`}
                    aria-label={`收起「${p.title}」`}
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              </header>
              <div className="min-h-0 flex-1 overflow-auto">{p.content}</div>
            </section>
            {next && (
              <div
                role="separator"
                aria-orientation="vertical"
                aria-label="拖动调整宽度"
                onPointerDown={startDrag(p.id, next.id)}
                className="group relative w-px shrink-0 cursor-col-resize bg-border-subtle"
              >
                <span className="absolute inset-y-0 -left-1.5 -right-1.5 transition-colors group-hover:bg-primary-200/60" />
              </div>
            )}
          </Fragment>
        );
      })}
    </div>
  );
}
