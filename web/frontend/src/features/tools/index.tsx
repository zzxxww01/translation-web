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
    <div className="flex h-full overflow-auto">
      <div className="mx-auto w-full max-w-4xl p-6 animate-liquid-rise">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gradient-primary" style={{ fontFamily: 'var(--font-display)' }}>工具箱</h2>
          <p className="text-sm text-muted-foreground mt-1">实用翻译辅助工具</p>
        </div>

        <Tabs value={currentTool} onValueChange={(v) => setCurrentTool(v as typeof currentTool)}>
          <TabsList className="mb-6 card-glass p-1">
            {tabs.map(tab => (
              <TabsTrigger key={tab.id} value={tab.id} className="gap-2 data-[state=active]:bg-gradient-primary data-[state=active]:text-white">
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
