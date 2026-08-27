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

// --- Agents ---

export function loadAgents(): Agent[] {
  try {
    const raw = localStorage.getItem(AGENTS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveAgents(agents: Agent[]): void {
  try {
    localStorage.setItem(AGENTS_KEY, JSON.stringify(agents));
  } catch (err) {
    console.error('Failed to save agents:', err);
  }
}
