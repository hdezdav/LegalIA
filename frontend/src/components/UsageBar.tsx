import { useMemo, useState, useEffect } from 'react';
import { api } from '../api';
import { AVAILABLE_MODELS } from '../constants';
import './UsageBar.css';

interface UsageBarProps {
  totalPromptTokens: number;
  totalCompletionTokens: number;
  lastLatencyMs?: number;
  activeModelId: string;
}

export function UsageBar({
  totalPromptTokens,
  totalCompletionTokens,
  lastLatencyMs,
  activeModelId,
}: UsageBarProps) {
  const [liveModels, setLiveModels] = useState<any[]>([]);

  useEffect(() => {
    let isMounted = true;
    api.getModels().then((data) => {
      if (isMounted && data && data.length > 0) {
        setLiveModels(data);
      }
    }).catch(() => {});
    return () => {
      isMounted = false;
    };
  }, []);

  const liveModel = liveModels.find((m) => m.id === activeModelId);
  const staticModel = AVAILABLE_MODELS.find((m) => m.id === activeModelId) || AVAILABLE_MODELS[0];

  const modelName = liveModel?.name || staticModel.name;
  const contextLabel = liveModel?.context_limit_label || staticModel.contextLimit;

  const totalTokens = totalPromptTokens + totalCompletionTokens;

  // Max tokens for bar scale
  const maxTokens = useMemo(() => {
    if (liveModel?.context_limit) return liveModel.context_limit;
    if (contextLabel.includes('1M')) return 1000000;
    if (contextLabel.includes('128k')) return 128000;
    return 200000;
  }, [liveModel, contextLabel]);

  const percentage = Math.min(100, Math.max(0.2, (totalTokens / maxTokens) * 100));

  const formatNumber = (n: number) => {
    return new Intl.NumberFormat('es-CO').format(n);
  };

  const remainingTokens = Math.max(0, maxTokens - totalTokens);

  return (
    <div className="usage-bar-container" title="Telemetría de tokens y capacidad total de contexto">
      <div className="usage-bar-meta-row">
        <div className="usage-left-info">
          <span className="usage-active-model">{modelName}</span>
          <span className="usage-divider">•</span>
          <span className="usage-token-count">
            <strong>{formatNumber(totalTokens)}</strong> / {contextLabel}
          </span>
          <span className="usage-pct-tag">({percentage < 0.1 ? '<0.1' : percentage.toFixed(1)}%)</span>
        </div>

        <div className="usage-right-info">
          {lastLatencyMs !== undefined && lastLatencyMs > 0 && (
            <span className="usage-latency-tag">⚡ {lastLatencyMs}ms</span>
          )}
          <span className="usage-savings-tag" title={`Capacidad disponible: ${formatNumber(remainingTokens)} tokens`}>
            Disponibles: {formatNumber(remainingTokens)}
          </span>
        </div>
      </div>

      {/* Progress Track */}
      <div className="usage-progress-track">
        <div
          className="usage-progress-fill"
          style={{
            width: `${percentage}%`,
            backgroundColor: percentage > 85 ? '#ef4444' : percentage > 60 ? '#f59e0b' : '#10b981',
          }}
        />
      </div>
    </div>
  );
}

