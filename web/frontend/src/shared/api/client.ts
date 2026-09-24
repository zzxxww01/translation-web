/** JSON API transport. A deadline covers headers AND consumption of the body. */
import { API_BASE, API_TIMEOUT, API_RETRY_COUNT, API_RETRY_DELAY } from '../constants';

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean>;
  timeout?: number;
  retry?: boolean;
}

export class ApiErrorWrapper extends Error {
  constructor(message: string, public status?: number, public data?: unknown) {
    super(message);
    this.name = 'ApiError';
  }
}

function abortError(): DOMException {
  return new DOMException('Request cancelled', 'AbortError');
}

function errorMessage(data: unknown, fallback: string): string {
  if (typeof data === 'string' && data.trim()) return data;
  if (Array.isArray(data)) {
    const messages = data.map(item => errorMessage(item, '')).filter(Boolean);
    return messages.join('; ') || fallback;
  }
  if (data && typeof data === 'object') {
    const obj = data as Record<string, unknown>;
    return errorMessage(obj.detail ?? obj.message ?? obj.msg, fallback);
  }
  return fallback;
}

function delay(ms: number, signal?: AbortSignal | null): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) { reject(abortError()); return; }
    const timer = setTimeout(() => {
      signal?.removeEventListener('abort', cancel);
      resolve();
    }, ms);
    const cancel = () => { clearTimeout(timer); reject(abortError()); };
    signal?.addEventListener('abort', cancel, { once: true });
  });
}

export class ApiClient {
  private defaultTimeout: number;
  private retryCount: number;
  private retryDelay: number;

  constructor(
    private baseUrl: string = API_BASE,
    options?: { timeout?: number; retryCount?: number; retryDelay?: number }
  ) {
    this.defaultTimeout = options?.timeout ?? API_TIMEOUT;
    this.retryCount = options?.retryCount ?? API_RETRY_COUNT;
    this.retryDelay = options?.retryDelay ?? API_RETRY_DELAY;
  }

  private buildUrl(endpoint: string, params?: RequestOptions['params']): string {
    const url = `${this.baseUrl}${endpoint}`;
    if (!params || Object.keys(params).length === 0) return url;
    const hashAt = url.indexOf('#');
    const hash = hashAt >= 0 ? url.slice(hashAt) : '';
    const beforeHash = hashAt >= 0 ? url.slice(0, hashAt) : url;
    const queryAt = beforeHash.indexOf('?');
    const path = queryAt >= 0 ? beforeHash.slice(0, queryAt) : beforeHash;
    const search = new URLSearchParams(queryAt >= 0 ? beforeHash.slice(queryAt + 1) : '');
    for (const [key, value] of Object.entries(params)) search.set(key, String(value));
    return `${path}?${search.toString()}${hash}`;
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      let data: unknown;
      try { data = await response.json(); } catch { /* fall back to status */ }
      throw new ApiErrorWrapper(errorMessage(data, response.statusText || 'API Error'), response.status, data);
    }
    if (response.status === 204) return undefined as T;
    const text = await response.text();
    try { return JSON.parse(text) as T; }
    catch { throw new ApiErrorWrapper('服务器返回的数据格式无效，请稍后重试', response.status); }
  }

  private async fetchWithTimeout<T>(url: string, init: RequestInit, timeout: number): Promise<T> {
    const controller = new AbortController();
    const external = init.signal;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let rejectAbort: (reason: unknown) => void = () => {};
    const aborted = new Promise<never>((_, reject) => { rejectAbort = reject; });
    const cancel = () => controller.abort(abortError());
    const onAbort = () => rejectAbort(controller.signal.reason);
    controller.signal.addEventListener('abort', onAbort, { once: true });
    external?.addEventListener('abort', cancel, { once: true });
    try {
      if (external?.aborted) throw abortError();
      if (Number.isFinite(timeout) && timeout > 0) {
        timer = setTimeout(() => controller.abort(new DOMException('Request timeout', 'TimeoutError')), timeout);
      }
      const request = fetch(url, { ...init, signal: controller.signal }).then(response => this.handleResponse<T>(response));
      return await Promise.race([request, aborted]);
    } finally {
      clearTimeout(timer);
      external?.removeEventListener('abort', cancel);
      controller.signal.removeEventListener('abort', onAbort);
    }
  }

  private async executeRequest<T>(fn: () => Promise<T>, options: RequestOptions | undefined, retryDefault: boolean): Promise<T> {
    const attempts = (options?.retry ?? retryDefault) ? this.retryCount : 0;
    for (let attempt = 0; ; attempt++) {
      if (options?.signal?.aborted) throw abortError();
      try { return await fn(); }
      catch (error: unknown) {
        const raw = error instanceof Error ? error : new Error(typeof error === 'string' ? error : '请求失败');
        if (raw.name === 'AbortError' || options?.signal?.aborted) throw abortError();
        if (raw.name === 'TimeoutError') throw new ApiErrorWrapper('请求超时，请稍后重试', 408);
        const status = raw instanceof ApiErrorWrapper ? raw.status : undefined;
        if (attempt < attempts && status !== undefined && (status === 408 || (status >= 500 && status < 600))) {
          await delay(this.retryDelay * 2 ** attempt, options?.signal);
          continue;
        }
        throw raw;
      }
    }
  }

  private request<T>(method: string, endpoint: string, body: BodyInit | undefined, options?: RequestOptions, json = true): Promise<T> {
    const init: RequestOptions = { ...options };
    delete init.params; delete init.timeout; delete init.retry;
    const headers = new Headers(init.headers);
    if (json && body !== undefined && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
    if (!json) headers.delete('Content-Type'); // the browser generates the multipart boundary
    const url = this.buildUrl(endpoint, options?.params);
    return this.executeRequest(
      () => this.fetchWithTimeout<T>(url, { ...init, method, headers, body }, options?.timeout ?? this.defaultTimeout),
      options, method === 'GET'
    );
  }

  get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>('GET', endpoint, undefined, options);
  }
  post<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>('POST', endpoint, data == null ? undefined : JSON.stringify(data), options);
  }
  postForm<T>(endpoint: string, formData: FormData, options?: Omit<RequestOptions, 'body'>): Promise<T> {
    return this.request<T>('POST', endpoint, formData, options, false);
  }
  put<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>('PUT', endpoint, data == null ? undefined : JSON.stringify(data), options);
  }
  patch<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>('PATCH', endpoint, data == null ? undefined : JSON.stringify(data), options);
  }
  delete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>('DELETE', endpoint, undefined, options);
  }

  upload<T>(endpoint: string, file: File, options?: RequestOptions & { fieldName?: string; onProgress?: (progress: number) => void }): Promise<T> {
    const form = new FormData();
    form.append(options?.fieldName || 'file', file);
    return new Promise<T>((resolve, reject) => {
      if (options?.signal?.aborted) { reject(abortError()); return; }
      const xhr = new XMLHttpRequest();
      const cancel = () => { xhr.abort(); finish(abortError()); };
      let settled = false;
      const finish = (error?: Error, value?: T) => {
        if (settled) return;
        settled = true;
        options?.signal?.removeEventListener('abort', cancel);
        if (error) reject(error); else resolve(value as T);
      };
      xhr.upload.addEventListener('progress', event => {
        if (event.lengthComputable && event.total > 0) options?.onProgress?.(Math.round(event.loaded / event.total * 100));
      });
      xhr.addEventListener('load', () => {
        if (xhr.status === 204) { finish(); return; }
        let value: unknown;
        try { value = JSON.parse(xhr.responseText); }
        catch { finish(new ApiErrorWrapper('服务器返回的数据格式无效', xhr.status)); return; }
        if (xhr.status >= 200 && xhr.status < 300) finish(undefined, value as T);
        else finish(new ApiErrorWrapper(errorMessage(value, 'Upload failed'), xhr.status, value));
      });
      xhr.addEventListener('error', () => finish(new ApiErrorWrapper('上传过程中发生网络错误，请重试')));
      xhr.addEventListener('abort', () => finish(abortError()));
      xhr.addEventListener('timeout', () => finish(new ApiErrorWrapper('上传超时，请稍后重试', 408)));
      try {
        xhr.open('POST', this.buildUrl(endpoint, options?.params));
        const timeout = options?.timeout ?? this.defaultTimeout;
        xhr.timeout = Number.isFinite(timeout) && timeout > 0 ? timeout : 0;
        xhr.withCredentials = options?.credentials === 'include';
        new Headers(options?.headers).forEach((value, key) => {
          if (key !== 'content-type') xhr.setRequestHeader(key, value);
        });
        options?.signal?.addEventListener('abort', cancel, { once: true });
        xhr.send(form);
      } catch (error) { finish(error instanceof Error ? error : new Error('Upload failed')); }
    });
  }
}

export const apiClient = new ApiClient();
export type { RequestOptions };
