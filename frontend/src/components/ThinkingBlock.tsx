import React, { useState, useEffect } from 'react';
import { LegaliaBotAvatar } from './LegaliaBotAvatar';
import './ThinkingBlock.css';

interface ThinkingBlockProps {
  modelName?: string;
  isGenerating?: boolean;
  thoughtContent?: string;
}

export const ThinkingBlock: React.FC<ThinkingBlockProps> = ({
  modelName,
  isGenerating = true,
  thoughtContent,
}) => {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    if (!isGenerating) return;

    // Tick once per second. The previous version ticked every 100ms purely to
    // render a fast-moving decimal, which is 10x the re-renders for no
    // information the reader can actually use.
    const timer = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(timer);
  }, [isGenerating]);

  const hasThought = Boolean(thoughtContent);

  return (
    <div
      className={`claude-thinking-container ${hasThought ? 'has-thought' : ''}`}
    >
      <div
        className="claude-thinking-header"
        onClick={() => hasThought && setIsExpanded(!isExpanded)}
      >
        <div className="thinking-avatar-cell">
          <LegaliaBotAvatar
            state={isGenerating ? 'thinking' : 'idle'}
            size={32}
          />
        </div>

        <div className="thinking-meta-info">
          <span className="thinking-bot-name">Legalia</span>
          {modelName && <span className="thinking-model-pill">{modelName}</span>}

          {isGenerating ? (
            <>
              <span className="thinking-dots" aria-hidden="true">
                <span />
                <span />
                <span />
              </span>
              <span className="thinking-elapsed">
                {elapsedSeconds > 0 ? `${elapsedSeconds}s` : ''}
              </span>
            </>
          ) : (
            <span className="thinking-elapsed">
              Respondió en {elapsedSeconds}s
            </span>
          )}
        </div>

        {hasThought && (
          <button
            type="button"
            className="thinking-toggle-btn"
            aria-expanded={isExpanded}
            title={isExpanded ? 'Ocultar razonamiento' : 'Ver razonamiento'}
          >
            <svg
              className={`thinking-chevron ${isExpanded ? 'expanded' : ''}`}
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </button>
        )}
      </div>

      {hasThought && isExpanded && (
        <div className="claude-thought-content">
          <div className="thought-inner-box">
            <div className="thought-tag">Razonamiento del modelo</div>
            <p>{thoughtContent}</p>
          </div>
        </div>
      )}
    </div>
  );
};
