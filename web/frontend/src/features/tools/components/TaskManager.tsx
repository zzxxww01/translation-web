import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Plus, Trash2, Save } from 'lucide-react';
import { useToolsStore } from '@/shared/stores';
import { useLoadTasks, useSaveTasks } from '../hooks';
import { cn } from '@/lib/utils';

export function TaskManager() {
  const { tasks, addTask, updateTask, deleteTask, toggleTask } = useToolsStore();
  const { isLoading } = useLoadTasks();
  const saveMutation = useSaveTasks();

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map(i => <Skeleton key={i} className="h-14 w-full" />)}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold">任务列表</h3>
        <Button
          size="sm"
          variant="outline"
          onClick={() => addTask({ id: Date.now().toString(), text: '新任务', completed: false })}
        >
          <Plus className="h-4 w-4" />
          添加
        </Button>
      </div>

      <div className="space-y-2">
        {tasks.length === 0 && (
          <p className="text-center text-sm text-muted-foreground py-8">暂无任务</p>
        )}
        {tasks.map(task => (
          <Card key={task.id} className={cn(task.completed && 'opacity-60')}>
            <CardContent className="flex items-center gap-3 p-3">
              <input
                type="checkbox"
                checked={task.completed}
                onChange={() => toggleTask(task.id)}
                className="h-4 w-4 rounded border-input"
              />
              <span
                className={cn('min-w-0 flex-1 text-sm outline-none', task.completed && 'line-through text-muted-foreground')}
                contentEditable
                suppressContentEditableWarning
                onBlur={(e) => updateTask(task.id, { text: e.currentTarget.textContent || '' })}
              >
                {task.text}
              </span>
              <Button variant="ghost" size="icon" onClick={() => deleteTask(task.id)}>
                <Trash2 className="h-4 w-4" />
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      {tasks.length > 0 && (
        <Button
          variant="outline"
          className="w-full"
          onClick={() => saveMutation.mutateAsync(tasks)}
          disabled={saveMutation.isPending}
        >
          <Save className="h-4 w-4" />
          {saveMutation.isPending ? '保存中...' : '保存任务'}
        </Button>
      )}
    </div>
  );
}
