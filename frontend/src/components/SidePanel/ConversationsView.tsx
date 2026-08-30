import { useState, useEffect } from 'react';
import { Conversation, TokenQuota } from '../../types';
import { SPECIALIZATIONS } from '../../constants';
import { formatTime, truncate } from '../../utils';
import { api } from '../../api';
import { PlusIcon, TrashIcon, SearchIcon } from '../Icons';
import { SpecializationIcon } from '../SpecializationMenu';

interface ConversationsViewProps {
  conversations: Conversation[];
  activeConversationId: string | null;
  quota?: TokenQuota | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onNewChat: () => void;
}

export function ConversationsView({
  conversations,
  activeConversationId,
  quota: propQuota,
  onSelect,
  onDelete,
  onNewChat,
}: ConversationsViewProps) {
  const [search, setSearch] = useState('');
  const [localQuota, setLocalQuota] = useState<TokenQuota>({
    total_tokens: 15000000,
    used_tokens: 1282915,
    remaining_tokens: 13717085,
    remaining_percent: 91.4,
    total_millions: 15.0,
    remaining_millions: 13.72,
    used_millions: 1.28,
    status: 'active',
    days_remaining: 10,
    rpm_limit: 120,
  });

  const quota = propQuota || localQuota;

  useEffect(() => {
    if (propQuota) return;
    let mounted = true;
    const fetchQuota = async () => {
      try {
        const data = await api.getQuota();
        if (mounted) setLocalQuota(data);
      } catch {}
    };

    fetchQuota();
    const interval = setInterval(fetchQuota, 8000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [propQuota]);

  const filtered = conversations.filter((c) =>
    c.title.toLowerCase().includes(search.toLowerCase())
  );

  const sorted = [...filtered].sort((a, b) => b.updated_at - a.updated_at);

  const getConversationSection = (timestamp: number) => {
    const date = new Date(timestamp);
    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    const startOfYesterday = startOfToday - 86400000;
    const startOf7Days = startOfToday - 7 * 86400000;
    const startOf30Days = startOfToday - 30 * 86400000;

    const time = date.getTime();
    if (time >= startOfToday) return 'Hoy';
    if (time >= startOfYesterday) return 'Ayer';
    if (time >= startOf7Days) return 'Últimos 7 días';
    if (time >= startOf30Days) return 'Últimos 30 días';
    return 'Meses anteriores';
  };

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    onDelete(id);
  };

  return (
    <div className="sidepanel-content">
      {/* Search and New Chat Row */}
      <div className="sidepanel-header-row">
        <div className="sidepanel-search-box">
          <SearchIcon size={14} className="search-icon" />
          <input
            type="text"
            placeholder="Buscar consultas..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <button
          className="sidepanel-square-btn"
          onClick={onNewChat}
          title="Nueva conversación"
        >
          <PlusIcon size={16} />
        </button>
      </div>

      {/* Conversations List */}
      <div className="sidepanel-body-scroll">
        {sorted.length === 0 ? (
          <div className="sidepanel-empty-text">
            {search ? 'Sin resultados para la búsqueda' : 'No hay conversaciones aún'}
          </div>
        ) : (
          <div className="sidepanel-items-stack">
            {sorted.map((conv, index) => {
              const spec =
                SPECIALIZATIONS.find((s) => s.id === conv.specialization) ||
                SPECIALIZATIONS[0];
              const isActive = conv.id === activeConversationId;

              const section = getConversationSection(conv.updated_at);
              const previousSection = index > 0 ? getConversationSection(sorted[index - 1].updated_at) : null;

              return (
                <div key={conv.id}>
                  {section !== previousSection && <div className="conversation-section-label">{section}</div>}
                  <div
                    className={`sidepanel-chat-item ${isActive ? 'active' : ''}`}
                    onClick={() => onSelect(conv.id)}
                  >
                  <div className="chat-item-icon" style={{ color: spec.color }}>
                    <SpecializationIcon id={spec.id} size={16} />
                  </div>
                  <div className="chat-item-info">
                    <div className="chat-item-title">{truncate(conv.title, 32)}</div>
                    <div className="chat-item-meta">
                      <span>{spec.name}</span>
                      <span>• {formatTime(conv.updated_at)}</span>
                    </div>
                  </div>
                  <button
                    className="chat-item-del-btn"
                    onClick={(e) => handleDelete(e, conv.id)}
                    title="Eliminar conversación"
                  >
                    <TrashIcon size={14} />
                  </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Minimalist AI Token Quota Bar (Bottom of SidePanel) */}
      <div className="sidepanel-quota-box">
        <div className="quota-meta-row">
          <span className="quota-label">Tokens IA del mes</span>
          <span className="quota-value">{quota.remaining_millions}M / {quota.total_millions}M</span>
        </div>
        <div className="quota-progress-track">
          <div
            className="quota-progress-bar"
            style={{ width: `${Math.min(100, Math.max(0, quota.remaining_percent))}%` }}
          />
        </div>
        <div className="quota-subtext-row">
          <span>{quota.remaining_percent}% disponible</span>
          <span>{quota.days_remaining ? `${quota.days_remaining} días restantes` : 'Mes activo'}</span>
        </div>
      </div>
    </div>
  );
}
