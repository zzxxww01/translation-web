interface TermConflictData {
  term: string;
  existing_translation: string;
  new_translation: string;
  existing_context: string;
  new_context: string;
  existing_section_id?: string;
  new_section_id: string;
}

interface TranslationProgressPayload {
  type: string;
  current?: number;
  total?: number;
  translated_count?: number;
  paragraph_id?: string;
  section_id?: string;
  translation?: string;
  error?: string;
  step?: string;
  message?: string;
  conflict?: TermConflictData;
}

interface TranslationProgressCallback {
  (data: TranslationProgressPayload): void;
}

interface TranslationCompleteCallback {
  (): void;
}

interface TermConflictCallback {
  (conflict: TermConflictData): Promise<{
    chosenTranslation: string;
    applyToAll: boolean;
  }>;
}

type TranslationMethodType = 'normal' | 'four-step';

interface TranslationState {
  isTranslating: boolean;
  projectId: string | null;
  progress: { current: number; total: number } | null;
  controller: AbortController | null;
  model: string | null;
  method: TranslationMethodType | null;
  currentStep: string | null;
  isPaused: boolean;
  pendingConflict: TermConflictData | null;
}

class FullTranslationService {
  private state: TranslationState = {
    isTranslating: false,
    projectId: null,
    progress: null,
    controller: null,
    model: null,
    method: null,
    currentStep: null,
    isPaused: false,
    pendingConflict: null,
  };

  private onProgressCallback: TranslationProgressCallback | null = null;
  private onCompleteCallback: TranslationCompleteCallback | null = null;
  private onTermConflictCallback: TermConflictCallback | null = null;

  setTermConflictCallback(callback: TermConflictCallback | null): void {
    this.onTermConflictCallback = callback;
  }

  async startTranslation(
    projectId: string,
    onProgress: TranslationProgressCallback,
    onComplete: TranslationCompleteCallback,
    model?: string,
    method: TranslationMethodType = 'normal'
  ): Promise<void> {
    if (this.state.isTranslating && this.state.projectId === projectId) {
      return;
    }

    if (this.state.isTranslating) {
      this.stopTranslation();
    }

    this.state.isTranslating = true;
    this.state.projectId = projectId;
    this.state.progress = { current: 0, total: 0 };
    this.state.model = model || null;
    this.state.method = method;
    this.state.currentStep = null;
    this.state.isPaused = false;
    this.state.pendingConflict = null;
    this.onProgressCallback = onProgress;
    this.onCompleteCallback = onComplete;

    const controller = new AbortController();
    this.state.controller = controller;

    const endpoint =
      method === 'four-step'
        ? `/api/projects/${projectId}/translate-four-step`
        : `/api/projects/${projectId}/translate-stream`;

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ model: model || 'preview' }),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No reader available');
      }

      const decoder = new TextDecoder();
      const translatedParagraphs = new Set<string>();
      let buffer = '';

      while (this.state.isTranslating) {
        const { done, value } = await reader.read();

        if (done) {
          buffer += decoder.decode();
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const frames = this.drainSseFrames(buffer);
        buffer = frames.remainder;

        for (const frame of frames.events) {
          const event = this.parseSseEvent(frame);
          if (!event) {
            continue;
          }

          const shouldStop = await this.handleEvent(projectId, event, translatedParagraphs);
          if (shouldStop) {
            return;
          }
        }
      }

      if (buffer.trim()) {
        const event = this.parseSseEvent(buffer);
        if (event) {
          const shouldStop = await this.handleEvent(projectId, event, translatedParagraphs);
          if (shouldStop) {
            return;
          }
        }
      }

      if (this.state.isTranslating) {
        this.finalizeTranslation(false);
      }
    } catch (error: unknown) {
      if (error instanceof Error && error.name === 'AbortError') {
        return;
      }

      console.error('Translation error:', error);
      this.finalizeTranslation(false);
    }
  }

  private drainSseFrames(buffer: string): { events: string[]; remainder: string } {
    const events: string[] = [];
    let remaining = buffer;

    while (true) {
      const match = remaining.match(/\r?\n\r?\n/);
      if (!match || match.index === undefined) {
        break;
      }

      const boundaryIndex = match.index;
      const boundaryLength = match[0].length;
      events.push(remaining.slice(0, boundaryIndex));
      remaining = remaining.slice(boundaryIndex + boundaryLength);
    }

    return { events, remainder: remaining };
  }

  private parseSseEvent(rawFrame: string): TranslationProgressPayload | null {
    const dataLines = rawFrame
      .split(/\r?\n/)
      .filter(line => line.startsWith('data:'))
      .map(line => line.slice(5).trimStart());

    if (!dataLines.length) {
      return null;
    }

    const dataText = dataLines.join('\n').trim();
    if (!dataText) {
      return null;
    }

    try {
      return JSON.parse(dataText) as TranslationProgressPayload;
    } catch {
      return null;
    }
  }

  private async handleEvent(
    projectId: string,
    data: TranslationProgressPayload,
    translatedParagraphs: Set<string>
  ): Promise<boolean> {
    if (data.type === 'start') {
      this.state.progress = { current: 0, total: data.total || 0 };
    } else if (data.type === 'translated' && data.paragraph_id && data.section_id && data.translation) {
      const paragraphKey = `${data.section_id}-${data.paragraph_id}`;
      if (!translatedParagraphs.has(paragraphKey)) {
        translatedParagraphs.add(paragraphKey);
      }
      this.state.progress = {
        current: data.current || this.state.progress?.current || 0,
        total: data.total || this.state.progress?.total || 0,
      };
    } else if (data.type === 'progress') {
      this.state.currentStep = data.step || data.message || null;
      this.state.progress = {
        current: data.current || this.state.progress?.current || 0,
        total: data.total || this.state.progress?.total || 0,
      };
    } else if (data.type === 'skip' || data.type === 'error') {
      this.state.progress = {
        current: data.current || this.state.progress?.current || 0,
        total: data.total || this.state.progress?.total || 0,
      };
    } else if (data.type === 'heartbeat') {
      return false;
    } else if (data.type === 'term_conflict') {
      this.state.isPaused = true;
      this.state.pendingConflict = data.conflict || null;

      if (this.onTermConflictCallback && data.conflict) {
        try {
          const resolution = await this.onTermConflictCallback(data.conflict);
          await this.resolveConflict(projectId, data.conflict.term, resolution);
          this.state.isPaused = false;
          this.state.pendingConflict = null;
        } catch (error) {
          console.error('Failed to resolve conflict:', error);
        }
      }
    } else if (data.type === 'complete') {
      if (data.translated_count !== undefined && data.total !== undefined) {
        this.state.progress = {
          current: data.translated_count,
          total: data.total,
        };
      }
      this.finalizeTranslation(true);
      if (this.onProgressCallback) {
        this.onProgressCallback(data);
      }
      return true;
    }

    if (this.onProgressCallback) {
      this.onProgressCallback(data);
    }

    return false;
  }

  private finalizeTranslation(isCompleted: boolean): void {
    this.state.isTranslating = false;
    this.state.controller = null;
    this.state.currentStep = null;
    this.state.isPaused = false;
    this.state.pendingConflict = null;

    if (this.onCompleteCallback) {
      this.onCompleteCallback();
    }

    if (!isCompleted) {
      this.state.method = null;
    }
  }

  private async resolveConflict(
    projectId: string,
    term: string,
    resolution: { chosenTranslation: string; applyToAll: boolean }
  ): Promise<void> {
    const response = await fetch(`/api/projects/${projectId}/resolve-conflict`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        term,
        chosen_translation: resolution.chosenTranslation,
        apply_to_all: resolution.applyToAll,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to resolve conflict: ${response.status}`);
    }
  }

  stopTranslation(): void {
    if (this.state.controller) {
      this.state.controller.abort();
      this.state.controller = null;
    }
    this.state.isTranslating = false;
    this.state.progress = null;
    this.state.method = null;
    this.state.currentStep = null;
    this.state.isPaused = false;
    this.state.pendingConflict = null;
  }

  getState(): TranslationState {
    return { ...this.state };
  }

  isTranslating(): boolean {
    return this.state.isTranslating;
  }

  isPaused(): boolean {
    return this.state.isPaused;
  }

  getPendingConflict(): TermConflictData | null {
    return this.state.pendingConflict;
  }

  getProjectId(): string | null {
    return this.state.projectId;
  }

  getProgress(): { current: number; total: number } | null {
    return this.state.progress;
  }

  getModel(): string | null {
    return this.state.model;
  }

  getMethod(): TranslationMethodType | null {
    return this.state.method;
  }

  getCurrentStep(): string | null {
    return this.state.currentStep;
  }
}

export const fullTranslationService = new FullTranslationService();

export type { TermConflictData, TermConflictCallback, TranslationMethodType };
