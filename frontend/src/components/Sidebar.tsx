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
  variant?: 'rail' | 'mobile';
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
  variant = 'rail',
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

  useEffect(() => {
    if (variant === 'mobile') {
      setProfileOpen(false);
    }
  }, [variant, isSidePanelOpen]);

  const handleTabClick = (tab: SidePanelTab) => {
    if (variant === 'mobile') {
      setProfileOpen(false);
    }
    onTabClick(tab);
  };

  const handleToggleSidePanel = () => {
    handleTabClick(activeTab || 'chats');
  };

  const navigation = (
    <>
      <button
        type="button"
        className={`rail-btn ${variant === 'rail' && isSidePanelOpen ? 'active' : ''}`}
        onClick={handleToggleSidePanel}
        title={isSidePanelOpen ? 'Ocultar panel lateral' : 'Mostrar panel lateral'}
        aria-label={isSidePanelOpen ? 'Ocultar panel lateral' : 'Mostrar panel lateral'}
      >
        <PanelLeftIcon size={19} />
      </button>

      {variant === 'rail' && <div className="rail-divider" />}

      <button
        type="button"
        className={`rail-btn ${activeTab === 'chats' && isSidePanelOpen ? 'active' : ''}`}
        onClick={() => handleTabClick('chats')}
        title="Historial de conversaciones"
        aria-label="Historial de conversaciones"
      >
        <MessageSquareIcon size={19} />
      </button>

      <button
        type="button"
        className={`rail-btn ${activeTab === 'agents' && isSidePanelOpen ? 'active' : ''}`}
        onClick={() => handleTabClick('agents')}
        title="Agentes y asistentes jurídicos"
        aria-label="Agentes y asistentes jurídicos"
      >
        <BotIcon size={19} />
      </button>

      <button
        type="button"
        className={`rail-btn ${activeTab === 'prompts' && isSidePanelOpen ? 'active' : ''}`}
        onClick={() => handleTabClick('prompts')}
        title="Biblioteca de plantillas de prompts"
        aria-label="Biblioteca de plantillas de prompts"
      >
        <FileTextIcon size={19} />
      </button>

      <button
        type="button"
        className={`rail-btn ${activeTab === 'instructions' && isSidePanelOpen ? 'active' : ''}`}
        onClick={() => handleTabClick('instructions')}
        title="Instrucciones personalizadas"
        aria-label="Instrucciones personalizadas"
      >
        <EditIcon size={19} />
      </button>

      <button
        type="button"
        className={`rail-btn ${activeTab === 'memories' && isSidePanelOpen ? 'active' : ''}`}
        onClick={() => handleTabClick('memories')}
        title="Memoria de contexto"
        aria-label="Memoria de contexto"
      >
        <BrainIcon size={19} />
      </button>

      <button
        type="button"
        className={`rail-btn ${activeTab === 'bookmarks' && isSidePanelOpen ? 'active' : ''}`}
        onClick={() => handleTabClick('bookmarks')}
        title="Marcadores y citas guardadas"
        aria-label="Marcadores y citas guardadas"
      >
        <BookmarkIcon size={19} />
      </button>

      <button
        type="button"
        className={`rail-btn ${activeTab === 'files' && isSidePanelOpen ? 'active' : ''}`}
        onClick={() => handleTabClick('files')}
        title="Archivos y anexos"
        aria-label="Archivos y anexos"
      >
        <PaperclipIcon size={19} />
      </button>
    </>
  );

  const profile = (
    <div className="rail-bottom" ref={profileRef}>
      <button
        type="button"
        className="rail-token-widget"
        onClick={() => setProfileOpen(!profileOpen)}
        title={`Tokens IA asignados: ${quota.remaining_millions}M / ${quota.total_millions}M (${quota.remaining_percent}% disponible)`}
        aria-label={`Tokens IA disponibles: ${quota.remaining_millions}M de ${quota.total_millions}M`}
      >
        <div className="rail-token-bar-track">
          <div
            className="rail-token-bar-fill"
            style={{ height: `${Math.min(100, Math.max(8, quota.remaining_percent))}%` }}
          />
        </div>
        <span className="rail-token-label">{quota.remaining_millions}M</span>
      </button>

      <button
        type="button"
        className="rail-avatar-circle"
        onClick={() => setProfileOpen(!profileOpen)}
        title={`Menú de usuario: ${activeUser?.full_name || 'Dr. Abogado'}`}
        aria-label={`Menú de usuario: ${activeUser?.full_name || 'Dr. Abogado'}`}
      >
        {getInitials(activeUser?.full_name)}
      </button>

      {profileOpen && (
        <div className="profile-popover-menu">
          <div className="profile-user-card">
            <div className="profile-card-name">{activeUser?.full_name || 'Dr. Abogado Titulado'}</div>
            <div className="profile-card-email">{activeUser?.email || 'abogado@legalia.co'}</div>
            <div className="profile-card-badge">Plan Profesional · Colombia</div>
          </div>

          <div className="profile-quota-card">
            <div className="profile-quota-header">
              <div className="profile-quota-title-row">
                <SparklesIcon size={14} className="quota-sparkle" />
                <span>Tokens IA Mensuales</span>
              </div>
              <span className="profile-quota-pct">{quota.remaining_percent}%</span>
            </div>
            <div className="profile-quota-nums"><strong>{quota.remaining_millions}M</strong> de {quota.total_millions}M disponibles</div>
            <div className="quota-progress-track">
              <div className="quota-progress-bar" style={{ width: `${Math.min(100, Math.max(0, quota.remaining_percent))}%` }} />
            </div>
            <div className="profile-quota-details">
              <span>Consumidos: {quota.used_millions}M</span>
              <span>{quota.days_remaining ? `${quota.days_remaining} días restantes` : 'Mes en curso'}</span>
            </div>
          </div>

          <div className="profile-menu-divider" />
          {onGoToLanding && (
            <button type="button" className="profile-menu-item" onClick={() => { setProfileOpen(false); onGoToLanding(); }}>
              <ScalesIcon size={16} />
              <span>Página Principal / Conoce Legalia</span>
            </button>
          )}
          <button type="button" className="profile-menu-item profile-logout-item" onClick={() => { setProfileOpen(false); onLogout(); }}>
            <LogOutIcon size={16} />
            <span>Cerrar Sesión</span>
          </button>
        </div>
      )}
    </div>
  );

  if (variant === 'mobile') {
    return <nav className="sidebar-mobile-nav" aria-label="Navegación principal"><div className="sidebar-mobile-nav-items">{navigation}</div>{profile}</nav>;
  }

  return (
    <aside className="sidebar-rail">
      {/* Top Rail Navigation */}
      <div className="rail-top">
        {navigation}
      </div>

      {/* Bottom Profile Avatar & Real-time AI Token Bar */}
      {profile}
    </aside>
  );
}
