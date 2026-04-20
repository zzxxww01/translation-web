import { useRef, useEffect } from 'react';
import { ChevronDown, ChevronUp, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { MessageBubble } from './MessageBubble';
import type { ConversationMessage } from '../store';

interface ConversationBubblesProps {
  messages: ConversationMessage[];
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  onRemoveMessage: (id: string) => void;
  onUpdateMessage: (id: string, content: string) => void;
  onClearAll: () => void;
  onSelectMessage?: (content: string) => void;
}

export function ConversationBubbles({
  messages,
  isCollapsed,
  onToggleCollapse,
  onRemoveMessage,
  onUpdateMessage,
  onClearAll,
  onSelectMessage,
}: ConversationBubblesProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current && !isCollapsed) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isCollapsed]);

  return (
    <Card className="flex flex-col">
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div className="flex items-center gap-2">
          <h3 className="font-medium">对话历史</h3>
          {messages.length > 0 && (
            <span className="text-xs text-muted-foreground">
              ({messages.length} 条消息)
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {messages.length > 0 && (
            <Button
              size="sm"
              variant="ghost"
              onClick={onClearAll}
              className="h-8 text-xs"
            >
              <Trash2 size={14} className="mr-1" />
              清空
            </Button>
          )}
          <Button
            size="sm"
            variant="ghost"
            onClick={onToggleCollapse}
            className="h-8 w-8 p-0"
          >
            {isCollapsed ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
          </Button>
        </div>
      </div>

      {!isCollapsed && (
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto p-4 space-y-3 min-h-[200px] max-h-[400px]"
        >
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
              暂无对话历史
            </div>
          ) : (
            messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                onDelete={onRemoveMessage}
                onEdit={onUpdateMessage}
                onSelect={onSelectMessage}
              />
            ))
          )}
        </div>
      )}
    </Card>
  );
}
