import { Agent, Memory, LegalSpecializationId } from './types';
import { SPECIALIZATIONS } from './constants';

/**
 * Builds the context block prepended to the outgoing user message.
 *
 * The Legalia API only accepts `user` and `assistant` roles (it drops anything
 * else), so agent instructions and memories travel as a prefix on the last user
 * message instead of a system message. The stored message keeps the clean text,
 * so the prefix never shows up in the transcript or in an export.
 */
export function buildContextBlock(options: {
  agent: Agent | null;
  memories: Memory[];
  memoriesEnabled: boolean;
  specialization: LegalSpecializationId;
}): string {
  const { agent, memories, memoriesEnabled, specialization } = options;
  const sections: string[] = [];

  if (agent) {
    sections.push(`Instrucciones del agente "${agent.name}":\n${agent.instructions}`);
  }

  if (memoriesEnabled && memories.length > 0) {
    const lines = memories.map((m) => `- ${m.key}: ${m.value}`).join('\n');
    sections.push(`Contexto del usuario:\n${lines}`);
  }

  if (specialization !== 'general') {
    const spec = SPECIALIZATIONS.find((s) => s.id === specialization);
    if (spec) {
      sections.push(`Área de consulta: derecho ${spec.name.toLowerCase()}.`);
    }
  }

  if (sections.length === 0) return '';

  return `[Contexto de la consulta]\n${sections.join('\n\n')}\n[Fin del contexto]`;
}
