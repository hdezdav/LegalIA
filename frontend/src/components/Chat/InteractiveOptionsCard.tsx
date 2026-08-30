import { useState } from 'react';
import { CheckIcon, EditIcon, XIcon } from '../Icons';
import './InteractiveOptionsCard.css';

export interface OptionItem {
  id: string;
  title: string;
  description?: string;
  icon?: string;
}

export interface ParsedQuestionOptions {
  title?: string;
  options: OptionItem[];
}

interface InteractiveOptionsCardProps {
  title?: string;
  description?: string;
  options: OptionItem[] | string[];
  disabled?: boolean;
  onSelectOption: (optionText: string) => void;
}

export function InteractiveOptionsCard({
  title,
  description,
  options,
  disabled = false,
  onSelectOption,
}: InteractiveOptionsCardProps) {
  const [selectedText, setSelectedText] = useState<string | null>(null);
  const [isDismissed, setIsDismissed] = useState(false);

  const normalizedOptions: OptionItem[] = options.slice(0, 5).map((opt, idx) => {
    if (typeof opt === 'string') {
      const parts = opt.split(' - ');
      return {
        id: `opt-${idx}`,
        title: parts[0].trim(),
        description: parts.length > 1 ? parts.slice(1).join(' - ').trim() : undefined,
      };
    }
    return opt;
  });

  if (isDismissed || normalizedOptions.length === 0) return null;

  const handleClick = (e: React.MouseEvent, opt: OptionItem) => {
    e.preventDefault();
    e.stopPropagation();
    if (disabled || selectedText) return;

    const fullText = opt.description ? `${opt.title}: ${opt.description}` : opt.title;
    setSelectedText(opt.title);
    onSelectOption(fullText);
  };

  const handleCustomInput = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    // Focus the chat input box smoothly
    const inputEl = document.querySelector('.chat-input, textarea') as HTMLTextAreaElement | HTMLInputElement | null;
    if (inputEl) {
      inputEl.focus();
    }
  };

  const isResolved = disabled || Boolean(selectedText);

  return (
    <section 
      className={`claude-options-card ${isResolved ? 'options-card-resolved' : ''}`} 
      aria-label={title || 'Opciones de respuesta'}
    >
      <div className="claude-options-header">
        <span className="claude-options-title">{title || description || 'Selecciona una opción para continuar:'}</span>
        {!isResolved && (
          <button 
            type="button" 
            className="claude-options-dismiss-btn"
            onClick={() => setIsDismissed(true)}
            title="Ocultar opciones"
            aria-label="Cerrar opciones"
          >
            <XIcon size={14} />
          </button>
        )}
      </div>

      {selectedText ? (
        <div className="options-selected-badge">
          <CheckIcon size={14} className="options-check-icon" />
          <span>Seleccionaste: <strong>{selectedText}</strong></span>
        </div>
      ) : (
        <>
          <div className="claude-options-list">
            {normalizedOptions.map((opt, index) => (
              <button
                key={opt.id}
                type="button"
                className={`claude-option-row ${disabled ? 'disabled' : ''}`}
                onClick={(e) => handleClick(e, opt)}
                disabled={disabled}
                title={opt.description || opt.title}
              >
                <span className="claude-option-number" aria-hidden="true">{index + 1}</span>
                <span className="claude-option-label-wrap">
                  <span className="claude-option-label">{opt.title}</span>
                  {opt.description && <span className="claude-option-desc">{opt.description}</span>}
                </span>
                <span className="claude-option-enter" aria-hidden="true">↵</span>
              </button>
            ))}
          </div>

          {!disabled && (
            <div className="claude-options-bottom-bar">
              <button
                type="button"
                className="claude-option-custom-btn"
                onClick={handleCustomInput}
                title="Escribir una respuesta personalizada"
              >
                <EditIcon size={13} />
                <span>Algo más</span>
              </button>

              <button
                type="button"
                className="claude-option-skip-btn"
                onClick={() => setIsDismissed(true)}
                title="Omitir selección de opciones"
              >
                Omitir
              </button>
            </div>
          )}
        </>
      )}
    </section>
  );
}

/**
 * Parser helper to convert raw markdown or JSON tool outputs to structured options.
 */
export function parseOptionsMarkdown(content: string): ParsedQuestionOptions {
  const trimmed = content.trim();
  
  // 1. Try parsing JSON format (e.g. from tool calls or JSON code blocks)
  if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
    try {
      const parsed = JSON.parse(trimmed);
      if (parsed.preguntas && Array.isArray(parsed.preguntas) && parsed.preguntas.length > 0) {
        const first = parsed.preguntas[0];
        const title = first.pregunta || first.title;
        const rawOpts = first.opciones || first.options || [];
        const options: OptionItem[] = rawOpts.map((o: any, idx: number) => ({
          id: `opt-${idx}`,
          title: typeof o === 'string' ? o : o.title || String(o),
          description: typeof o === 'object' ? o.description : undefined,
        }));
        return { title, options };
      }
      if (parsed.opciones && Array.isArray(parsed.opciones)) {
        const title = parsed.pregunta || parsed.title;
        const options: OptionItem[] = parsed.opciones.map((o: any, idx: number) => ({
          id: `opt-${idx}`,
          title: typeof o === 'string' ? o : o.title || String(o),
          description: typeof o === 'object' ? o.description : undefined,
        }));
        return { title, options };
      }
    } catch {
      // Fall through to markdown line parsing
    }
  }

  // 2. Parse Markdown lines format
  const lines = trimmed.split('\n');
  let title: string | undefined;
  const options: OptionItem[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;

    if (/^(title|pregunta):/i.test(line)) {
      title = line.replace(/^(title|pregunta):\s*/i, '').trim() || undefined;
      continue;
    }

    if (line.startsWith('- ') || line.startsWith('* ') || /^\d+\.\s+/.test(line)) {
      const cleanLine = line.replace(/^([-\*]|\d+\.)\s+(\[[\sxX]\]\s*)?/, '').trim();
      if (!cleanLine) continue;

      const splitMatch = cleanLine.split(/[:\-\–]\s+/);
      const optTitle = splitMatch[0].replace(/^\[|\]$/g, '').trim();
      const optDesc = splitMatch.length > 1 ? splitMatch.slice(1).join(' - ').trim() : undefined;

      options.push({
        id: `opt-${options.length}`,
        title: optTitle,
        description: optDesc,
      });
    } else if (line.startsWith('[') && line.endsWith(']')) {
      options.push({
        id: `opt-${options.length}`,
        title: line.slice(1, -1).trim(),
      });
    }
  }

  if (options.length === 0 && lines.length > 0) {
    lines.forEach((l, idx) => {
      if (l.trim()) {
        options.push({
          id: `opt-${idx}`,
          title: l.trim(),
        });
      }
    });
  }

  return { title, options };
}
