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
  title,
  description,
  options,
  onSelectOption,
}: InteractiveOptionsCardProps) {
  const normalizedOptions: OptionItem[] = options.slice(0, 3).map((opt, idx) => {
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

  if (normalizedOptions.length === 0) return null;

  const handleClick = (e: React.MouseEvent, opt: OptionItem) => {
    e.preventDefault();
    e.stopPropagation();
    const fullText = opt.description ? `${opt.title}: ${opt.description}` : opt.title;
    onSelectOption(fullText);
  };

  return (
    <section className="interactive-options-card" aria-label={title || 'Opciones de respuesta'}>
      {title && (
        <div className="options-card-header">
          <h3 className="options-card-title">{title}</h3>
          {description && <span className="options-card-desc">{description}</span>}
        </div>
      )}

      <div className="options-list">
        {normalizedOptions.map((opt, index) => (
          <button
            key={opt.id}
            type="button"
            className="option-row-btn"
            onClick={(e) => handleClick(e, opt)}
            title={opt.description || opt.title}
          >
            <span className="option-row-number" aria-hidden="true">{index + 1}</span>
            <span className="option-row-copy">
              <span className="option-row-label">{opt.title}</span>
              {opt.description && <span className="option-row-description">{opt.description}</span>}
            </span>
            <span className="option-row-enter" aria-hidden="true">↵</span>
          </button>
        ))}
      </div>
      <span className="options-card-hint">Selecciona una opción para continuar</span>
    </section>
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
