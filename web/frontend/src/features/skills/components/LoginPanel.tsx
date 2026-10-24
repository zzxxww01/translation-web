import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { LockKeyhole } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/input';
import { skillsApi } from '../api';
import { skillKeys } from '../hooks';

export function LoginPanel() {
  const queryClient = useQueryClient();
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!password) return;
    setSubmitting(true);
    setError(null);
    try {
      await skillsApi.login(password);
      setPassword('');
      await queryClient.invalidateQueries({ queryKey: ['skills'] });
      await queryClient.refetchQueries({ queryKey: skillKeys.me });
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex h-full items-center justify-center px-5">
      <form onSubmit={submit} className="w-full max-w-sm rounded-xl border border-border-subtle bg-white p-7 shadow-sm">
        <div className="mb-5 flex items-center gap-2.5 text-text-primary">
          <LockKeyhole className="h-5 w-5 text-primary-600" />
          <h1 className="text-xl">Claude</h1>
        </div>
        <p className="mb-5 text-sm leading-relaxed text-text-muted">
          这里会用你的 Claude 订阅在服务器上对话、跑 skill，需要先输入口令。
        </p>
        <Input
          type="password"
          autoComplete="current-password"
          placeholder="口令"
          value={password}
          onChange={e => setPassword(e.target.value)}
          aria-label="口令"
          autoFocus
        />
        {error && <p className="mt-2 text-sm text-error">{error}</p>}
        <Button type="submit" className="mt-5 w-full" disabled={!password || submitting}>
          {submitting ? '登录中…' : '登录'}
        </Button>
      </form>
    </div>
  );
}
