// @vitest-environment jsdom
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { expect, it, vi } from 'vitest';
import type { ReactNode } from 'react';
import { ModelSelector } from './ModelSelector';

vi.mock('../shared/api/models', () => ({ modelsApi: { getModels: vi.fn(async () => ({ providers: [{
  id: 'openai-official', name: 'OpenAI 官方 API', models: [{ alias: 'gpt-6.1-sol',
  real_model: 'gpt-6.1-sol', name: 'GPT-6.1 Sol', available: true }],
}] })) } }));
vi.mock('@/components/ui/select', () => ({
  Select: ({ children, value, onValueChange }: {children:ReactNode;value:string;onValueChange:(v:string)=>void}) =>
    <select value={value} onChange={e => onValueChange(e.target.value)}>{children}</select>,
  SelectContent: ({children}:{children:ReactNode}) => <>{children}</>,
  SelectItem: ({children, value, disabled}:{children:ReactNode;value:string;disabled?:boolean}) => <option value={value} disabled={disabled}>{children}</option>,
  SelectTrigger: () => null,
  SelectValue: () => null,
}));
it('offers official OpenAI without changing default and sends exact alias', async () => {
  const host = document.createElement('div'); document.body.append(host);
  const root = createRoot(host); const onChange = vi.fn();
  try {
    await act(async () => root.render(<ModelSelector onChange={onChange} />));
    const select = host.querySelector('select')!;
    expect(select.value).toBe('default');
    expect(onChange).not.toHaveBeenCalled();
    expect(host.textContent).toContain('GPT-6.1 Sol');
    await act(async () => { select.value = 'gpt-6.1-sol'; select.dispatchEvent(new Event('change', {bubbles:true})); });
    expect(onChange).toHaveBeenCalledWith('gpt-6.1-sol');
  } finally { await act(async () => root.unmount()); host.remove(); }
});
