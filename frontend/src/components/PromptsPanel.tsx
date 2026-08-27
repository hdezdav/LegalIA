import { useState } from 'react';
import { PromptTemplate } from '../types';
import { parseVariables, fillTemplate } from '../library';
import { getTranslations } from '../i18n';
import { generateUUID } from '../utils';
import { PlusIcon, StarIcon, StarFilledIcon, EditIcon, TrashIcon, CopyIcon, SearchIcon } from './Icons';
import './PromptsPanel.css';

const t = getTranslations('es');

interface PromptsPanelProps {
  prompts: PromptTemplate[];
  onSave: (prompt: PromptTemplate) => void;
  onDelete: (id: string) => void;
  onUse: (filled: string) => void;
  onClose: () => void;
}

export function PromptsPanel({ prompts, onSave, onDelete, onUse, onClose }: PromptsPanelProps) {
  const [view, setView] = useState<'list' | 'editor' | 'filler'>('list');
  const [editing, setEditing] = useState<PromptTemplate | null>(null);
  const [filling, setFilling] = useState<PromptTemplate | null>(null);
  const [variableValues, setVariableValues] = useState<Record<string, string>>({});
  const [search, setSearch] = useState('');

  const [formName, setFormName] = useState('');
  const [formBody, setFormBody] = useState('');
  const [formDescription, setFormDescription] = useState('');
  const [formCategory, setFormCategory] = useState('');

  const filtered = prompts.filter((p) => {
    if (!search) return true;
    const term = search.toLowerCase();
    return (
      p.name.toLowerCase().includes(term) ||
      p.body.toLowerCase().includes(term) ||
      p.description?.toLowerCase().includes(term) ||
      p.category?.toLowerCase().includes(term)
    );
  });

  const favorites = filtered.filter((p) => p.favorite);
  const regular = filtered.filter((p) => !p.favorite);

  const startNew = () => {
    setEditing(null);
    setFormName('');
    setFormBody('');
    setFormDescription('');
    setFormCategory('');
    setView('editor');
  };

  const startEdit = (prompt: PromptTemplate) => {
    setEditing(prompt);
    setFormName(prompt.name);
    setFormBody(prompt.body);
    setFormDescription(prompt.description || '');
    setFormCategory(prompt.category || '');
    setView('editor');
  };

  const handleSave = () => {
    if (!formName.trim() || !formBody.trim()) return;

    const now = Date.now();
    const saved: PromptTemplate = {
      id: editing?.id || generateUUID(),
      name: formName.trim(),
      body: formBody.trim(),
      description: formDescription.trim() || undefined,
      category: formCategory.trim() || undefined,
      favorite: editing?.favorite || false,
      created_at: editing?.created_at || now,
      updated_at: now,
    };

    onSave(saved);
    setView('list');
  };

  const toggleFavorite = (prompt: PromptTemplate) => {
    onSave({ ...prompt, favorite: !prompt.favorite, updated_at: Date.now() });
  };

  const startFill = (prompt: PromptTemplate) => {
    const vars = parseVariables(prompt.body);
    if (vars.length === 0) {
      onUse(prompt.body);
      onClose();
      return;
    }
    setFilling(prompt);
    setVariableValues(
      vars.reduce((acc, v) => {
        acc[v] = '';
        return acc;
      }, {} as Record<string, string>)
    );
    setView('filler');
  };

  const handleFill = () => {
    if (!filling) return;
    const filled = fillTemplate(filling.body, variableValues);
    onUse(filled);
    onClose();
  };

  const handleDuplicate = (prompt: PromptTemplate) => {
    const now = Date.now();
    const duplicate: PromptTemplate = {
      ...prompt,
      id: generateUUID(),
      name: `${prompt.name} (copia)`,
      favorite: false,
      created_at: now,
      updated_at: now,
    };
    onSave(duplicate);
  };

  return (
    <div className="prompts-panel">
      <div className="panel-backdrop" onClick={onClose} />
      <div className="panel-content">
        <header className="panel-header">
          <div>
            <h2 className="panel-title">{t.prompts.title}</h2>
            <p className="panel-subtitle">{t.prompts.subtitle}</p>
          </div>
          {view === 'list' && (
            <button className="btn-primary" onClick={startNew}>
              <PlusIcon size={16} />
              {t.prompts.newPrompt}
            </button>
          )}
        </header>

        {view === 'list' && (
          <>
            <div className="panel-search">
              <SearchIcon size={16} />
              <input
                type="text"
                placeholder={t.prompts.searchPrompts}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="search-input"
              />
            </div>

            <div className="panel-body">
              {filtered.length === 0 && !search && (
                <div className="empty-state">
                  <p className="empty-title">{t.prompts.empty}</p>
                  <p className="empty-hint">{t.prompts.emptyHint}</p>
                </div>
              )}

              {filtered.length === 0 && search && (
                <div className="empty-state">
                  <p className="empty-title">{t.common.none}</p>
                </div>
              )}

              {favorites.length > 0 && (
                <div className="prompt-section">
                  <h3 className="section-label">{t.prompts.favorites}</h3>
                  {favorites.map((p) => (
                    <PromptCard
                      key={p.id}
                      prompt={p}
                      onUse={() => startFill(p)}
                      onEdit={() => startEdit(p)}
                      onDelete={() => onDelete(p.id)}
                      onToggleFavorite={() => toggleFavorite(p)}
                      onDuplicate={() => handleDuplicate(p)}
                    />
                  ))}
                </div>
              )}

              {regular.length > 0 && (
                <div className="prompt-section">
                  {favorites.length > 0 && <h3 className="section-label">{t.common.all}</h3>}
                  {regular.map((p) => (
                    <PromptCard
                      key={p.id}
                      prompt={p}
                      onUse={() => startFill(p)}
                      onEdit={() => startEdit(p)}
                      onDelete={() => onDelete(p.id)}
                      onToggleFavorite={() => toggleFavorite(p)}
                      onDuplicate={() => handleDuplicate(p)}
                    />
                  ))}
                </div>
              )}
            </div>
          </>
        )}

        {view === 'editor' && (
          <div className="panel-body">
            <div className="form-group">
              <label className="form-label">{t.prompts.name}</label>
              <input
                type="text"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                placeholder={t.prompts.namePlaceholder}
                className="form-input"
              />
            </div>

            <div className="form-group">
              <label className="form-label">{t.prompts.body}</label>
              <textarea
                value={formBody}
                onChange={(e) => setFormBody(e.target.value)}
                placeholder={t.prompts.bodyPlaceholder}
                className="form-textarea"
                rows={8}
              />
              <p className="form-hint">{t.prompts.variableSyntaxHint}</p>
              {parseVariables(formBody).length > 0 && (
                <div className="variables-detected">
                  <span className="variables-label">{t.prompts.variablesDetected}:</span>
                  {parseVariables(formBody).map((v) => (
                    <span key={v} className="variable-pill">
                      {v}
                    </span>
                  ))}
                </div>
              )}
            </div>

            <div className="form-group">
              <label className="form-label">
                {t.prompts.description} <span className="form-optional">({t.common.optional})</span>
              </label>
              <input
                type="text"
                value={formDescription}
                onChange={(e) => setFormDescription(e.target.value)}
                placeholder={t.prompts.descriptionPlaceholder}
                className="form-input"
              />
            </div>

            <div className="form-group">
              <label className="form-label">
                {t.prompts.category} <span className="form-optional">({t.common.optional})</span>
              </label>
              <input
                type="text"
                value={formCategory}
                onChange={(e) => setFormCategory(e.target.value)}
                placeholder="Ej. Contratos"
                className="form-input"
              />
            </div>

            <div className="form-actions">
              <button className="btn-secondary" onClick={() => setView('list')}>
                {t.common.cancel}
              </button>
              <button
                className="btn-primary"
                onClick={handleSave}
                disabled={!formName.trim() || !formBody.trim()}
              >
                {t.common.save}
              </button>
            </div>
          </div>
        )}

        {view === 'filler' && filling && (
          <div className="panel-body">
            <p className="filler-title">{t.prompts.fillVariables}</p>
            <p className="filler-hint">{t.prompts.fillVariablesHint}</p>

            {parseVariables(filling.body).map((varName) => (
              <div key={varName} className="form-group">
                <label className="form-label">{varName}</label>
                <input
                  type="text"
                  value={variableValues[varName] || ''}
                  onChange={(e) =>
                    setVariableValues((prev) => ({ ...prev, [varName]: e.target.value }))
                  }
                  className="form-input"
                />
              </div>
            ))}

            <div className="form-actions">
              <button className="btn-secondary" onClick={() => setView('list')}>
                {t.common.cancel}
              </button>
              <button className="btn-primary" onClick={handleFill}>
                {t.prompts.insert}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

interface PromptCardProps {
  prompt: PromptTemplate;
  onUse: () => void;
  onEdit: () => void;
  onDelete: () => void;
  onToggleFavorite: () => void;
  onDuplicate: () => void;
}

function PromptCard({
  prompt,
  onUse,
  onEdit,
  onDelete,
  onToggleFavorite,
  onDuplicate,
}: PromptCardProps) {
  const vars = parseVariables(prompt.body);

  return (
    <div className="prompt-card">
      <div className="prompt-card-header">
        <div className="prompt-card-title-row">
          <h4 className="prompt-card-title">{prompt.name}</h4>
          {prompt.category && <span className="prompt-category">{prompt.category}</span>}
        </div>
        <button className="icon-btn" onClick={onToggleFavorite} title={t.prompts.favorite}>
          {prompt.favorite ? <StarFilledIcon size={16} /> : <StarIcon size={16} />}
        </button>
      </div>

      {prompt.description && <p className="prompt-card-desc">{prompt.description}</p>}

      <p className="prompt-card-preview">{prompt.body.slice(0, 120)}{prompt.body.length > 120 ? '...' : ''}</p>

      {vars.length > 0 && (
        <div className="prompt-card-vars">
          <span className="vars-label">{vars.length} variable{vars.length > 1 ? 's' : ''}</span>
          {vars.map((v) => (
            <span key={v} className="var-tag">
              {v}
            </span>
          ))}
        </div>
      )}

      <div className="prompt-card-actions">
        <button className="card-action-btn" onClick={onUse}>
          {t.prompts.insert}
        </button>
        <button className="icon-btn" onClick={onEdit} title={t.common.edit}>
          <EditIcon size={14} />
        </button>
        <button className="icon-btn" onClick={onDuplicate} title={t.common.duplicate}>
          <CopyIcon size={14} />
        </button>
        <button className="icon-btn" onClick={onDelete} title={t.common.delete}>
          <TrashIcon size={14} />
        </button>
      </div>
    </div>
  );
}
