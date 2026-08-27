import { useState, useRef, useEffect } from 'react';
import { api } from '../api';
import { ChevronDownIcon } from './Icons';
import './ModelSelector.css';

// Provider Logo Component
function ProviderLogo({ provider, size = 20 }: { provider: string; size?: number }) {
  const logoMap: Record<string, string> = {
    'Anthropic': '/logos/anthropic.svg',
    'OpenAI': '/logos/openai.svg',
    'Google': '/logos/google.svg',
    'xAI': '/logos/xai.svg',
    'Legalia': '/logos/legalia.svg',
  };

  const logoSrc = logoMap[provider] || logoMap['Legalia'];

  return (
    <img
      src={logoSrc}
      alt={`${provider} logo`}
      width={size}
      height={size}
      style={{ flexShrink: 0 }}
    />
  );
}

export interface ScrapedModelOption {
  id: string;
  name: string;
  provider: 'Anthropic' | 'Google' | 'OpenAI' | 'xAI' | 'Legalia';
  description: string;
  contextLimit: string;
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
    contextLimit: '200k tokens',
    badge: 'RAG Verificado',
  },

  // Anthropic Claude Models
  {
    id: 'claude-sonnet-4.6',
    name: 'Claude Sonnet 4.6',
    provider: 'Anthropic',
    description: 'Máxima precisión en razonamiento procesal y jurisprudencia colombiana',
    contextLimit: '200k tokens',
    badge: 'Recomendado',
  },
  {
    id: 'claude-sonnet-5',
    name: 'Claude Sonnet 5',
    provider: 'Anthropic',
    description: 'Excelente balance velocidad/precisión en redacción jurídica',
    contextLimit: '200k tokens',
  },
  {
    id: 'claude-opus-5',
    name: 'Claude Opus 5',
    provider: 'Anthropic',
    description: 'Análisis profundo de casaciones y expedientes extensos',
    contextLimit: '200k tokens',
  },
  {
    id: 'claude-opus-4.8',
    name: 'Claude Opus 4.8',
    provider: 'Anthropic',
    description: 'Versión optimizada para análisis de precedentes jurisprudenciales',
    contextLimit: '200k tokens',
  },
  {
    id: 'claude-opus-4.6',
    name: 'Claude Opus 4.6',
    provider: 'Anthropic',
    description: 'Modelo robusto para investigación normativa compleja',
    contextLimit: '200k tokens',
  },
  {
    id: 'claude-haiku-4.5',
    name: 'Claude Haiku 4.5',
    provider: 'Anthropic',
    description: 'Respuestas procesales ultrarrápidas y de bajo costo',
    contextLimit: '200k tokens',
    badge: 'Rápido',
  },

  // OpenAI GPT Models
  {
    id: 'gpt-5.6-sol',
    name: 'GPT-5.6 Sol',
    provider: 'OpenAI',
    description: 'Generación creativa y estructuración de minutas contractuales',
    contextLimit: '128k tokens',
  },
  {
    id: 'gpt-5.6-terra',
    name: 'GPT-5.6 Terra',
    provider: 'OpenAI',
    description: 'Modelo optimizado para análisis documental y síntesis',
    contextLimit: '128k tokens',
  },
  {
    id: 'gpt-5.6-luna',
    name: 'GPT-5.6 Luna',
    provider: 'OpenAI',
    description: 'Análisis jurídico multimodal y generación de argumentos',
    contextLimit: '128k tokens',
  },
  {
    id: 'gpt-5.5',
    name: 'GPT-5.5',
    provider: 'OpenAI',
    description: 'Redacción de demandas y escritos jurídicos estructurados',
    contextLimit: '128k tokens',
  },
  {
    id: 'gpt-5.4',
    name: 'GPT-5.4',
    provider: 'OpenAI',
    description: 'Modelo estable para consultas jurídicas generales',
    contextLimit: '128k tokens',
  },
  {
    id: 'gpt-5.4-mini',
    name: 'GPT-5.4 Mini',
    provider: 'OpenAI',
    description: 'Versión eficiente para consultas rápidas y borradores',
    contextLimit: '128k tokens',
    badge: 'Económico',
  },

  // Google Gemini Models
  {
    id: 'gemini-3.7-flash',
    name: 'Gemini 3.7 Flash',
    provider: 'Google',
    description: 'Ventana de contexto de 1M tokens para expedientes completos',
    contextLimit: '1M tokens',
    badge: '1M Tokens',
  },
  {
    id: 'gemini-3.6-flash',
    name: 'Gemini 3.6 Flash',
    provider: 'Google',
    description: 'Procesamiento ultrarrápido de documentos extensos',
    contextLimit: '1M tokens',
  },
  {
    id: 'gemini-3.5-flash',
    name: 'Gemini 3.5 Flash',
    provider: 'Google',
    description: 'Análisis multimodal con contexto extendido',
    contextLimit: '1M tokens',
  },
  {
    id: 'gemini-3.1-pro',
    name: 'Gemini 3.1 Pro',
    provider: 'Google',
    description: 'Razonamiento complejo y síntesis de múltiples fuentes',
    contextLimit: '1M tokens',
  },
  {
    id: 'gemini-3-flash-preview',
    name: 'Gemini 3 Flash Preview',
    provider: 'Google',
    description: 'Acceso anticipado a capacidades experimentales',
    contextLimit: '1M tokens',
    badge: 'Preview',
  },

  // xAI Grok Models
  {
    id: 'grok-4.6',
    name: 'Grok 4.6',
    provider: 'xAI',
    description: 'Motor de razonamiento avanzado con contexto en tiempo real',
    contextLimit: '128k tokens',
  },
  {
    id: 'grok-4.5',
    name: 'Grok 4.5',
    provider: 'xAI',
    description: 'Análisis y síntesis de información legal actualizada',
    contextLimit: '128k tokens',
  },
];

function mapRawModelToOption(raw: { id: string; owned_by?: string }): ScrapedModelOption {
  const id = raw.id;
  const owned = raw.owned_by || '';

  if (id === 'legalia') {
    return {
      id: 'legalia',
      name: 'Legalia Auto',
      provider: 'Legalia',
      description: 'Enrutador jurídico automático con verificación RAG estricta',
      contextLimit: '200k tokens',
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
      contextLimit: '200k tokens',
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
      description: 'Motor multimodal de Google con ventana de contexto extendida',
      contextLimit: '1M tokens',
      badge: id.includes('flash') ? '1M Tokens' : id.includes('preview') ? 'Preview' : undefined,
    };
  }

  if (id.includes('gpt') || owned.includes('gpt') || owned.includes('nodule')) {
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
      contextLimit: '128k tokens',
      badge: id.includes('mini') ? 'Económico' : undefined,
    };
  }

  if (id.includes('grok') || owned.includes('grok')) {
    return {
      id,
      name: id.replace('grok-', 'Grok '),
      provider: 'xAI',
      description: 'Motor de razonamiento xAI',
      contextLimit: '128k tokens',
    };
  }

  return {
    id,
    name: id,
    provider: 'Legalia',
    description: `Modelo disponible en Nodule (${id})`,
    contextLimit: '128k tokens',
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

  // Fetch live models from Nodule endpoint via backend API
  useEffect(() => {
    let isMounted = true;
    const fetchLiveModels = async () => {
      setLoadingModels(true);
      try {
        const rawList = await api.getModels();
        if (rawList && rawList.length > 0 && isMounted) {
          const filtered = rawList.filter(
            (r) =>
              !r.id.toLowerCase().includes('image') &&
              !r.id.toLowerCase().includes('dall') &&
              !r.id.toLowerCase().includes('embed')
          );
          const mapped = filtered.map(mapRawModelToOption);
          setModels(mapped);
        }
      } catch {
        // use fallback DEFAULT_MODELS
      } finally {
        if (isMounted) setLoadingModels(false);
      }
    };
    fetchLiveModels();
    return () => {
      isMounted = false;
    };
  }, []);

  const activeModel =
    models.find((m) => m.id === selectedModelId) ||
    DEFAULT_MODELS.find((m) => m.id === selectedModelId) ||
    models[0] ||
    DEFAULT_MODELS[0];

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

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
                          <span className="model-card-limit">{model.contextLimit}</span>
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
