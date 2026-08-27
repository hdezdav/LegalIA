import { useState, useRef, useEffect } from 'react';
import { LegalSpecializationId } from '../types';
import { SPECIALIZATIONS } from '../constants';
import {
  ChevronDownIcon,
  ScalesIcon,
  ScrollIcon,
  LandmarkIcon,
  ZapIcon,
  BriefcaseIcon,
  BuildingIcon,
  TrendingUpIcon,
  CoinsIcon,
} from './Icons';
import './SpecializationMenu.css';

interface SpecializationMenuProps {
  value: LegalSpecializationId;
  onChange: (id: LegalSpecializationId) => void;
}

export function SpecializationIcon({ id, size = 16, className }: { id: LegalSpecializationId; size?: number; className?: string }) {
  switch (id) {
    case 'constitucional':
      return <ScrollIcon size={size} className={className} />;
    case 'civil':
      return <LandmarkIcon size={size} className={className} />;
    case 'penal':
      return <ZapIcon size={size} className={className} />;
    case 'laboral':
      return <BriefcaseIcon size={size} className={className} />;
    case 'administrativo':
      return <BuildingIcon size={size} className={className} />;
    case 'comercial':
      return <TrendingUpIcon size={size} className={className} />;
    case 'tributario':
      return <CoinsIcon size={size} className={className} />;
    case 'general':
    default:
      return <ScalesIcon size={size} className={className} />;
  }
}

export function SpecializationMenu({ value, onChange }: SpecializationMenuProps) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const current = SPECIALIZATIONS.find((s) => s.id === value) || SPECIALIZATIONS[0];

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

  const handleSelect = (id: LegalSpecializationId) => {
    onChange(id);
    setOpen(false);
  };

  return (
    <div className="spec-menu" ref={menuRef}>
      <button className="spec-trigger" onClick={() => setOpen(!open)}>
        <span className="spec-trigger-icon" style={{ color: current.color }}>
          <SpecializationIcon id={current.id} size={16} />
        </span>
        <span className="spec-trigger-name">{current.name}</span>
        <ChevronDownIcon size={14} />
      </button>

      {open && (
        <div className="spec-dropdown">
          {SPECIALIZATIONS.map((spec) => (
            <button
              key={spec.id}
              className={`spec-option ${spec.id === value ? 'spec-option-active' : ''}`}
              onClick={() => handleSelect(spec.id)}
            >
              <span className="spec-option-icon" style={{ color: spec.color }}>
                <SpecializationIcon id={spec.id} size={18} />
              </span>
              <div className="spec-option-text">
                <div className="spec-option-name">{spec.name}</div>
                <div className="spec-option-desc">{spec.description}</div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
