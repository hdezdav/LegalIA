import { useState } from 'react';
import { Memory, MemoriesConfig } from '../../types';
import { PlusIcon, TrashIcon, BrainIcon, XIcon, CheckIcon } from '../Icons';

interface MemoriesViewProps {
  memories: Memory[];
  config: MemoriesConfig;
  onSave: (memory: Memory) => void;
  onDelete: (id: string) => void;
  onConfigChange: (config: MemoriesConfig) => void;
}

export function MemoriesView({
  memories,
  config,
  onSave,
  onDelete,
  onConfigChange,
}: MemoriesViewProps) {
  const [filter, setFilter] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [newKey, setNewKey] = useState('');
  const [newValue, setNewValue] = useState('');

  const filtered = memories.filter(
    (m) =>
      m.key.toLowerCase().includes(filter.toLowerCase()) ||
      m.value.toLowerCase().includes(filter.toLowerCase())
  );

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKey.trim() || !newValue.trim()) return;

    const memory: Memory = {
      id: crypto.randomUUID(),
      key: newKey.trim(),
      value: newValue.trim(),
      tokens: Math.ceil((newKey.length + newValue.length) / 4),
      created_at: Date.now(),
      updated_at: Date.now(),
    };

    onSave(memory);
    setNewKey('');
    setNewValue('');
    setShowAddModal(false);
  };

  const toggleEnabled = () => {
    onConfigChange({ ...config, enabled: !config.enabled });
  };

  return (
    <div className="sidepanel-content">
      {/* Top Filter and Add Row (LibreChat Style) */}
      <div className="sidepanel-header-row">
        <div className="sidepanel-search-box">
          <input
            type="text"
            placeholder="Filter memories..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
        </div>
        <button
          className="sidepanel-square-btn"
          onClick={() => setShowAddModal(true)}
          title="Crear nueva memoria"
        >
          <PlusIcon size={16} />
        </button>
      </div>

      {/* Toggle Button: [ ☑ Usar Memoria ] */}
      <div className="sidepanel-action-bar">
        <button
          className={`sidepanel-toggle-pill ${config.enabled ? 'active' : ''}`}
          onClick={toggleEnabled}
        >
          <span className="pill-checkbox">
            {config.enabled ? <CheckIcon size={13} /> : null}
          </span>
          <span className="pill-text">Usar Memoria</span>
        </button>
      </div>

      {/* Memory List or Empty State */}
      <div className="sidepanel-body-scroll">
        {filtered.length === 0 ? (
          <div className="sidepanel-empty-card">
            <div className="empty-card-icon-circle">
              <BrainIcon size={24} />
            </div>
            <h3 className="empty-card-title">No memories yet</h3>
            <p className="empty-card-desc">
              Sin memorias. Créelas manualmente o pida a la IA que recuerde algo relevante para sus consultas jurídicas.
            </p>
          </div>
        ) : (
          <div className="sidepanel-items-stack">
            {filtered.map((memory) => (
              <div key={memory.id} className="sidepanel-memory-card">
                <div className="memory-card-header">
                  <span className="memory-key-tag">{memory.key}</span>
                  <button
                    className="memory-delete-btn"
                    onClick={() => onDelete(memory.id)}
                    title="Eliminar memoria"
                  >
                    <TrashIcon size={14} />
                  </button>
                </div>
                <div className="memory-card-value">{memory.value}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add Memory Modal */}
      {showAddModal && (
        <div className="sidepanel-modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="sidepanel-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Nueva Memoria Jurídica</h3>
              <button className="modal-close-btn" onClick={() => setShowAddModal(false)}>
                <XIcon size={16} />
              </button>
            </div>
            <form onSubmit={handleCreate} className="modal-form">
              <div className="form-group">
                <label>Clave / Tópico</label>
                <input
                  type="text"
                  placeholder="ej. Especialidad del despacho, Jurisdicción preferida"
                  value={newKey}
                  onChange={(e) => setNewKey(e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label>Información a recordar</label>
                <textarea
                  placeholder="ej. Priorizar sentencias de unificación del Consejo de Estado Sección Tercera..."
                  value={newValue}
                  onChange={(e) => setNewValue(e.target.value)}
                  rows={3}
                  required
                />
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn-cancel"
                  onClick={() => setShowAddModal(false)}
                >
                  Cancelar
                </button>
                <button type="submit" className="btn-save">
                  Guardar Memoria
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
