/**
 * 欢迎页面组件
 * 显示在未选择项目时
 */

import {
  ArrowRight,
  BookOpenCheck,
  FileText,
  FolderOpen,
  Languages,
  Layers3,
  Plus,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';

interface WelcomeScreenProps {
  onNewProject?: () => void;
  onOpenProjects?: () => void;
}

const highlights = [
  { label: '输入', value: 'Markdown' },
  { label: '流程', value: '4 步确认' },
  { label: '粒度', value: '段落级' },
];

const featureCards = [
  {
    icon: Languages,
    eyebrow: 'Quality',
    title: '精准翻译',
    description: '按段落拆解、翻译、校对和确认，适合长篇技术内容。',
    tone: 'text-slate-950 bg-slate-50 border-slate-200',
  },
  {
    icon: BookOpenCheck,
    eyebrow: 'Terms',
    title: '术语管理',
    description: '项目术语集中维护，译名在全文里保持一致。',
    tone: 'text-slate-950 bg-slate-50 border-slate-200',
  },
  {
    icon: Layers3,
    eyebrow: 'Review',
    title: '高效协作',
    description: '逐段确认、随时编辑，长文进度清晰可控。',
    tone: 'text-slate-950 bg-slate-50 border-slate-200',
  },
];

export function WelcomeScreen({ onNewProject, onOpenProjects }: WelcomeScreenProps) {
  return (
    <div className="min-h-full bg-[#f7f8fa] px-3 py-4 md:bg-transparent md:px-6 md:py-8">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-3 md:gap-4">
        <section className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <div className="grid md:grid-cols-[1fr_0.92fr]">
            <div className="p-5 md:p-8">
              <div className="mb-5 flex items-center justify-between gap-3">
                <div className="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                  Longform Desk
                </div>
                <div className="flex h-10 w-10 items-center justify-center rounded-md bg-slate-950 text-white md:hidden">
                  <FileText className="h-5 w-5" />
                </div>
              </div>

              <h2 className="max-w-xl text-[2.15rem] font-semibold leading-[1.1] tracking-normal text-slate-950 md:text-5xl" style={{ fontFamily: 'var(--font-chinese)' }}>
                长文翻译
              </h2>
              <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600">
                从原文导入到逐段确认，保持上下文、术语和 Markdown 结构稳定。
              </p>

              <div className="mt-6 grid grid-cols-3 gap-px overflow-hidden rounded-lg border border-slate-200 bg-slate-200">
                {highlights.map((item) => (
                  <div key={item.label} className="bg-white px-3 py-3">
                    <div className="text-[11px] font-semibold text-slate-400">
                      {item.label}
                    </div>
                    <div className="mt-1 truncate text-sm font-semibold text-slate-950">
                      {item.value}
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-6 grid grid-cols-1 gap-2 sm:grid-cols-[1fr_auto]">
                <Button onClick={onNewProject} className="h-12 rounded-md">
                  <Plus className="h-4 w-4" />
                  新建项目
                </Button>
                <Button
                  onClick={onOpenProjects}
                  variant="outline"
                  className="h-12 rounded-md border-slate-200 bg-white"
                >
                  <FolderOpen className="h-4 w-4" />
                  选择项目
                </Button>
              </div>
            </div>

            <div className="border-t border-slate-200 bg-slate-50 p-4 text-slate-950 md:border-l md:border-t-0 md:p-6">
              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <div className="mb-4 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm font-semibold">
                    <FileText className="h-4 w-4 text-slate-500" />
                    source.md
                  </div>
                  <span className="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 text-[11px] font-semibold text-emerald-700">
                    Ready
                  </span>
                </div>
                <div className="space-y-3">
                  <div className="h-3 w-3/4 rounded-full bg-slate-800" />
                  <div className="h-3 w-full rounded-full bg-slate-200" />
                  <div className="h-3 w-5/6 rounded-full bg-slate-200" />
                  <div className="h-16 rounded-md border border-slate-200 bg-slate-50 p-3">
                    <div className="mb-2 h-2.5 w-24 rounded-full bg-slate-400" />
                    <div className="h-2.5 w-4/5 rounded-full bg-slate-200" />
                  </div>
                  <div className="grid grid-cols-[1fr_auto] items-center gap-3 rounded-md border border-slate-200 bg-slate-50 p-3">
                    <div>
                      <div className="h-2.5 w-20 rounded-full bg-slate-500" />
                      <div className="mt-2 h-2.5 w-32 rounded-full bg-slate-200" />
                    </div>
                    <ArrowRight className="h-4 w-4 text-slate-500" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <div className="grid gap-3 md:grid-cols-3">
          {featureCards.map((feature) => {
            const Icon = feature.icon;
            return (
              <article key={feature.title} className="rounded-lg border border-slate-200 bg-white p-4 md:p-5">
                <div className="mb-4 flex items-center justify-between gap-3">
                  <div className={`flex h-10 w-10 items-center justify-center rounded-md border ${feature.tone}`}>
                    <Icon className="h-5 w-5" />
                  </div>
                  <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                    {feature.eyebrow}
                  </span>
                </div>
                <h3 className="text-lg font-semibold text-slate-950">{feature.title}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-600">{feature.description}</p>
              </article>
            );
          })}
        </div>
      </div>
    </div>
  );
}
