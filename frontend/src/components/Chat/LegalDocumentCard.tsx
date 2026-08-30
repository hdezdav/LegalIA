import { useState } from 'react';
import { exportToWord, exportToPdf } from '../../utils/documentExport';
import { copyToClipboard } from '../../utils';
import { FileTextIcon, DownloadIcon, CopyIcon, CheckIcon } from '../Icons';
import './LegalDocumentCard.css';

interface LegalDocumentCardProps {
  title: string;
  type?: string;
  content: string;
}

export function LegalDocumentCard({ title, type = 'documento', content }: LegalDocumentCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const wordCount = content.trim().split(/\s+/).filter(Boolean).length;

  const handleCopy = async () => {
    const ok = await copyToClipboard(content);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const cleanTitle = title
    .replace(/^#+\s*/, '')
    .replace(/\*\*/g, '')
    .trim() || 'Documento Judicial';

  const getDocTypeBadge = (t: string) => {
    const lower = t.toLowerCase();
    if (lower.includes('contrat') || lower.includes('arrend') || lower.includes('laboral') || lower.includes('servici')) {
      return { label: 'Minuta Contractual', color: 'badge-contract' };
    }
    if (lower.includes('tutela')) {
      return { label: 'Acción Constitucional', color: 'badge-tutela' };
    }
    if (lower.includes('peticion') || lower.includes('derecho')) {
      return { label: 'Derecho de Petición', color: 'badge-peticion' };
    }
    if (lower.includes('demanda') || lower.includes('poder') || lower.includes('memorial') || lower.includes('recurso')) {
      return { label: 'Escrito Judicial', color: 'badge-judicial' };
    }
    return { label: 'Documento Oficial', color: 'badge-general' };
  };

  const badgeInfo = getDocTypeBadge(type || title);

  return (
    <div className="apple-legal-doc-card">
      <div className="doc-card-main-row">
        <div className="doc-card-icon-tile">
          <FileTextIcon size={22} className="doc-tile-icon" />
          <span className="doc-tile-ext">DOCX</span>
        </div>

        <div className="doc-card-info">
          <div className="doc-card-title-line">
            <h4 className="doc-card-heading" title={cleanTitle}>{cleanTitle}</h4>
            <span className={`doc-card-badge ${badgeInfo.color}`}>{badgeInfo.label}</span>
          </div>
          <div className="doc-card-meta-line">
            <span>Estándar Judicial Colombiano</span>
            <span>•</span>
            <span>{wordCount} palabras</span>
            <span>•</span>
            <span>Editable en Word / PDF</span>
          </div>
        </div>
      </div>

      <div className="doc-card-toolbar">
        <div className="doc-card-primary-actions">
          <button
            type="button"
            className="doc-action-btn doc-btn-primary"
            onClick={() => exportToWord(cleanTitle, content)}
            title="Descargar en formato Microsoft Word (.docx)"
          >
            <DownloadIcon size={14} />
            <span>Descargar Word</span>
          </button>

          <button
            type="button"
            className="doc-action-btn doc-btn-secondary"
            onClick={() => exportToPdf(cleanTitle, content)}
            title="Imprimir o guardar como PDF"
          >
            <FileTextIcon size={14} />
            <span>PDF / Imprimir</span>
          </button>

          <button
            type="button"
            className="doc-action-btn doc-btn-ghost"
            onClick={handleCopy}
            title="Copiar texto completo"
          >
            {copied ? <CheckIcon size={14} /> : <CopyIcon size={14} />}
            <span>{copied ? 'Copiado' : 'Copiar'}</span>
          </button>
        </div>

        <button
          type="button"
          className={`doc-action-btn doc-btn-toggle ${expanded ? 'active' : ''}`}
          onClick={() => setExpanded((curr) => !curr)}
          aria-expanded={expanded}
          title={expanded ? 'Ocultar vista previa' : 'Ver documento completo'}
        >
          <span>{expanded ? 'Ocultar vista previa' : 'Vista previa'}</span>
          <span className="doc-toggle-arrow" aria-hidden="true">{expanded ? '▴' : '▾'}</span>
        </button>
      </div>

      {expanded && (
        <div className="doc-card-preview-container">
          <div className="doc-card-sheet">
            <pre className="doc-sheet-text">{content}</pre>
          </div>
        </div>
      )}
    </div>
  );
}
