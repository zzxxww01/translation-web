import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Play } from 'lucide-react';
import { toast } from 'sonner';
import { PageHeader } from '@/components/layout/PageHeader';
import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { startRun } from '../api';
import { skillKeys } from '../hooks';
import { runKindLabel } from '../state';
import type { CatalogSkill, RunMeta } from '../types';
import { AttachmentPicker } from './AttachmentChips';

// 排第一并默认选中：不派发 skill，消息原样发给 Claude
const CHAT_OPTION: CatalogSkill = {
  name: '',
  description: '不指定 skill，像平常一样和 Claude 聊；任务对得上时它也会自己调用下面的 skill',
  available: true,
};

interface NewRunFormProps {
  catalog: CatalogSkill[];
  maxUploadMb: number;
  onStarted: (run: RunMeta) => void;
}

export function NewRunForm({ catalog, maxUploadMb, onStarted }: NewRunFormProps) {
  const queryClient = useQueryClient();
  const [skill, setSkill] = useState(CHAT_OPTION.name);
  const [message, setMessage] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [progress, setProgress] = useState<number | null>(null);

  const tooLarge = files.find(file => file.size > maxUploadMb * 1024 * 1024);
  const canStart = (message.trim() || files.length > 0) && !tooLarge && progress === null;

  const start = async () => {
    if (!canStart) return;
    setProgress(files.length ? 0 : 100);
    try {
      const run = await startRun({ skill, message, files }, setProgress);
      await queryClient.invalidateQueries({ queryKey: skillKeys.runs });
      onStarted(run);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '启动失败');
      setProgress(null);
    }
  };

  return (
    <div className="mx-auto w-full max-w-3xl px-5 pb-12 pt-8 sm:px-8 sm:pt-10">
      <PageHeader
        className="mb-7"
        title="Claude"
        description="直接和 Claude 对话，或选一个 skill 跑完整流程。都在服务器上用你的 Claude 订阅运行，关掉页面也不会中断；需要你确认时会停下来等你。"
      />

      <section className="space-y-6">
        <div>
          <h2 className="mb-3 text-sm font-medium text-text-secondary">方式</h2>
          <div className="grid gap-2 sm:grid-cols-2">
            {[CHAT_OPTION, ...catalog].map(item => (
              <button
                key={item.name || 'chat'}
                type="button"
                disabled={!item.available}
                onClick={() => setSkill(item.name)}
                className={cn(
                  'rounded-lg border px-4 py-3 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-50',
                  item.name === skill
                    ? 'border-primary-400 bg-primary-50'
                    : 'border-border-subtle bg-white hover:border-primary-200'
                )}
              >
                <div className="text-sm font-medium text-text-primary">{runKindLabel(item.name)}</div>
                <div className="mt-1 line-clamp-2 text-xs leading-relaxed text-text-muted">
                  {item.available ? item.description || '（无简介）' : '服务器上没有安装这个 skill'}
                </div>
              </button>
            ))}
          </div>
        </div>

        <div>
          <h2 className="mb-3 text-sm font-medium text-text-secondary">要做什么</h2>
          <Textarea
            rows={5}
            value={message}
            onChange={event => setMessage(event.target.value)}
            onKeyDown={event => {
              if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) start();
            }}
            placeholder={
              skill
                ? '例如：精翻这篇；或贴一个 YouTube 链接，说明要中文字幕还是双语字幕'
                : '想问什么、要做什么都可以，也可以附文件或贴链接'
            }
          />
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
            <AttachmentPicker files={files} onChange={setFiles} disabled={progress !== null} />
            <Button onClick={start} disabled={!canStart}>
              <Play /> {progress === null ? '开始' : progress < 100 ? `上传中 ${progress}%` : '启动中…'}
            </Button>
          </div>
          {tooLarge && (
            <p className="mt-2 text-sm text-error">
              {tooLarge.name} 超过 {maxUploadMb} MB 上限，大文件请改用链接
            </p>
          )}
        </div>
      </section>
    </div>
  );
}
