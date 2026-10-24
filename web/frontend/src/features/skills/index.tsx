import { useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ArrowLeft, LogOut } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import { findAgent, normalizeCatalog } from './agents';
import { skillsApi } from './api';
import { isUnauthorized, skillKeys, useCatalog, useRuns, useSkillsAuth } from './hooks';
import { LoginPanel } from './components/LoginPanel';
import { NewRunForm } from './components/NewRunForm';
import { RunList } from './components/RunList';
import { RunPanel } from './components/RunPanel';
import './styles.css';

function Spinner() {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="h-7 w-7 animate-spin rounded-full border-4 border-primary border-t-transparent" />
    </div>
  );
}

export function SkillsFeature() {
  const auth = useSkillsAuth();
  if (auth.isPending) return <Spinner />;
  if (auth.error) {
    if (isUnauthorized(auth.error)) return <LoginPanel />;
    return (
      <div className="flex h-full items-center justify-center px-6 text-center text-sm text-text-muted">
        skill-runner 服务连不上：{auth.error.message}
      </div>
    );
  }
  return <SkillsWorkspace maxUploadMb={auth.data.max_upload_mb} />;
}

function SkillsWorkspace({ maxUploadMb }: { maxUploadMb: number }) {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedId = searchParams.get('run');
  // 宽屏上「没选运行」就显示新建表单；窄屏列表和内容二选一，所以新建要单独的 URL 状态
  const creating = !selectedId && searchParams.get('new') === '1';
  const showDetail = Boolean(selectedId) || creating;
  const runs = useRuns(true);
  const catalogQuery = useCatalog(true);
  const catalog = normalizeCatalog(catalogQuery.data);
  const selected = runs.data?.find(run => run.id === selectedId) ?? null;

  const select = (id: string) => setSearchParams({ run: id });
  const openNew = () => setSearchParams({ new: '1' });
  const backToList = () => setSearchParams({});

  const logout = async () => {
    await skillsApi.logout();
    queryClient.removeQueries({ queryKey: ['skills'] });
    await queryClient.refetchQueries({ queryKey: skillKeys.me });
  };

  // cookie 过期后列表接口先报 401：让登录态重新检查，页面切回口令框
  const sessionExpired = isUnauthorized(runs.error);
  useEffect(() => {
    if (sessionExpired) queryClient.invalidateQueries({ queryKey: skillKeys.me });
  }, [sessionExpired, queryClient]);

  return (
    <div className="flex h-full min-h-0">
      {/* 窄屏上列表和内容二选一 */}
      <div
        className={cn(
          'w-full shrink-0 flex-col border-r border-border-subtle bg-[#fbf8f6] md:flex md:w-72',
          showDetail ? 'hidden' : 'flex'
        )}
      >
        <RunList runs={runs.data ?? []} catalog={catalog} selectedId={selectedId} onSelect={select} onNew={openNew} />
        <div className="border-t border-border-subtle px-4 py-2">
          <Button variant="ghost" size="sm" onClick={logout}>
            <LogOut /> 退出登录
          </Button>
        </div>
      </div>
      <div className={cn('min-w-0 flex-1 flex-col overflow-hidden', showDetail ? 'flex' : 'hidden md:flex')}>
        {showDetail && (
          <div className="border-b border-border-subtle px-3 py-2 md:hidden">
            <Button variant="ghost" size="sm" onClick={backToList}>
              <ArrowLeft /> 任务
            </Button>
          </div>
        )}
        <div className="min-h-0 flex-1 overflow-auto">
          {selectedId ? (
            selected ? (
              <RunPanel
                key={selected.id}
                run={selected}
                agent={findAgent(catalog, selected.skill)}
                maxUploadMb={maxUploadMb}
                onDeleted={backToList}
              />
            ) : runs.isPending ? (
              <Spinner />
            ) : (
              <div className="p-8 text-sm text-text-muted">这个任务不存在或已被删除。</div>
            )
          ) : (
            <NewRunForm
              catalog={catalog}
              maxUploadMb={maxUploadMb}
              onStarted={run => select(run.id)}
            />
          )}
        </div>
      </div>
    </div>
  );
}
