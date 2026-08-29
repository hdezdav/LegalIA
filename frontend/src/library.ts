import { PromptTemplate, Memory, Agent, MemoriesConfig } from './types';

const PROMPTS_KEY = 'legalia_prompts';
const MEMORIES_KEY = 'legalia_memories';
const MEMORIES_CONFIG_KEY = 'legalia_memories_config';
const AGENTS_KEY = 'legalia_agents';

// --- Prompts ---

export function loadPrompts(): PromptTemplate[] {
  try {
    const raw = localStorage.getItem(PROMPTS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function savePrompts(prompts: PromptTemplate[]): void {
  try {
    localStorage.setItem(PROMPTS_KEY, JSON.stringify(prompts));
  } catch (err) {
    console.error('Failed to save prompts:', err);
  }
}

export function parseVariables(body: string): string[] {
  const matches = body.match(/\{\{([^}]+)\}\}/g);
  if (!matches) return [];
  return Array.from(new Set(matches.map((m) => m.slice(2, -2).trim())));
}

export function fillTemplate(body: string, values: Record<string, string>): string {
  let result = body;
  for (const [key, value] of Object.entries(values)) {
    const regex = new RegExp(`\\{\\{${key}\\}\\}`, 'g');
    result = result.replace(regex, value);
  }
  return result;
}

// --- Memories ---

export function loadMemories(): Memory[] {
  try {
    const raw = localStorage.getItem(MEMORIES_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveMemories(memories: Memory[]): void {
  try {
    localStorage.setItem(MEMORIES_KEY, JSON.stringify(memories));
  } catch (err) {
    console.error('Failed to save memories:', err);
  }
}

export function loadMemoriesConfig(): MemoriesConfig {
  try {
    const raw = localStorage.getItem(MEMORIES_CONFIG_KEY);
    if (!raw) return { enabled: false, maxTokens: 2000 };
    return JSON.parse(raw);
  } catch {
    return { enabled: false, maxTokens: 2000 };
  }
}

export function saveMemoriesConfig(config: MemoriesConfig): void {
  try {
    localStorage.setItem(MEMORIES_CONFIG_KEY, JSON.stringify(config));
  } catch (err) {
    console.error('Failed to save memories config:', err);
  }
}

export function estimateTokens(text: string): number {
  // Rough estimate: ~4 chars per token
  return Math.ceil(text.length / 4);
}

export function getTotalMemoryTokens(memories: Memory[]): number {
  return memories.reduce((sum, m) => sum + m.tokens, 0);
}

export const DEFAULT_PRESET_AGENTS: Agent[] = [
  {
    id: 'preset-constitucional',
    name: 'Consultor Constitucional & Tutelas',
    description: 'Especialista en Acción de Tutela, Derechos Fundamentales y Jurisprudencia de la Corte Constitucional.',
    icon: 'scroll',
    specialization: 'constitucional',
    model: 'claude-sonnet-5',
    is_preset: true,
    instructions:
      'Eres el Consultor Constitucional Senior de Legalia. Tu función es estructurar acciones de tutela, derechos de petición, análisis de procedibilidad, subsidiariedad e inmediatez conforme a los Decretos 2591/91, 1069/15 y la jurisprudencia unificada (SU y C) de la Corte Constitucional.',
    conversation_starters: [
      'Redactar Acción de Tutela por negación de medicamentos/tratamiento de salud',
      '¿Cuáles son las causales específicas de procedibilidad de tutela contra providencias judiciales?',
      'Estructurar Derecho de Petición por falta de respuesta oportuna de una entidad',
    ],
    tools: { rag_corpus: true, docx_export: true, interactive_forms: true },
    created_at: 1700000000000,
    updated_at: 1700000000000,
  },
  {
    id: 'preset-laboral',
    name: 'Litigante Laboral & Seguridad Social',
    description: 'Cálculo de liquidaciones, estabilidad laboral reforzada, fueros de salud, maternidad y demandas ordinarias.',
    icon: 'briefcase',
    specialization: 'laboral',
    model: 'claude-sonnet-5',
    is_preset: true,
    instructions:
      'Eres el Especialista en Derecho Laboral y de la Seguridad Social de Legalia. Aplica con exactitud el Código Sustantivo del Trabajo (CST), Ley 100 de 1993, Ley 789 de 2002 y la jurisprudencia de la Sala de Casación Laboral de la Corte Suprema de Justicia. Proporciona liquidaciones numéricas y citas de artículos exactas.',
    conversation_starters: [
      'Liquidar prestaciones e indemnización por despido sin justa causa',
      'Analizar caso de despido con fuero de salud (estabilidad laboral reforzada)',
      'Redactar carta de terminación de contrato con justa causa (Art. 62 CST)',
    ],
     tools: { rag_corpus: true, docx_export: true, interactive_forms: true },
    created_at: 1700000000000,
    updated_at: 1700000000000,
  },
  {
    id: 'preset-comercial',
    name: 'Auditor Contractual & Minutas',
    description: 'Redacción y auditoría de contratos mercantiles, arrendamiento (Ley 820), prestación de servicios y NDA.',
    icon: 'trending',
    specialization: 'comercial',
    model: 'claude-sonnet-5',
    is_preset: true,
    instructions:
      'Eres el Especialista en Contratación Privada y Mercantil de Legalia. Redactas minutas contractuales blindadas, equilibradas y directamente ejecutables según el Código Civil y Código de Comercio. Siempre entregas los documentos en bloques de código estructurados para su exportación a Word.',
    conversation_starters: [
      'Redactar Contrato de Arrendamiento de Vivienda Urbana con fiador y codeudor',
      'Elaborar Acuerdo de Confidencialidad y No Divulgación (NDA) bilateral',
      'Redactar Contrato de Prestación de Servicios Profesionales con cláusula penal',
    ],
    tools: { rag_corpus: true, docx_export: true, interactive_forms: true },
    created_at: 1700000000000,
    updated_at: 1700000000000,
  },
  {
    id: 'preset-procesal',
    name: 'Estratega Procesal & Litigios (CGP)',
    description: 'Estructuración de demandas, excepciones previas, recursos ordinarios y extraordinarios (Casación y Revisión).',
    icon: 'landmark',
    specialization: 'civil',
    model: 'claude-sonnet-5',
    is_preset: true,
    instructions:
      'Eres el Consultor Procesal de Legalia. Dominas el Código General del Proceso (Ley 1564 de 2012) y el CPACA (Ley 1437 de 2011 / Ley 2080 de 2021). Asesoras sobre términos judiciales, cargas probatorias, medidas cautelares y medios impugnatorios.',
    conversation_starters: [
      'Estructurar excepciones previas en proceso verbal declarativo (Art. 100 CGP)',
      'Términos y causales para interponer recurso extraordinario de casación civil',
      'Requisitos para solicitar medidas cautelares innominadas en el CGP',
    ],
    tools: { rag_corpus: true, docx_export: true, interactive_forms: true },
    created_at: 1700000000000,
    updated_at: 1700000000000,
  },
];

export function loadAgents(): Agent[] {
  try {
    const raw = localStorage.getItem(AGENTS_KEY);
    if (!raw) {
      saveAgents(DEFAULT_PRESET_AGENTS);
      return DEFAULT_PRESET_AGENTS;
    }
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed) && parsed.length > 0) {
      return parsed;
    }
    saveAgents(DEFAULT_PRESET_AGENTS);
    return DEFAULT_PRESET_AGENTS;
  } catch {
    return DEFAULT_PRESET_AGENTS;
  }
}

export function saveAgents(agents: Agent[]): void {
  try {
    localStorage.setItem(AGENTS_KEY, JSON.stringify(agents));
  } catch (err) {
    console.error('Failed to save agents:', err);
  }
}
