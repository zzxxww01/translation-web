import { useState } from 'react';
import { Trash2, Edit2, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { ConversationMessage } from '../store';

interface MessageBubbleProps {
  message: ConversationMessage;
  onDelete: (id: string) => void;
  onEdit: (id: string, content: string) => void;
}

export function MessageBubble({ message, onDelete, onEdit }: MessageBubbleProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [isTranslationExpanded, setIsTranslationExpanded] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(message.content);

  const isThemMessage = message.role === 'them';

  const handleSaveEdit = () => {
    if (editContent.trim() !== message.content) {
      onEdit(message.id, editContent.trim());
    }
    setIsEditing(false);
  };

  return (
    <div
      className={cn(
        'flex w-full',
        isThemMessage ? 'justify-start' : 'justify-end'
      )}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div
        className={cn(
          'relative max-w-[70%] rounded-2xl px-4 py-2.5',
          isThemMessage
            ? 'bg-muted text-foreground rounded-bl-sm'
            : 'bg-primary text-primary-foreground rounded-br-sm'
        )}
      >
        {isEditing ? (
          <div className="space-y-2">
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="w-full min-h-[60px] p-2 rounded border bg-background text-foreground"
              autoFocus
            />
            <div className="flex gap-2">
              <Button size="sm" onClick={handleSaveEdit}>保存</Button>
              <Button size="sm" variant="outline" onClick={() => setIsEditing(false)}>取消</Button>
            </div>
          </div>
        ) : (
          <>
            <div className="whitespace-pre-wrap break-words">{message.content}</div>

            {isThemMessage && message.translation && (
              <div className="mt-2 pt-2 border-t border-border/50">
                <button
                  onClick={() => setIsTranslationExpanded(!isTranslationExpanded)}
                  className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                >
                  {isTranslationExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  中文翻译
                </button>
                {isTranslationExpanded && (
                  <div className="mt-1 text-sm opacity-80">{message.translation}</div>
                )}
              </div>
            )}
          </>
        )}

        {isHovered && !isEditing && (
          <div className="absolute -top-8 right-0 flex gap-1 bg-background border rounded-md shadow-sm p-1">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setIsEditing(true)}
              className="h-6 w-6 p-0"
            >
              <Edit2 size={14} />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onDelete(message.id)}
              className="h-6 w-6 p-0 text-destructive hover:text-destructive"
            >
              <Trash2 size={14} />
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
