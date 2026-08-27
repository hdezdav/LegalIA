import { useState } from 'react';
import { PromptTemplate } from '../../types';
import { generateUUID } from '../../utils';
import { PlusIcon, TrashIcon, SearchIcon, StarIcon, StarFilledIcon, FileTextIcon } from '../Icons';

interface PromptsViewProps {
  prompts: PromptTemplate[];
  onSave: (prompt: PromptTemplate) => void;
  onDelete: (id: string) => void;
  onUse: (promptBody: string) => void;
}

export function PromptsView({
  prompts,
  onSave,
  onDelete,
  onUse,
}: PromptsViewProps) {
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [editingPrompt, setEditingPrompt] = useState<PromptTemplate | null>(null);

  const categories = ['all', ...new Set(prompts.map((p) => p.category || 'General'))];

  const filtered = prompts.filter((p) => {
    const matchesSearch =
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.body.toLowerCase().includes(search.toLowerCase());
    const matchesCategory =
      categoryFilter === 'all' || (p.category || 'General') === categoryFilter;
    return matchesSearch && matchesCategory;
  });

  const handleToggleFavorite = (prompt: PromptTemplate) => {
    onSave({ ...prompt, favorite: !prompt.favorite, updated_at: Date.now() });
  };

  const handleCreateNew = () => {
    setEditingPrompt({
      id: generateUUID(),
      name: '',
      body: '',
      description: '',
      category: 'General',
      favorite: false,
      created_at: Date.now(),
      updated_at: Date.now(),
    });
  };

  const handleSaveForm = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingPrompt || !editingPrompt.name.trim() || !editingPrompt.body.trim()) return;
    onSave(editingPrompt);
    setEditingPrompt(null);
  };

  return (
    <div className="sidepanel-content">
      {/* Header Search & Add */}
      <div className="sidepanel-header-row">
        <div className="sidepanel-search-box">
          <SearchIcon size={14} className="search-icon" />
          <input
            type="text"
            placeholder="Buscar plantillas..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <button
          className="sidepanel-square-btn"
          onClick={handleCreateNew}
          title="Crear plantilla de prompt"
        >
          <PlusIcon size={16} />
        </button>
      </div>

      {/* Category Pills */}
      <div className="sidepanel-category-chips">
        {categories.map((cat) => (
          <button
            key={cat}
            className={`category-chip ${categoryFilter === cat ? 'active' : ''}`}
            onClick={() => setCategoryFilter(cat)}
          >
            {cat === 'all' ? 'Todos' : cat}
          </button>
        ))}
      </div>

      {/* Body List */}
      <div className="sidepanel-body-scroll">
        {filtered.length === 0 ? (
          <div className="sidepanel-empty-card">
            <div className="empty-card-icon-circle">
              <FileTextIcon size={24} />
            </div>
            <h3 className="empty-card-title">Sin plantillas</h3>
            <p className="empty-card-desc">
              Crea plantillas reutilizables para tutelas, contratos, demandas o recursos jurídicos.
            </p>
          </div>
        ) : (
          <div className="sidepanel-items-stack">
            {filtered.map((prompt) => (
              <div key={prompt.id} className="sidepanel-prompt-card">
                <div className="prompt-card-header">
                  <span className="prompt-title">{prompt.name}</span>
                  <div className="prompt-header-actions">
                    <button
                      className="prompt-icon-btn"
                      onClick={() => handleToggleFavorite(prompt)}
                      title={prompt.favorite ? 'Quitar de favoritos' : 'Marcar favorito'}
                    >
                      {prompt.favorite ? <StarFilledIcon size={14} /> : <StarIcon size={14} />}
                    </button>
                    <button
                      className="prompt-icon-btn"
                      onClick={() => onDelete(prompt.id)}
                      title="Eliminar plantilla"
                    >
                      <TrashIcon size={14} />
                    </button>
                  </div>
                </div>
                {prompt.description && (
                  <p className="prompt-card-desc">{prompt.description}</p>
                )}
                <div className="prompt-card-body-preview">{prompt.body}</div>
                <div className="prompt-card-footer">
                  <span className="prompt-cat-badge">{prompt.category || 'General'}</span>
                  <button
                    className="btn-use-prompt"
                    onClick={() => onUse(prompt.body)}
                  >
                    Usar en consulta
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal Editor */}
      {editingPrompt && (
        <div className="sidepanel-modal-overlay" onClick={() => setEditingPrompt(null)}>
          <div className="sidepanel-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{editingPrompt.name ? 'Editar Plantilla' : 'Nueva Plantilla'}</h3>
              <button className="modal-close-btn" onClick={() => setEditingPrompt(null)}>
                ✕
              </button>
            </div>
            <form onSubmit={handleSaveForm} className="modal-form">
              <div className="form-group">
                <label>Nombre de la plantilla</label>
                <input
                  type="text"
                  placeholder="ej. Minuta de Derecho de Petición"
                  value={editingPrompt.name}
                  onChange={(e) =>
                    setEditingPrompt({ ...editingPrompt, name: e.target.value })
                  }
                  required
                />
              </div>
              <div className="form-group">
                <label>Categoría</label>
                <input
                  type="text"
                  placeholder="ej. Constitucional, Laboral, Civil"
                  value={editingPrompt.category}
                  onChange={(e) =>
                    setEditingPrompt({ ...editingPrompt, category: e.target.value })
                  }
                />
              </div>
              <div className="form-group">
                <label>Contenido del Prompt</label>
                <textarea
                  placeholder="Redacta un derecho de petición dirigido a {{entidad}} solicitando..."
                  value={editingPrompt.body}
                  onChange={(e) =>
                    setEditingPrompt({ ...editingPrompt, body: e.target.value })
                  }
                  rows={4}
                  required
                />
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn-cancel"
                  onClick={() => setEditingPrompt(null)}
                >
                  Cancelar
                </button>
                <button type="submit" className="btn-save">
                  Guardar Plantilla
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
