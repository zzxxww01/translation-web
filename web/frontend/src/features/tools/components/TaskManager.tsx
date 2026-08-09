import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
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
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">任务列表</h3>
        <Button
          size="sm"
          variant="outline"
          onClick={() => addTask({ id: crypto.randomUUID(), text: '新任务', completed: false })}
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
                aria-label={`${task.completed ? '标记为未完成' : '标记为已完成'}：${task.text}`}
              />
              <Input
                value={task.text}
                onChange={event => updateTask(task.id, { text: event.target.value })}
                aria-label="任务内容"
                className={cn('h-9 min-w-0 flex-1 border-0 bg-transparent px-1 shadow-none', task.completed && 'line-through text-muted-foreground')}
              />
              <Button variant="ghost" size="icon" onClick={() => deleteTask(task.id)} title="删除任务">
                <Trash2 className="h-4 w-4" />
                <span className="sr-only">删除任务</span>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      {tasks.length > 0 && (
        <Button
          variant="outline"
          className="w-full"
          onClick={() => void saveMutation.mutateAsync(tasks)}
          disabled={saveMutation.isPending}
        >
          <Save className="h-4 w-4" />
          {saveMutation.isPending ? '保存中...' : '保存任务'}
        </Button>
      )}
    </div>
  );
}
