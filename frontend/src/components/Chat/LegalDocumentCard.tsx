import { useState } from 'react';
import { exportToWord, exportToPdf, exportToMarkdown } from '../../utils/documentExport';
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
    return { label: 'Documento Jurídico', color: 'badge-general' };
  };

  const badgeInfo = getDocTypeBadge(type || title);

  return (
    <div className="legal-doc-card">
      <div className="legal-doc-header">
        <div className="legal-doc-icon-wrap">
          <FileTextIcon size={22} className="legal-doc-icon" />
        </div>
        <div className="legal-doc-meta">
          <div className="legal-doc-title-row">
            <h4 className="legal-doc-title">{title}</h4>
            <span className={`legal-doc-type-badge ${badgeInfo.color}`}>{badgeInfo.label}</span>
          </div>
          <p className="legal-doc-subtitle">
            Listo para descargar y diligenciar · {wordCount} palabras · Estándar legal colombiano
          </p>
        </div>
      </div>

      {/* Action Buttons Toolbar */}
      <div className="legal-doc-actions">
        <button
          type="button"
          className="legal-doc-btn legal-doc-btn-word"
          onClick={() => exportToWord(title, content)}
          title="Descargar en formato Microsoft Word (.doc / .docx)"
        >
          <DownloadIcon size={14} />
          <span>Descargar Word (.docx)</span>
        </button>

        <button
          type="button"
          className="legal-doc-btn legal-doc-btn-pdf"
          onClick={() => exportToPdf(title, content)}
          title="Imprimir o guardar en formato PDF"
        >
          <FileTextIcon size={14} />
          <span>Imprimir / PDF</span>
        </button>

        <button
          type="button"
          className="legal-doc-btn legal-doc-btn-secondary"
          onClick={() => exportToMarkdown(title, content)}
          title="Descargar en formato Markdown (.md)"
        >
          <DownloadIcon size={14} />
          <span>Markdown (.md)</span>
        </button>

        <button
          type="button"
          className="legal-doc-btn legal-doc-btn-secondary"
          onClick={handleCopy}
          title="Copiar texto completo al portapapeles"
        >
          {copied ? <CheckIcon size={14} /> : <CopyIcon size={14} />}
          <span>{copied ? 'Copiado' : 'Copiar texto'}</span>
        </button>

        <button
          type="button"
          className="legal-doc-btn legal-doc-btn-toggle"
          onClick={() => setExpanded(!expanded)}
          title={expanded ? 'Colapsar vista previa' : 'Ver documento completo'}
        >
          <span>{expanded ? '▲ Ocultar vista previa' : '▼ Ver vista previa'}</span>
        </button>
      </div>

      {/* Expandable Document Preview */}
      {expanded && (
        <div className="legal-doc-preview-body">
          <div className="legal-doc-preview-content">
            <pre className="legal-doc-pre">{content}</pre>
          </div>
        </div>
      )}
    </div>
  );
}
