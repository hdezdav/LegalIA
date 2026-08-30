import React, { useEffect } from 'react';
import { ExternalLinkIcon, CopyIcon, CheckIcon, FileTextIcon, ShieldCheckIcon } from '../Icons';
import { SourceItem } from './SourcesRail';
import './CitationInspectorModal.css';

interface CitationInspectorModalProps {
  source: SourceItem | null;
  isOpen: boolean;
  onClose: () => void;
}

export function CitationInspectorModal({ source, isOpen, onClose }: CitationInspectorModalProps) {
  const [copied, setCopied] = React.useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !source) return null;

  const handleCopyCitation = async () => {
    const textToCopy = source.snippet
      ? `"${source.snippet}" — ${source.title} (${source.domain})`
      : `${source.title} — Consultado en LegalIA (${source.url})`;
    
    if (navigator.clipboard) {
      await navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="citation-modal-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div 
        className="citation-modal-sheet"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="citation-modal-handle" />
        
        <div className="citation-modal-header">
          <div className="citation-header-left">
            <div className="citation-icon-chip">
              <FileTextIcon size={16} />
            </div>
            <div className="citation-title-group">
              <span className="citation-tag">
                <ShieldCheckIcon size={12} />
                Fuente Jurídica Verificada
              </span>
              <h3 className="citation-title">{source.title}</h3>
              <span className="citation-domain">{source.domain}</span>
            </div>
          </div>
          <button 
            type="button" 
            className="citation-close-btn" 
            onClick={onClose}
            aria-label="Cerrar visor"
          >
            ✕
          </button>
        </div>

        <div className="citation-modal-body">
          {source.snippet ? (
            <div className="citation-excerpt-container">
              <span className="citation-section-label">Fragmento Normativo Respaldo</span>
              <blockquote className="citation-quote">
                {source.snippet}
              </blockquote>
            </div>
          ) : (
            <div className="citation-empty-excerpt">
              <p>Referencia normativa consultada directamente en el corpus oficial de jurisprudencia y legislación colombiana.</p>
            </div>
          )}
        </div>

        <div className="citation-modal-footer">
          <button 
            type="button" 
            className="citation-action-btn citation-copy-btn" 
            onClick={handleCopyCitation}
          >
            {copied ? <CheckIcon size={14} /> : <CopyIcon size={14} />}
            <span>{copied ? 'Cita Copiada' : 'Copiar Cita'}</span>
          </button>

          {source.url && (
            <a 
              href={source.url} 
              target="_blank" 
              rel="noopener noreferrer" 
              className="citation-action-btn citation-primary-btn"
            >
              <span>Consultar en Fuente Oficial</span>
              <ExternalLinkIcon size={14} />
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
