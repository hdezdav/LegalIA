import { ParsedFile } from '../../../types';
import { XIcon, FileTextIcon } from '../../Icons';
import './Files.css';

interface DocumentPreviewModalProps {
  file: ParsedFile | null;
  onClose: () => void;
}

export function DocumentPreviewModal({ file, onClose }: DocumentPreviewModalProps) {
  if (!file) return null;

  return (
    <div className="doc-modal-backdrop" onClick={onClose}>
      <div className="doc-modal-window" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="doc-modal-header">
          <div className="doc-modal-title-group">
            <span style={{ color: 'var(--link)', display: 'flex' }}>
              <FileTextIcon size={20} />
            </span>
            <div>
              <h3 className="doc-modal-filename">{file.filename}</h3>
              <div className="doc-modal-subtitle">
                <span>{file.analysis.doc_type}</span>
                <span>•</span>
                <span>{file.analysis.jurisdiction}</span>
                <span>•</span>
              </div>
            </div>
          </div>
          <button className="doc-modal-close-btn" onClick={onClose} title="Cerrar vista previa">
            <XIcon size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="doc-modal-body">
          {/* Metadata Cards */}
          <div className="doc-modal-meta-grid">
            {file.analysis.parties.demandante && (
              <div className="doc-meta-card">
                <div className="meta-card-label">Demandante / Accionante</div>
                <div className="meta-card-value">{file.analysis.parties.demandante}</div>
              </div>
            )}
            {file.analysis.parties.demandado && (
              <div className="doc-meta-card">
                <div className="meta-card-label">Demandado / Accionado</div>
                <div className="meta-card-value">{file.analysis.parties.demandado}</div>
              </div>
            )}
            {file.analysis.radicado && (
              <div className="doc-meta-card">
                <div className="meta-card-label">Radicado / Expediente</div>
                <div className="meta-card-value">{file.analysis.radicado}</div>
              </div>
            )}
            <div className="doc-meta-card">
              <div className="meta-card-label">Extensión del documento</div>
              <div className="meta-card-value">
                {file.stats.word_count} palabras
              </div>
            </div>
          </div>

          {/* Extracted Key Clauses */}
          {file.analysis.key_clauses && file.analysis.key_clauses.length > 0 && (
            <div className="doc-clauses-section">
              <h4 className="clauses-section-title">Cláusulas y Secciones Identificadas</h4>
              <div className="clauses-grid">
                {file.analysis.key_clauses.map((clause, i) => (
                  <div key={i} className="clause-item">
                    <span className="clause-tag">{clause.title}</span>
                    <p className="clause-snippet">{clause.summary}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Clean Markdown Content View */}
          <div className="doc-markdown-content-section">
            <h4 className="clauses-section-title">Contenido Estructurado (Markdown)</h4>
            <pre className="doc-markdown-pre">
              {file.markdown}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}
