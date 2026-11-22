import { BookOpen, Bot, FileText, MessageCircle, MessageSquare, Newspaper, Sparkles, Wrench, type LucideIcon } from 'lucide-react';

export interface NavItem {
  path: string;
  label: string;
  icon: LucideIcon;
  /** 切走再切回来时回到上次看的那个会话 / 对话，不用重新点、重新加载 */
  remember?: boolean;
}

/**
 * 全站功能导航，只有这一份：顶栏导航、手机侧边菜单、文章工作台左上角的功能菜单都用它。
 * 文章库、长文翻译、Claude 精翻合成一个「文章」工作台；长文编辑器从工作台「⋯」进入。
 */
export const NAV_ITEMS: NavItem[] = [
  { path: '/articles', label: '文章', icon: Newspaper },
  { path: '/post', label: '帖子翻译', icon: MessageSquare },
  { path: '/wechat', label: '微信排版', icon: FileText },
  { path: '/slack', label: 'Slack', icon: MessageCircle, remember: true },
  { path: '/glossary', label: '术语库', icon: BookOpen },
  { path: '/tools', label: '工具箱', icon: Wrench },
  { path: '/chat', label: 'Chatbot', icon: Bot },
  { path: '/skills', label: 'Agent', icon: Sparkles, remember: true },
];
