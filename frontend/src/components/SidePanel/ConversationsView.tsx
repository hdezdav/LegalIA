import { useState } from 'react';
import { Conversation } from '../../types';
import { SPECIALIZATIONS } from '../../constants';
import { formatTime, truncate } from '../../utils';
import { PlusIcon, TrashIcon, SearchIcon } from '../Icons';
import { SpecializationIcon } from '../SpecializationMenu';

interface ConversationsViewProps {
  conversations: Conversation[];
  activeConversationId: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onNewChat: () => void;
}

export function ConversationsView({
  conversations,
  activeConversationId,
  onSelect,
  onDelete,
  onNewChat,
}: ConversationsViewProps) {
  const [search, setSearch] = useState('');
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const filtered = conversations.filter((c) =>
    c.title.toLowerCase().includes(search.toLowerCase())
  );

  const sorted = [...filtered].sort((a, b) => b.updated_at - a.updated_at);

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (confirmDeleteId === id) {
      onDelete(id);
      setConfirmDeleteId(null);
    } else {
      setConfirmDeleteId(id);
      setTimeout(() => setConfirmDeleteId(null), 3000);
    }
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
            {sorted.map((conv) => {
              const spec =
                SPECIALIZATIONS.find((s) => s.id === conv.specialization) ||
                SPECIALIZATIONS[0];
              const isActive = conv.id === activeConversationId;
              const isConfirm = confirmDeleteId === conv.id;

              return (
                <div
                  key={conv.id}
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
                    className={`chat-item-del-btn ${isConfirm ? 'confirm' : ''}`}
                    onClick={(e) => handleDelete(e, conv.id)}
                    title={isConfirm ? 'Confirmar eliminación' : 'Eliminar'}
                  >
                    <TrashIcon size={14} />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
