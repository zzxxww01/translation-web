export type MessageRole = 'them' | 'me';

export interface ConversationMessage {
  id: string;  // UUID for React key
  role: MessageRole;
  content: string;
  timestamp: number;
}
