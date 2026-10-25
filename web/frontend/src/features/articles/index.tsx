import { useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { ArrowLeft, Newspaper } from 'lucide-react';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
import type { SubstackArticle } from '@/features/substack/api';
import { ArticlePreview } from './components/ArticlePreview';
import { ArticleSidebar } from './components/ArticleSidebar';
import { Workbench } from './components/Workbench';

/**
 * 「文章」：文章库 + 项目 + 两路翻译 + 三栏对照，一个页面走完。
 * /articles 是列表和文章卡，/articles/:projectId 是工作台。设计见 docs/superpowers/specs/2026-10-25-article-workbench-design.md。
 */
export function ArticlesFeature() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [selected, setSelected] = useState<SubstackArticle | null>(null);
  const [listOpen, setListOpen] = useState(false);
  const slug = searchParams.get('a');
  const article = selected && selected.slug === slug ? selected : null;

  const openProject = (id: string) => {
    setListOpen(false);
    navigate(`/articles/${id}`);
  };
  const sidebar = (
    <ArticleSidebar
      selectedSlug={slug}
      selectedProjectId={projectId ?? null}
      onSelectArticle={item => {
        setSelected(item);
        setListOpen(false);
        if (projectId) navigate(`/articles?a=${encodeURIComponent(item.slug)}`);
        else setSearchParams({ a: item.slug });
      }}
      onSelectProject={openProject}
    />
  );

  if (projectId) {
    return (
      <div className="h-full">
        <Workbench key={projectId} projectId={projectId} onShowList={() => setListOpen(true)} />
        <Sheet open={listOpen} onOpenChange={setListOpen}>
          <SheetContent side="left" className="w-[340px] bg-bg-primary p-0 sm:max-w-[340px]">
            <SheetTitle className="sr-only">文章列表</SheetTitle>
            {sidebar}
          </SheetContent>
        </Sheet>
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0">
      <aside className={`${article ? 'hidden md:flex' : 'flex'} w-full shrink-0 flex-col border-r border-border-subtle bg-bg-primary md:w-[340px]`}>
        {sidebar}
      </aside>
      <section className={`${article ? 'flex' : 'hidden md:flex'} min-w-0 flex-1 flex-col overflow-y-auto`}>
        {article ? (
          <>
            <button type="button" onClick={() => setSearchParams({})} className="flex items-center gap-1 px-5 pt-4 text-sm text-text-muted md:hidden">
              <ArrowLeft className="h-4 w-4" /> 文章列表
            </button>
            <ArticlePreview key={article.url} article={article} onImported={openProject} />
          </>
        ) : (
          <div className="m-auto max-w-sm px-6 text-center text-text-muted">
            <Newspaper className="mx-auto h-8 w-8 text-text-disabled" />
            <p className="mt-3 text-sm leading-relaxed">
              左边选一篇文章。没导入的先看中文摘要，一键导入后网页版和第二个译本同时开翻；已导入的直接进三栏对照。
            </p>
          </div>
        )}
      </section>
    </div>
  );
}
