import { useState, useEffect } from 'react';
import { Agent, LegalSpecializationId } from '../../types';
import { SPECIALIZATIONS } from '../../constants';
import { generateUUID } from '../../utils';
import {
  PlusIcon,
  ChevronDownIcon,
  SlidersIcon,
  ToggleOnIcon,
  ToggleOffIcon,
  TrashIcon,
  CheckIcon,
  BotIcon,
} from '../Icons';
import { SpecializationIcon } from '../SpecializationMenu';

interface AgentsViewProps {
  agents: Agent[];
  activeAgentId: string | null;
  onSave: (agent: Agent) => void;
  onDelete: (id: string) => void;
  onSelect: (id: string | null) => void;
}

const DEFAULT_MODELS = [
  { id: 'legalia-sonnet', name: 'Legalia Sonnet (Recomendado)' },
  { id: 'legalia-fast', name: 'Legalia Fast (Haiku)' },
  { id: 'legalia-opus', name: 'Legalia Corpus Master' },
];

export function AgentsView({
  agents,
  activeAgentId,
  onSave,
  onDelete,
  onSelect,
}: AgentsViewProps) {
  const [selectedAgentId, setSelectedAgentId] = useState<string>('new');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [model, setModel] = useState('legalia-sonnet');
  const [category, setCategory] = useState<LegalSpecializationId>('general');
  const [instructions, setInstructions] = useState('');
  const [supportName, setSupportName] = useState('');
  const [supportEmail, setSupportEmail] = useState('');
  const [useAllSkills, setUseAllSkills] = useState(false);
  const [icon, setIcon] = useState('⚖️');

  // Load selected agent data
  useEffect(() => {
    if (selectedAgentId === 'new') {
      setName('');
      setDescription('');
      setModel('legalia-sonnet');
      setCategory('general');
      setInstructions('');
      setSupportName('');
      setSupportEmail('');
      setIcon('⚖️');
    } else {
      const existing = agents.find((a) => a.id === selectedAgentId);
      if (existing) {
        setName(existing.name);
        setDescription(existing.description || '');
        setCategory(existing.specialization || 'general');
        setInstructions(existing.instructions || '');
        setIcon(existing.icon || '⚖️');
      }
    }
  }, [selectedAgentId, agents]);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    const agent: Agent = {
      id: selectedAgentId === 'new' ? generateUUID() : selectedAgentId,
      name: name.trim(),
      description: description.trim(),
      icon,
      instructions: instructions.trim(),
      specialization: category,
      created_at: Date.now(),
      updated_at: Date.now(),
    };

    onSave(agent);
    onSelect(agent.id);
    setSelectedAgentId(agent.id);
  };

  const handleDelete = () => {
    if (selectedAgentId !== 'new') {
      onDelete(selectedAgentId);
      setSelectedAgentId('new');
    }
  };

  const isActive = activeAgentId && activeAgentId === selectedAgentId;

  return (
    <div className="sidepanel-content sidepanel-agent-builder">
      {/* Top Agent Selector Dropdown (LibreChat Screenshot 2) */}
      <div className="agent-select-wrapper">
        <select
          className="agent-select-dropdown"
          value={selectedAgentId}
          onChange={(e) => setSelectedAgentId(e.target.value)}
        >
          <option value="new">+ Crear nuevo agente</option>
          {agents.map((agent) => (
            <option key={agent.id} value={agent.id}>
              {agent.name} {agent.id === activeAgentId ? '(Activo)' : ''}
            </option>
          ))}
        </select>
        <ChevronDownIcon size={16} className="select-chevron" />
      </div>

      {/* Form Fields Scroll Area */}
      <form onSubmit={handleSave} className="agent-form-scroll">
        {/* Avatar + Name + Description Header */}
        <div className="agent-identity-row">
          <div className="agent-avatar-picker" title="Icono del agente">
            <span className="avatar-preview">
              <SpecializationIcon id={category} size={20} />
            </span>
            <div className="avatar-plus-badge">
              <PlusIcon size={12} />
            </div>
          </div>
          <div className="agent-identity-inputs">
            <input
              type="text"
              placeholder="Opcional: El nombre del agente"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="agent-text-input bold"
              required
            />
            <input
              type="text"
              placeholder="Opcional: Describa su Agente"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="agent-text-input"
            />
          </div>
        </div>

        {/* Two-Column Model & Category (LibreChat Screenshot 2) */}
        <div className="agent-two-col">
          <div className="agent-col-field">
            <label className="agent-field-label">MODELO *</label>
            <div className="select-box">
              <select value={model} onChange={(e) => setModel(e.target.value)}>
                {DEFAULT_MODELS.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
              <ChevronDownIcon size={14} />
            </div>
          </div>

          <div className="agent-col-field">
            <label className="agent-field-label">CATEGORY *</label>
            <div className="select-box">
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value as LegalSpecializationId)}
              >
                {SPECIALIZATIONS.map((spec) => (
                  <option key={spec.id} value={spec.id}>
                    {spec.name}
                  </option>
                ))}
              </select>
              <ChevronDownIcon size={14} />
            </div>
          </div>
        </div>

        {/* INSTRUCCIONES Section */}
        <div className="agent-section">
          <div className="agent-section-header">
            <label className="agent-field-label">INSTRUCCIONES</label>
            <div className="section-header-actions">
              <button type="button" className="icon-btn-micro" title="Agregar variable">
                <PlusIcon size={14} />
              </button>
            </div>
          </div>
          <textarea
            className="agent-textarea"
            rows={4}
            placeholder="Las instrucciones del sistema que utiliza el agente (ej. Actúa como magistrado auxiliar experto en casación laboral...)"
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
          />
        </div>

        {/* TOOLS Section (Dashed Card) */}
        <div className="agent-section">
          <div className="agent-section-header">
            <label className="agent-field-label">TOOLS</label>
            <button type="button" className="action-text-btn">
              <PlusIcon size={13} /> Agregar
            </button>
          </div>
          <div className="dashed-drop-card">
            <PlusIcon size={16} className="dashed-card-icon" />
            <div className="dashed-card-title">No tools yet</div>
            <div className="dashed-card-desc">
              Add a tool to give your agent extra abilities.
            </div>
          </div>
        </div>

        {/* SKILLS Section (Dashed Card + Toggle) */}
        <div className="agent-section">
          <div className="agent-section-header">
            <label className="agent-field-label">SKILLS</label>
            <button type="button" className="action-text-btn">
              <PlusIcon size={13} /> Agregar
            </button>
          </div>
          <div className="agent-toggle-row">
            <span className="toggle-label">Use all skills</span>
            <button
              type="button"
              className="toggle-icon-btn"
              onClick={() => setUseAllSkills(!useAllSkills)}
            >
              {useAllSkills ? <ToggleOnIcon size={24} /> : <ToggleOffIcon size={24} />}
            </button>
          </div>
          <div className="dashed-drop-card">
            <PlusIcon size={16} className="dashed-card-icon" />
            <div className="dashed-card-title">No skills yet</div>
            <div className="dashed-card-desc">
              Add a skill to give your agent reusable instructions.
            </div>
          </div>
        </div>

        {/* ARCHIVOS DE CONTEXTO Section */}
        <div className="agent-section">
          <div className="agent-section-header">
            <label className="agent-field-label">ARCHIVOS DE CONTEXTO</label>
            <button type="button" className="action-text-btn">
              <PlusIcon size={13} /> Agregar
            </button>
          </div>
          <div className="agent-hint-text">
            Es necesario crear el Agente antes de subir archivos.
          </div>
        </div>

        {/* CONTACTO DE SOPORTE */}
        <div className="agent-section">
          <label className="agent-field-label">CONTACTO DE SOPORTE</label>
          <div className="agent-contact-inputs">
            <input
              type="text"
              placeholder="Support contact name"
              value={supportName}
              onChange={(e) => setSupportName(e.target.value)}
              className="agent-text-input"
            />
            <input
              type="email"
              placeholder="support@example.com"
              value={supportEmail}
              onChange={(e) => setSupportEmail(e.target.value)}
              className="agent-text-input"
            />
          </div>
        </div>

        {/* Avanzado Section */}
        <div className="agent-advanced-row">
          <div className="advanced-title">
            <SlidersIcon size={15} />
            <span>Avanzado</span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="agent-actions-footer">
          {selectedAgentId !== 'new' && (
            <button
              type="button"
              className={`btn-toggle-active ${isActive ? 'active' : ''}`}
              onClick={() => onSelect(isActive ? null : selectedAgentId)}
            >
              {isActive ? <CheckIcon size={14} /> : <BotIcon size={14} />}
              {isActive ? 'Agente Activo' : 'Activar Agente'}
            </button>
          )}

          <div className="footer-right-buttons">
            {selectedAgentId !== 'new' && (
              <button
                type="button"
                className="btn-danger-icon"
                onClick={handleDelete}
                title="Eliminar este agente"
              >
                <TrashIcon size={16} />
              </button>
            )}
            <button type="submit" className="btn-primary-agent">
              {selectedAgentId === 'new' ? 'Crear Agente' : 'Guardar Cambios'}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
