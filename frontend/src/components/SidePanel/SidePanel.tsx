import { useEffect, useRef, useState } from 'react';
import {
  SidePanelTab,
  Conversation,
  Agent,
  PromptTemplate,
  Memory,
  MemoriesConfig,
  ParsedFile,
  TokenQuota,
  User,
} from '../../types';
import {
  PlusIcon,
  MessageSquareIcon,
  BotIcon,
  FileTextIcon,
  PaperclipIcon,
  BrainIcon,
  SparklesIcon,
  LogOutIcon,
  ScalesIcon,
} from '../Icons';
import { ConversationsView } from './ConversationsView';
import { AgentsView } from './AgentsView';
import { PromptsView } from './PromptsView';
import { MemoriesView } from './MemoriesView';
import { BookmarksView } from './BookmarksView';
import { FilesView } from './FilesView';
import './SidePanel.css';

interface SidePanelProps {
  activeTab: SidePanelTab | null;
  isOpen: boolean;
  onClose?: () => void;
  onLogout?: () => void;
  onGoToLanding?: () => void;
  user?: User | null;
  onTabClick: (tab: SidePanelTab) => void;
  quota?: TokenQuota | null;
  // Conversations
  conversations: Conversation[];
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
  onNewConversation: () => void;
  // Agents
  agents: Agent[];
  activeAgentId: string | null;
  onSaveAgent: (agent: Agent) => void;
  onDeleteAgent: (id: string) => void;
  onSelectAgent: (id: string | null) => void;
  // Prompts
  prompts: PromptTemplate[];
  onSavePrompt: (prompt: PromptTemplate) => void;
  onDeletePrompt: (id: string) => void;
  onUsePrompt: (body: string) => void;
  // Memories
  memories: Memory[];
  memoriesConfig: MemoriesConfig;
  onSaveMemory: (memory: Memory) => void;
  onDeleteMemory: (id: string) => void;
  onMemoriesConfigChange: (config: MemoriesConfig) => void;
  // Files
  files: ParsedFile[];
  onAddFile: (file: ParsedFile) => void;
  onDeleteFile: (id: string) => void;
  onInsertFileToChat: (file: ParsedFile) => void;
}

export function SidePanel({
  activeTab,
  isOpen,
  onClose,
  onLogout,
  onGoToLanding,
  user,
  onTabClick,
  quota,
  conversations,
  activeConversationId,
  onSelectConversation,
  onDeleteConversation,
  onNewConversation,
  agents,
  activeAgentId,
  onSaveAgent,
  onDeleteAgent,
  onSelectAgent,
  prompts,
  onSavePrompt,
  onDeletePrompt,
  onUsePrompt,
  memories,
  memoriesConfig,
  onSaveMemory,
  onDeleteMemory,
  onMemoriesConfigChange,
  files,
  onAddFile,
  onDeleteFile,
  onInsertFileToChat,
}: SidePanelProps) {
  const [isMobile, setIsMobile] = useState(false);
  const mobileCloseButtonRef = useRef<HTMLButtonElement>(null);
  const previouslyFocusedElementRef = useRef<HTMLElement | null>(null);
  const onCloseRef = useRef(onClose);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(max-width: 768px)');
    const handleChange = () => setIsMobile(mediaQuery.matches);
    handleChange();
    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  useEffect(() => {
    if (!isOpen || !isMobile) return;

    previouslyFocusedElementRef.current = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onCloseRef.current?.();
    };

    document.body.style.overflow = 'hidden';
    document.addEventListener('keydown', handleKeyDown);
    mobileCloseButtonRef.current?.focus();
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener('keydown', handleKeyDown);
      if (previouslyFocusedElementRef.current?.isConnected) {
        previouslyFocusedElementRef.current.focus();
      }
      previouslyFocusedElementRef.current = null;
    };
  }, [isOpen, isMobile]);

  if (!isOpen || !activeTab) {
    return null;
  }

  const renderContent = () => {
    switch (activeTab) {
      case 'chats':
        return (
          <ConversationsView
            conversations={conversations}
            activeConversationId={activeConversationId}
            quota={quota}
            onSelect={onSelectConversation}
            onDelete={onDeleteConversation}
            onNewChat={onNewConversation}
          />
        );
      case 'agents':
        return (
          <AgentsView
            agents={agents}
            activeAgentId={activeAgentId}
            onSave={onSaveAgent}
            onDelete={onDeleteAgent}
            onSelect={onSelectAgent}
          />
        );
      case 'prompts':
        return (
          <PromptsView
            prompts={prompts}
            onSave={onSavePrompt}
            onDelete={onDeletePrompt}
            onUse={onUsePrompt}
          />
        );
      case 'memories':
        return (
          <MemoriesView
            memories={memories}
            config={memoriesConfig}
            onSave={onSaveMemory}
            onDelete={onDeleteMemory}
            onConfigChange={onMemoriesConfigChange}
          />
        );
      case 'bookmarks':
        return <BookmarksView />;
      case 'files':
        return (
          <FilesView
            files={files}
            onAddFile={onAddFile}
            onDeleteFile={onDeleteFile}
            onInsertToChat={onInsertFileToChat}
          />
        );
      case 'instructions':
        return (
          <div className="sidepanel-content">
            <div className="sidepanel-header-row">
              <h3 className="sidepanel-view-title">Instrucciones Personalizadas</h3>
            </div>
            <div className="sidepanel-body-scroll">
              <div className="sidepanel-empty-card">
                <h3 className="empty-card-title">Instrucciones del Sistema</h3>
                <p className="empty-card-desc">
                  Define directrices jurídicas globales que aplicarán a todas tus interacciones con Legalia.
                </p>
              </div>
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  if (!isOpen) return null;

  const getInitials = (name?: string) => {
    if (!name) return 'AB';
    const parts = name.trim().split(' ');
    if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    return name.slice(0, 2).toUpperCase();
  };

  const handleMobileNewChat = () => {
    onNewConversation();
    if (onClose) onClose();
  };

  const handleMobileSelectTab = (tab: SidePanelTab) => {
    onTabClick(tab);
  };

  return (
    <>
      <div className="sidepanel-backdrop" onClick={onClose} aria-hidden="true" />
      <aside
        className="sidepanel-dock"
        role={isMobile ? 'dialog' : undefined}
        aria-modal={isMobile ? 'true' : undefined}
        aria-labelledby={isMobile ? 'sidepanel-mobile-title' : undefined}
      >
        {/* Mobile Header: Brand + Close */}
        <div className="sidepanel-mobile-header">
          <div className="mobile-header-brand">
            <img src="/logos/legalia.svg" alt="LegalIA" className="mobile-brand-logo" />
            <span id="sidepanel-mobile-title" className="sidepanel-mobile-title">LegalIA</span>
          </div>
          <button
            type="button"
            className="sidepanel-mobile-close-btn"
            onClick={onClose}
            aria-label="Cerrar panel"
            ref={mobileCloseButtonRef}
          >
            ✕
          </button>
        </div>

        {/* Mobile Primary CTA: Nueva Conversación */}
        <div className="mobile-drawer-cta-row">
          <button
            type="button"
            className="mobile-drawer-new-chat-btn"
            onClick={handleMobileNewChat}
          >
            <PlusIcon size={16} />
            <span>Nueva conversación</span>
          </button>
        </div>

        {/* Mobile Segmented Navigation Tabs */}
        <div className="mobile-drawer-tabs-scroll">
          <button
            type="button"
            className={`mobile-tab-pill ${activeTab === 'chats' ? 'active' : ''}`}
            onClick={() => handleMobileSelectTab('chats')}
          >
            <MessageSquareIcon size={14} />
            <span>Chats</span>
          </button>
          <button
            type="button"
            className={`mobile-tab-pill ${activeTab === 'agents' ? 'active' : ''}`}
            onClick={() => handleMobileSelectTab('agents')}
          >
            <BotIcon size={14} />
            <span>Agentes</span>
          </button>
          <button
            type="button"
            className={`mobile-tab-pill ${activeTab === 'prompts' ? 'active' : ''}`}
            onClick={() => handleMobileSelectTab('prompts')}
          >
            <FileTextIcon size={14} />
            <span>Prompts</span>
          </button>
          <button
            type="button"
            className={`mobile-tab-pill ${activeTab === 'files' ? 'active' : ''}`}
            onClick={() => handleMobileSelectTab('files')}
          >
            <PaperclipIcon size={14} />
            <span>Archivos</span>
          </button>
          <button
            type="button"
            className={`mobile-tab-pill ${activeTab === 'memories' ? 'active' : ''}`}
            onClick={() => handleMobileSelectTab('memories')}
          >
            <BrainIcon size={14} />
            <span>Memoria</span>
          </button>
        </div>

        {/* Main Content Area */}
        <div className="sidepanel-view-container">
          {renderContent()}
        </div>

        {/* Mobile Footer: User Profile & Remaining Tokens */}
        <div className="mobile-drawer-footer">
          <div className="mobile-user-row">
            <div className="mobile-user-avatar">
              {getInitials(user?.full_name)}
            </div>
            <div className="mobile-user-info">
              <span className="mobile-user-name">{user?.full_name || 'Dr. Abogado'}</span>
              <span className="mobile-user-quota">
                <SparklesIcon size={11} className="quota-sparkle" />
                {quota?.remaining_millions || '13.7'}M tokens disponibles
              </span>
            </div>
            {onGoToLanding && (
              <button
                type="button"
                className="mobile-landing-btn"
                onClick={() => {
                  if (onClose) onClose();
                  onGoToLanding();
                }}
                title="Página principal"
                aria-label="Página principal"
              >
                <ScalesIcon size={16} />
              </button>
            )}
            {onLogout && (
              <button
                type="button"
                className="mobile-logout-btn"
                onClick={() => {
                  if (onClose) onClose();
                  onLogout();
                }}
                title="Cerrar sesión"
                aria-label="Cerrar sesión"
              >
                <LogOutIcon size={16} />
              </button>
            )}
          </div>
        </div>
      </aside>
    </>
  );
}
