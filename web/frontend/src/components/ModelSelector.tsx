import React, { useEffect, useState } from 'react';
import { Cpu } from 'lucide-react';
import { modelsApi } from '../shared/api/models';
import type { ProviderInfo } from '../shared/types';
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
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
        {providers.map((provider) => (
          <SelectGroup key={provider.id}>
            <SelectLabel>{provider.name}</SelectLabel>
            {provider.models.map((model) => (
              <SelectItem
                key={model.alias}
                value={model.alias}
                disabled={!model.available}
              >
                <div className="flex flex-col">
                  <span className="font-medium">{model.name}</span>
                  <span className="text-xs text-text-muted">
                    {model.description}
                    {model.supports_thinking && ' • 支持思考'}
                    {!model.available && ' • 不可用'}
                  </span>
                </div>
              </SelectItem>
            ))}
          </SelectGroup>
        ))}
      </SelectContent>
    </Select>
  );
};
