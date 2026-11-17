import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/input';
import { useSaveSlackCredentials } from './hooks';
import type { SlackStatus } from './types';

/** 凭证缺失或失效时显示：只写不回显，保存后后端会立刻用 auth.test 校验。 */
export function CredentialsPanel({ status }: { status?: SlackStatus }) {
  const [token, setToken] = useState('');
  const [cookie, setCookie] = useState('');
  const save = useSaveSlackCredentials();

  return (
    <div className="mx-auto mt-10 max-w-lg rounded-xl border border-border-subtle bg-white p-6 shadow-sm">
      <h2 className="text-lg text-text-primary">连接 Slack（只读）</h2>
      <p className="mt-1 text-sm text-text-muted">
        {status?.configured ? status.error || 'Slack 凭证已失效' : '还没有配置 Slack 凭证'}。
        在浏览器登录 Slack 网页版，从开发者工具里复制 xoxc token 和 d cookie 填进来。只用于读取消息，不会发送任何内容。
      </p>
      <form
        className="mt-4 space-y-3"
        onSubmit={e => {
          e.preventDefault();
          save.mutate({ token, cookie_d: cookie }, { onSuccess: s => { if (s.ok) { setToken(''); setCookie(''); } } });
        }}
      >
        <Input type="password" autoComplete="off" placeholder="xoxc-…" value={token} onChange={e => setToken(e.target.value)} aria-label="xoxc token" />
        <Input type="password" autoComplete="off" placeholder="xoxd-…（d cookie）" value={cookie} onChange={e => setCookie(e.target.value)} aria-label="d cookie" />
        <Button type="submit" disabled={!token.trim() || !cookie.trim() || save.isPending} className="w-full">
          {save.isPending ? '校验中…' : '保存并连接'}
        </Button>
      </form>
    </div>
  );
}
