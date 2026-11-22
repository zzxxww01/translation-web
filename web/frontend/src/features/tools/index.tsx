import { PageHeader } from '@/components/layout/PageHeader';
import { Clock, Languages, Mail } from 'lucide-react';
import { useToolsStore } from '@/shared/stores';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { TimezoneConverter } from './components/TimezoneConverter';
import { TextTranslator } from './components/TextTranslator';
import { EmailReplyGenerator } from './components/EmailReplyGenerator';

// 2026-11-22：去掉「任务管理」和「Slack 回复（旧版）」；Chatbot 是顶部导航里单独的一页
// 时区转换放第一个，也是默认打开的工具
const tabs = [
  { id: 'timezone', label: '时区转换', icon: <Clock className="h-4 w-4" /> },
  { id: 'translator', label: '文本翻译', icon: <Languages className="h-4 w-4" /> },
  { id: 'email', label: '邮件回复', icon: <Mail className="h-4 w-4" /> },
] as const;

export function ToolsFeature() {
  const { currentTool, setCurrentTool } = useToolsStore();

  return (
    <div className="flex h-full min-w-0 overflow-auto">
      {/* 三个工具同一宽度（和帖子翻译一样），切标签时版面不跳 */}
      <div className="mx-auto w-full min-w-0 max-w-7xl px-4 pb-12 pt-5 sm:px-8">
        <PageHeader className="mb-5" title="工具箱" />

        <Tabs value={currentTool} onValueChange={(v) => setCurrentTool(v as typeof currentTool)}>
          <div className="mb-5">
            <TabsList>
              {tabs.map(tab => (
                <TabsTrigger key={tab.id} value={tab.id}>
                  {tab.icon}
                  {tab.label}
                </TabsTrigger>
              ))}
            </TabsList>
          </div>

          <TabsContent value="timezone">
            <TimezoneConverter />
          </TabsContent>
          <TabsContent value="translator">
            <TextTranslator />
          </TabsContent>
          <TabsContent value="email">
            <EmailReplyGenerator />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
