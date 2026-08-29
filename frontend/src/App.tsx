import { useState, useEffect, useCallback } from 'react';
import { api } from './api';
import {
  Conversation,
  User,
  PromptTemplate,
  Memory,
  MemoriesConfig,
  Agent,
  SidePanelTab,
  ParsedFile,
  TokenQuota,
} from './types';
import { createConversation, loadConversations, saveConversations } from './storage';
import {
  loadPrompts,
  savePrompts,
  loadMemories,
  saveMemories,
  loadMemoriesConfig,
  saveMemoriesConfig,
  loadAgents,
  saveAgents,
} from './library';
import { Sidebar } from './components/Sidebar';
import { SidePanel } from './components/SidePanel/SidePanel';
import { Chat } from './components/Chat';
import { Auth } from './components/Auth';
import { Landing } from './components/Landing/Landing';
import './App.css';

const THEME_KEY = 'legalia_theme';
const ACTIVE_CONVO_KEY = 'legalia_active_convo';
const ACTIVE_AGENT_KEY = 'legalia_active_agent';
const SELECTED_MODEL_KEY = 'legalia_selected_model';
const FILES_KEY = 'legalia_files';

export function App() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(api.isAuthenticated());
  const [loading, setLoading] = useState(true);

  // View state: 'landing' | 'app' | 'auth'
  const [currentView, setCurrentView] = useState<'landing' | 'app' | 'auth'>(() => {
    // If explicitly in /app path or authenticated, go to app; otherwise show landing
    if (window.location.hash === '#app') return 'app';
    if (api.isAuthenticated()) return 'app';
    return 'landing';
  });

  // Selected AI Engine (Claude, GPT, Gemini)
  const [selectedModelId, setSelectedModelId] = useState<string>(() => {
    return localStorage.getItem(SELECTED_MODEL_KEY) || 'claude-sonnet-4.6';
  });

  // Conversations State
  const [conversations, setConversations] = useState<Conversation[]>(() => loadConversations());
  const [activeConversationId, setActiveConversationId] = useState<string | null>(() => {
    const stored = localStorage.getItem(ACTIVE_CONVO_KEY);
    return stored || null;
  });

  // Library States
  const [prompts, setPrompts] = useState<PromptTemplate[]>(() => loadPrompts());
  const [memories, setMemories] = useState<Memory[]>(() => loadMemories());
  const [memoriesConfig, setMemoriesConfig] = useState<MemoriesConfig>(() => loadMemoriesConfig());
  const [agents, setAgents] = useState<Agent[]>(() => loadAgents());
  const [activeAgentId, setActiveAgentId] = useState<string | null>(() => {
    const stored = localStorage.getItem(ACTIVE_AGENT_KEY);
    return stored || null;
  });

  // Files State (MarkItDown parsed documents)
  const [files, setFiles] = useState<ParsedFile[]>(() => {
    try {
      const stored = localStorage.getItem(FILES_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  // SidePanel Unified Tab Navigation State (LibreChat Architecture)
  const [activeTab, setActiveTab] = useState<SidePanelTab | null>('chats');
  const [sidePanelOpen, setSidePanelOpen] = useState(true);

  // Injected text from Prompts/Files into Chat
  const [injectedText, setInjectedText] = useState<string | null>(null);
  const [injectedFile, setInjectedFile] = useState<ParsedFile | null>(null);

  // Real-time Token Quota State (synced across sidebar, panel, and completions)
  const [quota, setQuota] = useState<TokenQuota | null>(null);

  const refreshQuota = useCallback(async () => {
    try {
      const data = await api.getQuota();
      setQuota(data);
    } catch {}
  }, []);

  useEffect(() => {
    refreshQuota();
    const interval = setInterval(refreshQuota, 3000);
    const handleFocus = () => refreshQuota();
    window.addEventListener('focus', handleFocus);
    return () => {
      clearInterval(interval);
      window.removeEventListener('focus', handleFocus);
    };
  }, [refreshQuota]);

  const [theme] = useState<'light' | 'dark'>(() => {
    const stored = localStorage.getItem(THEME_KEY);
    if (stored === 'light' || stored === 'dark') return stored;
    return 'light';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem(SELECTED_MODEL_KEY, selectedModelId);
  }, [selectedModelId]);

  useEffect(() => {
    saveConversations(conversations);
  }, [conversations]);

  useEffect(() => {
    if (activeConversationId) {
      localStorage.setItem(ACTIVE_CONVO_KEY, activeConversationId);
    }
  }, [activeConversationId]);

  useEffect(() => {
    savePrompts(prompts);
  }, [prompts]);

  useEffect(() => {
    saveMemories(memories);
  }, [memories]);

  useEffect(() => {
    saveMemoriesConfig(memoriesConfig);
  }, [memoriesConfig]);

  useEffect(() => {
    saveAgents(agents);
  }, [agents]);

  useEffect(() => {
    try {
      localStorage.setItem(FILES_KEY, JSON.stringify(files));
    } catch {
      // ignore
    }
  }, [files]);

  useEffect(() => {
    if (activeAgentId) {
      localStorage.setItem(ACTIVE_AGENT_KEY, activeAgentId);
    } else {
      localStorage.removeItem(ACTIVE_AGENT_KEY);
    }
  }, [activeAgentId]);

  useEffect(() => {
    const checkAuth = async () => {
      if (api.isAuthenticated()) {
        try {
          const user = await api.getMe();
          setCurrentUser(user);
          setIsAuthenticated(true);
        } catch {
          api.logout();
          setIsAuthenticated(false);
          setCurrentUser(null);
        }
      }
      setLoading(false);
    };
    checkAuth();
  }, []);

  useEffect(() => {
    if (conversations.length > 0 && !activeConversationId) {
      setActiveConversationId(conversations[0].id);
    } else if (conversations.length === 0) {
      const fresh = createConversation();
      setConversations([fresh]);
      setActiveConversationId(fresh.id);
    }
  }, [conversations, activeConversationId]);

  const activeConversation =
    conversations.find((c) => c.id === activeConversationId) || conversations[0];

  const handleNewConversation = useCallback(() => {
    const fresh = createConversation();
    setConversations((prev) => [fresh, ...prev]);
    setActiveConversationId(fresh.id);
  }, []);

  const handleSelectConversation = (id: string) => {
    setActiveConversationId(id);
    if (window.innerWidth <= 768) {
      setSidePanelOpen(false);
    }
  };

  const handleUpdateConversation = (updated: Conversation) => {
    setConversations((prev) => {
      const exists = prev.some((c) => c.id === updated.id);
      if (exists) {
        return prev.map((c) => (c.id === updated.id ? updated : c));
      }
      return [updated, ...prev];
    });
  };

  const handleDeleteConversation = (id: string) => {
    setConversations((prev) => {
      const filtered = prev.filter((c) => c.id !== id);
      if (filtered.length === 0) {
        const fresh = createConversation();
        setActiveConversationId(fresh.id);
        return [fresh];
      }
      if (activeConversationId === id) {
        setActiveConversationId(filtered[0].id);
      }
      return filtered;
    });
  };

  // Rail tab click handler: toggles or switches SidePanel tab
  const handleTabClick = (tab: SidePanelTab) => {
    if (activeTab === tab && sidePanelOpen) {
      setSidePanelOpen(false);
    } else {
      setActiveTab(tab);
      setSidePanelOpen(true);
    }
  };

  const handleLoginSuccess = async () => {
    try {
      const user = await api.getMe();
      setCurrentUser(user);
    } catch {
      // Ignore
    }
    setIsAuthenticated(true);
    setCurrentView('app');
  };

  const handleLogout = () => {
    api.logout();
    setCurrentUser(null);
    setIsAuthenticated(false);
    setCurrentView('landing');
  };

  // Prompts Handlers
  const handleSavePrompt = (prompt: PromptTemplate) => {
    setPrompts((prev) => {
      const exists = prev.some((p) => p.id === prompt.id);
      if (exists) {
        return prev.map((p) => (p.id === prompt.id ? prompt : p));
      }
      return [prompt, ...prev];
    });
  };

  const handleDeletePrompt = (id: string) => {
    setPrompts((prev) => prev.filter((p) => p.id !== id));
  };

  const handleUsePrompt = (promptBody: string) => {
    setInjectedText(promptBody);
    if (window.innerWidth <= 768) {
      setSidePanelOpen(false);
    }
  };

  // Files Handlers
  const handleAddFile = (file: ParsedFile) => {
    setFiles((prev) => [file, ...prev]);
  };

  const handleDeleteFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const handleInsertFileToChat = (file: ParsedFile) => {
    setInjectedFile(file);
    setInjectedText(
      `Analiza este documento (${file.filename}) y realiza un resumen ejecutivo procesal identificando partes, pretensiones, hechos clave y normas aplicables:`
    );
    if (window.innerWidth <= 768) {
      setSidePanelOpen(false);
    }
  };

  // Memories Handlers
  const handleSaveMemory = (memory: Memory) => {
    setMemories((prev) => {
      const exists = prev.some((m) => m.id === memory.id);
      if (exists) {
        return prev.map((m) => (m.id === memory.id ? memory : m));
      }
      return [memory, ...prev];
    });
  };

  const handleDeleteMemory = (id: string) => {
    setMemories((prev) => prev.filter((m) => m.id !== id));
  };

  // Agents Handlers
  const handleSaveAgent = (agent: Agent) => {
    setAgents((prev) => {
      const exists = prev.some((a) => a.id === agent.id);
      if (exists) {
        return prev.map((a) => (a.id === agent.id ? agent : a));
      }
      return [agent, ...prev];
    });
  };

  const handleDeleteAgent = (id: string) => {
    setAgents((prev) => prev.filter((a) => a.id !== id));
    if (activeAgentId === id) {
      setActiveAgentId(null);
    }
  };

  if (loading) {
    return (
      <div className="app-loading">
        <div className="loading-spinner" />
        <p>Cargando Legalia...</p>
      </div>
    );
  }

  // 1. Landing Page View
  if (currentView === 'landing') {
    return (
      <Landing
        onGoToApp={() => {
          if (isAuthenticated) {
            setCurrentView('app');
          } else {
            setCurrentView('app'); // Allows guest exploration
          }
        }}
        onLogin={() => setCurrentView('auth')}
      />
    );
  }

  // 2. Authentication View
  if (currentView === 'auth' || (!isAuthenticated && currentView === 'app' && !api.isAuthenticated())) {
    return (
      <Auth
        onLogin={handleLoginSuccess}
        onBackToLanding={() => setCurrentView('landing')}
      />
    );
  }

  // 3. Main Workspace Application View
  return (
    <div className="app-root">
      {/* 1. Left Rail (52px wide) */}
      <Sidebar
        currentUser={currentUser}
        quota={quota}
        activeTab={activeTab}
        isSidePanelOpen={sidePanelOpen}
        onTabClick={handleTabClick}
        onLogout={handleLogout}
        onGoToLanding={() => setCurrentView('landing')}
      />

      {/* 2. Unified SidePanel (330px wide docked) */}
      <SidePanel
        activeTab={activeTab}
        isOpen={sidePanelOpen}
        onClose={() => setSidePanelOpen(false)}
        quota={quota}
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelectConversation={handleSelectConversation}
        onDeleteConversation={handleDeleteConversation}
        onNewConversation={handleNewConversation}
        agents={agents}
        activeAgentId={activeAgentId}
        onSaveAgent={handleSaveAgent}
        onDeleteAgent={handleDeleteAgent}
        onSelectAgent={setActiveAgentId}
        prompts={prompts}
        onSavePrompt={handleSavePrompt}
        onDeletePrompt={handleDeletePrompt}
        onUsePrompt={handleUsePrompt}
        memories={memories}
        memoriesConfig={memoriesConfig}
        onSaveMemory={handleSaveMemory}
        onDeleteMemory={handleDeleteMemory}
        onMemoriesConfigChange={setMemoriesConfig}
        files={files}
        onAddFile={handleAddFile}
        onDeleteFile={handleDeleteFile}
        onInsertFileToChat={handleInsertFileToChat}
      />

      {/* 3. Main Chat Workspace */}
      {activeConversation && (
        <Chat
          conversation={activeConversation}
          currentUser={currentUser}
          activeAgent={agents.find((a) => a.id === activeAgentId) || null}
          agents={agents}
          activeAgentId={activeAgentId}
          onSelectAgent={setActiveAgentId}
          memories={memories}
          memoriesEnabled={memoriesConfig.enabled}
          injectedText={injectedText}
          injectedFile={injectedFile}
          sidebarCollapsed={!sidePanelOpen}
          selectedModelId={selectedModelId}
          onSelectModel={setSelectedModelId}
          onUpdateConversation={handleUpdateConversation}
          onOpenSidebar={() => {
            setSidePanelOpen((prev) => !prev);
            if (!activeTab) setActiveTab('chats');
          }}
          onOpenPrompts={() => {
            setActiveTab('prompts');
            setSidePanelOpen(true);
          }}
          onOpenAgents={() => {
            setActiveTab('agents');
            setSidePanelOpen(true);
          }}
          onInjectedTextConsumed={() => setInjectedText(null)}
          onInjectedFileConsumed={() => setInjectedFile(null)}
          onNewChat={handleNewConversation}
          onMessageComplete={refreshQuota}
        />
      )}
    </div>
  );
}
