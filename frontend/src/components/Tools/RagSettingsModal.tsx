import { useState } from 'react';
import { SlidersIcon, CheckIcon } from '../Icons';
import './RagSettingsModal.css';

export interface RagSettingsConfig {
  topK: number;
  vigenciaOnly: boolean;
  reranking: boolean;
  searchMode: 'hibrido' | 'doctrinal' | 'literal';
}

interface RagSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  settings: RagSettingsConfig;
  onSaveSettings: (settings: RagSettingsConfig) => void;
}

export function RagSettingsModal({
  isOpen,
  onClose,
  settings,
  onSaveSettings,
}: RagSettingsModalProps) {
  const [topK, setTopK] = useState(settings.topK || 5);
  const [vigenciaOnly, setVigenciaOnly] = useState(settings.vigenciaOnly ?? true);
  const [reranking, setReranking] = useState(settings.reranking ?? true);
  const [searchMode, setSearchMode] = useState(settings.searchMode || 'hibrido');

  if (!isOpen) return null;

  const handleSave = () => {
    onSaveSettings({
      topK,
      vigenciaOnly,
      reranking,
      searchMode,
    });
    onClose();
  };

  return (
    <div className="rag-modal-overlay" onClick={onClose}>
      <div className="rag-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="rag-modal-header">
          <div className="rag-modal-title-row">
            <SlidersIcon size={18} />
            <h4>Ajustes de Búsqueda y Recuperación Jurídica (RAG)</h4>
          </div>
          <button type="button" className="rag-close-btn" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="rag-modal-body">
          <div className="rag-setting-row">
            <div className="setting-info">
              <label>Modo de Búsqueda Normativa</label>
              <span>Determina la estrategia de consulta en el corpus legal colombiano</span>
            </div>
            <select
              value={searchMode}
              onChange={(e) => setSearchMode(e.target.value as any)}
              className="rag-select"
            >
              <option value="hibrido">Búsqueda Híbrida (Semántica + Textual Exacta)</option>
              <option value="doctrinal">Doctrinario & Jurisprudencial (Altas Cortes)</option>
              <option value="literal">Literal Normativo (Artículos específicos)</option>
            </select>
          </div>

          <div className="rag-setting-row">
            <div className="setting-info">
              <label>Número de Citas y Fragmentos Oficiales: {topK}</label>
              <span>Cantidad de artículos y extractos procesados por consulta (Top-K)</span>
            </div>
            <input
              type="range"
              min="3"
              max="12"
              step="1"
              value={topK}
              onChange={(e) => setTopK(parseInt(e.target.value, 10))}
              className="rag-slider"
            />
          </div>

          <div className="rag-setting-row rag-toggle-row">
            <div className="setting-info">
              <label>Filtro Estricto de Vigencia</label>
              <span>Excluir automáticamente normas derogadas o inexequibles</span>
            </div>
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={vigenciaOnly}
                onChange={(e) => setVigenciaOnly(e.target.checked)}
              />
              <span className="slider-round" />
            </label>
          </div>

          <div className="rag-setting-row rag-toggle-row">
            <div className="setting-info">
              <label>Reranker Neuronal de Precisión</label>
              <span>Reordena los fragmentos según relevancia jurídica antes de responder</span>
            </div>
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={reranking}
                onChange={(e) => setReranking(e.target.checked)}
              />
              <span className="slider-round" />
            </label>
          </div>
        </div>

        <div className="rag-modal-footer">
          <button type="button" className="btn-rag-cancel" onClick={onClose}>
            Cancelar
          </button>
          <button type="button" className="btn-rag-save" onClick={handleSave}>
            <CheckIcon size={14} />
            <span>Aplicar Ajustes</span>
          </button>
        </div>
      </div>
    </div>
  );
}
