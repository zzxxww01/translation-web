export type ContextType = 'incoming' | 'draft';

export interface RefinementVariant {
  id: string;
  content: string;
  timestamp: number;
}

export interface RefinementSession {
  contextType: ContextType;
  originalInput: string;
  variants: RefinementVariant[];
  isRefining: boolean;
}

export interface ConversationMessage {
  role: string;
  content: string;
}
