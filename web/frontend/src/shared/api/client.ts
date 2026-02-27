/**
 * API 客户端
 * 提供统一的 API 请求接口，支持超时、重试、错误处理
 */

import type { ApiError } from '../types';
import { API_BASE, API_TIMEOUT, API_RETRY_COUNT, API_RETRY_DELAY } from '../constants';

/**
 * API 请求选项
 */
interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean>;
  timeout?: number;
  retry?: boolean;
}

/**
 * API 错误类
 */
export class ApiErrorWrapper extends Error {
  public status?: number;
  public data?: unknown;

  constructor(message: string, status?: number, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

/**
 * 延迟函数
 */
function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * 判断是否应该重试请求
 */
function shouldRetry(status: number | undefined): boolean {
  if (!status) return false;
  // 5xx 错误和 408 请求超时可以重试
  return status >= 500 || status === 408;
}

/**
 * API 客户端类
 */
export class ApiClient {
  private baseUrl: string;
  private defaultTimeout: number;
  private retryCount: number;
  private retryDelay: number;

  constructor(
    baseUrl: string = API_BASE,
    options?: { timeout?: number; retryCount?: number; retryDelay?: number }
  ) {
    this.baseUrl = baseUrl;
    this.defaultTimeout = options?.timeout ?? API_TIMEOUT;
    this.retryCount = options?.retryCount ?? API_RETRY_COUNT;
    this.retryDelay = options?.retryDelay ?? API_RETRY_DELAY;
  }

  /**
   * 构建 URL，支持查询参数
   */
  private buildUrl(endpoint: string, params?: Record<string, string | number | boolean>): string {
    const url = `${this.baseUrl}${endpoint}`;
    if (params) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        searchParams.append(key, String(value));
      });
      const queryString = searchParams.toString();
      if (queryString) {
        return `${url}?${queryString}`;
      }
    }
    return url;
  }

  /**
   * 创建带超时的 fetch
   */
  private fetchWithTimeout(
    url: string,
    options: RequestInit,
    timeout: number
  ): Promise<Response> {
    if (!Number.isFinite(timeout) || timeout <= 0) {
      return fetch(url, options);
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    return fetch(url, {
      ...options,
      signal: controller.signal,
    })
      .finally(() => {
        clearTimeout(timeoutId);
      });
  }

  /**
   * 处理响应
   */
  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      let errorData: ApiError = { detail: 'Unknown error', status: response.status };

      try {
        const data = await response.json();
        errorData = { ...data, status: response.status };
      } catch {
        // JSON 解析失败，使用默认错误消息
        errorData.detail = response.statusText || 'API Error';
      }

      throw new ApiErrorWrapper(
        errorData.detail || 'API Error',
        response.status,
        errorData
      );
    }

    // 处理 204 No Content
    if (response.status === 204) {
      return undefined as T;
    }

    const text = await response.text();
    let data: T;
    try {
      data = JSON.parse(text) as T;
    } catch {
      throw new Error('Invalid JSON response from server');
    }

    return data;
  }

  /**
   * 执行请求（带重试）
   */
  private async executeRequest<T>(
    fn: () => Promise<Response>,
    options?: RequestOptions
  ): Promise<T> {
    const retry = options?.retry !== false;
    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= (retry ? this.retryCount : 0); attempt++) {
      try {
        const response = await fn();
        return await this.handleResponse<T>(response);
      } catch (error) {
        const rawError = error as Error;
        const errorName = (rawError as { name?: string } | null)?.name ?? '';
        const isAbort =
          errorName === 'AbortError' ||
          errorName === 'TimeoutError' ||
          rawError.message.toLowerCase().includes('aborted');

        const normalizedError = isAbort
          ? new ApiErrorWrapper('Request timeout. Please try again.', 408)
          : rawError;

        lastError = normalizedError as Error;

        // 判断是否需要重试
        if (
          retry &&
          attempt < this.retryCount &&
          normalizedError instanceof ApiErrorWrapper &&
          shouldRetry(normalizedError.status) &&
          !isAbort
        ) {
          // 等待后重试
          await delay(this.retryDelay * Math.pow(2, attempt));
          continue;
        }

        throw normalizedError;
      }
    }

    throw lastError;
  }

  /**
   * GET 请求
   */
  async get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    const url = this.buildUrl(endpoint, options?.params);

    return this.executeRequest<T>(
      () =>
        this.fetchWithTimeout(
          url,
          {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
              ...options?.headers,
            },
          },
          options?.timeout ?? this.defaultTimeout
        ),
      options
    );
  }

  /**
   * POST 请求
   */
  async post<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
    const url = this.buildUrl(endpoint, options?.params);
    const hasBody = data !== undefined && data !== null;
    return this.executeRequest<T>(
      () =>
        this.fetchWithTimeout(
          url,
          {
            method: 'POST',
            headers: {
              ...(hasBody ? { 'Content-Type': 'application/json' } : {}),
              ...options?.headers,
            },
            body: hasBody ? JSON.stringify(data) : undefined,
          },
          options?.timeout ?? this.defaultTimeout
        ),
      options
    );
  }

  /**
   * POST form-data request.
   */
  async postForm<T>(
    endpoint: string,
    formData: FormData,
    options?: Omit<RequestOptions, 'body'>
  ): Promise<T> {
    const url = this.buildUrl(endpoint, options?.params);
    return this.executeRequest<T>(
      () =>
        this.fetchWithTimeout(
          url,
          {
            method: 'POST',
            headers: {
              ...options?.headers,
            },
            body: formData,
          },
          options?.timeout ?? this.defaultTimeout
        ),
      options
    );
  }

  /**
   * PUT 请求
   */
  async put<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
    const url = this.buildUrl(endpoint, options?.params);
    const hasBody = data !== undefined && data !== null;
    return this.executeRequest<T>(
      () =>
        this.fetchWithTimeout(
          url,
          {
            method: 'PUT',
            headers: {
              ...(hasBody ? { 'Content-Type': 'application/json' } : {}),
              ...options?.headers,
            },
            body: hasBody ? JSON.stringify(data) : undefined,
          },
          options?.timeout ?? this.defaultTimeout
        ),
      options
    );
  }

  /**
   * PATCH 请求
   */
  async patch<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
    const url = this.buildUrl(endpoint, options?.params);
    const hasBody = data !== undefined && data !== null;
    return this.executeRequest<T>(
      () =>
        this.fetchWithTimeout(
          url,
          {
            method: 'PATCH',
            headers: {
              ...(hasBody ? { 'Content-Type': 'application/json' } : {}),
              ...options?.headers,
            },
            body: hasBody ? JSON.stringify(data) : undefined,
          },
          options?.timeout ?? this.defaultTimeout
        ),
      options
    );
  }

  /**
   * DELETE 请求
   */
  async delete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    const url = this.buildUrl(endpoint, options?.params);
    return this.executeRequest<T>(
      () =>
        this.fetchWithTimeout(
          url,
          {
            method: 'DELETE',
            headers: {
              'Content-Type': 'application/json',
              ...options?.headers,
            },
          },
          options?.timeout ?? this.defaultTimeout
        ),
      options
    );
  }

  /**
   * 上传文件
   */
  async upload<T>(
    endpoint: string,
    file: File,
    options?: RequestOptions & { fieldName?: string; onProgress?: (progress: number) => void }
  ): Promise<T> {
    const url = this.buildUrl(endpoint, options?.params);
    const formData = new FormData();
    formData.append(options?.fieldName || 'file', file);

    // 使用 XMLHttpRequest 以支持进度回调
    return new Promise<T>((resolve, reject) => {
      const xhr = new XMLHttpRequest();

      // 监听上传进度
      if (options?.onProgress) {
        xhr.upload.addEventListener('progress', e => {
          if (e.lengthComputable) {
            options.onProgress?.(Math.round((e.loaded / e.total) * 100));
          }
        });
      }

      // 监听响应
      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const response = JSON.parse(xhr.responseText);
            resolve(response as T);
          } catch {
            resolve(undefined as T);
          }
        } else {
          let errorData: ApiError = { detail: 'Upload failed', status: xhr.status };
          try {
            errorData = { ...JSON.parse(xhr.responseText), status: xhr.status };
          } catch {
            // 使用默认错误
          }
          reject(new ApiErrorWrapper(errorData.detail || 'Upload failed', xhr.status));
        }
      });

      // 监听错误
      xhr.addEventListener('error', () => {
        reject(new ApiErrorWrapper('Network error during upload'));
      });

      // 监听超时
      xhr.addEventListener('timeout', () => {
        reject(new ApiErrorWrapper('Upload timeout'));
      });

      // 发送请求
      xhr.open('POST', url);
      xhr.timeout = options?.timeout ?? this.defaultTimeout;

      // 添加自定义 headers
      if (options?.headers) {
        Object.entries(options.headers).forEach(([key, value]) => {
          if (key.toLowerCase() !== 'content-type') {
            xhr.setRequestHeader(key, value as string);
          }
        });
      }

      xhr.send(formData);
    });
  }
}

/**
 * 导出单例实例
 */
export const apiClient = new ApiClient();

/**
 * 导出类型
 */
export type { RequestOptions };
