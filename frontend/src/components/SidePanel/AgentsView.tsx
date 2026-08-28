import { useState, useEffect } from 'react';
import { Agent, LegalSpecializationId, AgentToolsConfig } from '../../types';
import { SPECIALIZATIONS } from '../../constants';
import { generateUUID } from '../../utils';
import {
  PlusIcon,
  ChevronDownIcon,
  TrashIcon,
  CheckIcon,
  BotIcon,
  SparklesIcon,
  CopyIcon,
} from '../Icons';

interface AgentsViewProps {
  agents: Agent[];
  activeAgentId: string | null;
  onSave: (agent: Agent) => void;
  onDelete: (id: string) => void;
  onSelect: (id: string | null) => void;
}

const AVAILABLE_MODELS = [
  { id: 'claude-sonnet-5', name: 'Claude Sonnet 5 (Recomendado Jurídico)' },
  { id: 'claude-sonnet-4.6', name: 'Claude Sonnet 4.6 (Equilibrado)' },
  { id: 'claude-haiku-4.5', name: 'Claude Haiku 4.5 (Rápido / Consultas breves)' },
  { id: 'gpt-4o', name: 'GPT-4o (OpenAI)' },
];

const EMOJI_PRESETS = ['⚖️', '🏛️', '💼', '📝', '🔍', '📜', '🛡️', '💡', '👔', '🎓', '🤖', '📖'];

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
  const [model, setModel] = useState('claude-sonnet-5');
  const [category, setCategory] = useState<LegalSpecializationId>('general');
  const [instructions, setInstructions] = useState('');
  const [icon, setIcon] = useState('⚖️');
  const [starters, setStarters] = useState<string[]>([]);
  const [newStarter, setNewStarter] = useState('');
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const [tools, setTools] = useState<AgentToolsConfig>({
    rag_corpus: true,
    docx_export: true,
    labor_calculator: false,
    interactive_forms: true,
  });

  // Load selected agent data
  useEffect(() => {
    if (selectedAgentId === 'new') {
      setName('');
      setDescription('');
      setModel('claude-sonnet-5');
      setCategory('general');
      setInstructions('');
      setIcon('⚖️');
      setStarters([
        '¿Cuáles son los requisitos de procedibilidad?',
        'Redactar documento legal con normativa aplicable',
      ]);
      setTools({
        rag_corpus: true,
        docx_export: true,
        labor_calculator: false,
        interactive_forms: true,
      });
    } else {
      const existing = agents.find((a) => a.id === selectedAgentId);
      if (existing) {
        setName(existing.name);
        setDescription(existing.description || '');
        setModel(existing.model || 'claude-sonnet-5');
        setCategory(existing.specialization || 'general');
        setInstructions(existing.instructions || '');
        setIcon(existing.icon || '⚖️');
        setStarters(existing.conversation_starters || []);
        setTools(
          existing.tools || {
            rag_corpus: true,
            docx_export: true,
            labor_calculator: false,
            interactive_forms: true,
          }
        );
      }
    }
  }, [selectedAgentId, agents]);

  const handleAddStarter = () => {
    if (!newStarter.trim()) return;
    setStarters((prev) => [...prev, newStarter.trim()]);
    setNewStarter('');
  };

  const handleRemoveStarter = (idx: number) => {
    setStarters((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleToggleTool = (key: keyof AgentToolsConfig) => {
    setTools((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    const agent: Agent = {
      id: selectedAgentId === 'new' ? generateUUID() : selectedAgentId,
      name: name.trim(),
      description: description.trim(),
      icon,
      model,
      instructions: instructions.trim(),
      specialization: category,
      conversation_starters: starters.filter((s) => s.trim().length > 0),
      tools,
      is_preset: agents.find((a) => a.id === selectedAgentId)?.is_preset || false,
      created_at: Date.now(),
      updated_at: Date.now(),
    };

    onSave(agent);
    onSelect(agent.id);
    setSelectedAgentId(agent.id);
  };

  const handleDuplicate = () => {
    const newId = generateUUID();
    const clonedAgent: Agent = {
      id: newId,
      name: `${name} (Copia)`,
      description,
      icon,
      model,
      instructions,
      specialization: category,
      conversation_starters: [...starters],
      tools: { ...tools },
      is_preset: false,
      created_at: Date.now(),
      updated_at: Date.now(),
    };
    onSave(clonedAgent);
    onSelect(clonedAgent.id);
    setSelectedAgentId(clonedAgent.id);
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
      {/* Top Agent Selector Dropdown (LibreChat Style) */}
      <div className="agent-select-wrapper">
        <select
          className="agent-select-dropdown"
          value={selectedAgentId}
          onChange={(e) => setSelectedAgentId(e.target.value)}
        >
          <option value="new">+ Crear nuevo agente personalizado</option>
          <optgroup label="Agentes Disponibles">
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.icon || '🤖'} {agent.name} {agent.id === activeAgentId ? '✓ (Activo)' : ''}
              </option>
            ))}
          </optgroup>
        </select>
        <ChevronDownIcon size={16} className="select-chevron" />
      </div>

      {/* Form Fields Scroll Area */}
      <form onSubmit={handleSave} className="agent-form-scroll">
        {/* Avatar + Name + Description Header */}
        <div className="agent-identity-row">
          <div className="agent-avatar-picker-wrapper">
            <button
              type="button"
              className="agent-avatar-picker"
              onClick={() => setShowEmojiPicker(!showEmojiPicker)}
              title="Cambiar icono del agente"
            >
              <span className="avatar-preview-text">{icon}</span>
              <div className="avatar-plus-badge">
                <PlusIcon size={10} />
              </div>
            </button>

            {showEmojiPicker && (
              <div className="emoji-picker-popover">
                <div className="emoji-picker-grid">
                  {EMOJI_PRESETS.map((em) => (
                    <button
                      key={em}
                      type="button"
                      className="emoji-preset-btn"
                      onClick={() => {
                        setIcon(em);
                        setShowEmojiPicker(false);
                      }}
                    >
                      {em}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="agent-identity-inputs">
            <input
              type="text"
              placeholder="Nombre del Agente (ej. Especialista en Tutelas)"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="agent-text-input bold"
              required
            />
            <input
              type="text"
              placeholder="Descripción breve de su función"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="agent-text-input"
            />
          </div>
        </div>

        {/* Two-Column Model & Category */}
        <div className="agent-two-col">
          <div className="agent-col-field">
            <label className="agent-field-label">MODELO LLM *</label>
            <div className="select-box">
              <select value={model} onChange={(e) => setModel(e.target.value)}>
                {AVAILABLE_MODELS.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
              <ChevronDownIcon size={14} />
            </div>
          </div>

          <div className="agent-col-field">
            <label className="agent-field-label">ESPECIALIDAD JURÍDICA *</label>
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

        {/* INSTRUCCIONES DEL SISTEMA */}
        <div className="agent-section">
          <div className="agent-section-header">
            <label className="agent-field-label">INSTRUCCIONES DEL SISTEMA (PROMPT)</label>
          </div>
          <textarea
            className="agent-textarea"
            rows={5}
            placeholder="Instrucciones para el agente (ej. Actúa como magistrado auxiliar experto en casación laboral... Cita jurisprudencia de la Sala Laboral y calcula indemnizaciones según Art. 64 CST...)"
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
          />
        </div>

        {/* CONVERSATION STARTERS (LibreChat Style) */}
        <div className="agent-section">
          <div className="agent-section-header">
            <label className="agent-field-label">PREGUNTAS SUGERIDAS (CONVERSATION STARTERS)</label>
          </div>
          <div className="starters-list">
            {starters.map((starter, idx) => (
              <div key={idx} className="starter-item-row">
                <span className="starter-text">{starter}</span>
                <button
                  type="button"
                  className="starter-remove-btn"
                  onClick={() => handleRemoveStarter(idx)}
                  title="Eliminar pregunta"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
          <div className="starter-add-row">
            <input
              type="text"
              placeholder="Ej. Redactar derecho de petición por salud..."
              value={newStarter}
              onChange={(e) => setNewStarter(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleAddStarter();
                }
              }}
              className="agent-text-input"
            />
            <button
              type="button"
              className="action-text-btn"
              onClick={handleAddStarter}
              disabled={!newStarter.trim()}
            >
              <PlusIcon size={13} /> Añadir
            </button>
          </div>
        </div>

        {/* HERRAMIENTAS & CAPACIDADES (TOOLS & SKILLS) */}
        <div className="agent-section">
          <div className="agent-section-header">
            <label className="agent-field-label">CAPACIDADES Y HERRAMIENTAS ACTIVAS</label>
          </div>
          <div className="tools-toggle-grid">
            <label className="tool-checkbox-item">
              <input
                type="checkbox"
                checked={tools.rag_corpus ?? true}
                onChange={() => handleToggleTool('rag_corpus')}
              />
              <div className="tool-checkbox-info">
                <span className="tool-name">🔍 Búsqueda en Corpus Oficial (RAG)</span>
                <span className="tool-desc">Recupera leyes, decretos y jurisprudencia colombiana oficial.</span>
              </div>
            </label>

            <label className="tool-checkbox-item">
              <input
                type="checkbox"
                checked={tools.docx_export ?? true}
                onChange={() => handleToggleTool('docx_export')}
              />
              <div className="tool-checkbox-info">
                <span className="tool-name">📄 Exportador Word (.docx) y PDF</span>
                <span className="tool-desc">Genera minutas descargables en Microsoft Word con formato legal.</span>
              </div>
            </label>

            <label className="tool-checkbox-item">
              <input
                type="checkbox"
                checked={tools.labor_calculator ?? false}
                onChange={() => handleToggleTool('labor_calculator')}
              />
              <div className="tool-checkbox-info">
                <span className="tool-name">⚖️ Calculadora Laboral y Prestacional</span>
                <span className="tool-desc">Calcula cesantías, primas, vacaciones e indemnizaciones Art. 64 CST.</span>
              </div>
            </label>

            <label className="tool-checkbox-item">
              <input
                type="checkbox"
                checked={tools.interactive_forms ?? true}
                onChange={() => handleToggleTool('interactive_forms')}
              />
              <div className="tool-checkbox-info">
                <span className="tool-name">⚡ Tarjetas de Selección y Formularios Intake</span>
                <span className="tool-desc">Despliega preguntas con opciones y cuestionarios en el chat.</span>
              </div>
            </label>
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
              <span>{isActive ? 'Agente Activo' : 'Activar Agente'}</span>
            </button>
          )}

          <div className="footer-right-buttons">
            {selectedAgentId !== 'new' && (
              <>
                <button
                  type="button"
                  className="btn-secondary-agent"
                  onClick={handleDuplicate}
                  title="Duplicar agente"
                >
                  <CopyIcon size={14} />
                  <span>Duplicar</span>
                </button>
                <button
                  type="button"
                  className="btn-danger-icon"
                  onClick={handleDelete}
                  title="Eliminar este agente"
                >
                  <TrashIcon size={15} />
                </button>
              </>
            )}
            <button type="submit" className="btn-primary-agent">
              <SparklesIcon size={14} />
              <span>{selectedAgentId === 'new' ? 'Crear Agente' : 'Guardar Cambios'}</span>
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
