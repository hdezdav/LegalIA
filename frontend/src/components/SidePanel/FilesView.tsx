import { useState, useRef, ChangeEvent } from 'react';
import { ParsedFile } from '../../types';
import { api } from '../../api';
import { PaperclipIcon, PlusIcon, TrashIcon, FileTextIcon, SparklesIcon } from '../Icons';
import { DocumentPreviewModal } from '../Chat/Files/DocumentPreviewModal';

interface FilesViewProps {
  files: ParsedFile[];
  onAddFile: (file: ParsedFile) => void;
  onDeleteFile: (id: string) => void;
  onInsertToChat: (file: ParsedFile) => void;
}

export function FilesView({
  files,
  onAddFile,
  onDeleteFile,
  onInsertToChat,
}: FilesViewProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewFile, setPreviewFile] = useState<ParsedFile | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (e: ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files;
    if (!selectedFiles || selectedFiles.length === 0) return;

    setIsUploading(true);
    setError(null);

    try {
      for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i];
        const parsed: ParsedFile = await api.uploadAndParseFile(file);
        onAddFile(parsed);
      }
    } catch (err: any) {
      setError(err.message || 'No se pudo procesar el archivo. Intenta de nuevo.');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    const droppedFiles = e.dataTransfer.files;
    if (!droppedFiles || droppedFiles.length === 0) return;

    setIsUploading(true);
    setError(null);

    try {
      for (let i = 0; i < droppedFiles.length; i++) {
        const file = droppedFiles[i];
        const parsed: ParsedFile = await api.uploadAndParseFile(file);
        onAddFile(parsed);
      }
    } catch (err: any) {
      setError(err.message || 'Error al procesar archivo');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="sidepanel-content">
      {/* Document Preview Modal */}
      <DocumentPreviewModal
        file={previewFile}
        onClose={() => setPreviewFile(null)}
      />

      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        multiple
        accept=".pdf,.docx,.doc,.txt,.md,.rtf,.xlsx"
        style={{ display: 'none' }}
      />

      <div className="sidepanel-header-row">
        <h3 className="sidepanel-view-title">Archivos y Anexos</h3>
        <button
          className="sidepanel-square-btn"
          onClick={() => fileInputRef.current?.click()}
          title="Subir archivo jurídico"
          disabled={isUploading}
        >
          <PlusIcon size={16} />
        </button>
      </div>

      <div className="sidepanel-body-scroll">
        {/* Drag and Drop Zone */}
        <div
          className="dashed-drop-card"
          style={{ cursor: 'pointer' }}
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
        >
          <PaperclipIcon size={20} className="dashed-card-icon" />
          <div className="dashed-card-title">
            {isUploading ? 'Preparando archivo…' : 'Arrastra o selecciona archivos'}
          </div>
          <div className="dashed-card-desc">
            PDF, DOCX, sentencias o contratos. Puedes revisar el contenido antes de usarlo en una consulta.
          </div>
        </div>

        {error && <div className="upload-error-banner">{error}</div>}

        {/* Files List */}
        {files.length > 0 && (
          <div className="sidepanel-items-stack" style={{ marginTop: '0.75rem' }}>
            {files.map((file) => (
              <div
                key={file.id}
                className="sidepanel-prompt-card"
                onClick={() => setPreviewFile(file)}
                style={{ cursor: 'pointer' }}
              >
                <div className="prompt-card-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <span style={{ color: 'var(--link)', display: 'flex' }}>
                      <FileTextIcon size={16} />
                    </span>
                    <span className="prompt-title">{file.filename}</span>
                  </div>
                  <button
                    className="prompt-icon-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteFile(file.id);
                    }}
                    title="Eliminar archivo"
                  >
                    <TrashIcon size={14} />
                  </button>
                </div>

                <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', margin: '0.25rem 0' }}>
                  <span className="prompt-cat-badge">{file.analysis.doc_type}</span>
                </div>

                {file.analysis.parties.demandante && (
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                    <strong>Pte:</strong> {file.analysis.parties.demandante}
                  </div>
                )}
                {file.analysis.parties.demandado && (
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                    <strong>Pda:</strong> {file.analysis.parties.demandado}
                  </div>
                )}

                <div className="prompt-card-footer" style={{ marginTop: '0.4rem' }}>
                  <span style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>
                    {file.stats.word_count} palabras
                  </span>
                  <button
                    className="btn-use-prompt"
                    onClick={(e) => {
                      e.stopPropagation();
                      onInsertToChat(file);
                    }}
                    title="Enviar a la consulta actual"
                  >
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                      <SparklesIcon size={12} />
                      <span>Usar en chat</span>
                    </span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
