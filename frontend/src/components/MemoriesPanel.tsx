import { useState } from 'react';
import { Memory, MemoriesConfig } from '../types';
import { estimateTokens, getTotalMemoryTokens } from '../library';
import { getTranslations } from '../i18n';
import { generateUUID } from '../utils';
import { PlusIcon, EditIcon, TrashIcon, ToggleOnIcon, ToggleOffIcon } from './Icons';
import './MemoriesPanel.css';

const t = getTranslations('es');

interface MemoriesPanelProps {
  memories: Memory[];
  config: MemoriesConfig;
  onSave: (memory: Memory) => void;
  onDelete: (id: string) => void;
  onConfigChange: (config: MemoriesConfig) => void;
  onClose: () => void;
}

export function MemoriesPanel({
  memories,
  config,
  onSave,
  onDelete,
  onConfigChange,
  onClose,
}: MemoriesPanelProps) {
  const [view, setView] = useState<'list' | 'editor'>('list');
  const [editing, setEditing] = useState<Memory | null>(null);

  const [formKey, setFormKey] = useState('');
  const [formValue, setFormValue] = useState('');

  const totalTokens = getTotalMemoryTokens(memories);
  const utilizationPct = Math.min(100, (totalTokens / config.maxTokens) * 100);

  const startNew = () => {
    setEditing(null);
    setFormKey('');
    setFormValue('');
    setView('editor');
  };

  const startEdit = (memory: Memory) => {
    setEditing(memory);
    setFormKey(memory.key);
    setFormValue(memory.value);
    setView('editor');
  };

  const handleSave = () => {
    if (!formKey.trim() || !formValue.trim()) return;

    const now = Date.now();
    const saved: Memory = {
      id: editing?.id || generateUUID(),
      key: formKey.trim(),
      value: formValue.trim(),
      tokens: estimateTokens(formValue.trim()),
      created_at: editing?.created_at || now,
      updated_at: now,
    };

    onSave(saved);
    setView('list');
  };

  const formatDate = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleDateString('es-CO', { year: 'numeric', month: 'short', day: 'numeric' });
  };

  return (
    <div className="memories-panel">
      <div className="panel-backdrop" onClick={onClose} />
      <div className="panel-content">
        <header className="panel-header">
          <div>
            <h2 className="panel-title">{t.memories.title}</h2>
            <p className="panel-subtitle">{t.memories.subtitle}</p>
          </div>
          {view === 'list' && (
            <button className="btn-primary" onClick={startNew}>
              <PlusIcon size={16} />
              {t.memories.newMemory}
            </button>
          )}
        </header>

        {view === 'list' && (
          <>
            <div className="memories-controls">
              <button
                className="toggle-row"
                onClick={() => onConfigChange({ ...config, enabled: !config.enabled })}
              >
                {config.enabled ? <ToggleOnIcon size={20} /> : <ToggleOffIcon size={20} />}
                <div className="toggle-label-group">
                  <span className="toggle-label">{t.memories.enabled}</span>
                  <span className="toggle-hint">{t.memories.enabledHint}</span>
                </div>
              </button>

              <div className="usage-bar-group">
                <div className="usage-label">
                  <span>{t.memories.usage}</span>
                  <span className="usage-value">
                    {totalTokens} {t.memories.usageOf} {config.maxTokens} {t.memories.tokens}
                  </span>
                </div>
                <div className="usage-bar-track">
                  <div
                    className="usage-bar-fill"
                    style={{
                      width: `${utilizationPct}%`,
                      backgroundColor:
                        utilizationPct > 90
                          ? '#ef4444'
                          : utilizationPct > 70
                          ? '#f59e0b'
                          : 'rgb(var(--accent-primary))',
                    }}
                  />
                </div>
              </div>
            </div>

            <div className="panel-body">
              {memories.length === 0 && (
                <div className="empty-state">
                  <p className="empty-title">{t.memories.empty}</p>
                  <p className="empty-hint">{t.memories.emptyHint}</p>
                </div>
              )}

              {memories.map((memory) => (
                <div key={memory.id} className="memory-card">
                  <div className="memory-card-header">
                    <h4 className="memory-card-key">{memory.key}</h4>
                    <div className="memory-card-actions">
                      <button className="icon-btn" onClick={() => startEdit(memory)} title={t.common.edit}>
                        <EditIcon size={14} />
                      </button>
                      <button
                        className="icon-btn"
                        onClick={() => onDelete(memory.id)}
                        title={t.common.delete}
                      >
                        <TrashIcon size={14} />
                      </button>
                    </div>
                  </div>
                  <p className="memory-card-value">{memory.value}</p>
                  <div className="memory-card-meta">
                    <span className="memory-tokens">
                      {memory.tokens} {t.memories.tokens}
                    </span>
                    <span className="memory-updated">
                      {t.memories.updated}: {formatDate(memory.updated_at)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {view === 'editor' && (
          <div className="panel-body">
            <div className="form-group">
              <label className="form-label">{t.memories.key}</label>
              <input
                type="text"
                value={formKey}
                onChange={(e) => setFormKey(e.target.value)}
                placeholder={t.memories.keyPlaceholder}
                className="form-input"
              />
            </div>

            <div className="form-group">
              <label className="form-label">{t.memories.value}</label>
              <textarea
                value={formValue}
                onChange={(e) => setFormValue(e.target.value)}
                placeholder={t.memories.valuePlaceholder}
                className="form-textarea"
                rows={6}
              />
              <p className="form-hint">
                ~{estimateTokens(formValue)} {t.memories.tokens}
              </p>
            </div>

            <div className="form-actions">
              <button className="btn-secondary" onClick={() => setView('list')}>
                {t.common.cancel}
              </button>
              <button
                className="btn-primary"
                onClick={handleSave}
                disabled={!formKey.trim() || !formValue.trim()}
              >
                {t.common.save}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
