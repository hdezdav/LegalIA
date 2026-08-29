import { useState } from 'react';
import { ParsedFile } from '../../../types';
import { XIcon, SparklesIcon, FileTextIcon } from '../../Icons';
import { DocumentPreviewModal } from './DocumentPreviewModal';
import './Files.css';

interface FileRowProps {
  files: ParsedFile[];
  onRemove: (id: string) => void;
  onQuickAction: (action: 'clauses' | 'summary' | 'verify', file: ParsedFile) => void;
}

export function FileRow({ files, onRemove, onQuickAction }: FileRowProps) {
  const [previewFile, setPreviewFile] = useState<ParsedFile | null>(null);

  if (!files || files.length === 0) {
    return null;
  }

  const getExt = (filename: string): string => {
    const parts = filename.split('.');
    if (parts.length > 1) {
      return parts[parts.length - 1].toLowerCase().slice(0, 4);
    }
    return 'doc';
  };

  return (
    <div style={{ width: '100%' }}>
      {/* Document Preview Modal */}
      <DocumentPreviewModal
        file={previewFile}
        onClose={() => setPreviewFile(null)}
      />

      {/* File Chips Container */}
      <div className="librechat-file-row">
        {files.map((file) => {
          const ext = getExt(file.filename);
          return (
            <div
              key={file.id}
              className="librechat-file-chip"
              onClick={() => setPreviewFile(file)}
              style={{ cursor: 'pointer' }}
              title="Haz clic para ver vista previa y análisis procesal"
            >
              <div className={`file-badge-icon ${ext}`}>
                {ext}
              </div>

              <div className="file-chip-details">
                <div className="file-chip-title" title={file.filename}>
                  {file.filename}
                </div>
                <div className="file-chip-meta">
                  <span className="file-chip-type-tag">
                    {file.analysis.doc_type}
                  </span>
                </div>
              </div>

              <button
                type="button"
                className="file-chip-close-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  onRemove(file.id);
                }}
                title="Remover archivo"
              >
                <XIcon size={12} />
              </button>
            </div>
          );
        })}
      </div>

      {/* Lawyer Quick Actions Tray */}
      <div className="file-lawyer-actions-tray">
        <button
          type="button"
          className="lawyer-action-pill"
          onClick={() => onQuickAction('clauses', files[0])}
        >
          <SparklesIcon size={12} />
          <span>Analizar Cláusulas y Riesgos</span>
        </button>
        <button
          type="button"
          className="lawyer-action-pill"
          onClick={() => onQuickAction('summary', files[0])}
        >
          <FileTextIcon size={12} />
          <span>Resumen Procesal Ejecutivo</span>
        </button>
        <button
          type="button"
          className="lawyer-action-pill"
          onClick={() => onQuickAction('verify', files[0])}
        >
          <span>Cotejar precedente y normas</span>
        </button>
      </div>
    </div>
  );
}
