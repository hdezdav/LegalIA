import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Message as MessageType } from '../types';
import { copyToClipboard } from '../utils';
import { getTranslations } from '../i18n';
import { UserIcon, CopyIcon, CheckIcon } from './Icons';
import { LegaliaBotAvatar } from './LegaliaBotAvatar';
import './Message.css';

const t = getTranslations('es');

interface MessageProps {
  message: MessageType;
}

export function Message({ message }: MessageProps) {
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
        {isUser ? <UserIcon size={15} /> : <LegaliaBotAvatar size={28} state="idle" interactive={true} />}
      </div>

      <div className="msg-body">
        <div className="msg-name">{isUser ? t.chat.you : t.chat.assistant}</div>

        <div className="msg-content">
          {isUser ? (
            <div className="msg-plain">{message.content}</div>
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
          )}
        </div>

        {message.metadata && (
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

        {!isUser && (
          <div className="msg-actions">
            <button className="msg-action-btn" onClick={handleCopy}>
              {copied ? <CheckIcon size={14} /> : <CopyIcon size={14} />}
              {copied ? t.chat.copied : t.chat.copy}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
