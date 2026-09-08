import { useState, useRef, useEffect } from 'react';
import { api } from '../api';
import { ChevronDownIcon } from './Icons';
import './ModelSelector.css';

// Provider Logo Component with Crisp Inline SVGs (Claude, OpenAI, Google, xAI, Legalia)
export function ProviderLogo({ provider, size = 18 }: { provider: string; size?: number }) {
  if (provider === 'Anthropic' || provider === 'Claude') {
    return (
      <svg width={size} height={size} viewBox="0 0 100 100" fill="#CC6747" style={{ flexShrink: 0 }}>
        <path d="m19.6 66.5 19.7-11 .3-1-.3-.5h-1l-3.3-.2-11.2-.3L14 53l-9.5-.5-2.4-.5L0 49l.2-1.5 2-1.3 2.9.2 6.3.5 9.5.6 6.9.4L38 49.1h1.6l.2-.7-.5-.4-.4-.4L29 41l-10.6-7-5.6-4.1-3-2-1.5-2-.6-4.2 2.7-3 3.7.3.9.2 3.7 2.9 8 6.1L37 36l1.5 1.2.6-.4.1-.3-.7-1.1L33 25l-6-10.4-2.7-4.3-.7-2.6c-.3-1-.4-2-.4-3l3-4.2L28 0l4.2.6L33.8 2l2.6 6 4.1 9.3L47 29.9l2 3.8 1 3.4.3 1h.7v-.5l.5-7.2 1-8.7 1-11.2.3-3.2 1.6-3.8 3-2L61 2.6l2 2.9-.3 1.8-1.1 7.7L59 27.1l-1.5 8.2h.9l1-1.1 4.1-5.4 6.9-8.6 3-3.5L77 13l2.3-1.8h4.3l3.1 4.7-1.4 4.9-4.4 5.6-3.7 4.7-5.3 7.1-3.2 5.7.3.4h.7l12-2.6 6.4-1.1 7.6-1.3 3.5 1.6.4 1.6-1.4 3.4-8.2 2-9.6 2-14.3 3.3-.2.1.2.3 6.4.6 2.8.2h6.8l12.6 1 3.3 2 1.9 2.7-.3 2-5.1 2.6-6.8-1.6-16-3.8-5.4-1.3h-.8v.4l4.6 4.5 8.3 7.5L89 80.1l.5 2.4-1.3 2-1.4-.2-9.2-7-3.6-3-8-6.8h-.5v.7l1.8 2.7 9.8 14.7.5 4.5-.7 1.4-2.6 1-2.7-.6-5.8-8-6-9-4.7-8.2-.5.4-2.9 30.2-1.3 1.5-3 1.2-2.5-2-1.4-3 1.4-6.2 1.6-8 1.3-6.4 1.2-7.9.7-2.6v-.2H49L43 72l-9 12.3-7.2 7.6-1.7.7-3-1.5.3-2.8L24 86l10-12.8 6-7.9 4-4.6-.1-.5h-.3L17.2 77.4l-4.7.6-2-2 .2-3 1-1 8-5.5Z"/>
      </svg>
    );
  }

  if (provider === 'OpenAI') {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" style={{ flexShrink: 0, color: 'var(--text-primary)' }}>
        <path d="M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.985 5.985 0 0 0-3.998 2.9 6.046 6.046 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073zM13.26 22.43a4.476 4.476 0 0 1-2.876-1.04l.141-.081 4.779-2.758a.795.795 0 0 0 .392-.681v-6.737l2.02 1.168a.071.071 0 0 1 .038.052v5.583a4.504 4.504 0 0 1-4.494 4.494zM3.6 18.304a4.47 4.47 0 0 1-.535-3.014l.142.085 4.783 2.759a.771.771 0 0 0 .78 0l5.843-3.369v2.332a.08.08 0 0 1-.033.062L9.74 19.95a4.5 4.5 0 0 1-6.14-1.646zM2.34 7.896a4.485 4.485 0 0 1 2.366-1.973V11.6a.766.766 0 0 0 .388.676l5.815 3.355-2.02 1.168a.076.076 0 0 1-.071 0l-4.83-2.786A4.504 4.504 0 0 1 2.34 7.872zm16.597 3.855l-5.833-3.387L15.119 7.2a.076.076 0 0 1 .071 0l4.83 2.791a4.494 4.494 0 0 1-.676 8.105v-5.678a.79.79 0 0 0-.407-.667zm2.01-3.023l-.141-.085-4.774-2.782a.776.776 0 0 0-.785 0L9.409 9.23V6.897a.066.066 0 0 1 .028-.061l4.83-2.787a4.5 4.5 0 0 1 6.68 4.66zm-12.64 4.135l-2.02-1.164a.08.08 0 0 1-.038-.057V6.075a4.5 4.5 0 0 1 7.375-3.453l-.142.08L8.704 5.46a.795.795 0 0 0-.393.681zm1.097-2.365l2.602-1.5 2.607 1.5v2.999l-2.597 1.5-2.612-1.5z" />
      </svg>
    );
  }

  if (provider === 'Google') {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" style={{ flexShrink: 0 }}>
        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
      </svg>
    );
  }

  if (provider === 'xAI') {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" style={{ flexShrink: 0, color: 'var(--text-primary)' }}>
        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
      </svg>
    );
  }

  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, color: 'var(--text-primary)' }}>
      <path d="M12 2L2 7v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  );
}

export interface ScrapedModelOption {
  id: string;
  name: string;
  provider: 'Anthropic' | 'Google' | 'OpenAI' | 'xAI' | 'Legalia';
  description: string;
  badge?: string;
  owned_by?: string;
}

const DEFAULT_MODELS: ScrapedModelOption[] = [
  // Legalia
  {
    id: 'legalia',
    name: 'Legalia Auto',
    provider: 'Legalia',
    description: 'Enrutador jurídico automático con verificación RAG estricta',
    badge: 'RAG Verificado',
  },

  // Anthropic Claude Models
  {
    id: 'claude-sonnet-4.6',
    name: 'Claude Sonnet 4.6',
    provider: 'Anthropic',
    description: 'Máxima precisión en razonamiento procesal y jurisprudencia colombiana',
    badge: 'Recomendado',
  },
  {
    id: 'claude-sonnet-5',
    name: 'Claude Sonnet 5',
    provider: 'Anthropic',
    description: 'Excelente balance velocidad/precisión en redacción jurídica',
  },
  {
    id: 'claude-opus-5',
    name: 'Claude Opus 5',
    provider: 'Anthropic',
    description: 'Análisis profundo de casaciones y expedientes extensos',
  },
  {
    id: 'claude-opus-4.8',
    name: 'Claude Opus 4.8',
    provider: 'Anthropic',
    description: 'Versión optimizada para análisis de precedentes jurisprudenciales',
  },
  {
    id: 'claude-opus-4.6',
    name: 'Claude Opus 4.6',
    provider: 'Anthropic',
    description: 'Modelo robusto para investigación normativa compleja',
  },
  {
    id: 'claude-haiku-4.5',
    name: 'Claude Haiku 4.5',
    provider: 'Anthropic',
    description: 'Respuestas procesales ultrarrápidas y de bajo costo',
    badge: 'Rápido',
  },

  // OpenAI GPT Models
  {
    id: 'gpt-5.6-sol',
    name: 'GPT-5.6 Sol',
    provider: 'OpenAI',
    description: 'Generación creativa y estructuración de minutas contractuales',
  },
  {
    id: 'gpt-5.6-terra',
    name: 'GPT-5.6 Terra',
    provider: 'OpenAI',
    description: 'Modelo optimizado para análisis documental y síntesis',
  },
  {
    id: 'gpt-5.6-luna',
    name: 'GPT-5.6 Luna',
    provider: 'OpenAI',
    description: 'Análisis jurídico multimodal y generación de argumentos',
  },
  {
    id: 'gpt-5.5',
    name: 'GPT-5.5',
    provider: 'OpenAI',
    description: 'Redacción de demandas y escritos jurídicos estructurados',
  },
  {
    id: 'gpt-5.4',
    name: 'GPT-5.4',
    provider: 'OpenAI',
    description: 'Modelo estable para consultas jurídicas generales',
  },
  {
    id: 'gpt-5.4-mini',
    name: 'GPT-5.4 Mini',
    provider: 'OpenAI',
    description: 'Versión eficiente para consultas rápidas y borradores',
    badge: 'Económico',
  },

  // Google Gemini Models
  {
    id: 'gemini-3.7-flash',
    name: 'Gemini 3.7 Flash',
    provider: 'Google',
    description: 'Motor multimodal de alta velocidad para expedientes y doctrinas',
    badge: 'Rápido',
  },
  {
    id: 'gemini-3.6-flash',
    name: 'Gemini 3.6 Flash',
    provider: 'Google',
    description: 'Procesamiento ultrarrápido de documentos extensos',
  },
  {
    id: 'gemini-3.5-flash',
    name: 'Gemini 3.5 Flash',
    provider: 'Google',
    description: 'Análisis multimodal y extracción conceptual',
  },
  {
    id: 'gemini-3.1-pro',
    name: 'Gemini 3.1 Pro',
    provider: 'Google',
    description: 'Razonamiento complejo y síntesis de múltiples fuentes',
  },
  {
    id: 'gemini-3-flash-preview',
    name: 'Gemini 3 Flash Preview',
    provider: 'Google',
    description: 'Acceso anticipado a capacidades experimentales',
    badge: 'Preview',
  },

  // xAI Grok Models
  {
    id: 'grok-4.6',
    name: 'Grok 4.6',
    provider: 'xAI',
    description: 'Motor de razonamiento avanzado con contexto en tiempo real',
  },
  {
    id: 'grok-4.5',
    name: 'Grok 4.5',
    provider: 'xAI',
    description: 'Análisis y síntesis de información legal actualizada',
  },
];

function mapRawModelToOption(raw: {
  id: string;
  name?: string;
  provider?: string;
  context_limit?: number;
  context_limit_label?: string;
  description?: string;
  badge?: string | null;
  owned_by?: string;
  created?: number;
}): ScrapedModelOption {
  const id = raw.id;
  const owned = (raw.owned_by || '').toLowerCase();

  // If backend provided enriched fields
  if (raw.name && raw.provider && raw.description) {
    return {
      id: raw.id,
      name: raw.name,
      provider: (raw.provider as any) || 'Legalia',
      description: raw.description,
      badge: raw.badge || undefined,
      owned_by: raw.owned_by,
    };
  }

  if (id === 'legalia') {
    return {
      id: 'legalia',
      name: 'Legalia Auto',
      provider: 'Legalia',
      description: 'Enrutador jurídico automático con verificación RAG estricta',
      badge: 'RAG Verificado',
    };
  }

  if (id.includes('claude') || owned.includes('anthropic') || owned.includes('kiro')) {
    let name = id;
    if (id === 'claude-sonnet-4.6') name = 'Claude Sonnet 4.6';
    else if (id === 'claude-sonnet-5') name = 'Claude Sonnet 5';
    else if (id === 'claude-opus-5') name = 'Claude Opus 5';
    else if (id === 'claude-opus-4.8') name = 'Claude Opus 4.8';
    else if (id === 'claude-opus-4.6') name = 'Claude Opus 4.6';
    else if (id === 'claude-haiku-4.5') name = 'Claude Haiku 4.5';

    return {
      id,
      name,
      provider: 'Anthropic',
      description: 'Motor Anthropic con alta capacidad de análisis doctrinal y jurisprudencial',
      badge: id === 'claude-sonnet-4.6' ? 'Recomendado' : id.includes('haiku') ? 'Rápido' : undefined,
    };
  }

  if (id.includes('gemini') || owned.includes('gemini') || owned.includes('antigravity')) {
    let name = id.replace('gemini-', 'Gemini ').replace('-preview', ' Preview').replace('-', '.');

    // Format Gemini model names
    if (id === 'gemini-3.7-flash') name = 'Gemini 3.7 Flash';
    else if (id === 'gemini-3.6-flash') name = 'Gemini 3.6 Flash';
    else if (id === 'gemini-3.5-flash') name = 'Gemini 3.5 Flash';
    else if (id === 'gemini-3.1-pro') name = 'Gemini 3.1 Pro';
    else if (id === 'gemini-3-flash-preview') name = 'Gemini 3 Flash Preview';

    return {
      id,
      name,
      provider: 'Google',
      description: 'Motor multimodal de Google optimizado para expedientes',
      badge: id.includes('preview') ? 'Preview' : undefined,
    };
  }

  if (id.includes('gpt') || owned.includes('gpt') || owned.includes('openai')) {
    let name = id.toUpperCase().replace(/-/g, ' ');

    // Format GPT model names
    if (id === 'gpt-5.6-sol') name = 'GPT-5.6 Sol';
    else if (id === 'gpt-5.6-terra') name = 'GPT-5.6 Terra';
    else if (id === 'gpt-5.6-luna') name = 'GPT-5.6 Luna';
    else if (id === 'gpt-5.5') name = 'GPT-5.5';
    else if (id === 'gpt-5.4') name = 'GPT-5.4';
    else if (id === 'gpt-5.4-mini') name = 'GPT-5.4 Mini';

    return {
      id,
      name,
      provider: 'OpenAI',
      description: 'Motor OpenAI para redacción contractual y estructuración de alegatos',
      badge: id.includes('mini') ? 'Económico' : undefined,
    };
  }

  if (id.includes('grok') || owned.includes('grok')) {
    return {
      id,
      name: id.replace('grok-', 'Grok '),
      provider: 'xAI',
      description: 'Motor de razonamiento xAI',
    };
  }

  return {
    id,
    name: id,
    provider: 'Legalia',
    description: `Modelo disponible (${id})`,
  };
}

interface ModelSelectorProps {
  selectedModelId: string;
  onSelectModel: (modelId: string) => void;
}

export function ModelSelector({ selectedModelId, onSelectModel }: ModelSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [models, setModels] = useState<ScrapedModelOption[]>(DEFAULT_MODELS);
  const [loadingModels, setLoadingModels] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent | TouchEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('touchstart', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside);
    };
  }, [isOpen]);

  // Fetch models dynamically from /api/v1/models
  useEffect(() => {
    let isMounted = true;
    async function loadDynamicModels() {
      try {
        setLoadingModels(true);
        const dynamicModels = await api.getModels();
        if (isMounted && dynamicModels && dynamicModels.length > 0) {
          const parsed = dynamicModels.map(mapRawModelToOption);
          // Combine with Legalia Auto at the top
          const hasLegalia = parsed.some(m => m.id === 'legalia');
          const finalModels = hasLegalia ? parsed : [DEFAULT_MODELS[0], ...parsed];
          setModels(finalModels);
        }
      } catch (err) {
        console.warn('Using fallback models list:', err);
      } finally {
        if (isMounted) setLoadingModels(false);
      }
    }

    loadDynamicModels();
    return () => {
      isMounted = false;
    };
  }, []);

  const activeModel =
    models.find((m) => m.id === selectedModelId) ||
    DEFAULT_MODELS.find((m) => m.id === selectedModelId) ||
    models[0] ||
    DEFAULT_MODELS[0];

  const handleSelect = (model: ScrapedModelOption) => {
    onSelectModel(model.id);
    setIsOpen(false);
  };

  // Group models by provider
  const groupedModels = models.reduce((acc, model) => {
    const provider = model.provider;
    if (!acc[provider]) {
      acc[provider] = [];
    }
    acc[provider].push(model);
    return acc;
  }, {} as Record<string, ScrapedModelOption[]>);

  const providerOrder = ['Legalia', 'Anthropic', 'OpenAI', 'Google', 'xAI'];
  const sortedProviders = providerOrder.filter(p => groupedModels[p]);

  return (
    <div className="model-selector-wrapper" ref={dropdownRef}>
      <button
        type="button"
        className="model-selector-btn"
        onClick={() => setIsOpen(!isOpen)}
        title="Seleccionar motor de IA"
      >
        <ProviderLogo provider={activeModel.provider} size={18} />
        <span className="model-btn-name">{activeModel.name}</span>
        {activeModel.badge && (
          <span className="model-btn-badge">{activeModel.badge}</span>
        )}
        <ChevronDownIcon size={14} className="model-chevron" />
      </button>

      {isOpen && (
        <div className="model-dropdown-menu">
          <div className="model-dropdown-header">
            <span>Motores de IA ({models.length} modelos en vivo)</span>
            {loadingModels && <span className="mini-spinner" style={{ width: 10, height: 10 }} />}
          </div>

          <div className="model-options-list">
            {sortedProviders.map((providerName) => (
              <div key={providerName} className="model-provider-group">
                <div className="provider-group-header">
                  <ProviderLogo provider={providerName} size={16} />
                  <span className="provider-group-name">{providerName}</span>
                  <span className="provider-group-count">
                    {groupedModels[providerName].length} {groupedModels[providerName].length === 1 ? 'modelo' : 'modelos'}
                  </span>
                </div>

                {groupedModels[providerName].map((model) => {
                  const isSelected = model.id === activeModel.id;
                  return (
                    <div
                      key={model.id}
                      className={`model-option-card ${isSelected ? 'selected' : ''}`}
                      onClick={() => handleSelect(model)}
                    >
                      <div className="model-card-top">
                        <div className="model-card-title-row">
                          <span className="model-card-name">{model.name}</span>
                        </div>

                        <div className="model-card-badges">
                          {model.badge && (
                            <span className="model-card-badge">{model.badge}</span>
                          )}
                        </div>
                      </div>

                      <p className="model-card-desc">{model.description}</p>
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
