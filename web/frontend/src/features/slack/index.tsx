import { useState, useCallback, useRef } from 'react';
import { Send, User, MessageCircle, Plus, Edit3, Pin, Trash2 } from 'lucide-react';
import { useSlackStore } from '../../shared/stores';
import { useConversations } from './hooks';
import { slackApi } from './api';
import { Button } from '../../components/ui';
import { Textarea } from '../../components/ui';
import { Input } from '../../components/ui';
import { Modal } from '../../components/ui';
import { useToast } from '../../components/ui';
import { ChatBubble } from './components/ChatBubble';
import { NewConversationModal } from './components/NewConversationModal';
import { ContextMenu } from './components/ContextMenu';
import { detectLanguage, generateId } from '../../shared/utils';
import { MessageRole, ConversationStyle } from '../../shared/constants';

// 预设模板 IDs
const TEMPLATE_IDS = ['__template_michelle__', '__template_public_channel__', '__template_quick__'];

/**
 * Slack 回复功能模块
 */
export function SlackFeature() {
  const {
    currentConversation,
    conversations,
    messages,
    setCurrentConversation,
    setConversations,
    addMessage,
  } = useSlackStore();

  const { showSuccess } = useToast();
  const [isNewConvModalOpen, setIsNewConvModalOpen] = useState(false);
  const [inputThem, setInputThem] = useState('');
  const [inputMe, setInputMe] = useState('');
  const themInputRef = useRef<HTMLTextAreaElement>(null);
  const meInputRef = useRef<HTMLTextAreaElement>(null);

  // 右键菜单状态
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; convId: string } | null>(null);
  
  // 重命名弹窗状态
  const [renameModal, setRenameModal] = useState<{ convId: string; name: string } | null>(null);

  useConversations();

  // 分离模板和历史对话
  const templates = conversations.filter(c => TEMPLATE_IDS.includes(c.id));
  const historyConversations = conversations.filter(c => !TEMPLATE_IDS.includes(c.id));

  // 点击模板 -> 创建新对话
  const handleClickTemplate = async (templateId: string) => {
    const template = conversations.find(c => c.id === templateId);
    if (!template) return;

    // 生成新对话 ID 和名称
    const newId = generateId('conv');
    const timestamp = new Date().toLocaleString('zh-CN', { 
      month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' 
    });
    const baseName = template.name.replace(' (Guide/上司)', '').replace('Slack ', '');
    const newName = `${baseName} - (${timestamp})`;

    try {
      const newConv = await slackApi.createConversation({
        id: newId,
        name: newName,
        style: ConversationStyle.CASUAL,
        system_prompt: template.system_prompt,
      });
      
      // 切换到新对话并刷新列表
      setCurrentConversation({ ...newConv, history: [] });
      const updatedList = await slackApi.getConversations();
      setConversations(updatedList);
    } catch (e) {
      console.error('创建对话失败:', e);
    }
  };

  // 选择历史对话 -> 加载完整历史
  const handleSelectConversation = useCallback(async (convId: string) => {
    try {
      const fullConv = await slackApi.getConversation(convId);
      setCurrentConversation(fullConv);
    } catch (_error) {
      const conv = conversations.find(c => c.id === convId);
      if (conv) setCurrentConversation(conv);
    }
  }, [conversations, setCurrentConversation]);

  // 右键菜单
  const handleContextMenu = (e: React.MouseEvent, convId: string) => {
    e.preventDefault();
    setContextMenu({ x: e.clientX, y: e.clientY, convId });
  };

  // 重命名对话
  const handleRename = async () => {
    if (!renameModal) return;
    try {
      await slackApi.updateConversation(renameModal.convId, { name: renameModal.name });
      const updatedList = await slackApi.getConversations();
      setConversations(updatedList);
      showSuccess('已重命名');
    } catch (e) {
      console.error('重命名失败:', e);
    }
    setRenameModal(null);
  };

  // 置顶/取消置顶
  const handleTogglePin = async (convId: string) => {
    const conv = conversations.find(c => c.id === convId);
    if (!conv) return;
    try {
      await slackApi.updateConversation(convId, { is_pinned: !conv.is_pinned });
      const updatedList = await slackApi.getConversations();
      setConversations(updatedList);
    } catch (e) {
      console.error('置顶操作失败:', e);
    }
  };

  // 删除对话
  const handleDelete = async (convId: string) => {
    if (!confirm('确定删除此对话？')) return;
    try {
      await slackApi.deleteConversation(convId);
      const updatedList = await slackApi.getConversations();
      setConversations(updatedList);
      if (currentConversation?.id === convId) {
        setCurrentConversation(null);
      }
      showSuccess('已删除');
    } catch (e) {
      console.error('删除对话失败:', e);
    }
  };

  // 发送对方消息
  const handleSendThem = async () => {
    const content = inputThem.trim();
    if (!content || !currentConversation) return;

    setInputThem('');
    if (themInputRef.current) themInputRef.current.style.height = 'auto';

    addMessage({ role: MessageRole.THEM, content_en: content });

    // 如果是新对话且第一条消息，自动重命名
    if (messages.length === 0 && currentConversation.name.includes(' - (')) {
      const namePreview = content.substring(0, 15) + (content.length > 15 ? '...' : '');
      const newName = currentConversation.name.replace(' - (', ` - ${namePreview} (`);
      try {
        await slackApi.updateConversation(currentConversation.id, { name: newName });
        setCurrentConversation({ ...currentConversation, name: newName });
        const updatedList = await slackApi.getConversations();
        setConversations(updatedList);
      } catch (e) {
        console.error('更新对话名称失败:', e);
      }
    }

    // 同步到后端
    try {
      await slackApi.addMessage(currentConversation.id, {
        role: MessageRole.THEM,
        content_en: content,
      });
    } catch (e) {
      console.error('添加消息失败:', e);
    }
  };

  // 发送我的消息
  const handleSendMe = async () => {
    const content = inputMe.trim();
    if (!content || !currentConversation) return;

    setInputMe('');
    if (meInputRef.current) meInputRef.current.style.height = 'auto';

    const isChinese = detectLanguage(content) === 'zh';
    addMessage({
      role: MessageRole.ME,
      content_en: isChinese ? '' : content,
      content_cn: isChinese ? content : '',
    });

    try {
      await slackApi.addMessage(currentConversation.id, {
        role: MessageRole.ME,
        content_en: isChinese ? '' : content,
        content_cn: isChinese ? content : '',
      });
    } catch (e) {
      console.error('添加消息失败:', e);
    }
  };

  // 自动调整文本框高度
  const autoResize = (el: HTMLTextAreaElement) => {
    el.style.height = 'auto';
    el.style.height = Math.min(Math.max(el.scrollHeight, 48), 150) + 'px';
  };

  return (
    <div className="flex h-full overflow-auto">
      {/* 侧边栏 */}
      <aside className="w-60 border-r border-border-subtle bg-bg-secondary flex flex-col">
        {/* 开始新对话区 */}
        <div className="p-3 border-b border-border-subtle">
          <div className="text-sm font-semibold text-text-secondary mb-2.5">开始新对话</div>
          <div className="space-y-1">
            {templates.map(t => (
              <button
                key={t.id}
                onClick={() => handleClickTemplate(t.id)}
                className="w-full rounded-lg px-4 py-2.5 text-left text-base hover:bg-bg-tertiary transition-colors flex items-center gap-2"
              >
                <span>📌</span>
                <span className="truncate">{t.name}</span>
              </button>
            ))}
            <button
              onClick={() => setIsNewConvModalOpen(true)}
              className="w-full rounded-lg px-4 py-2.5 text-left text-base hover:bg-bg-tertiary transition-colors flex items-center gap-2 text-primary-600"
            >
              <Plus className="h-5 w-5" />
              <span>新增联系人</span>
            </button>
          </div>
        </div>

        {/* 历史对话区 */}
        <div className="flex-1 overflow-y-auto p-3">
          <div className="text-sm font-semibold text-text-secondary mb-2.5">历史对话</div>
          {historyConversations.length === 0 ? (
            <div className="text-center text-text-muted text-sm py-6">暂无历史</div>
          ) : (
            <div className="space-y-1">
              {historyConversations.map(conv => (
                <button
                  key={conv.id}
                  onClick={() => handleSelectConversation(conv.id)}
                  onContextMenu={(e) => handleContextMenu(e, conv.id)}
                  className={`w-full rounded-md px-3 py-2 text-left text-sm transition-colors ${
                    currentConversation?.id === conv.id
                      ? 'bg-primary-50 text-primary-700'
                      : 'hover:bg-bg-tertiary'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {conv.is_pinned && <span className="text-xs">📌</span>}
                    <User className="h-5 w-5 flex-shrink-0" />
                    <span className="truncate">{conv.name}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </aside>

      {/* 主内容区 */}
      <main className="flex-1 flex flex-col">
        {/* 对话标题 */}
        <div className="border-b border-border-subtle px-6 py-4">
          <h3 className="text-lg font-semibold">
            {currentConversation?.name || '💬 Slack 回复助手'}
          </h3>
        </div>

        {/* 消息列表 */}
        <div className="flex-1 overflow-y-auto p-6">
          {!currentConversation ? (
            <div className="flex h-full items-center justify-center text-center">
              <div className="text-text-muted">
                <MessageCircle className="mx-auto mb-4 h-12 w-12 opacity-50" />
                <p>选择或创建对话开始</p>
              </div>
            </div>
          ) : messages.length === 0 ? (
            <div className="flex h-full items-center justify-center text-center">
              <div className="text-text-muted">
                <MessageCircle className="mx-auto mb-4 h-12 w-12 opacity-50" />
                <p>暂无消息</p>
                <p className="mt-2 text-sm">在下方输入开始对话</p>
              </div>
            </div>
          ) : (
            <div className="mx-auto max-w-3xl space-y-4">
              {messages.map((msg, index) => (
                <div key={index} className={`flex ${msg.role === 'me' ? 'justify-end' : 'justify-start'}`}>
                  <ChatBubble message={msg} index={index} conversationId={currentConversation?.id || ''} />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 输入区 */}
        {currentConversation && (
          <div className="border-t border-border-subtle bg-bg-secondary p-4">
            <div className="mx-auto max-w-3xl grid grid-cols-2 gap-4">
              {/* 对方输入 */}
              <div>
                <label className="mb-2 flex items-center gap-2 text-base font-medium text-text-primary">
                  <User className="h-5 w-5 text-text-muted" />
                  对方消息
                </label>
                <Textarea
                  ref={themInputRef}
                  value={inputThem}
                  onChange={(e) => { setInputThem(e.target.value); if (themInputRef.current) autoResize(themInputRef.current); }}
                  placeholder="对方发来的消息..."
                  className="min-h-[100px] max-h-[180px]"
                  showCharCount={false}
                />
                <Button size="md" variant="secondary" onClick={handleSendThem} disabled={!inputThem.trim()} className="mt-3 w-full">
                  发送对方消息
                </Button>
              </div>

              {/* 我的输入 */}
              <div>
                <label className="mb-2 flex items-center gap-2 text-base font-medium text-text-primary">
                  <Send className="h-5 w-5 text-text-muted" />
                  我的回复
                </label>
                <Textarea
                  ref={meInputRef}
                  value={inputMe}
                  onChange={(e) => { setInputMe(e.target.value); if (meInputRef.current) autoResize(meInputRef.current); }}
                  placeholder="记录我发送的内容..."
                  className="min-h-[80px] max-h-[150px]"
                  showCharCount={false}
                />
                <Button size="md" variant="primary" onClick={handleSendMe} disabled={!inputMe.trim()} className="mt-3 w-full">
                  发送我的消息
                </Button>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* 右键菜单 */}
      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          onClose={() => setContextMenu(null)}
          items={[
            {
              label: '重命名',
              icon: <Edit3 className="h-4 w-4" />,
              onClick: () => {
                const conv = conversations.find(c => c.id === contextMenu.convId);
                if (conv) setRenameModal({ convId: conv.id, name: conv.name });
              },
            },
            {
              label: conversations.find(c => c.id === contextMenu.convId)?.is_pinned ? '取消置顶' : '置顶',
              icon: <Pin className="h-4 w-4" />,
              onClick: () => handleTogglePin(contextMenu.convId),
            },
            {
              label: '删除',
              icon: <Trash2 className="h-4 w-4" />,
              onClick: () => handleDelete(contextMenu.convId),
              danger: true,
            },
          ]}
        />
      )}

      {/* 重命名弹窗 */}
      <Modal isOpen={!!renameModal} onClose={() => setRenameModal(null)} title="重命名对话" size="sm">
        <div className="space-y-4">
          <Input
            label="对话名称"
            value={renameModal?.name || ''}
            onChange={(e) => renameModal && setRenameModal({ ...renameModal, name: e.target.value })}
            autoFocus
          />
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setRenameModal(null)}>取消</Button>
            <Button variant="primary" onClick={handleRename}>保存</Button>
          </div>
        </div>
      </Modal>

      {/* 新增联系人弹窗 */}
      <NewConversationModal isOpen={isNewConvModalOpen} onClose={() => setIsNewConvModalOpen(false)} />
    </div>
  );
}
