import { useState, FormEvent } from 'react';
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

interface InteractiveFormCardProps {
  title: string;
  description?: string;
  fields: FormField[];
  submitLabel?: string;
  onSubmitForm: (formattedPrompt: string) => void;
}

export function InteractiveFormCard({
  title,
  description,
  fields,
  submitLabel = 'Generar documento con estos datos',
  onSubmitForm,
}: InteractiveFormCardProps) {
  const [formData, setFormData] = useState<Record<string, string>>({});

  const handleChange = (name: string, value: string) => {
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    e.stopPropagation();

    // Format fields into a clear legal instruction prompt for Claude
    const fieldLines = fields.map((f) => {
      const val = formData[f.name]?.trim() || '[No especificado]';
      return `• **${f.label}**: ${val}`;
    });

    const fullPrompt = `Por favor procede a redactar el documento con los siguientes datos específicos suministrados:\n\n**${title}**\n${fieldLines.join('\n')}\n\nIncluye todas las cláusulas legales y formato oficial descargable.`;

    onSubmitForm(fullPrompt);
  };

  return (
    <div className="interactive-form-card">
      <div className="form-card-header">
        <div className="form-card-badge">Formulario Jurídico</div>
        <h4 className="form-card-title">{title}</h4>
        {description && <p className="form-card-desc">{description}</p>}
      </div>

      <form onSubmit={handleSubmit} className="form-card-body">
        <div className="form-fields-grid">
          {fields.map((field) => (
            <div key={field.name} className="form-field-group">
              <label htmlFor={`form-input-${field.name}`} className="form-field-label">
                {field.label}
                {field.required && <span className="field-required">*</span>}
              </label>

              {field.type === 'select' && field.options ? (
                <select
                  id={`form-input-${field.name}`}
                  className="form-field-input form-field-select"
                  value={formData[field.name] || ''}
                  onChange={(e) => handleChange(field.name, e.target.value)}
                  required={field.required}
                >
                  <option value="">Selecciona una opción...</option>
                  {field.options.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  id={`form-input-${field.name}`}
                  type={field.type || 'text'}
                  className="form-field-input"
                  placeholder={field.placeholder || `Ingresa ${field.label.toLowerCase()}`}
                  value={formData[field.name] || ''}
                  onChange={(e) => handleChange(field.name, e.target.value)}
                  required={field.required}
                />
              )}
            </div>
          ))}
        </div>

        <div className="form-card-footer">
          <button type="submit" className="form-submit-btn">
            <SparklesIcon size={15} />
            <span>{submitLabel}</span>
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
      }
    }
  }

  if (currentField && currentField.name && currentField.label) {
    fields.push(currentField as FormField);
  }

  // Fallback if no structured fields were parsed
  if (fields.length === 0) {
    fields.push(
      { name: 'nombre_partes', label: 'Nombre Completo de las Partes', placeholder: 'Ej. Arrendador y Arrendatario' },
      { name: 'identificacion', label: 'Documentos de Identidad (C.C. / NIT)', placeholder: 'Ej. C.C. 1.020.345.678' },
      { name: 'objeto_motivo', label: 'Objeto, Motivo o Hechos Principales', placeholder: 'Ej. Arrendamiento de apartamento en Bogotá' }
    );
  }

  return { title, description, fields };
}
