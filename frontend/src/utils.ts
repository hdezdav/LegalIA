import { Conversation } from './types';

export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (err) {
    console.error('Failed to copy:', err);
    return false;
  }
}

export function formatTime(timestamp: number): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'Ahora';
  if (diffMins < 60) return `Hace ${diffMins}m`;
  if (diffHours < 24) return `Hace ${diffHours}h`;
  if (diffDays < 7) return `Hace ${diffDays}d`;

  return date.toLocaleDateString('es-CO', {
    month: 'short',
    day: 'numeric',
    year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
  });
}

export function exportConversationToMarkdown(conversation: Conversation): string {
  let markdown = `# ${conversation.title}\n\n`;
  markdown += `**Especialización:** ${conversation.specialization}\n`;
  markdown += `**Fecha:** ${new Date(conversation.created_at).toLocaleDateString('es-CO')}\n\n`;
  markdown += '---\n\n';

  for (const message of conversation.messages) {
    const role = message.role === 'user' ? '**Usuario**' : '**Legalia**';
    markdown += `### ${role}\n\n`;
    markdown += `${message.content}\n\n`;

    if (message.metadata) {
      if (message.metadata.refused_for_lack_of_evidence) {
        markdown += '*⚠️ Sin evidencia suficiente en el corpus*\n\n';
      }
      if (message.metadata.verification_status) {
        markdown += `*Estado: ${message.metadata.verification_status}*\n\n`;
      }
    }
  }

  markdown += '---\n\n';
  markdown += '*Generado por Legalia · Plataforma de Inteligencia Artificial Jurídica para Colombia*\n';

  return markdown;
}

export function downloadFile(filename: string, content: string): void {
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function parseCitationsFromText(text: string): number[] {
  const matches = text.match(/\[(\d+)\]/g);
  if (!matches) return [];
  return [...new Set(matches.map((m) => parseInt(m.slice(1, -1))))].sort(
    (a, b) => a - b
  );
}

export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + '...';
}

export function generateUUID(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

