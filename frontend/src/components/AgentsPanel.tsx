import { useState } from 'react';
import { Agent, LegalSpecializationId } from '../types';
import { SPECIALIZATIONS } from '../constants';
import { getTranslations } from '../i18n';
import { PlusIcon, EditIcon, TrashIcon, CheckIcon } from './Icons';
import './AgentsPanel.css';

const t = getTranslations('es');

interface AgentsPanelProps {
  agents: Agent[];
  activeAgentId: string | null;
  onSave: (agent: Agent) => void;
  onDelete: (id: string) => void;
  onSelect: (id: string | null) => void;
  onClose: () => void;
}

export function AgentsPanel({
  agents,
  activeAgentId,
  onSave,
  onDelete,
  onSelect,
  onClose,
}: AgentsPanelProps) {
  const [view, setView] = useState<'list' | 'editor'>('list');
  const [editing, setEditing] = useState<Agent | null>(null);

  const [formName, setFormName] = useState('');
  const [formDescription, setFormDescription] = useState('');
  const [formIcon, setFormIcon] = useState('⚖️');
  const [formInstructions, setFormInstructions] = useState('');
  const [formSpecialization, setFormSpecialization] = useState<LegalSpecializationId>('general');

  const startNew = () => {
    setEditing(null);
    setFormName('');
    setFormDescription('');
    setFormIcon('⚖️');
    setFormInstructions('');
    setFormSpecialization('general');
    setView('editor');
  };

  const startEdit = (agent: Agent) => {
    setEditing(agent);
    setFormName(agent.name);
    setFormDescription(agent.description);
    setFormIcon(agent.icon);
    setFormInstructions(agent.instructions);
    setFormSpecialization(agent.specialization);
    setView('editor');
  };

  const handleSave = () => {
    if (!formName.trim() || !formInstructions.trim()) return;

    const now = Date.now();
    const saved: Agent = {
      id: editing?.id || crypto.randomUUID(),
      name: formName.trim(),
      description: formDescription.trim(),
      icon: formIcon,
      instructions: formInstructions.trim(),
      specialization: formSpecialization,
      created_at: editing?.created_at || now,
      updated_at: now,
    };

    onSave(saved);
    setView('list');
  };

  const handleSelectAgent = (id: string | null) => {
    onSelect(id);
    onClose();
  };

  return (
    <div className="agents-panel">
      <div className="panel-backdrop" onClick={onClose} />
      <div className="panel-content">
        <header className="panel-header">
          <div>
            <h2 className="panel-title">{t.agents.title}</h2>
            <p className="panel-subtitle">{t.agents.subtitle}</p>
          </div>
          {view === 'list' && (
            <button className="btn-primary" onClick={startNew}>
              <PlusIcon size={16} />
              {t.agents.newAgent}
            </button>
          )}
        </header>

        {view === 'list' && (
          <div className="panel-body">
            <div className="agent-card agent-card-none" onClick={() => handleSelectAgent(null)}>
              <div className="agent-card-header">
                <div className="agent-card-icon-row">
                  <span className="agent-card-icon">🤖</span>
                  <h4 className="agent-card-name">{t.agents.noAgent}</h4>
                </div>
                {activeAgentId === null && (
                  <CheckIcon size={16} className="agent-card-check" />
                )}
              </div>
              <p className="agent-card-desc">Legalia estándar sin personalización</p>
            </div>

            {agents.length === 0 && (
              <div className="empty-state">
                <p className="empty-title">{t.agents.empty}</p>
                <p className="empty-hint">{t.agents.emptyHint}</p>
              </div>
            )}

            {agents.map((agent) => (
              <div key={agent.id} className="agent-card">
                <div className="agent-card-header">
                  <div className="agent-card-icon-row" onClick={() => handleSelectAgent(agent.id)}>
                    <span className="agent-card-icon">{agent.icon}</span>
                    <h4 className="agent-card-name">{agent.name}</h4>
                  </div>
                  <div className="agent-card-actions">
                    {activeAgentId === agent.id && (
                      <CheckIcon size={16} className="agent-card-check" />
                    )}
                    <button className="icon-btn" onClick={() => startEdit(agent)} title={t.common.edit}>
                      <EditIcon size={14} />
                    </button>
                    <button
                      className="icon-btn"
                      onClick={() => onDelete(agent.id)}
                      title={t.common.delete}
                    >
                      <TrashIcon size={14} />
                    </button>
                  </div>
                </div>

                {agent.description && <p className="agent-card-desc">{agent.description}</p>}

                <p className="agent-card-preview">
                  {agent.instructions.slice(0, 140)}
                  {agent.instructions.length > 140 ? '...' : ''}
                </p>

                <div className="agent-card-meta">
                  <span className="agent-spec">
                    {SPECIALIZATIONS.find((s) => s.id === agent.specialization)?.icon}{' '}
                    {SPECIALIZATIONS.find((s) => s.id === agent.specialization)?.name}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

        {view === 'editor' && (
          <div className="panel-body">
            <div className="form-group">
              <label className="form-label">{t.agents.icon}</label>
              <input
                type="text"
                value={formIcon}
                onChange={(e) => setFormIcon(e.target.value)}
                placeholder="⚖️"
                className="form-input form-input-icon"
                maxLength={2}
              />
            </div>

            <div className="form-group">
              <label className="form-label">{t.agents.name}</label>
              <input
                type="text"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                placeholder={t.agents.namePlaceholder}
                className="form-input"
              />
            </div>

            <div className="form-group">
              <label className="form-label">
                {t.agents.description} <span className="form-optional">({t.common.optional})</span>
              </label>
              <input
                type="text"
                value={formDescription}
                onChange={(e) => setFormDescription(e.target.value)}
                placeholder={t.agents.descriptionPlaceholder}
                className="form-input"
              />
            </div>

            <div className="form-group">
              <label className="form-label">{t.agents.instructions}</label>
              <textarea
                value={formInstructions}
                onChange={(e) => setFormInstructions(e.target.value)}
                placeholder={t.agents.instructionsPlaceholder}
                className="form-textarea"
                rows={8}
              />
            </div>

            <div className="form-group">
              <label className="form-label">{t.agents.specialization}</label>
              <select
                value={formSpecialization}
                onChange={(e) => setFormSpecialization(e.target.value as LegalSpecializationId)}
                className="form-select"
              >
                {SPECIALIZATIONS.map((spec) => (
                  <option key={spec.id} value={spec.id}>
                    {spec.icon} {spec.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-actions">
              <button className="btn-secondary" onClick={() => setView('list')}>
                {t.common.cancel}
              </button>
              <button
                className="btn-primary"
                onClick={handleSave}
                disabled={!formName.trim() || !formInstructions.trim()}
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
