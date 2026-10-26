import type { Agent } from './types';

/** 通用 Agent：直接对话、不派发 skill。服务端目录里没有这一条时（旧版服务端）用它兜底。 */
export const CHAT_AGENT: Agent = {
  name: '',
  title: '通用 Agent',
  icon: 'general',
  description: '什么都能问，也能在服务器上动手干活',
  hint: '想问什么、要做什么直接说，也可以附文件或贴链接',
  examples: [],
  harness: 'claude',
  available: true,
};

function fill(item: Partial<Agent>): Agent {
  const name = item.name ?? '';
  const harness = item.harness === 'codex' || item.harness === 'antigravity' ? item.harness : 'claude';
  if (!name) return { ...CHAT_AGENT, ...item, name, harness, title: item.title || CHAT_AGENT.title, icon: item.icon || CHAT_AGENT.icon };
  return {
    name,
    title: item.title || name,
    icon: item.icon || 'skill',
    description: item.description ?? '',
    hint: item.hint ?? '',
    examples: item.examples ?? [],
    harness,
    available: item.available ?? true,
  };
}

/** 补齐缺的字段，并保证通用 Agent 排第一、后面是各专职 Agent */
export function normalizeCatalog(raw: Partial<Agent>[] | undefined): Agent[] {
  const agents = (raw ?? []).map(fill);
  const chat = agents.find(agent => !agent.name) ?? CHAT_AGENT;
  return [chat, ...agents.filter(agent => agent.name)];
}

/** 对话所属的 Agent。skill 后来从目录里去掉了，也给一个能显示的名字。 */
export function findAgent(catalog: Agent[], skill: string): Agent {
  return catalog.find(agent => agent.name === skill) ?? fill({ name: skill });
}
