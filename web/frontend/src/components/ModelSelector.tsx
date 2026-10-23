import React, { useEffect, useState } from 'react';
import { Cpu } from 'lucide-react';
import { modelsApi } from '../shared/api/models';
import type { ProviderInfo } from '../shared/types';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface ModelSelectorProps {
  value?: string;
  onChange: (model: string) => void;
  className?: string;
  disabled?: boolean;
}

export const ModelSelector: React.FC<ModelSelectorProps> = ({
  value,
  onChange,
  className = '',
  disabled = false,
}) => {
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        setLoading(true);
        const response = await modelsApi.getModels();
        setProviders(response.providers);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch models:', err);
        setError('Failed to load models');
      } finally {
        setLoading(false);
      }
    };

    fetchModels();
  }, []);

  if (loading) {
    return (
      <Select disabled>
        <SelectTrigger className={className}>
          <SelectValue placeholder="加载模型中..." />
        </SelectTrigger>
      </Select>
    );
  }

  if (error) {
    return (
      <Select disabled>
        <SelectTrigger className={className}>
          <SelectValue placeholder="加载失败" />
        </SelectTrigger>
      </Select>
    );
  }

  // 只列模型名，不分来源分组；多个别名指向同一个真实模型时只显示第一个。
  // 当前选中的若是被折叠的别名，仍保留它，否则选择框会显示成空白。
  const seenModels = new Set<string>();
  const models = providers.flatMap(provider => provider.models).filter(model => {
    const key = model.real_model || model.alias;
    if (seenModels.has(key) && model.alias !== value) return false;
    seenModels.add(key);
    return true;
  });

  return (
    <Select value={value || 'default'} onValueChange={(val) => onChange(val === 'default' ? '' : val)} disabled={disabled}>
      <SelectTrigger className={className}>
        <div className="flex items-center gap-2">
          <Cpu className="h-3.5 w-3.5 text-text-muted" />
          <SelectValue placeholder="默认模型" />
        </div>
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="default">默认模型</SelectItem>
        {models.map((model) => (
          <SelectItem key={model.alias} value={model.alias} disabled={!model.available}>
            {model.name}
            {!model.available && <span className="text-text-muted"> · 不可用</span>}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
};
