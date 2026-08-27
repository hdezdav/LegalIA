import { useState, useRef, useEffect } from 'react';
import { User, SidePanelTab } from '../types';
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
} from './Icons';
import './Sidebar.css';

interface SidebarProps {
  user?: User | null;
  currentUser?: User | null;
  activeTab: SidePanelTab | null;
  isSidePanelOpen: boolean;
  onTabClick: (tab: SidePanelTab) => void;
  onLogout: () => void;
  onGoToLanding?: () => void;
}

export function Sidebar({
  user,
  currentUser,
  activeTab,
  isSidePanelOpen,
  onTabClick,
  onLogout,
  onGoToLanding,
}: SidebarProps) {
  const activeUser = user || currentUser;
  const [profileOpen, setProfileOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);

  const getInitials = (name?: string) => {
    if (!name) return 'AB';
    const parts = name.trim().split(' ');
    if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    return name.slice(0, 2).toUpperCase();
  };

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
      {/* Top Rail Navigation (LibreChat-Clean Architecture) */}
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

      {/* Bottom Profile Avatar & Popover Menu */}
      <div className="rail-bottom" ref={profileRef}>
        <div
          className="rail-avatar-circle"
          onClick={() => setProfileOpen(!profileOpen)}
          title={`Menú de usuario: ${activeUser?.full_name || 'Dr. Abogado'}`}
        >
          {getInitials(activeUser?.full_name)}
        </div>

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
