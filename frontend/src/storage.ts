import { Conversation } from './types';

const STORAGE_KEY = 'legalia_conversations';

export function loadConversations(): Conversation[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed;
  } catch {
    return [];
  }
}

export function saveConversations(conversations: Conversation[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
  } catch (err) {
    console.error('Failed to persist conversations:', err);
  }
}

export function createConversation(): Conversation {
  const now = Date.now();
  return {
    id: crypto.randomUUID(),
    title: 'Nueva conversación',
    specialization: 'general',
    messages: [],
    created_at: now,
    updated_at: now,
  };
}
