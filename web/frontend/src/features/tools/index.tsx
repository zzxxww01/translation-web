import { Suspense, lazy } from 'react';
import { PageHeader } from '@/components/layout/PageHeader';
import { Bot, Clock, Languages, Loader2, Mail } from 'lucide-react';
import { useToolsStore } from '@/shared/stores';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { TimezoneConverter } from './components/TimezoneConverter';
import { TextTranslator } from './components/TextTranslator';
import { EmailReplyGenerator } from './components/EmailReplyGenerator';

const ChatFeature = lazy(() => import('@/features/chat').then(module => ({ default: module.ChatFeature })));

// 2026-11-22：去掉「任务管理」和「Slack 回复（旧版）」
// 2026-11-28：Chatbot 从顶部导航收进来，放第二个；时区转换仍是第一个、默认打开
const tabs = [
  { id: 'timezone', label: '时区转换', icon: <Clock className="h-4 w-4" /> },
  { id: 'chat', label: 'Chatbot', icon: <Bot className="h-4 w-4" /> },
  { id: 'translator', label: '文本翻译', icon: <Languages className="h-4 w-4" /> },
  { id: 'email', label: '邮件回复', icon: <Mail className="h-4 w-4" /> },
] as const;

export function ToolsFeature() {
  const { currentTool, setCurrentTool } = useToolsStore();

  return (
    <Tabs value={currentTool} onValueChange={(v) => setCurrentTool(v as typeof currentTool)} className="flex h-full min-w-0 flex-col">
      {/* 标题和标签固定在上面；Chatbot 占满下面整块（自己有会话列表和输入框），其他工具在下面滚动 */}
      <div className="mx-auto w-full min-w-0 max-w-7xl shrink-0 px-4 pt-5 sm:px-8">
        <PageHeader className="mb-5" title="工具箱" />
        {/* 手机上四个标签放不下：横向滑动 */}
        <div className="-mx-4 mb-5 overflow-x-auto px-4 sm:mx-0 sm:px-0">
          <TabsList className="w-max">
            {tabs.map(tab => (
              <TabsTrigger key={tab.id} value={tab.id}>
                {tab.icon}
                {tab.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>
      </div>

      <TabsContent value="chat" className="mt-0 min-h-0 flex-1 border-t border-border-subtle data-[state=inactive]:hidden">
        <Suspense fallback={<div className="flex justify-center py-12"><Loader2 className="h-5 w-5 animate-spin text-text-muted" /></div>}>
          <ChatFeature />
        </Suspense>
      </TabsContent>
      {currentTool !== 'chat' && (
        <div className="min-h-0 flex-1 overflow-auto">
          {/* 三个工具同一宽度（和帖子翻译一样），切标签时版面不跳 */}
          <div className="mx-auto w-full min-w-0 max-w-7xl px-4 pb-12 sm:px-8">
            <TabsContent value="timezone" className="mt-0">
              <TimezoneConverter />
            </TabsContent>
            <TabsContent value="translator" className="mt-0">
              <TextTranslator />
            </TabsContent>
            <TabsContent value="email" className="mt-0">
              <EmailReplyGenerator />
            </TabsContent>
          </div>
        </div>
      )}
    </Tabs>
  );
}
