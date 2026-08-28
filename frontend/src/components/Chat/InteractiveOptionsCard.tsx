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
  onSelectOption: (optionText: string) => void;
}

export function InteractiveOptionsCard({
  title = 'Selecciona una opción para continuar:',
  description,
  options,
  onSelectOption,
}: InteractiveOptionsCardProps) {
  const normalizedOptions: OptionItem[] = options.map((opt, idx) => {
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

  const handleClick = (e: React.MouseEvent, opt: OptionItem) => {
    e.preventDefault();
    e.stopPropagation();
    const fullText = opt.description ? `${opt.title}: ${opt.description}` : opt.title;
    onSelectOption(fullText);
  };

  return (
    <div className="interactive-options-card">
      <div className="options-card-header">
        <div className="options-card-badge">Opción guiada</div>
        <h4 className="options-card-title">{title}</h4>
        {description && <p className="options-card-desc">{description}</p>}
      </div>

      <div className="options-grid">
        {normalizedOptions.map((opt) => (
          <button
            key={opt.id}
            type="button"
            className="option-chip-btn"
            onClick={(e) => handleClick(e, opt)}
          >
            <div className="option-chip-indicator">
              <span className="option-radio-dot" />
            </div>
            <div className="option-chip-text">
              <span className="option-chip-title">{opt.title}</span>
              {opt.description && (
                <span className="option-chip-sub">{opt.description}</span>
              )}
            </div>
            <span className="option-arrow">→</span>
          </button>
        ))}
      </div>
    </div>
  );
}

/**
 * Parser helper to convert raw markdown text inside ```interactive-options block to items.
 */
export function parseOptionsMarkdown(content: string): ParsedQuestionOptions {
  const lines = content.trim().split('\n');
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
