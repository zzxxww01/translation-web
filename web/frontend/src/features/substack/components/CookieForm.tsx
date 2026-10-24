import { useState } from 'react';
import { KeyRound } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button-extended';
import { Textarea } from '@/components/ui/textarea';
import { errorText, substackApi } from '../api';

interface CookieFormProps {
  /** 触发原因，例如「订阅 cookie 已失效」；为空时显示通用说明 */
  reason?: string;
  domain?: string;
  onSaved: () => void;
  onCancel?: () => void;
}

/** 粘贴订阅 cookie。整行请求头直接粘进来即可，后端只留登录会话那一项。 */
export function CookieForm({ reason, domain = 'newsletter.semianalysis.com', onSaved, onCancel }: CookieFormProps) {
  const [value, setValue] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const save = async () => {
    if (!value.trim()) {
      toast.error('请先粘贴 cookie');
      return;
    }
    setIsSaving(true);
    try {
      await substackApi.saveCookie(value);
      setValue('');
      toast.success('订阅 cookie 已保存');
      onSaved();
    } catch (error) {
      toast.error(errorText(error, '保存 cookie 失败'));
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-3 rounded-lg border border-border bg-bg-secondary p-4">
      <div className="flex items-start gap-2">
        <KeyRound className="mt-0.5 h-4 w-4 shrink-0 text-text-muted" />
        <div className="space-y-1 text-sm">
          <p className="font-medium text-text-primary">{reason || '填写订阅 cookie 才能导入付费文章'}</p>
          <p className="text-text-muted">
            在电脑浏览器登录后打开任意一篇 {domain} 的文章，按 F12 打开 Network，刷新页面，点第一条请求，
            把 Request Headers 里 <code>cookie</code> 的整行值复制到下面。建议用无痕窗口登录、复制完直接关掉窗口，不要点退出登录。
          </p>
        </div>
      </div>
      <Textarea
        aria-label="订阅 cookie"
        placeholder="粘贴整行 cookie，或只粘 connect.sid=…"
        value={value}
        onChange={e => setValue(e.target.value)}
        rows={3}
        className="font-mono text-xs"
      />
      <div className="flex justify-end gap-2">
        {onCancel && (
          <Button type="button" variant="outline" size="sm" onClick={onCancel} disabled={isSaving}>
            取消
          </Button>
        )}
        <Button type="button" size="sm" onClick={save} isLoading={isSaving}>
          保存
        </Button>
      </div>
    </div>
  );
}
