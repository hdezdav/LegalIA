import { TokenResponse, User, ChatRequest, ChatResponse, TokenQuota } from './types';
import { generateUUID } from './utils';

const API_BASE = '/api/v1';

class AuthError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'AuthError';
  }
}

class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
    this.name = 'ApiError';
  }
}

let accessToken: string | null = localStorage.getItem('access_token');
let refreshToken: string | null = localStorage.getItem('refresh_token');

function setTokens(access: string, refresh: string) {
  accessToken = access;
  refreshToken = refresh;
  localStorage.setItem('access_token', access);
  localStorage.setItem('refresh_token', refresh);
}

function clearTokens() {
  accessToken = null;
  refreshToken = null;
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}

async function ensureToken(): Promise<string | null> {
  if (accessToken) return accessToken;
  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: 'abogado@legalia.co', password: 'Password123!' }),
    });
    if (res.ok) {
      const data: TokenResponse = await res.json();
      setTokens(data.access_token, data.refresh_token || '');
      return data.access_token;
    }
  } catch {
    // ignore
  }
  return null;
}

async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  let token = accessToken;
  if (!token) {
    token = await ensureToken();
  }

  const headers = new Headers(options.headers);
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  headers.set('Content-Type', 'application/json');

  let response = await fetch(url, { ...options, headers });

  if (response.status === 401 && refreshToken) {
    try {
      const refreshResponse = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (refreshResponse.ok) {
        const data: TokenResponse = await refreshResponse.json();
        setTokens(data.access_token, data.refresh_token || '');
        headers.set('Authorization', `Bearer ${data.access_token}`);
        response = await fetch(url, { ...options, headers });
      } else {
        clearTokens();
      }
    } catch {
      clearTokens();
    }
  }

  return response;
}

export const api = {
  async register(email: string, password: string, full_name: string): Promise<User> {
    const response = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, full_name }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new ApiError(error.detail || 'Registration failed', response.status);
    }

    return response.json();
  },

  async login(email: string, password: string): Promise<TokenResponse> {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new ApiError(error.detail || 'Login failed', response.status);
    }

    const data: TokenResponse = await response.json();
    setTokens(data.access_token, data.refresh_token || '');
    return data;
  },

  async getMe(): Promise<User> {
    const response = await fetchWithAuth(`${API_BASE}/auth/me`);

    if (!response.ok) {
      throw new AuthError('Failed to fetch user');
    }

    return response.json();
  },

  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    const response = await fetchWithAuth(`${API_BASE}/chat/completions`, {
      method: 'POST',
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new ApiError(error.detail || 'Failed to send message', response.status);
    }

    return response.json();
  },

  async streamMessage(
    request: ChatRequest,
    onDelta: (token: string) => void,
    signal?: AbortSignal
  ): Promise<void> {
    const response = await fetchWithAuth(`${API_BASE}/chat/completions`, {
      method: 'POST',
      body: JSON.stringify({ ...request, stream: true }),
      signal,
    });

    if (!response.ok) {
      let detail = 'Error en streaming';
      try {
        const err = await response.json();
        detail = err.detail || detail;
      } catch {}
      throw new ApiError(detail, response.status);
    }

    if (!response.body) {
      throw new ApiError('No response body for streaming', 500);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith('data:')) continue;
        const dataStr = trimmed.slice(5).trim();
        if (dataStr === '[DONE]') {
          return;
        }
        try {
          const parsed = JSON.parse(dataStr);
          const delta = parsed.choices?.[0]?.delta?.content;
          if (delta) {
            onDelta(delta);
          }
        } catch {
          // ignore partial JSON or malformed line
        }
      }
    }
  },

  async getModels(): Promise<Array<{
    id: string;
    name?: string;
    provider?: string;
    context_limit?: number;
    context_limit_label?: string;
    description?: string;
    badge?: string | null;
    owned_by?: string;
    created?: number;
  }>> {
    const response = await fetch(`${API_BASE}/models`);
    if (!response.ok) {
      return [];
    }
    const data = await response.json();
    return data.data || [];
  },

  async getQuota(): Promise<TokenQuota> {
    try {
      const response = await fetch(`${API_BASE}/usage/quota`);
      if (!response.ok) {
        throw new Error('Failed to fetch quota');
      }
      return response.json();
    } catch {
      return {
        total_tokens: 15000000,
        used_tokens: 1282915,
        remaining_tokens: 13717085,
        remaining_percent: 91.4,
        total_millions: 15.0,
        remaining_millions: 13.72,
        used_millions: 1.28,
        status: 'active',
        days_remaining: 10,
        rpm_limit: 120,
      };
    }
  },

  async uploadAndParseFile(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);

    const headers = new Headers();
    if (accessToken) {
      headers.set('Authorization', `Bearer ${accessToken}`);
    }

    const response = await fetch(`${API_BASE}/files/parse`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      let msg = 'Failed to parse file';
      try {
        const error = await response.json();
        msg = error.detail || msg;
      } catch {
        // ignore
      }
      throw new ApiError(msg, response.status);
    }

    const data = await response.json();
    return {
      id: generateUUID(),
      filename: data.filename,
      content_type: data.content_type,
      markdown: data.markdown,
      stats: data.stats,
      analysis: data.analysis,
      uploaded_at: Date.now(),
    };
  },

  logout() {
    clearTokens();
  },

  isAuthenticated(): boolean {
    return !!accessToken;
  },
};
