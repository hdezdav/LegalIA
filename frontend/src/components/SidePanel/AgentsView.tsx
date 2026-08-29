import { useState, useEffect } from 'react';
import { Agent, LegalSpecializationId, AgentToolsConfig } from '../../types';
import { SPECIALIZATIONS } from '../../constants';
import { generateUUID } from '../../utils';
import { AgentSymbol, LEGAL_SYMBOLS } from '../AgentSymbol';
import {
  PlusIcon,
  ChevronDownIcon,
  TrashIcon,
  CheckIcon,
  BotIcon,
  SparklesIcon,
  CopyIcon,
  ShieldIcon,
  FileTextIcon,
  SlidersIcon,
} from '../Icons';

interface AgentsViewProps {
  agents: Agent[];
  activeAgentId: string | null;
  onSave: (agent: Agent) => void;
  onDelete: (id: string) => void;
  onSelect: (id: string | null) => void;
}

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
  const [category, setCategory] = useState<LegalSpecializationId>('general');
  const [instructions, setInstructions] = useState('');
  const [icon, setIcon] = useState('scale');
  const [starters, setStarters] = useState<string[]>([]);
  const [newStarter, setNewStarter] = useState('');
  const [showSymbolPicker, setShowSymbolPicker] = useState(false);
  const [tools, setTools] = useState<AgentToolsConfig>({
    rag_corpus: true,
    docx_export: true,
    interactive_forms: true,
  });

  // Load selected agent data
  useEffect(() => {
    if (selectedAgentId === 'new') {
      setName('');
      setDescription('');
      setCategory('general');
      setInstructions('');
      setIcon('scale');
      setStarters([
        '¿Cuáles son los requisitos de procedibilidad?',
        'Redactar documento legal con normativa aplicable',
      ]);
      setTools({
        rag_corpus: true,
        docx_export: true,
        interactive_forms: true,
      });
    } else {
      const existing = agents.find((a) => a.id === selectedAgentId);
      if (existing) {
        setName(existing.name);
        setDescription(existing.description || '');
        setCategory(existing.specialization || 'general');
        setInstructions(existing.instructions || '');
        setIcon(existing.icon || 'scale');
        setStarters(existing.conversation_starters || []);
        const existingTools = existing.tools || {};
        setTools({
          rag_corpus: existingTools.rag_corpus ?? true,
          docx_export: existingTools.docx_export ?? true,
          interactive_forms: existingTools.interactive_forms ?? true,
        });
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
        <div className="agent-select-icon-left">
          {selectedAgentId === 'new' ? (
            <PlusIcon size={15} />
          ) : (
            <AgentSymbol icon={icon} size={15} />
          )}
        </div>
        <select
          className="agent-select-dropdown"
          value={selectedAgentId}
          onChange={(e) => setSelectedAgentId(e.target.value)}
        >
          <option value="new">+ Crear nuevo agente jurídico</option>
          <optgroup label="Agentes Jurídicos Disponibles">
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name} {agent.id === activeAgentId ? '✓ (Activo)' : ''}
              </option>
            ))}
          </optgroup>
        </select>
        <ChevronDownIcon size={14} className="select-chevron" />
      </div>

      {/* Form Fields Scroll Area */}
      <form onSubmit={handleSave} className="agent-form-scroll">
        {/* Symbol + Name + Description Header */}
        <div className="agent-identity-row">
          <div className="agent-symbol-picker-wrapper">
            <button
              type="button"
              className="agent-symbol-picker-btn"
              onClick={() => setShowSymbolPicker(!showSymbolPicker)}
              title="Seleccionar símbolo jurídico"
            >
              <div className="agent-symbol-box">
                <AgentSymbol icon={icon} size={22} />
              </div>
              <span className="agent-symbol-change-label">Cambiar</span>
            </button>

            {showSymbolPicker && (
              <div className="symbol-picker-popover">
                <div className="symbol-picker-header">
                  <span>Símbolos Jurídicos</span>
                  <button
                    type="button"
                    className="symbol-close-btn"
                    onClick={() => setShowSymbolPicker(false)}
                  >
                    ✕
                  </button>
                </div>
                <div className="symbol-picker-grid">
                  {LEGAL_SYMBOLS.map((sym) => {
                    const isSelected = icon === sym.id;
                    return (
                      <button
                        key={sym.id}
                        type="button"
                        className={`symbol-preset-btn ${isSelected ? 'selected' : ''}`}
                        onClick={() => {
                          setIcon(sym.id);
                          setShowSymbolPicker(false);
                        }}
                        title={sym.name}
                      >
                        <AgentSymbol icon={sym.id} size={18} color={sym.color} />
                        <span className="symbol-preset-name">{sym.name}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          <div className="agent-identity-inputs">
            <div className="agent-input-group">
              <label className="agent-field-label">NOMBRE DEL AGENTE *</label>
              <input
                type="text"
                placeholder="Ej. Especialista en Tutelas y Salud"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="agent-text-input agent-name-input"
                required
              />
            </div>
            <div className="agent-input-group">
              <label className="agent-field-label">DESCRIPCIÓN BREVE</label>
              <input
                type="text"
                placeholder="Ej. Análisis de procedibilidad y subsidiariedad"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="agent-text-input"
              />
            </div>
          </div>
        </div>

        {/* Single Full-Width Rama / Especialidad Jurídica */}
        <div className="agent-input-group">
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

        {/* INSTRUCCIONES DEL SISTEMA */}
        <div className="agent-section">
          <div className="agent-section-header">
            <label className="agent-field-label">
              <FileTextIcon size={13} />
              <span>INSTRUCCIONES DEL SISTEMA</span>
            </label>
          </div>
          <textarea
            className="agent-textarea"
            rows={5}
            placeholder="Define el rol del agente (ej. Actúa como magistrado auxiliar experto en casación laboral... Cita jurisprudencia de la Sala Laboral y liquida indemnizaciones según Art. 64 CST...)"
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
          />
        </div>

        {/* CONVERSATION STARTERS (LibreChat Style) */}
        <div className="agent-section">
          <div className="agent-section-header">
            <label className="agent-field-label">
              <SparklesIcon size={13} />
              <span>PREGUNTAS SUGERIDAS</span>
            </label>
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
              placeholder="Ej. Redactar tutela por salud..."
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

        {/* HERRAMIENTAS & CAPACIDADES */}
        <div className="agent-section">
          <div className="agent-section-header">
            <label className="agent-field-label">
              <SlidersIcon size={13} />
              <span>CAPACIDADES ACTIVAS</span>
            </label>
          </div>
          <div className="tools-toggle-grid">
            <label className="tool-checkbox-item">
              <input
                type="checkbox"
                checked={tools.rag_corpus ?? true}
                onChange={() => handleToggleTool('rag_corpus')}
              />
              <div className="tool-checkbox-info">
                <span className="tool-name">
                  <ShieldIcon size={14} style={{ color: '#2563eb' }} /> Búsqueda Corpus Jurídico (RAG)
                </span>
                <span className="tool-desc">
                  Recupera citas normativas oficiales y jurisprudencia colombiana.
                </span>
              </div>
            </label>

            <label className="tool-checkbox-item">
              <input
                type="checkbox"
                checked={tools.docx_export ?? true}
                onChange={() => handleToggleTool('docx_export')}
              />
              <div className="tool-checkbox-info">
                <span className="tool-name">
                  <FileTextIcon size={14} style={{ color: '#10b981' }} /> Exportador Word (.docx) y PDF
                </span>
                <span className="tool-desc">
                  Genera minutas estructuradas listas para descargar.
                </span>
              </div>
            </label>

            <label className="tool-checkbox-item">
              <input
                type="checkbox"
                checked={tools.interactive_forms ?? true}
                onChange={() => handleToggleTool('interactive_forms')}
              />
              <div className="tool-checkbox-info">
                <span className="tool-name">
                  <SparklesIcon size={14} style={{ color: '#8b5cf6' }} /> Tarjetas y Formularios Intake
                </span>
                <span className="tool-desc">
                  Despliega opciones interactivas para recolección de datos.
                </span>
              </div>
            </label>
          </div>
        </div>

        {/* Apple Design Action Buttons Footer */}
        <div className="agent-actions-footer">
          {selectedAgentId !== 'new' && (
            <div className="agent-actions-secondary-row">
              <button
                type="button"
                className={`btn-toggle-active ${isActive ? 'active' : ''}`}
                onClick={() => onSelect(isActive ? null : selectedAgentId)}
                title={isActive ? 'Desactivar agente' : 'Establecer como agente activo'}
              >
                {isActive ? <CheckIcon size={14} /> : <BotIcon size={14} />}
                <span>{isActive ? 'Agente Activo' : 'Activar'}</span>
              </button>

              <div className="agent-actions-tools-group">
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
                  <TrashIcon size={14} />
                </button>
              </div>
            </div>
          )}

          <button type="submit" className="btn-primary-agent">
            <SparklesIcon size={14} />
            <span>{selectedAgentId === 'new' ? 'Crear Agente' : 'Guardar Cambios'}</span>
          </button>
        </div>
      </form>
    </div>
  );
}
