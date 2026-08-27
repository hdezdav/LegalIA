import {
  SidePanelTab,
  Conversation,
  Agent,
  PromptTemplate,
  Memory,
  MemoriesConfig,
  ParsedFile,
  TokenQuota,
} from '../../types';
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

  return (
    <aside className="sidepanel-dock">
      {renderContent()}
    </aside>
  );
}
