import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent as ReactKeyboardEvent } from 'react';
import { SparklesIcon } from '../Icons';
import './InteractiveFormCard.css';

export interface FormField {
  name: string;
  label: string;
  placeholder?: string;
  type?: 'text' | 'date' | 'number' | 'select';
  options?: string[];
  required?: boolean;
}

export interface InteractiveFormCardProps {
  title: string;
  description?: string;
  fields: FormField[];
  submitLabel?: string;
  onSubmitForm: (formattedPrompt: string) => void;
  onDismiss?: () => void;
}

export function InteractiveFormCard({
  title,
  description,
  fields,
  submitLabel = 'Generar documento',
  onSubmitForm,
  onDismiss,
}: InteractiveFormCardProps) {
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, boolean>>({});
  const [currentIndex, setCurrentIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const currentField = fields[currentIndex];
  const currentValue = currentField ? formData[currentField.name] || '' : '';

  useEffect(() => {
    if (!onDismiss) return;
    const handleEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key === 'Escape') onDismiss();
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [onDismiss]);

  const handleChange = (name: string, value: string) => {
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: false }));
    }
  };

  useEffect(() => {
    inputRef.current?.focus();
  }, [currentIndex]);

  const advance = (value = currentValue, allowEmpty = false) => {
    if (!currentField) return;
    if (currentField.required && !value.trim() && !allowEmpty) {
      setErrors((prev) => ({ ...prev, [currentField.name]: true }));
      return;
    }
    if (currentIndex < fields.length - 1) {
      setCurrentIndex((prev) => prev + 1);
    } else {
      handleSubmit(undefined, { ...formData, [currentField.name]: value });
    }
  };

  const handleFieldKeyDown = (event: ReactKeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      advance();
    }
  };

  const handleSubmit = (e?: FormEvent, values = formData) => {
    e?.preventDefault();
    e?.stopPropagation();

    // Check required fields
    const newErrors: Record<string, boolean> = {};
    let hasError = false;

    fields.forEach((field) => {
      if (field.required && !values[field.name]?.trim()) {
        newErrors[field.name] = true;
        hasError = true;
      }
    });

    if (hasError) {
      setErrors(newErrors);
      return;
    }

    // Format fields into a clear legal prompt for the LLM
    const fieldLines = fields.map((f) => {
      const val = values[f.name]?.trim() || '[No especificado]';
      return `• **${f.label}**: ${val}`;
    });

    const fullPrompt = `Por favor procede a redactar el documento con los siguientes datos específicos suministrados:\n\n**${title}**\n${fieldLines.join('\n')}\n\nGenera la minuta en un bloque descargable.`;

    onSubmitForm(fullPrompt);
  };

  if (fields.length === 0 || !currentField) return null;

  const hasError = errors[currentField.name];
  const isLastField = currentIndex === fields.length - 1;

  return (
    <div className="apple-form-card" aria-label="Formulario de datos jurídicos">
      <div className="apple-form-header">
        <div className="apple-form-title-group">
          <span className="apple-form-step">Pregunta {currentIndex + 1} de {fields.length}</span>
          <h4 className="apple-form-title">{title}</h4>
          {description && <p className="apple-form-description">{description}</p>}
        </div>
        {onDismiss && (
          <button
            type="button"
            className="apple-form-close-btn"
            onClick={onDismiss}
            title="Cerrar formulario"
            aria-label="Cerrar formulario"
          >
            ×
          </button>
        )}
      </div>

      <form onSubmit={(event) => { event.preventDefault(); advance(); }} className="apple-form-body">
        <div className="apple-form-fields-group">
          <div className="apple-form-field">
            <label htmlFor={`field-${currentField.name}`} className="apple-field-label">
              <span>{currentField.label}</span>
              {currentField.required && <span className="apple-field-required">*</span>}
            </label>

            {currentField.type === 'select' && currentField.options?.length ? (
              <>
                <div className="apple-option-list" role="listbox" aria-label={currentField.label}>
                  {currentField.options.map((option, index) => (
                    <button
                      key={option}
                      type="button"
                      role="option"
                      aria-selected={currentValue === option}
                      className={`apple-option-row ${currentValue === option ? 'is-selected' : ''}`}
                      onClick={() => {
                        handleChange(currentField.name, option);
                        advance(option);
                      }}
                      onKeyDown={(event) => {
                        if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return;
                        event.preventDefault();
                        const buttons = Array.from(
                          event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>('.apple-option-row') || []
                        );
                        const nextIndex = index + (event.key === 'ArrowDown' ? 1 : -1);
                        buttons[nextIndex]?.focus();
                      }}
                    >
                      <span className="apple-option-number">{index + 1}</span>
                      <span>{option}</span>
                      <span className="apple-option-check" aria-hidden="true">{currentValue === option ? '✓' : ''}</span>
                    </button>
                  ))}
                </div>
                <select
                  id={`field-${currentField.name}`}
                  className={`apple-field-input apple-field-select ${hasError ? 'apple-field-error' : ''}`}
                  value={currentValue}
                  onChange={(event) => {
                    handleChange(currentField.name, event.target.value);
                    if (event.target.value) advance(event.target.value);
                  }}
                >
                  <option value="">Selecciona una opción…</option>
                  {currentField.options.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
              </>
            ) : (
              <input
                ref={inputRef}
                id={`field-${currentField.name}`}
                type={currentField.type || 'text'}
                className={`apple-field-input ${hasError ? 'apple-field-error' : ''}`}
                placeholder={currentField.placeholder || `Escribe ${currentField.label.toLowerCase()}`}
                value={currentValue}
                onChange={(event) => handleChange(currentField.name, event.target.value)}
                onKeyDown={handleFieldKeyDown}
                aria-invalid={hasError || undefined}
              />
            )}

            {hasError && <span className="apple-field-error-text">Este campo es obligatorio</span>}
          </div>
        </div>

        <div className="apple-form-actions">
          {currentIndex > 0 && (
            <button type="button" className="apple-form-btn-secondary" onClick={() => setCurrentIndex((prev) => prev - 1)}>
              Atrás
            </button>
          )}
          {onDismiss && (
            <button
              type="button"
              className="apple-form-btn-secondary"
              onClick={() => advance('', true)}
              disabled={currentField.required}
              title={currentField.required ? 'Este campo es obligatorio' : 'Omitir esta pregunta'}
            >
              Omitir
            </button>
          )}
          <button type="submit" className="apple-form-btn-primary">
            <SparklesIcon size={14} />
            <span>{isLastField ? submitLabel : 'Continuar'}</span>
          </button>
        </div>
      </form>
    </div>
  );
}

/**
 * Parses raw text from ```legal-form block into structured fields.
 */
export function parseFormMarkdown(content: string): {
  title: string;
  description?: string;
  fields: FormField[];
} {
  const lines = content.trim().split('\n');
  let title = 'Datos para elaboración del documento';
  let description: string | undefined;
  const fields: FormField[] = [];

  let currentField: Partial<FormField> | null = null;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;

    if (line.startsWith('title:') || line.startsWith('titulo:')) {
      title = line.replace(/^(title|titulo):\s*/i, '').trim();
      continue;
    }

    if (line.startsWith('description:') || line.startsWith('descripcion:')) {
      description = line.replace(/^(description|descripcion):\s*/i, '').trim();
      continue;
    }

    if (line.startsWith('- label:') || line.startsWith('label:')) {
      if (currentField && currentField.name && currentField.label) {
        fields.push(currentField as FormField);
      }
      const labelVal = line.replace(/^(-\s*)?label:\s*/i, '').trim();
      const slugName = labelVal.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
      currentField = {
        name: slugName || `field_${fields.length + 1}`,
        label: labelVal,
        type: 'text',
      };
      continue;
    }

    if (currentField) {
      if (line.startsWith('name:')) {
        currentField.name = line.replace(/^name:\s*/i, '').trim();
      } else if (line.startsWith('placeholder:')) {
        currentField.placeholder = line.replace(/^placeholder:\s*/i, '').trim();
      } else if (line.startsWith('type:')) {
        currentField.type = line.replace(/^type:\s*/i, '').trim() as any;
      } else if (line.startsWith('options:')) {
        const rawOpts = line.replace(/^options:\s*/i, '').trim();
        currentField.options = rawOpts.split(',').map((s) => s.trim()).filter(Boolean);
        currentField.type = 'select';
      } else if (line.startsWith('required:')) {
        currentField.required = /^(true|yes|si|sí|required)$/i.test(line.replace(/^required:\s*/i, '').trim());
      }
    }
  }

  if (currentField && currentField.name && currentField.label) {
    fields.push(currentField as FormField);
  }

  // Fallback if no structured fields were parsed
  if (fields.length === 0) {
    fields.push(
      { name: 'nombre_partes', label: 'Nombre de las Partes', placeholder: 'Ej. Arrendador y Arrendatario', required: true },
      { name: 'identificacion', label: 'Identificación (C.C. / NIT)', placeholder: 'Ej. C.C. 1.020.345.678' },
      { name: 'motivo_principal', label: 'Motivo o Pretensión', placeholder: 'Ej. Arrendamiento de inmueble', required: true }
    );
  }

  return { title, description, fields };
}
