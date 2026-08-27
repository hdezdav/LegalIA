import { LegalSpecialization } from './types';

export const SPECIALIZATIONS: LegalSpecialization[] = [
  {
    id: 'general',
    name: 'General & Jurisprudencia',
    iconKey: 'scale',
    description: 'Consultas generales de derecho y jurisprudencia colombiana',
    color: '#2563eb',
  },
  {
    id: 'constitucional',
    name: 'Constitucional & Tutela',
    iconKey: 'scroll',
    description: 'Derechos fundamentales, tutela y Constitución de 1991',
    color: '#d97706',
  },
  {
    id: 'civil',
    name: 'Civil & Procesal CGP',
    iconKey: 'landmark',
    description: 'Contratos, obligaciones, familia y Código General del Proceso',
    color: '#0284c7',
  },
  {
    id: 'penal',
    name: 'Penal & Procesal Penal',
    iconKey: 'zap',
    description: 'Delitos, penas y sistema penal acusatorio (Ley 906)',
    color: '#ef4444',
  },
  {
    id: 'laboral',
    name: 'Laboral & Seguridad Social',
    iconKey: 'briefcase',
    description: 'Código Sustantivo del Trabajo, fueros y pensiones',
    color: '#f59e0b',
  },
  {
    id: 'administrativo',
    name: 'Administrativo & CPACA',
    iconKey: 'building',
    description: 'Actos administrativos, contratación estatal y demandas al Estado',
    color: '#3b82f6',
  },
  {
    id: 'comercial',
    name: 'Comercial & Societario',
    iconKey: 'trending',
    description: 'Sociedades, SAS, títulos valores y contratos mercantiles',
    color: '#10b981',
  },
  {
    id: 'tributario',
    name: 'Tributario & Fiscal',
    iconKey: 'coins',
    description: 'Estatuto Tributario, impuestos DIAN y aduanas',
    color: '#8b5cf6',
  },
];

export const SPANISH_GREETINGS = [
  '¿En qué vamos a profundizar hoy, {name}?',
  '¿En qué podemos trabajar hoy, {name}?',
  '¿Qué caso o consulta jurídica analizamos hoy, {name}?',
  '¿Qué norma o jurisprudencia revisamos hoy, {name}?',
  '¿En qué asunto legal profundizamos hoy, {name}?',
];

export const EXAMPLE_PROMPTS = [
  '¿Cuáles son los requisitos de procedibilidad de la acción de tutela?',
  '¿Qué causales eximen de responsabilidad contractual en el régimen civil colombiano?',
  '¿Cuál es el término para contestar una demanda en el Código General del Proceso?',
  '¿Cómo opera la indemnización por despido sin justa causa según el CST?',
];

export interface ModelOption {
  id: string;
  name: string;
  provider: 'Anthropic' | 'Google' | 'OpenAI' | 'Legalia';
  description: string;
  contextLimit: string;
  badge?: string;
}

export const AVAILABLE_MODELS: ModelOption[] = [
  {
    id: 'claude-sonnet-4.6',
    name: 'Claude 3.7 Sonnet',
    provider: 'Anthropic',
    description: 'Máxima precisión en razonamiento procesal y jurisprudencia colombiana',
    contextLimit: '200k tokens',
    badge: 'Recomendado',
  },
  {
    id: 'claude-sonnet-5',
    name: 'Claude 3.5 Sonnet',
    provider: 'Anthropic',
    description: 'Excelente balance de velocidad y precisión en redacción jurídica',
    contextLimit: '200k tokens',
  },
  {
    id: 'claude-opus-5',
    name: 'Claude Opus 5',
    provider: 'Anthropic',
    description: 'Análisis profundo de expedientes complejos y casaciones',
    contextLimit: '200k tokens',
  },
  {
    id: 'gemini-3.7-flash',
    name: 'Gemini 3.7 Flash',
    provider: 'Google',
    description: 'Ultrarrápido para consultas procesales inmediatas y resúmenes',
    contextLimit: '1M tokens',
    badge: 'Rápido',
  },
  {
    id: 'gpt-5.6-sol',
    name: 'GPT-5.6 Sol',
    provider: 'OpenAI',
    description: 'Generación creativa y estructuración de minutas contractuales',
    contextLimit: '128k tokens',
  },
  {
    id: 'legalia',
    name: 'Legalia Auto',
    provider: 'Legalia',
    description: 'Enrutador automático con verificación RAG estricta',
    contextLimit: '200k tokens',
  },
];
