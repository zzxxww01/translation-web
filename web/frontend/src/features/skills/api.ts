import { apiClient, ApiErrorWrapper } from '../../shared/api/client';
import type { Agent, Answers, RunFile, RunMeta } from './types';

export const SKILLS_BASE = '/api/skills';

export const skillsApi = {
  me: () => apiClient.get<{ ok: boolean; max_active: number; max_upload_mb: number }>('/skills/me', { retry: false }),
  login: (password: string) => apiClient.post<{ ok: boolean }>('/skills/login', { password }, { retry: false }),
  logout: () => apiClient.post('/skills/logout'),
  // 旧版服务端只给 name/description/available，用 normalizeCatalog 补齐
  catalog: () => apiClient.get<Partial<Agent>[]>('/skills/catalog'),
  runs: () => apiClient.get<RunMeta[]>('/skills/runs'),
  files: (runId: string) => apiClient.get<RunFile[]>(`/skills/runs/${runId}/files`),
  answer: (runId: string, qid: string, payload: { answers?: Answers; response?: string }) =>
    apiClient.post<RunMeta>(`/skills/runs/${runId}/answer`, { qid, ...payload }, { retry: false }),
  interrupt: (runId: string) => apiClient.post<RunMeta>(`/skills/runs/${runId}/interrupt`, undefined, { retry: false }),
  remove: (runId: string) => apiClient.delete<{ ok: boolean }>(`/skills/runs/${runId}`),
};

export function fileUrl(runId: string, path: string): string {
  return `${SKILLS_BASE}/runs/${runId}/files/${path.split('/').map(encodeURIComponent).join('/')}`;
}

export function eventsUrl(runId: string, after: number): string {
  return `${SKILLS_BASE}/runs/${runId}/events?after=${after}`;
}

/** multipart 提交，带上传进度。fetch 拿不到上传进度，所以用 XHR。 */
function postMultipart<T>(path: string, form: FormData, onProgress?: (percent: number) => void): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${SKILLS_BASE}${path}`);
    xhr.timeout = 0; // 大文件上传时间不可预估；首条消息的起进程时间由服务器自己兜底
    xhr.upload.addEventListener('progress', event => {
      if (event.lengthComputable && event.total > 0) onProgress?.(Math.round((event.loaded / event.total) * 100));
    });
    xhr.addEventListener('load', () => {
      let data: unknown;
      try {
        data = JSON.parse(xhr.responseText);
      } catch {
        data = undefined;
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(data as T);
        return;
      }
      const detail = (data as { detail?: unknown } | undefined)?.detail;
      reject(new ApiErrorWrapper(typeof detail === 'string' ? detail : `请求失败（${xhr.status}）`, xhr.status, data));
    });
    xhr.addEventListener('error', () => reject(new ApiErrorWrapper('网络错误，请重试')));
    xhr.send(form);
  });
}

/** 需要你确认（比如术语表）时，多少分钟没回复就让它按自己的建议继续；和网页版术语确认的 10 分钟一致 */
export const AUTO_REPLY_MINUTES = 10;

export function startRun(
  input: { skill: string; message: string; files: File[]; harness?: 'claude' | 'codex'; autoReplyMinutes?: number; title?: string },
  onProgress?: (percent: number) => void
): Promise<RunMeta> {
  const form = new FormData();
  form.append('skill', input.skill);
  form.append('harness', input.harness ?? 'claude');
  form.append('message', input.message);
  if (input.autoReplyMinutes) form.append('auto_reply_minutes', String(input.autoReplyMinutes));
  if (input.title) form.append('title', input.title);
  input.files.forEach(file => form.append('files', file));
  return postMultipart<RunMeta>('/runs', form, onProgress);
}

export function sendMessage(
  runId: string,
  input: { message: string; files: File[] },
  onProgress?: (percent: number) => void
): Promise<RunMeta> {
  const form = new FormData();
  form.append('message', input.message);
  input.files.forEach(file => form.append('files', file));
  return postMultipart<RunMeta>(`/runs/${runId}/messages`, form, onProgress);
}
