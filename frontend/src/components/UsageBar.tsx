import { useState, useEffect } from 'react';
import { api } from '../api';
import { AVAILABLE_MODELS } from '../constants';
import { TokenQuota } from '../types';
import './UsageBar.css';

interface UsageBarProps {
  totalPromptTokens: number;
  totalCompletionTokens: number;
  lastLatencyMs?: number;
  activeModelId: string;
  quota?: TokenQuota | null;
}

export function UsageBar({
  totalPromptTokens,
  totalCompletionTokens,
  lastLatencyMs,
  activeModelId,
  quota: propQuota,
}: UsageBarProps) {
  const [liveModels, setLiveModels] = useState<any[]>([]);
  const [localQuota, setLocalQuota] = useState<TokenQuota | null>(null);

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

  useEffect(() => {
    if (!propQuota) {
      let isMounted = true;
      api.getQuota().then((q) => {
        if (isMounted) setLocalQuota(q);
      }).catch(() => {});
      return () => {
        isMounted = false;
      };
    }
  }, [propQuota]);

  const quota = propQuota || localQuota;
  const liveModel = liveModels.find((m) => m.id === activeModelId);
  const staticModel = AVAILABLE_MODELS.find((m) => m.id === activeModelId) || AVAILABLE_MODELS[0];
  const modelName = liveModel?.name || staticModel.name;

  const totalChatTokens = totalPromptTokens + totalCompletionTokens;

  const formatNumber = (n: number) => {
    return new Intl.NumberFormat('es-CO').format(n);
  };

  const remainingPercent = quota ? quota.remaining_percent : 100;
  const remainingMillions = quota ? quota.remaining_millions : 15;
  const totalMillions = quota ? quota.total_millions : 15;
  const requestsRemaining = quota?.requests_remaining;

  return (
    <div className="usage-bar-container" title="Bolsa global de tokens IA en tiempo real">
      <div className="usage-bar-meta-row">
        <div className="usage-left-info">
          <span className="usage-active-model">{modelName}</span>
          <span className="usage-divider">•</span>
          <span className="usage-token-count">
            <strong>{remainingMillions}M</strong> / {totalMillions}M tokens disponibles
          </span>
          <span className="usage-pct-tag">({remainingPercent}% libre)</span>
        </div>

        <div className="usage-right-info">
          {totalChatTokens > 0 && (
            <span className="usage-chat-tokens-tag" title="Tokens acumulados en esta conversación">
              Chat: {formatNumber(totalChatTokens)} tokens
            </span>
          )}
          {lastLatencyMs !== undefined && lastLatencyMs > 0 && (
            <span className="usage-latency-tag">⚡ {lastLatencyMs}ms</span>
          )}
          {requestsRemaining !== undefined && requestsRemaining > 0 && (
            <span className="usage-savings-tag" title={`Peticiones estimadas restantes: ${requestsRemaining}`}>
              {requestsRemaining} peticiones rest.
            </span>
          )}
        </div>
      </div>

      {/* Unified Global Quota Progress Track */}
      <div className="usage-progress-track">
        <div
          className="usage-progress-fill"
          style={{
            width: `${Math.min(100, Math.max(0, remainingPercent))}%`,
            backgroundColor: remainingPercent < 15 ? '#ef4444' : remainingPercent < 35 ? '#f59e0b' : '#10b981',
          }}
        />
      </div>
    </div>
  );
}
