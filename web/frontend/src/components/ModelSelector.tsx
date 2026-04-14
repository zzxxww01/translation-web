import React, { useEffect, useState } from 'react';
import { modelsApi } from '../shared/api/models';
import type { ProviderInfo } from '../shared/types';

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
      <select className={className} disabled>
        <option>Loading models...</option>
      </select>
    );
  }

  if (error) {
    return (
      <select className={className} disabled>
        <option>Error loading models</option>
      </select>
    );
  }

  return (
    <select
      className={className}
      value={value || ''}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
    >
      <option value="">Default model</option>
      {providers.map((provider) => (
        <optgroup key={provider.id} label={provider.name}>
          {provider.models.map((model) => (
            <option
              key={model.alias}
              value={model.alias}
              disabled={!model.available}
            >
              {model.name} - {model.description}
              {model.supports_thinking ? ' [思考]' : ''}
              {!model.available ? ' [不可用]' : ''}
            </option>
          ))}
        </optgroup>
      ))}
    </select>
  );
};
