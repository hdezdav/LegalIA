import { useState, useMemo, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Message as MessageType } from '../types';
import { copyToClipboard } from '../utils';
import { exportToWord, exportToPdf } from '../utils/documentExport';
import { getTranslations } from '../i18n';
import { UserIcon, CopyIcon, CheckIcon, RefreshIcon, SparklesIcon, DownloadIcon, FileTextIcon } from './Icons';
import { LegaliaBotAvatar } from './LegaliaBotAvatar';
import { LegalDocumentCard } from './Chat/LegalDocumentCard';
import { InteractiveOptionsCard, parseOptionsMarkdown } from './Chat/InteractiveOptionsCard';
import { parseFormMarkdown } from './Chat/InteractiveFormCard';
import type { FormField } from './Chat/InteractiveFormCard';
import { SourcesRail } from './Chat/SourcesRail';
import './Message.css';

const t = getTranslations('es');

interface MessageProps {
  message: MessageType;
  isStreaming?: boolean;
  onRegenerate?: () => void;
  onSendMessage?: (text: string) => void;
  onFormReady?: (messageId: string, form: { title: string; description?: string; fields: FormField[] }, contentKey: string) => void;
}

function CodeBlock({ inline, className, children, onSendMessage, isStreaming, ...props }: any) {
  const [copied, setCopied] = useState(false);
  const match = /language-([\w-]+)/.exec(className || '');
  const language = match ? match[1].toLowerCase() : '';
  const codeContent = String(children).replace(/\n$/, '');
  const isOptionsBlock = !inline && (
    language.includes('interactive-options') ||
    language.includes('options') ||
    language.includes('opciones') ||
    language.includes('preguntas')
  );
  const isFormBlock = !inline && (
    language.includes('legal-form') ||
    language.includes('form') ||
    language.includes('formulario') ||
    language.includes('intake')
  );
  const parsedOptions = isOptionsBlock ? parseOptionsMarkdown(codeContent) : null;

  if (inline || !match) {
    return (
      <code className={`inline-code ${className || ''}`} {...props}>
        {children}
      </code>
    );
  }

  // Interactive choices remain attached to the assistant response.
  if (isOptionsBlock) {
    if (isStreaming || !parsedOptions?.options.length) return null;
    return (
      <InteractiveOptionsCard
        title={parsedOptions.title}
        options={parsedOptions.options}
        onSelectOption={(text) => onSendMessage?.(text)}
      />
    );
  }

  // Forms are published to Chat after the complete assistant message arrives.
  if (isFormBlock) {
    return null;
  }

  // 3. Detect legal document code blocks
  const isLegalDoc =
    language.includes('legal-document') ||
    language.includes('document') ||
    language.includes('minuta') ||
    language.includes('contrato') ||
    language.includes('tutela') ||
    language.includes('demanda') ||
    language.includes('peticion') ||
    language === 'doc';

  if (isLegalDoc) {
    let title = 'Documento Jurídico';
    const lines = codeContent.split('\n');
    for (const line of lines) {
      const clean = line.replace(/^[#\*\s\-]+|[#\*\s\-]+$/g, '').trim();
      if (clean && clean.length > 5 && clean.length < 90) {
        title = clean;
        break;
      }
    }
    return <LegalDocumentCard title={title} type={language} content={codeContent} />;
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

export function Message({ message, isStreaming = false, onRegenerate, onSendMessage, onFormReady }: MessageProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    const ok = await copyToClipboard(message.content);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const isUser = message.role === 'user';
  const isThinking = !isUser && isStreaming && !message.content.trim();

  useEffect(() => {
    if (isUser || isStreaming || !message.content.trim()) return;
    const formMatch = message.content.match(/```(?:legal-form|formulario|intake|form)\s*\n([\s\S]*?)```/i);
    if (!formMatch) return;
    const parsed = parseFormMarkdown(formMatch[1]);
    if (parsed.fields.length) onFormReady?.(message.id, parsed, formMatch[1].trim());
  }, [isUser, isStreaming, message.id, message.content, onFormReady]);

  // Detect if full assistant message is a drafted legal document
  const isDraftedLegalDoc = useMemo(() => {
    if (isUser || !message.content) return false;
    const upper = message.content.toUpperCase();
    const matchesKeyword =
      upper.includes('CONTRATO DE') ||
      upper.includes('DERECHO DE PETICIÓN') ||
      upper.includes('DERECHO DE PETICION') ||
      upper.includes('ACCIÓN DE TUTELA') ||
      upper.includes('ACCION DE TUTELA') ||
      upper.includes('SEÑOR JUEZ') ||
      upper.includes('MINUTA') ||
      upper.includes('PODER ESPECIAL') ||
      upper.includes('MEMORIAL DE') ||
      upper.includes('CLÁUSULA PRIMERA') ||
      upper.includes('CLAUSULA PRIMERA');

    const hasStructure = message.content.length > 250;
    return matchesKeyword && hasStructure;
  }, [isUser, message.content]);

  // Extract a document title from message
  const docTitle = useMemo(() => {
    if (!isDraftedLegalDoc) return 'Documento Legal';
    const lines = message.content.split('\n');
    for (const l of lines) {
      const clean = l.replace(/^[#\*\s\-]+|[#\*\s\-]+$/g, '').trim();
      if (clean && clean.length > 6 && clean.length < 100) {
        return clean;
      }
    }
    return 'Documento Jurídico Legalia';
  }, [isDraftedLegalDoc, message.content]);

  return (
    <div className={`msg-row ${isUser ? 'msg-row-user' : 'msg-row-assistant'}`}>
      <div className={`msg-avatar ${isUser ? 'msg-avatar-user' : 'msg-avatar-assistant'}`}>
        {isUser ? (
          <UserIcon size={15} />
        ) : (
          <LegaliaBotAvatar
            size={28}
            state={isStreaming ? (isThinking ? 'thinking' : 'answering') : 'idle'}
            interactive={true}
          />
        )}
      </div>

      <div className="msg-body">
        <div className="msg-header-row">
          <span className="msg-name">{isUser ? t.chat.you : t.chat.assistant}</span>
        </div>

        <div className="msg-content">
          {isUser ? (
            <div className="msg-plain">{message.content}</div>
          ) : isThinking ? (
            <div className="librechat-thinking-indicator">
              <SparklesIcon size={14} className="thinking-spark-icon" />
              <span className="thinking-text">Pensando...</span>
              <span className="thinking-dots">
                <span />
                <span />
                <span />
              </span>
            </div>
          ) : (
            <>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                   code: (props) => (
                     <CodeBlock
                       {...props}
                       onSendMessage={onSendMessage}
                       isStreaming={isStreaming}
                     />
                   ),
                   a: ({ href, children, ...props }) => {
                     const isCitation = typeof children === 'string' && /^\[?\d+\]?$/.test(children.trim());
                     return (
                       <a
                         href={href}
                         target="_blank"
                         rel="noopener noreferrer"
                         className={isCitation ? 'inline-citation-badge' : 'markdown-link'}
                         {...props}
                       >
                         {children}
                       </a>
                     );
                   },
                }}
              >
                {message.content}
              </ReactMarkdown>
              {isStreaming && <span className="librechat-cursor" />}
              {!isStreaming && <SourcesRail markdown={message.content} metadataCitations={message.metadata?.citations} />}
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
            {isDraftedLegalDoc && (
              <>
                <button
                  type="button"
                  className="msg-action-btn msg-action-btn-primary"
                  onClick={() => exportToWord(docTitle, message.content)}
                  title="Descargar documento en Microsoft Word (.docx)"
                >
                  <DownloadIcon size={13} />
                  <span>Descargar Word (.docx)</span>
                </button>

                <button
                  type="button"
                  className="msg-action-btn"
                  onClick={() => exportToPdf(docTitle, message.content)}
                  title="Imprimir o guardar como PDF"
                >
                  <FileTextIcon size={13} />
                  <span>PDF / Imprimir</span>
                </button>
              </>
            )}

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
