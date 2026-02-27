/**
 * 工具箱功能模块
 * 同步原生 JS 版本的所有功能
 */

import { useState, useEffect, useCallback } from 'react';
import {
  CheckSquare,
  Languages,
  Mail,
  Clock,
  Plus,
  Trash2,
  RotateCw,
  ArrowRightLeft,
  Send,
} from 'lucide-react';
import { useToolsStore } from '../../shared/stores';
import { useLoadTasks, useSaveTasks, useTranslateText, useGenerateEmailReply, useConvertTimezone } from './hooks';
import { Button } from '../../components/ui';
import { Input } from '../../components/ui';
import { Textarea } from '../../components/ui';
import { TabsWithPanel } from '../../components/ui';
import { copyToClipboard } from '../../shared/utils';
import { EmailStyle } from '../../shared/constants';
import type { TimezoneConvertResult } from '../../shared/types';

type ToolTab = 'tasks' | 'translator' | 'email' | 'timezone';

const toolTabs = [
  { id: 'tasks', label: '任务管理', icon: <CheckSquare className="h-5 w-5" /> },
  { id: 'translator', label: '文本翻译', icon: <Languages className="h-5 w-5" /> },
  { id: 'email', label: '邮件回复', icon: <Mail className="h-5 w-5" /> },
  { id: 'timezone', label: '时区转换', icon: <Clock className="h-5 w-5" /> },
];

/**
 * 格式化时间
 */
function formatTime(date: Date): string {
  const hours = date.getHours().toString().padStart(2, '0');
  const minutes = date.getMinutes().toString().padStart(2, '0');
  const seconds = date.getSeconds().toString().padStart(2, '0');
  return `${hours}:${minutes}:${seconds}`;
}

/**
 * 格式化日期
 */
function formatDate(date: Date): string {
  const year = date.getFullYear();
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  const day = date.getDate().toString().padStart(2, '0');
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
  const weekday = weekdays[date.getDay()];
  return `${year}/${month}/${day} ${weekday}`;
}

/**
 * 实时时间卡片组件
 */
interface LiveTimeCardProps {
  title: string;
  timeZone: string;
}

function LiveTimeCard({ title, timeZone }: LiveTimeCardProps) {
  const [time, setTime] = useState('');
  const [date, setDate] = useState('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const localTime = new Date(now.toLocaleString('en-US', { timeZone }));
      setTime(formatTime(localTime));
      setDate(formatDate(localTime));
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, [timeZone]);

  return (
    <div className="card p-4 text-center">
      <div className="mb-2 text-sm text-text-muted">{title}</div>
      <div className="text-2xl font-bold">{time}</div>
      <div className="text-sm text-text-muted">{date}</div>
    </div>
  );
}

/**
 * 工具箱功能模块
 */
export function ToolsFeature() {
  const { currentTool, tasks, addTask, updateTask, deleteTask, toggleTask, setCurrentTool } =
    useToolsStore();

  const { isLoading: tasksLoading } = useLoadTasks();
  const saveTasksMutation = useSaveTasks();
  const translateMutation = useTranslateText();
  const emailReplyMutation = useGenerateEmailReply();
  const timezoneMutation = useConvertTimezone();

  // 文本翻译状态
  const [transSource, setTransSource] = useState('');
  const [transTarget, setTransTarget] = useState('');
  const [transSourceLang, setTransSourceLang] = useState('auto');
  const [transTargetLang, setTransTargetLang] = useState('zh');

  // 邮件回复状态
  const [emailSender, setEmailSender] = useState('');
  const [emailSubject, setEmailSubject] = useState('');
  const [emailContent, setEmailContent] = useState('');
  const [emailStyle, setEmailStyle] = useState<EmailStyle>(EmailStyle.PROFESSIONAL);
  const [emailReplies, setEmailReplies] = useState<Array<{ type: string; content: string }>>([]);
  const [selectedReplyIndex, setSelectedReplyIndex] = useState(0);

  // 时区转换状态
  const [timezoneInput, setTimezoneInput] = useState('');
  const [timezoneResult, setTimezoneResult] = useState<TimezoneConvertResult | null>(null);

  // 渲染任务管理工具
  const renderTasksTool = () => (
    <div className="space-y-4">
      {tasksLoading && (
        <div className="text-sm text-text-muted">正在加载任务...</div>
      )}
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">✅ 任务列表</h3>
        <Button size="sm" onClick={() => addTask({ id: Date.now().toString(), text: '新任务', completed: false })} title="添加任务">
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      <div className="space-y-2">
        {tasks.map(task => (
          <div key={task.id} className={`card p-4 flex items-center gap-3 ${task.completed ? 'opacity-60' : ''}`}>
            <input
              type="checkbox"
              checked={task.completed}
              onChange={() => toggleTask(task.id)}
              className="h-5 w-5"
            />
            <span
              className={`flex-1 ${task.completed ? 'line-through text-text-muted' : ''}`}
              contentEditable
              suppressContentEditableWarning
              onBlur={(e) => updateTask(task.id, { text: e.currentTarget.textContent || '' })}
            >
              {task.text}
            </span>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => deleteTask(task.id)}
            >
              <Trash2 className="h-5 w-5" />
            </Button>
          </div>
        ))}
      </div>

      {tasks.length > 0 && (
        <Button
          variant="secondary"
          className="w-full"
          onClick={async () => {
            await saveTasksMutation.mutateAsync(tasks);
          }}
          isLoading={saveTasksMutation.isPending}
        >
          保存任务
        </Button>
      )}
    </div>
  );

  // 渲染文本翻译工具
  const renderTranslatorTool = () => (
    <div className="grid grid-cols-3 gap-4">
      {/* 源文本 */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-base font-semibold">原文</label>
          <select
            value={transSourceLang}
            onChange={(e) => setTransSourceLang(e.target.value)}
            className="rounded-md border border-border px-3 py-1.5 text-base focus:outline-none focus:ring-1 focus:ring-primary-500"
          >
            <option value="auto">自动检测</option>
            <option value="en">英语</option>
            <option value="zh">中文</option>
          </select>
        </div>
        <Textarea
          value={transSource}
          onChange={(e) => setTransSource(e.target.value)}
          placeholder="输入要翻译的文本..."
          className="min-h-[150px]"
          showCharCount={false}
        />
      </div>

      {/* 操作 */}
      <div className="flex flex-col items-center justify-center gap-4">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => {
            const tempLang = transSourceLang;
            setTransSourceLang(transTargetLang === 'auto' ? 'en' : transTargetLang);
            setTransTargetLang(tempLang === 'auto' ? 'zh' : tempLang);
            const tempText = transSource;
            setTransSource(transTarget);
            setTransTarget(tempText);
          }}
          title="交换语言"
        >
          <ArrowRightLeft className="h-5 w-5" />
        </Button>
        <Button
          variant="primary"
          onClick={async () => {
            if (!transSource.trim()) return;
            const result = await translateMutation.mutateAsync({
              text: transSource,
              source_lang: transSourceLang,
              target_lang: transTargetLang,
            });
            setTransTarget(result.translation);
          }}
          isLoading={translateMutation.isPending}
          disabled={!transSource.trim()}
          className="whitespace-nowrap"
        >
          <RotateCw className="h-5 w-5" />
          翻译
        </Button>
      </div>

      {/* 译文 */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-base font-semibold">译文</label>
          <select
            value={transTargetLang}
            onChange={(e) => setTransTargetLang(e.target.value)}
            className="rounded-md border border-border px-3 py-1.5 text-base focus:outline-none focus:ring-1 focus:ring-primary-500"
          >
            <option value="zh">中文</option>
            <option value="en">英语</option>
          </select>
        </div>
        <Textarea
          value={transTarget}
          readOnly
          placeholder="翻译结果..."
          className="min-h-[150px]"
          showCharCount={false}
        />
        <Button
          variant="secondary"
          className="w-full"
          onClick={async () => {
            if (transTarget) await copyToClipboard(transTarget);
          }}
          disabled={!transTarget}
        >
          复制译文
        </Button>
      </div>
    </div>
  );

  // 渲染邮件回复工具
  const renderEmailTool = () => (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <Input
          label="发件人（可选）"
          placeholder="例如: John Smith"
          value={emailSender}
          onChange={(e) => setEmailSender(e.target.value)}
        />
        <div>
          <label className="mb-1.5 block text-sm font-medium text-text-primary">回复风格</label>
          <select
            value={emailStyle}
            onChange={(e) => setEmailStyle(e.target.value as EmailStyle)}
            className="w-full rounded-md border border-border px-3 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="professional">专业正式</option>
            <option value="polite">礼貌客气</option>
            <option value="casual">轻松随意</option>
          </select>
        </div>
      </div>

      <Input
        label="邮件主题（可选）"
        placeholder="邮件主题..."
        value={emailSubject}
        onChange={(e) => setEmailSubject(e.target.value)}
      />

      <Textarea
        label="邮件内容"
        value={emailContent}
        onChange={(e) => setEmailContent(e.target.value)}
        placeholder="粘贴收到的邮件内容..."
        className="min-h-[150px]"
        showCharCount={false}
      />

      <div className="flex gap-2">
        <Button
          variant="secondary"
          onClick={() => {
            setEmailSender('');
            setEmailSubject('');
            setEmailContent('');
            setEmailReplies([]);
          }}
        >
          清空
        </Button>
        <Button
          variant="primary"
          onClick={async () => {
            if (!emailContent.trim()) return;
            const result = await emailReplyMutation.mutateAsync({
              sender: emailSender,
              subject: emailSubject,
              content: emailContent,
              style: emailStyle,
            });
            setEmailReplies(result.replies);
          }}
          isLoading={emailReplyMutation.isPending}
          disabled={!emailContent.trim()}
          className="whitespace-nowrap"
        >
          <Send className="h-5 w-5" />
          生成回复
        </Button>
      </div>

      {/* 回复建议 */}
      {emailReplies.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-lg font-semibold">✨ 回复建议</h4>
          <div className="space-y-2">
            {emailReplies.map((reply, index) => (
              <div
                key={index}
                onClick={() => setSelectedReplyIndex(index)}
                className={`card p-4 cursor-pointer transition-all ${
                  selectedReplyIndex === index ? 'border-primary-500 bg-primary-50' : ''
                }`}
              >
                <div className="mb-2 text-sm font-medium text-text-muted">{reply.type}</div>
                <div className="text-base">{reply.content}</div>
              </div>
            ))}
          </div>
          <Button
            variant="secondary"
            onClick={async () => {
              if (emailReplies[selectedReplyIndex]) {
                await copyToClipboard(emailReplies[selectedReplyIndex].content);
              }
            }}
          >
            复制选中回复
          </Button>
        </div>
      )}
    </div>
  );

  // 处理时区转换
  const handleTimezoneConvert = useCallback(async () => {
    if (!timezoneInput.trim()) return;
    const result = await timezoneMutation.mutateAsync({
      input: timezoneInput,
      source_timezone: 'auto',
    });
    setTimezoneResult(result);
  }, [timezoneInput, timezoneMutation]);

  // 渲染时区转换工具
  const renderTimezoneTool = () => (
    <div className="space-y-6">
      {/* 实时时间显示 */}
      <div className="grid grid-cols-2 gap-4">
        <LiveTimeCard title="📍 北京时间" timeZone="Asia/Shanghai" />
        <LiveTimeCard title="🇺🇸 美中时间" timeZone="America/Chicago" />
      </div>

      {/* 时间转换输入 */}
      <div>
        <label className="mb-2 block text-sm font-medium text-text-primary">
          📅 输入时间
        </label>
        <Input
          placeholder="例如: 今天下午3点、明天上午9:30、1/26/26 4pm cdt、1/15/26 2:00 pm、2024-01-15 14:00"
          value={timezoneInput}
          onChange={(e) => setTimezoneInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              handleTimezoneConvert();
            }
          }}
        />
        <p className="mt-1 text-sm text-text-muted">
          支持格式: 今天下午3点、1/26/26 4pm、M/D/YY h:mm am/pm、YYYY-MM-DD HH:mm，默认时区: CDT
        </p>
      </div>

      <Button
        variant="primary"
        onClick={handleTimezoneConvert}
        isLoading={timezoneMutation.isPending}
        disabled={!timezoneInput.trim()}
        className="w-full"
      >
        <RotateCw className="h-4 w-4" />
        🔄 转换
      </Button>

      {/* 转换结果 */}
      {timezoneResult && (
        <div className="space-y-3">
          <h4 className="text-lg font-semibold">📍 转换结果</h4>
          <div className="grid grid-cols-2 gap-3">
            <div className="card p-3">
              <div className="text-sm text-text-muted">美东时间</div>
              <div className="text-base font-semibold">{timezoneResult.est || '--'}</div>
            </div>
            <div className="card p-3">
              <div className="text-sm text-text-muted">美中时间</div>
              <div className="text-base font-semibold">{timezoneResult.cst || '--'}</div>
            </div>
            <div className="card p-3">
              <div className="text-sm text-text-muted">美山时间</div>
              <div className="text-base font-semibold">{timezoneResult.mst || '--'}</div>
            </div>
            <div className="card p-3">
              <div className="text-sm text-text-muted">美西时间</div>
              <div className="text-base font-semibold">{timezoneResult.pst || '--'}</div>
            </div>
            <div className="card p-3 col-span-2 bg-primary-50 border-primary-200">
              <div className="text-xs text-primary-600">北京时间</div>
              <div className="text-lg font-semibold text-primary-700">{timezoneResult.beijing || '--'}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <div className="flex h-full overflow-auto">
      <div className="mx-auto w-full max-w-4xl p-6">
        {/* 标题 */}
        <div className="mb-6">
          <h2 className="text-2xl font-bold">🧰 工具箱</h2>
        </div>

        {/* 工具选项卡 */}
        <TabsWithPanel
          tabs={toolTabs}
          activeTab={currentTool}
          onChange={(tab) => setCurrentTool(tab as ToolTab)}
          variant="pills"
          renderPanel={(tabId) => {
            switch (tabId) {
              case 'tasks':
                return renderTasksTool();
              case 'translator':
                return renderTranslatorTool();
              case 'email':
                return renderEmailTool();
              case 'timezone':
                return renderTimezoneTool();
              default:
                return null;
            }
          }}
        />
      </div>
    </div>
  );
}
