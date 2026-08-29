import { useState, useRef, useEffect } from 'react';
import { LegalSpecializationId, Agent } from '../types';
import { SPECIALIZATIONS } from '../constants';
import { AgentSymbol } from './AgentSymbol';
import {
  ChevronDownIcon,
  PlusIcon,
  CheckIcon,
  BotIcon,
} from './Icons';
import './SpecializationMenu.css';

interface SpecializationMenuProps {
  value: LegalSpecializationId;
  onChange: (id: LegalSpecializationId) => void;
  agents?: Agent[];
  activeAgentId?: string | null;
  onSelectAgent?: (id: string | null) => void;
  onOpenAgentCreator?: () => void;
}

export function SpecializationIcon({
  id,
  size = 16,
  className,
}: {
  id: LegalSpecializationId;
  size?: number;
  className?: string;
}) {
  const spec = SPECIALIZATIONS.find((s) => s.id === id);
  return <AgentSymbol icon={id} size={size} className={className} color={spec?.color} />;
}

export function SpecializationMenu({
  value,
  onChange,
  agents = [],
  activeAgentId = null,
  onSelectAgent,
  onOpenAgentCreator,
}: SpecializationMenuProps) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Determine current active agent or base specialization
  const activeAgent = activeAgentId ? agents.find((a) => a.id === activeAgentId) : null;
  const currentSpec = SPECIALIZATIONS.find((s) => s.id === value) || SPECIALIZATIONS[0];

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };

    if (open) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [open]);

  const handleSelectSpecialization = (id: LegalSpecializationId) => {
    if (onSelectAgent) onSelectAgent(null);
    onChange(id);
    setOpen(false);
  };

  const handleSelectAgent = (agent: Agent) => {
    if (onSelectAgent) onSelectAgent(agent.id);
    if (agent.specialization) {
      onChange(agent.specialization);
    }
    setOpen(false);
  };

  return (
    <div className="spec-menu" ref={menuRef}>
      <button
        type="button"
        className={`spec-trigger ${activeAgent ? 'has-active-agent' : ''}`}
        onClick={() => setOpen(!open)}
        title="Seleccionar especialidad o agente jurídico"
      >
        <span className="spec-trigger-icon">
          {activeAgent ? (
            <AgentSymbol icon={activeAgent.icon} size={16} />
          ) : (
            <AgentSymbol icon={currentSpec.id} size={16} color={currentSpec.color} />
          )}
        </span>
        <span className="spec-trigger-name">
          {activeAgent ? activeAgent.name : currentSpec.name}
        </span>
        {activeAgent && <span className="spec-agent-tag">Agente</span>}
        <ChevronDownIcon size={13} className="spec-chevron" />
      </button>

      {open && (
        <div className="spec-dropdown">
          <div className="spec-dropdown-header">
            <span>Especialidades & Agentes Jurídicos</span>
          </div>

          {/* Section 1: Agentes Personalizados y Presets */}
          {agents.length > 0 && (
            <div className="spec-group">
              <div className="spec-group-title">
                <BotIcon size={13} />
                <span>Agentes Jurídicos Especializados</span>
              </div>
              {agents.map((agent) => {
                const isAgentActive = activeAgentId === agent.id;
                return (
                  <button
                    key={agent.id}
                    type="button"
                    className={`spec-option spec-agent-option ${isAgentActive ? 'spec-option-active' : ''}`}
                    onClick={() => handleSelectAgent(agent)}
                  >
                    <span className="spec-option-icon">
                      <AgentSymbol icon={agent.icon} size={17} />
                    </span>
                    <div className="spec-option-text">
                      <div className="spec-option-name-row">
                        <span className="spec-option-name">{agent.name}</span>
                        {agent.is_preset && <span className="spec-badge-preset">Oficial</span>}
                      </div>
                      <div className="spec-option-desc">{agent.description}</div>
                    </div>
                    {isAgentActive && <CheckIcon size={14} className="spec-option-check" />}
                  </button>
                );
              })}
            </div>
          )}

          {/* Section 2: Especialidades de Rama Base */}
          <div className="spec-group">
            <div className="spec-group-title">
              <span>Especialidades Base</span>
            </div>
            {SPECIALIZATIONS.map((spec) => {
              const isSpecActive = !activeAgentId && spec.id === value;
              return (
                <button
                  key={spec.id}
                  type="button"
                  className={`spec-option ${isSpecActive ? 'spec-option-active' : ''}`}
                  onClick={() => handleSelectSpecialization(spec.id)}
                >
                  <span className="spec-option-icon" style={{ color: spec.color }}>
                    <AgentSymbol icon={spec.id} size={17} color={spec.color} />
                  </span>
                  <div className="spec-option-text">
                    <div className="spec-option-name">{spec.name}</div>
                    <div className="spec-option-desc">{spec.description}</div>
                  </div>
                  {isSpecActive && <CheckIcon size={14} className="spec-option-check" />}
                </button>
              );
            })}
          </div>

          {/* Section 3: Create Agent Action Footer */}
          {onOpenAgentCreator && (
            <div className="spec-dropdown-footer">
              <button
                type="button"
                className="spec-create-agent-btn"
                onClick={() => {
                  setOpen(false);
                  onOpenAgentCreator();
                }}
              >
                <PlusIcon size={14} />
                <span>Crear nuevo agente jurídico</span>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
