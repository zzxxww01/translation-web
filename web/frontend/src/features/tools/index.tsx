import { CheckSquare, Languages, Mail, Clock } from 'lucide-react';
import { useToolsStore } from '@/shared/stores';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { TimezoneConverter } from './components/TimezoneConverter';
import { TextTranslator } from './components/TextTranslator';
import { EmailReplyGenerator } from './components/EmailReplyGenerator';
import { TaskManager } from './components/TaskManager';

const tabs = [
  { id: 'timezone', label: '时区转换', icon: <Clock className="h-4 w-4" /> },
  { id: 'translator', label: '文本翻译', icon: <Languages className="h-4 w-4" /> },
  { id: 'email', label: '邮件回复', icon: <Mail className="h-4 w-4" /> },
  { id: 'tasks', label: '任务管理', icon: <CheckSquare className="h-4 w-4" /> },
] as const;

export function ToolsFeature() {
  const { currentTool, setCurrentTool } = useToolsStore();

  return (
    <div className="flex h-full overflow-auto bg-[#f7f8fa] md:bg-transparent">
      <div className="mx-auto w-full max-w-5xl p-3 animate-liquid-rise md:p-6">
        <div className="mb-4 flex flex-col gap-1 md:mb-5">
          <h2 className="text-2xl font-semibold tracking-normal text-slate-950 md:text-3xl" style={{ fontFamily: 'var(--font-display)' }}>工具箱</h2>
          <p className="text-sm text-slate-500">常用翻译辅助工具集中处理。</p>
        </div>

        <Tabs value={currentTool} onValueChange={(v) => setCurrentTool(v as typeof currentTool)}>
          <TabsList className="mb-4 grid h-auto w-full grid-cols-2 gap-1 p-1 sm:inline-flex sm:w-auto sm:grid-cols-none md:mb-5">
            {tabs.map(tab => (
              <TabsTrigger key={tab.id} value={tab.id} className="h-9 gap-2">
                {tab.icon}
                {tab.label}
              </TabsTrigger>
            ))}
          </TabsList>

          <TabsContent value="timezone">
            <TimezoneConverter />
          </TabsContent>
          <TabsContent value="translator">
            <TextTranslator />
          </TabsContent>
          <TabsContent value="email">
            <EmailReplyGenerator />
          </TabsContent>
          <TabsContent value="tasks">
            <TaskManager />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
