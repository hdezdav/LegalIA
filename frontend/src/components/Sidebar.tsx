import { useState, useRef, useEffect } from 'react';
import { User, SidePanelTab, TokenQuota } from '../types';
import { api } from '../api';
import {
  PanelLeftIcon,
  MessageSquareIcon,
  BotIcon,
  FileTextIcon,
  EditIcon,
  BrainIcon,
  BookmarkIcon,
  PaperclipIcon,
  ScalesIcon,
  LogOutIcon,
  SparklesIcon,
} from './Icons';
import './Sidebar.css';

interface SidebarProps {
  user?: User | null;
  currentUser?: User | null;
  quota?: TokenQuota | null;
  activeTab: SidePanelTab | null;
  isSidePanelOpen: boolean;
  onTabClick: (tab: SidePanelTab) => void;
  onLogout: () => void;
  onGoToLanding?: () => void;
}

export function Sidebar({
  user,
  currentUser,
  quota: propQuota,
  activeTab,
  isSidePanelOpen,
  onTabClick,
  onLogout,
  onGoToLanding,
}: SidebarProps) {
  const activeUser = user || currentUser;
  const [profileOpen, setProfileOpen] = useState(false);
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
  const profileRef = useRef<HTMLDivElement>(null);

  const getInitials = (name?: string) => {
    if (!name) return 'AB';
    const parts = name.trim().split(' ');
    if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    return name.slice(0, 2).toUpperCase();
  };

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

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
    };
    if (profileOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [profileOpen]);

  const handleToggleSidePanel = () => {
    onTabClick(activeTab || 'chats');
  };

  return (
    <aside className="sidebar-rail">
      {/* Top Rail Navigation */}
      <div className="rail-top">
        <button
          className={`rail-btn ${isSidePanelOpen ? 'active' : ''}`}
          onClick={handleToggleSidePanel}
          title={isSidePanelOpen ? 'Ocultar panel lateral' : 'Mostrar panel lateral'}
        >
          <PanelLeftIcon size={19} />
        </button>

        <div className="rail-divider" />

        {/* Tab 1: Chats History */}
        <button
          className={`rail-btn ${activeTab === 'chats' && isSidePanelOpen ? 'active' : ''}`}
          onClick={() => onTabClick('chats')}
          title="Historial de conversaciones"
        >
          <MessageSquareIcon size={19} />
        </button>

        {/* Tab 2: Agents & Assistants */}
        <button
          className={`rail-btn ${activeTab === 'agents' && isSidePanelOpen ? 'active' : ''}`}
          onClick={() => onTabClick('agents')}
          title="Agentes y asistentes jurídicos"
        >
          <BotIcon size={19} />
        </button>

        {/* Tab 3: Prompts Library */}
        <button
          className={`rail-btn ${activeTab === 'prompts' && isSidePanelOpen ? 'active' : ''}`}
          onClick={() => onTabClick('prompts')}
          title="Biblioteca de plantillas de prompts"
        >
          <FileTextIcon size={19} />
        </button>

        {/* Tab 4: Custom Instructions */}
        <button
          className={`rail-btn ${activeTab === 'instructions' && isSidePanelOpen ? 'active' : ''}`}
          onClick={() => onTabClick('instructions')}
          title="Instrucciones personalizadas"
        >
          <EditIcon size={19} />
        </button>

        {/* Tab 5: Memories */}
        <button
          className={`rail-btn ${activeTab === 'memories' && isSidePanelOpen ? 'active' : ''}`}
          onClick={() => onTabClick('memories')}
          title="Memoria de contexto"
        >
          <BrainIcon size={19} />
        </button>

        {/* Tab 6: Bookmarks */}
        <button
          className={`rail-btn ${activeTab === 'bookmarks' && isSidePanelOpen ? 'active' : ''}`}
          onClick={() => onTabClick('bookmarks')}
          title="Marcadores y citas guardadas"
        >
          <BookmarkIcon size={19} />
        </button>

        {/* Tab 7: Files & Attachments */}
        <button
          className={`rail-btn ${activeTab === 'files' && isSidePanelOpen ? 'active' : ''}`}
          onClick={() => onTabClick('files')}
          title="Archivos y anexos"
        >
          <PaperclipIcon size={19} />
        </button>
      </div>

      {/* Bottom Profile Avatar & Real-time AI Token Bar */}
      <div className="rail-bottom" ref={profileRef}>
        {/* Minimalist AI Token Bar (directly above avatar) */}
        <div
          className="rail-token-widget"
          onClick={() => setProfileOpen(!profileOpen)}
          title={`Tokens IA asignados: ${quota.remaining_millions}M / ${quota.total_millions}M (${quota.remaining_percent}% disponible)`}
        >
          <div className="rail-token-bar-track">
            <div
              className="rail-token-bar-fill"
              style={{ height: `${Math.min(100, Math.max(8, quota.remaining_percent))}%` }}
            />
          </div>
          <span className="rail-token-label">{quota.remaining_millions}M</span>
        </div>

        {/* User Profile Avatar Circle */}
        <div
          className="rail-avatar-circle"
          onClick={() => setProfileOpen(!profileOpen)}
          title={`Menú de usuario: ${activeUser?.full_name || 'Dr. Abogado'}`}
        >
          {getInitials(activeUser?.full_name)}
        </div>

        {/* Profile & Token Quota Popover */}
        {profileOpen && (
          <div className="profile-popover-menu">
            <div className="profile-user-card">
              <div className="profile-card-name">
                {activeUser?.full_name || 'Dr. Abogado Titulado'}
              </div>
              <div className="profile-card-email">
                {activeUser?.email || 'abogado@legalia.co'}
              </div>
              <div className="profile-card-badge">
                Plan Profesional · Colombia
              </div>
            </div>

            {/* Total Monthly AI Token Balance Card */}
            <div className="profile-quota-card">
              <div className="profile-quota-header">
                <div className="profile-quota-title-row">
                  <SparklesIcon size={14} className="quota-sparkle" />
                  <span>Tokens IA Mensuales</span>
                </div>
                <span className="profile-quota-pct">{quota.remaining_percent}%</span>
              </div>

              <div className="profile-quota-nums">
                <strong>{quota.remaining_millions}M</strong> de {quota.total_millions}M disponibles
              </div>

              <div className="quota-progress-track">
                <div
                  className="quota-progress-bar"
                  style={{ width: `${Math.min(100, Math.max(0, quota.remaining_percent))}%` }}
                />
              </div>

              <div className="profile-quota-details">
                <span>Consumidos: {quota.used_millions}M</span>
                <span>{quota.days_remaining ? `${quota.days_remaining} días restantes` : 'Mes en curso'}</span>
              </div>
            </div>

            <div className="profile-menu-divider" />

            {onGoToLanding && (
              <button
                className="profile-menu-item"
                onClick={() => {
                  setProfileOpen(false);
                  onGoToLanding();
                }}
              >
                <ScalesIcon size={16} />
                <span>Página Principal / Conoce Legalia</span>
              </button>
            )}

            <button
              className="profile-menu-item profile-logout-item"
              onClick={() => {
                setProfileOpen(false);
                onLogout();
              }}
            >
              <LogOutIcon size={16} />
              <span>Cerrar Sesión</span>
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}
