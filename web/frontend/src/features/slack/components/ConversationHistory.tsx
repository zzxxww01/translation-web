import { useState } from 'react';
import { X, ChevronDown, ChevronUp, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import type { ConversationMessage } from '@/shared/types';

interface ConversationHistoryProps {
  messages: ConversationMessage[];
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  onRemoveMessage: (id: string) => void;
  onUpdateMessage: (id: string, content: string) => void;
  onClearAll: () => void;
}

export function ConversationHistory({
  messages,
  isCollapsed,
  onToggleCollapse,
  onRemoveMessage,
  onUpdateMessage,
  onClearAll,
}: ConversationHistoryProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');

  const handleStartEdit = (msg: ConversationMessage) => {
    setEditingId(msg.id);
    setEditContent(msg.content);
  };

  const handleSaveEdit = (id: string) => {
    if (editContent.trim()) {
      onUpdateMessage(id, editContent.trim());
    }
    setEditingId(null);
    setEditContent('');
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditContent('');
  };

  return (
    <Card className="mb-6 p-4">
      <div className="mb-2 flex items-center justify-between">
        <button
          onClick={onToggleCollapse}
          className="flex items-center gap-2 text-sm font-semibold hover:text-primary"
        >
          {isCollapsed ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
          对话历史 ({messages.length} 条消息)
        </button>
        {messages.length > 0 && (
          <Button variant="ghost" size="sm" onClick={onClearAll}>
            <Trash2 className="h-4 w-4" />
            清空对话
          </Button>
        )}
      </div>

      {!isCollapsed && (
        <div className="space-y-2">
          {messages.length === 0 ? (
            <div className="rounded-lg border border-dashed bg-muted/30 p-6 text-center text-sm text-muted-foreground">
              暂无对话历史。使用"英译中 + 建议回复"或"生成英文版本"后，消息会自动加入历史记录。
            </div>
          ) : (
            messages.map((msg) => (
            <div
              key={msg.id}
              className="group flex items-start gap-2 rounded-lg border bg-muted/30 p-3"
            >
              <div className="flex-1">
                <div className="mb-1 text-xs font-semibold text-muted-foreground">
                  {msg.role === 'me' ? '[我]' : '[对方]'}
                </div>
                {editingId === msg.id ? (
                  <div className="space-y-2">
                    <textarea
                      value={editContent}
                      onChange={(e) => setEditContent(e.target.value)}
                      className="w-full rounded border p-2 text-sm"
                      rows={3}
                    />
                    <div className="flex gap-2">
                      <Button size="sm" onClick={() => handleSaveEdit(msg.id)}>
                        保存
                      </Button>
                      <Button size="sm" variant="outline" onClick={handleCancelEdit}>
                        取消
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div
                    onClick={() => handleStartEdit(msg)}
                    className="cursor-pointer whitespace-pre-wrap text-sm hover:text-primary"
                  >
                    {msg.content}
                  </div>
                )}
              </div>
              <button
                onClick={() => onRemoveMessage(msg.id)}
                className="opacity-0 transition-opacity group-hover:opacity-100"
              >
                <X className="h-4 w-4 text-muted-foreground hover:text-destructive" />
              </button>
            </div>
          )))}
        </div>
      )}
    </Card>
  );
}
