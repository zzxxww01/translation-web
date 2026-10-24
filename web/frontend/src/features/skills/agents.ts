import type { Agent } from './types';

/** 直接和 Claude 聊天。服务端目录里没有这一条时（旧版服务端）用它兜底。 */
export const CHAT_AGENT: Agent = {
  name: '',
  title: 'Claude',
  icon: 'chat',
  description: '什么都能聊，也能在服务器上动手干活',
  hint: '想问什么、要做什么都可以，也可以附文件或贴链接',
  examples: [],
  available: true,
};

function fill(item: Partial<Agent>): Agent {
  const name = item.name ?? '';
  if (!name) return { ...CHAT_AGENT, ...item, name, title: item.title || CHAT_AGENT.title, icon: item.icon || CHAT_AGENT.icon };
  return {
    name,
    title: item.title || name,
    icon: item.icon || 'skill',
    description: item.description ?? '',
    hint: item.hint ?? '',
    examples: item.examples ?? [],
    available: item.available ?? true,
  };
}

/** 补齐缺的字段，并保证 Claude 聊天排第一、后面是各专职 agent */
export function normalizeCatalog(raw: Partial<Agent>[] | undefined): Agent[] {
  const agents = (raw ?? []).map(fill);
  const chat = agents.find(agent => !agent.name) ?? CHAT_AGENT;
  return [chat, ...agents.filter(agent => agent.name)];
}

/** 任务所属的 agent。skill 后来从目录里去掉了，也给一个能显示的名字。 */
export function findAgent(catalog: Agent[], skill: string): Agent {
  return catalog.find(agent => agent.name === skill) ?? fill({ name: skill });
}
