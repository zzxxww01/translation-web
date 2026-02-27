/**
 * 增强全文翻译服务
 * 支持模型选择、暂停/恢复、进度跟踪等功能
 */

import { useState, useEffect } from 'react';

export interface TranslationProgress {
  current: number;
  total: number;
  currentStep?: string;
  model?: string;
  estimatedTimeRemaining?: number;
  sectionsCompleted?: number;
  totalSections?: number;
}

export interface TranslationEvent {
  type: 'start' | 'progress' | 'pause' | 'resume' | 'complete' | 'error' | 'stop';
  data?: unknown;
  progress?: TranslationProgress;
  error?: string;
}

interface StreamEventPayload {
  type: string;
  total?: number;
  model?: string;
  current?: number;
  paragraph_id?: string;
  error?: string;
  [key: string]: unknown;
}

export interface TranslationOptions {
  model: string;
  mode: 'section' | 'four_step';
  pauseAfterSections?: number;
  retryOnFailure?: boolean;
  maxRetries?: number;
}

export type TranslationEventHandler = (event: TranslationEvent) => void;

export class EnhancedFullTranslationService {
  private projectId: string;
  private eventSource: EventSource | null = null;
  private isTranslating: boolean = false;
  private isPaused: boolean = false;
  private shouldStop: boolean = false;
  private eventHandlers: TranslationEventHandler[] = [];

  // Progress tracking
  private startTime: number = 0;
  private progress: TranslationProgress = {
    current: 0,
    total: 0,
  };

  // Performance statistics
  private stats = {
    totalParagraphs: 0,
    translatedParagraphs: 0,
    skippedParagraphs: 0,
    errorCount: 0,
    avgTimePerParagraph: 0,
    currentModel: '',
  };

  constructor(projectId: string) {
    this.projectId = projectId;
  }

  /**
   * 添加事件监听器
   */
  public addEventListener(handler: TranslationEventHandler): void {
    this.eventHandlers.push(handler);
  }

  /**
   * 移除事件监听器
   */
  public removeEventListener(handler: TranslationEventHandler): void {
    const index = this.eventHandlers.indexOf(handler);
    if (index > -1) {
      this.eventHandlers.splice(index, 1);
    }
  }

  /**
   * 触发事件
   */
  private emit(event: TranslationEvent): void {
    this.eventHandlers.forEach(handler => {
      try {
        handler(event);
      } catch (error) {
        console.error('Event handler error:', error);
      }
    });
  }

  /**
   * 开始翻译
   */
  public async startTranslation(options: TranslationOptions): Promise<void> {
    if (this.isTranslating) {
      throw new Error('Translation is already in progress');
    }

    this.isTranslating = true;
    this.isPaused = false;
    this.shouldStop = false;
    this.startTime = Date.now();
    this.stats.currentModel = options.model;

    this.emit({
      type: 'start',
      data: { options },
      progress: this.progress,
    });

    try {
      await this.performTranslation(options);
    } catch (error) {
      this.emit({
        type: 'error',
        error: error instanceof Error ? error.message : 'Unknown error',
        progress: this.progress,
      });
      throw error;
    }
  }

  /**
   * 暂停翻译
   */
  public pauseTranslation(): void {
    if (!this.isTranslating || this.isPaused) {
      return;
    }

    this.isPaused = true;
    this.emit({
      type: 'pause',
      progress: this.progress,
    });
  }

  /**
   * 恢复翻译
   */
  public resumeTranslation(): void {
    if (!this.isTranslating || !this.isPaused) {
      return;
    }

    this.isPaused = false;
    this.emit({
      type: 'resume',
      progress: this.progress,
    });
  }

  /**
   * 停止翻译
   */
  public stopTranslation(): void {
    this.shouldStop = true;
    this.isPaused = false;

    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }

    this.isTranslating = false;
    this.emit({
      type: 'stop',
      progress: this.progress,
    });
  }

  /**
   * 获取当前状态
   */
  public getStatus() {
    return {
      isTranslating: this.isTranslating,
      isPaused: this.isPaused,
      progress: this.progress,
      stats: this.stats,
    };
  }

  /**
   * 执行翻译
   */
  private async performTranslation(options: TranslationOptions): Promise<void> {
    try {
      // 构建API URL
      const url = new URL(`/api/projects/${this.projectId}/translate-stream`, window.location.origin);
      if (options.model) {
        url.searchParams.set('model', options.model);
      }
      if (options.mode) {
        url.searchParams.set('mode', options.mode);
      }

      // 创建EventSource连接
      this.eventSource = new EventSource(url.toString());

      return new Promise((resolve, reject) => {
        if (!this.eventSource) {
          reject(new Error('Failed to create EventSource'));
          return;
        }

        this.eventSource.onmessage = (event) => {
          try {
            const parsed = JSON.parse(event.data) as unknown;
            if (parsed && typeof parsed === 'object') {
              this.handleStreamEvent(parsed as StreamEventPayload, resolve);
            }
          } catch (error) {
            console.error('Failed to parse stream event:', error);
          }
        };

        this.eventSource.onerror = (error) => {
          console.error('EventSource error:', error);
          this.stopTranslation();
          reject(new Error('Translation stream error'));
        };
      });

    } catch (error) {
      this.isTranslating = false;
      throw error;
    }
  }

  /**
   * 处理流事件
   */
  private handleStreamEvent(
    data: StreamEventPayload,
    resolve: () => void
  ): void {
    // 检查是否应该停止
    if (this.shouldStop) {
      this.eventSource?.close();
      this.isTranslating = false;
      resolve();
      return;
    }

    // 检查是否暂停
    if (this.isPaused) {
      // 暂停时不处理进度事件，但继续监听
      return;
    }

    switch (data.type) {
      case 'start':
        this.progress = {
          current: 0,
          total: data.total || 0,
          model: data.model,
        };
        this.stats.totalParagraphs = data.total || 0;
        this.emit({
          type: 'progress',
          progress: this.progress,
        });
        break;

      case 'translated':
      case 'skip':
        this.progress.current = data.current || 0;
        this.progress.currentStep = data.type === 'translated' ?
          `翻译段落 ${data.paragraph_id}` :
          `跳过段落 ${data.paragraph_id}`;

        // 更新统计
        if (data.type === 'translated') {
          this.stats.translatedParagraphs++;
        } else {
          this.stats.skippedParagraphs++;
        }

        // 计算预估剩余时间
        this.updateEstimatedTime();

        this.emit({
          type: 'progress',
          data,
          progress: this.progress,
        });
        break;

      case 'complete':
        this.progress.current = data.total || this.progress.total;
        this.progress.currentStep = '翻译完成';
        this.progress.estimatedTimeRemaining = 0;

        this.isTranslating = false;
        this.eventSource?.close();
        this.eventSource = null;

        this.emit({
          type: 'complete',
          data,
          progress: this.progress,
        });
        resolve();
        break;

      case 'error':
        this.stats.errorCount++;
        if (data.error) {
          console.error('Translation error:', data.error);
          this.emit({
            type: 'error',
            error: data.error,
            progress: this.progress,
          });
        }
        break;

      default:
        console.log('Unknown stream event:', data);
    }
  }

  /**
   * 更新预估剩余时间
   */
  private updateEstimatedTime(): void {
    const elapsed = Date.now() - this.startTime;
    const completed = this.progress.current;
    const remaining = this.progress.total - completed;

    if (completed > 0 && remaining > 0) {
      const avgTimePerItem = elapsed / completed;
      this.progress.estimatedTimeRemaining = Math.round((avgTimePerItem * remaining) / 1000);
      this.stats.avgTimePerParagraph = avgTimePerItem / 1000;
    }
  }

  /**
   * 重试失败的翻译
   */
  public async retryTranslation(options: TranslationOptions): Promise<void> {
    if (this.isTranslating) {
      throw new Error('Cannot retry while translation is in progress');
    }

    // 重置状态
    this.progress.current = Math.max(0, this.progress.current - 1);
    this.stats.errorCount = 0;

    // 重新开始翻译
    await this.startTranslation(options);
  }

  /**
   * 获取性能统计
   */
  public getPerformanceStats() {
    const elapsed = this.isTranslating ? Date.now() - this.startTime : 0;

    return {
      ...this.stats,
      elapsedTime: Math.round(elapsed / 1000),
      successRate: this.stats.totalParagraphs > 0 ?
        (this.stats.translatedParagraphs / this.stats.totalParagraphs) * 100 : 0,
      errorRate: this.stats.totalParagraphs > 0 ?
        (this.stats.errorCount / this.stats.totalParagraphs) * 100 : 0,
    };
  }

  /**
   * 清理资源
   */
  public dispose(): void {
    this.stopTranslation();
    this.eventHandlers = [];
  }
}

/**
 * 创建翻译服务实例
 */
export function createEnhancedTranslationService(projectId: string): EnhancedFullTranslationService {
  return new EnhancedFullTranslationService(projectId);
}

/**
 * 翻译服务Hook（React）
 */
export function useEnhancedTranslationService(projectId: string) {
  const [service] = useState(() => createEnhancedTranslationService(projectId));
  const [status, setStatus] = useState(service.getStatus());

  useEffect(() => {
    const handleEvent = () => {
      setStatus(service.getStatus());
    };

    service.addEventListener(handleEvent);

    return () => {
      service.removeEventListener(handleEvent);
      service.dispose();
    };
  }, [service]);

  return {
    service,
    ...status,
    startTranslation: (options: TranslationOptions) => service.startTranslation(options),
    pauseTranslation: () => service.pauseTranslation(),
    resumeTranslation: () => service.resumeTranslation(),
    stopTranslation: () => service.stopTranslation(),
    retryTranslation: (options: TranslationOptions) => service.retryTranslation(options),
    getPerformanceStats: () => service.getPerformanceStats(),
  };
}
