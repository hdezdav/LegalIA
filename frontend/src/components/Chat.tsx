import { useState, useRef, useEffect, FormEvent, useMemo, ChangeEvent } from 'react';
import { api } from '../api';
import {
  Agent,
  Conversation,
  LegalSpecializationId,
  Memory,
  Message as MessageType,
  User,
  ParsedFile,
} from '../types';
import { SPECIALIZATIONS, SPANISH_GREETINGS, EXAMPLE_PROMPTS } from '../constants';
import { exportConversationToMarkdown, downloadFile, generateUUID } from '../utils';
import { buildContextBlock } from '../context';
import { Message } from './Message';
import { SpecializationMenu } from './SpecializationMenu';
import { ModelSelector } from './ModelSelector';
import { FileRow } from './Chat/Files/FileRow';
import { AttachFileMenu } from './Chat/Files/AttachFileMenu';
import {
  MenuIcon,
  ArrowUpIcon,
  DownloadIcon,
  SlidersIcon,
  MicIcon,
  FileTextIcon,
  BotIcon,
  PaperclipIcon,
  SquareIcon,
  PlusIcon,
} from './Icons';
import { LegaliaBotAvatar } from './LegaliaBotAvatar';
import './Chat.css';

interface ChatProps {
  conversation: Conversation;
  currentUser?: User | null;
  activeAgent?: Agent | null;
  memories?: Memory[];
  memoriesEnabled?: boolean;
  injectedText?: string | null;
  sidebarCollapsed?: boolean;
  selectedModelId?: string;
  onSelectModel?: (modelId: string) => void;
  onUpdateConversation: (conv: Conversation) => void;
  onOpenSidebar?: () => void;
  onOpenPrompts?: () => void;
  onOpenAgents?: () => void;
  onInjectedTextConsumed?: () => void;
  onNewChat?: () => void;
}

export function Chat({
  conversation,
  currentUser,
  activeAgent = null,
  memories = [],
  memoriesEnabled = false,
  injectedText = null,
  sidebarCollapsed,
  selectedModelId = 'claude-sonnet-4.6',
  onSelectModel,
  onUpdateConversation,
  onOpenSidebar,
  onOpenPrompts,
  onOpenAgents,
  onInjectedTextConsumed,
  onNewChat,
}: ChatProps) {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState<ParsedFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isDraggingOver, setIsDraggingOver] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const firstName = useMemo(() => {
    if (!currentUser?.full_name) return 'Doctor(a)';
    return currentUser.full_name.trim().split(' ')[0];
  }, [currentUser]);

  const greetingText = useMemo(() => {
    const template = SPANISH_GREETINGS[0] || '¿En qué vamos a profundizar hoy, {name}?';
    return template.replace('{name}', firstName);
  }, [firstName]);

  useEffect(() => {
    if (injectedText) {
      setInput(injectedText);
      onInjectedTextConsumed?.();
      textareaRef.current?.focus();
    }
  }, [injectedText, onInjectedTextConsumed]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversation.messages, loading]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  const specialization = SPECIALIZATIONS.find((s) => s.id === conversation.specialization);

  const handleSpecializationChange = (id: LegalSpecializationId) => {
    onUpdateConversation({ ...conversation, specialization: id });
  };

  const handleExport = () => {
    const markdown = exportConversationToMarkdown(conversation);
    downloadFile(`${conversation.title.replace(/\s+/g, '_')}.md`, markdown);
  };

  const handleStopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setLoading(false);
  };

  // Document Upload & MarkItDown Parsing Handler
  const handleFileSelect = async (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setIsUploading(true);
    setUploadError(null);

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const parsed: ParsedFile = await api.uploadAndParseFile(file);
        setAttachedFiles((prev) => [...prev, parsed]);
      }
    } catch (err: any) {
      setUploadError(err.message || 'Error al procesar el archivo con MarkItDown');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  // Drag and Drop over Chat Area
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDraggingOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDraggingOver(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDraggingOver(false);
    const files = e.dataTransfer.files;
    if (!files || files.length === 0) return;

    setIsUploading(true);
    setUploadError(null);

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const parsed: ParsedFile = await api.uploadAndParseFile(file);
        setAttachedFiles((prev) => [...prev, parsed]);
      }
    } catch (err: any) {
      setUploadError(err.message || 'Error al procesar el archivo con MarkItDown');
    } finally {
      setIsUploading(false);
    }
  };

  const handleRemoveAttachedFile = (id: string) => {
    setAttachedFiles((prev) => prev.filter((f) => f.id !== id));
  };

  // Quick Action Prompts for Lawyers
  const handleQuickAction = (type: 'clauses' | 'summary' | 'verify', file: ParsedFile) => {
    if (type === 'clauses') {
      setInput(
        `Analiza este documento (${file.filename}) e identifica cláusulas de riesgo, penalidades, prórrogas automáticas, ambigüedades y recomendaciones de blindaje jurídico según la ley colombiana:`
      );
    } else if (type === 'summary') {
      setInput(
        `Elabora un resumen procesal ejecutivo estructurado de este documento (${file.filename}) destacando: Partes procesales, Hechos jurídicos relevantes, Pretensiones, Términos y Cuantía estimada:`
      );
    } else if (type === 'verify') {
      setInput(
        `Coteja las normas, artículos y jurisprudencia citada en este documento (${file.filename}). Verifica si las normas están vigentes en Colombia y si existen sentencias de unificación o precedentes contrarios:`
      );
    }
    textareaRef.current?.focus();
  };

  const handleSubmit = async (e?: FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = input.trim();
    if ((!trimmed && attachedFiles.length === 0) || loading || isUploading) return;

    let displayContent = trimmed;
    let payloadContent = trimmed;

    // If documents are attached, format with MarkItDown optimized block
    if (attachedFiles.length > 0) {
      const docBlocks = attachedFiles.map(
        (f) =>
          `[DOCUMENTO ADJUNTO - CONVERTIDO VÍA MARKITDOWN]\nNombre: ${f.filename}\nTipo: ${f.analysis.doc_type}\nJurisdicción: ${f.analysis.jurisdiction}\n\n${f.markdown}\n---`
      ).join('\n\n');

      payloadContent = `${docBlocks}\n\nConsulta del litigante: ${trimmed || 'Por favor analiza este documento adjunto.'}`;
      if (!displayContent) {
        displayContent = `Analizar documento adjunto (${attachedFiles.map((f) => f.filename).join(', ')})`;
      }
    }

    const userMessage: MessageType = {
      id: generateUUID(),
      role: 'user',
      content: displayContent,
      timestamp: Date.now(),
      attachedFiles: attachedFiles.length > 0 ? [...attachedFiles] : undefined,
    };

    setAttachedFiles([]);

    const isFirstMessage = conversation.messages.length === 0;
    const derivedTitle = isFirstMessage
      ? displayContent.slice(0, 42) + (displayContent.length > 42 ? '...' : '')
      : conversation.title;

    const assistantMsgId = generateUUID();
    const assistantPlaceholder: MessageType = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
    };

    let currentConversation: Conversation = {
      ...conversation,
      title: derivedTitle,
      messages: [...conversation.messages, userMessage, assistantPlaceholder],
      updated_at: Date.now(),
    };
    onUpdateConversation(currentConversation);

    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
    setLoading(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    let accumulatedText = '';

    try {
      const contextBlock = buildContextBlock({
        agent: activeAgent,
        memories,
        memoriesEnabled,
        specialization: conversation.specialization,
      });

      const apiMessages: Array<{ role: 'user' | 'assistant'; content: string }> = [
        ...conversation.messages.map((m) => ({ role: m.role, content: m.content })),
        {
          role: 'user',
          content: contextBlock ? `${contextBlock}\n\n${payloadContent}` : payloadContent,
        },
      ];

      await api.streamMessage(
        {
          model: selectedModelId,
          messages: apiMessages,
        },
        (token: string) => {
          accumulatedText += token;
          currentConversation = {
            ...currentConversation,
            messages: currentConversation.messages.map((m) =>
              m.id === assistantMsgId ? { ...m, content: accumulatedText } : m
            ),
            updated_at: Date.now(),
          };
          onUpdateConversation(currentConversation);
        },
        controller.signal
      );

    } catch (err: any) {
      if (err.name === 'AbortError') {
        // User manually stopped streaming
      } else {
        const errorText = accumulatedText
          ? `${accumulatedText}\n\n*[Respuesta interrumpida: ${err.message || 'error de conexión'}]*`
          : `No se pudo procesar la consulta: ${err?.message || 'error de conexión con el motor legal'}`;
        currentConversation = {
          ...currentConversation,
          messages: currentConversation.messages.map((m) =>
            m.id === assistantMsgId ? { ...m, content: errorText } : m
          ),
          updated_at: Date.now(),
        };
        onUpdateConversation(currentConversation);
      }
    } finally {
      setLoading(false);
      abortControllerRef.current = null;
    }
  };

  const handleRegenerate = async () => {
    if (loading || conversation.messages.length < 2) return;
    const lastUserIdx = [...conversation.messages].reverse().findIndex((m) => m.role === 'user');
    if (lastUserIdx === -1) return;
    const actualIdx = conversation.messages.length - 1 - lastUserIdx;
    const lastUserMessage = conversation.messages[actualIdx];

    // Remove the last assistant message
    const trimmedMessages = conversation.messages.slice(0, actualIdx + 1);
    const assistantMsgId = generateUUID();
    const assistantPlaceholder: MessageType = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
    };

    let currentConversation: Conversation = {
      ...conversation,
      messages: [...trimmedMessages, assistantPlaceholder],
      updated_at: Date.now(),
    };
    onUpdateConversation(currentConversation);
    setLoading(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;
    let accumulatedText = '';

    try {
      const contextBlock = buildContextBlock({
        agent: activeAgent,
        memories,
        memoriesEnabled,
        specialization: conversation.specialization,
      });

      const apiMessages: Array<{ role: 'user' | 'assistant'; content: string }> = [
        ...trimmedMessages.slice(0, -1).map((m) => ({ role: m.role, content: m.content })),
        {
          role: 'user',
          content: contextBlock ? `${contextBlock}\n\n${lastUserMessage.content}` : lastUserMessage.content,
        },
      ];

      await api.streamMessage(
        {
          model: selectedModelId,
          messages: apiMessages,
        },
        (token: string) => {
          accumulatedText += token;
          currentConversation = {
            ...currentConversation,
            messages: currentConversation.messages.map((m) =>
              m.id === assistantMsgId ? { ...m, content: accumulatedText } : m
            ),
            updated_at: Date.now(),
          };
          onUpdateConversation(currentConversation);
        },
        controller.signal
      );
    } catch (err: any) {
      if (err.name === 'AbortError') {
        // stopped
      } else {
        const errorText = accumulatedText
          ? `${accumulatedText}\n\n*[Respuesta interrumpida: ${err.message || 'error'}]*`
          : `No se pudo procesar la consulta: ${err?.message || 'error'}`;
        currentConversation = {
          ...currentConversation,
          messages: currentConversation.messages.map((m) =>
            m.id === assistantMsgId ? { ...m, content: errorText } : m
          ),
          updated_at: Date.now(),
        };
        onUpdateConversation(currentConversation);
      }
    } finally {
      setLoading(false);
      abortControllerRef.current = null;
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const isEmpty = conversation.messages.length === 0;

  return (
    <div
      className="chat-main"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Hidden File Input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileSelect}
        multiple
        accept=".pdf,.docx,.doc,.txt,.md,.rtf,.xlsx"
        style={{ display: 'none' }}
      />

      {/* Drag & Drop Overlay */}
      {isDraggingOver && (
        <div className="chat-drag-overlay">
          <div className="drag-overlay-icon">
            <PaperclipIcon size={24} />
          </div>
          <div className="drag-overlay-title">Suelta tus documentos jurídicos aquí</div>
          <div className="drag-overlay-subtitle">Conversión automática con MarkItDown (-75% tokens)</div>
        </div>
      )}

      {/* Top Bar with ModelSelector & Specialization */}
      <header className="chat-topbar">
        <div className="topbar-left">
          {sidebarCollapsed && (
            <button className="topbar-icon-btn" onClick={onOpenSidebar} title="Expandir panel lateral">
              <MenuIcon size={18} />
            </button>
          )}

          {/* Model Selector (Claude / GPT / Gemini / Grok) */}
          {onSelectModel && (
            <ModelSelector
              selectedModelId={selectedModelId}
              onSelectModel={onSelectModel}
            />
          )}

          <SpecializationMenu
            value={conversation.specialization}
            onChange={handleSpecializationChange}
          />

          {activeAgent && onOpenAgents && (
            <button className="topbar-chip-btn" onClick={onOpenAgents} title="Agente activo">
              <BotIcon size={14} />
              <span>{activeAgent.name}</span>
            </button>
          )}
        </div>
        <div className="topbar-right">
          {onNewChat && (
            <button className="topbar-icon-btn" onClick={onNewChat} title="Nueva conversación">
              <PlusIcon size={16} />
            </button>
          )}
          {onOpenPrompts && (
            <button className="topbar-icon-btn" onClick={onOpenPrompts} title="Biblioteca de prompts">
              <FileTextIcon size={16} />
            </button>
          )}
          {!isEmpty && (
            <button className="topbar-icon-btn" onClick={handleExport} title="Exportar conversación">
              <DownloadIcon size={16} />
            </button>
          )}
        </div>
      </header>

      {/* Main View Area */}
      <div className={`chat-scroll ${isEmpty ? 'chat-scroll-empty' : ''}`}>
        {isEmpty ? (
          <div className="empty-hero-container">
            <div className="empty-greeting-row">
              <div className="hero-avatar-wrapper">
                <LegaliaBotAvatar size={84} state="idle" interactive={true} glow={true} />
              </div>
              <h1 className="empty-greeting-title">{greetingText}</h1>
              <p className="empty-greeting-subtitle">
                Asistente jurídico inteligente especializado en derecho y jurisprudencia colombiana
              </p>
            </div>

            {/* Centered Composer Capsule */}
            <div className="centered-composer-wrapper">
              <form onSubmit={handleSubmit} className="composer-capsule">
                {/* Attached File Chips (LibreChat Style) */}
                <FileRow
                  files={attachedFiles}
                  onRemove={handleRemoveAttachedFile}
                  onQuickAction={handleQuickAction}
                />

                {/* Upload Status / Error */}
                {isUploading && (
                  <div className="uploading-banner">
                    <span className="mini-spinner" />
                    <span>Procesando con MarkItDown y optimizando tokens...</span>
                  </div>
                )}
                {uploadError && (
                  <div className="upload-error-banner">{uploadError}</div>
                )}

                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={`Mensaje o consulta a Legalia (${specialization?.name || 'General'})...`}
                  rows={1}
                  disabled={loading || isUploading}
                  className="capsule-textarea"
                />

                <div className="capsule-bottom-bar">
                  <div className="capsule-left-actions">
                    <AttachFileMenu
                      onSelectUpload={() => fileInputRef.current?.click()}
                      disabled={isUploading}
                    />
                    {onOpenPrompts && (
                      <button type="button" className="capsule-icon-btn" onClick={onOpenPrompts} title="Plantillas de prompts">
                        <FileTextIcon size={17} />
                      </button>
                    )}
                    <button type="button" className="capsule-icon-btn" title="Ajustes de búsqueda RAG">
                      <SlidersIcon size={17} />
                    </button>
                  </div>

                  <div className="capsule-right-actions">
                    <button type="button" className="capsule-icon-btn" title="Dictado por voz">
                      <MicIcon size={17} />
                    </button>
                    {loading ? (
                      <button
                        type="button"
                        onClick={handleStopGeneration}
                        className="capsule-stop-btn"
                        title="Detener generación"
                      >
                        <SquareIcon size={14} />
                      </button>
                    ) : (
                      <button
                        type="submit"
                        disabled={(!input.trim() && attachedFiles.length === 0) || isUploading}
                        className="capsule-send-btn"
                        title="Enviar mensaje"
                      >
                        <ArrowUpIcon size={17} />
                      </button>
                    )}
                  </div>
                </div>
              </form>
            </div>

            {/* Subtle Prompt Suggestions Grid */}
            <div className="welcome-prompt-grid">
              {EXAMPLE_PROMPTS.slice(0, 2).map((prompt: string) => (
                <button
                  key={prompt}
                  className="welcome-prompt-pill"
                  onClick={() => setInput(prompt)}
                >
                  <span>{prompt}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="message-list">
            {conversation.messages.map((message, idx) => (
              <div key={message.id}>
                {message.attachedFiles && message.attachedFiles.length > 0 && (
                  <div className="message-attached-file-badge">
                    <FileTextIcon size={14} />
                    <span>{message.attachedFiles[0].filename}</span>
                    <span className="badge-tag">
                      MarkItDown (-{message.attachedFiles[0].stats.token_reduction_pct}% tokens)
                    </span>
                  </div>
                )}
                <Message
                  message={message}
                  isStreaming={loading && idx === conversation.messages.length - 1 && message.role === 'assistant'}
                  onRegenerate={idx === conversation.messages.length - 1 && message.role === 'assistant' ? handleRegenerate : undefined}
                />
              </div>
            ))}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Sticky Bottom Composer for active conversations */}
      {!isEmpty && (
        <div className="chat-input-area">
          <form onSubmit={handleSubmit} className="input-shell-capsule">
            {/* Attached File Chips (LibreChat Style) */}
            <FileRow
              files={attachedFiles}
              onRemove={handleRemoveAttachedFile}
              onQuickAction={handleQuickAction}
            />

            {isUploading && (
              <div className="uploading-banner">
                <span className="mini-spinner" />
                <span>Procesando documento con MarkItDown...</span>
              </div>
            )}

            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Escribe tu consulta o pide un análisis del documento..."
              rows={1}
              disabled={loading || isUploading}
              className="input-textarea"
            />
            <div className="shell-bottom-bar">
              <div className="shell-left-actions">
                <AttachFileMenu
                  onSelectUpload={() => fileInputRef.current?.click()}
                  disabled={isUploading}
                />
                {onOpenPrompts && (
                  <button type="button" className="capsule-icon-btn" onClick={onOpenPrompts} title="Plantillas de prompts">
                    <FileTextIcon size={16} />
                  </button>
                )}
                <button type="button" className="capsule-icon-btn" title="Ajustes de búsqueda RAG">
                  <SlidersIcon size={16} />
                </button>
              </div>
              <div className="shell-right-actions">
                {loading ? (
                  <button
                    type="button"
                    onClick={handleStopGeneration}
                    className="capsule-stop-btn"
                    title="Detener generación"
                  >
                    <SquareIcon size={14} />
                  </button>
                ) : (
                  <button
                    type="submit"
                    disabled={(!input.trim() && attachedFiles.length === 0) || isUploading}
                    className="capsule-send-btn"
                    title="Enviar"
                  >
                    <ArrowUpIcon size={16} />
                  </button>
                )}
              </div>
            </div>
          </form>
          <div className="input-disclaimer">
            Legalia v0.1 · Principio: <strong>NO EVIDENCE → NO ANSWER</strong> · Telemetría en tiempo real.
          </div>
        </div>
      )}

      {/* Subtle Footer for Empty State */}
      {isEmpty && (
        <footer className="empty-bottom-footer">
          <span>Legalia v0.1 · IA jurídica con Claude Sonnet</span>
          <span>•</span>
          <a href="#" onClick={(e) => e.preventDefault()}>Política de privacidad</a>
          <span>•</span>
          <a href="#" onClick={(e) => e.preventDefault()}>Términos de servicio</a>
        </footer>
      )}
    </div>
  );
}
