import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Message as MessageType } from '../types';
import { copyToClipboard } from '../utils';
import { getTranslations } from '../i18n';
import { UserIcon, CopyIcon, CheckIcon, RefreshIcon } from './Icons';
import { LegaliaBotAvatar } from './LegaliaBotAvatar';
import './Message.css';

const t = getTranslations('es');

interface MessageProps {
  message: MessageType;
  isStreaming?: boolean;
  onRegenerate?: () => void;
}

function CodeBlock({ inline, className, children, ...props }: any) {
  const [copied, setCopied] = useState(false);
  const match = /language-(\w+)/.exec(className || '');
  const language = match ? match[1] : '';
  const codeContent = String(children).replace(/\n$/, '');

  if (inline || !match) {
    return (
      <code className={`inline-code ${className || ''}`} {...props}>
        {children}
      </code>
    );
  }

  const handleCopyCode = async () => {
    await copyToClipboard(codeContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="librechat-code-block">
      <div className="code-block-header">
        <span className="code-lang-tag">{language}</span>
        <button type="button" className="code-copy-btn" onClick={handleCopyCode}>
          {copied ? (
            <>
              <CheckIcon size={12} />
              <span>Copiado</span>
            </>
          ) : (
            <>
              <CopyIcon size={12} />
              <span>Copiar código</span>
            </>
          )}
        </button>
      </div>
      <pre className="code-pre">
        <code className={className} {...props}>
          {children}
        </code>
      </pre>
    </div>
  );
}

export function Message({ message, isStreaming = false, onRegenerate }: MessageProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    const ok = await copyToClipboard(message.content);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const isUser = message.role === 'user';

  return (
    <div className={`msg-row ${isUser ? 'msg-row-user' : 'msg-row-assistant'}`}>
      <div className={`msg-avatar ${isUser ? 'msg-avatar-user' : 'msg-avatar-assistant'}`}>
        {isUser ? (
          <UserIcon size={15} />
        ) : (
          <LegaliaBotAvatar size={28} state={isStreaming ? 'answering' : 'idle'} interactive={true} />
        )}
      </div>

      <div className="msg-body">
        <div className="msg-header-row">
          <span className="msg-name">{isUser ? t.chat.you : t.chat.assistant}</span>
          {isStreaming && <span className="msg-streaming-badge">Generando...</span>}
        </div>

        <div className="msg-content">
          {isUser ? (
            <div className="msg-plain">{message.content}</div>
          ) : (
            <>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code: CodeBlock,
                }}
              >
                {message.content}
              </ReactMarkdown>
              {isStreaming && <span className="streaming-cursor">▊</span>}
            </>
          )}
        </div>

        {message.metadata && !isStreaming && (
          <div className="msg-metadata">
            {message.metadata.verification_status && (
              <span
                className={`badge ${
                  message.metadata.refused_for_lack_of_evidence ? 'badge-warn' : 'badge-ok'
                }`}
              >
                {message.metadata.refused_for_lack_of_evidence
                  ? t.evidence.noEvidence
                  : t.evidence.verified}
              </span>
            )}

            {message.metadata.context_chunk_count !== undefined && (
              <span className="badge badge-neutral">
                {message.metadata.context_chunk_count} {t.evidence.fragments}
              </span>
            )}

            {message.metadata.reranked && (
              <span className="badge badge-muted">{t.evidence.reranked}</span>
            )}
          </div>
        )}

        {!isUser && !isStreaming && (
          <div className="msg-actions">
            <button className="msg-action-btn" onClick={handleCopy} title="Copiar mensaje">
              {copied ? <CheckIcon size={13} /> : <CopyIcon size={13} />}
              <span>{copied ? t.chat.copied : t.chat.copy}</span>
            </button>
            {onRegenerate && (
              <button className="msg-action-btn" onClick={onRegenerate} title="Regenerar respuesta">
                <RefreshIcon size={13} />
                <span>Regenerar</span>
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
