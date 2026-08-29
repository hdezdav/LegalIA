export type LegalSpecializationId =
  | 'general'
  | 'constitucional'
  | 'civil'
  | 'penal'
  | 'laboral'
  | 'administrativo'
  | 'comercial'
  | 'tributario';

export interface LegalSpecialization {
  id: LegalSpecializationId;
  name: string;
  icon?: string;
  iconKey?: string;
  description: string;
  color: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  created_at: number;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  metadata?: {
    refused_for_lack_of_evidence?: boolean;
    verification_status?: string;
    retrieval_candidate_count?: number;
    context_chunk_count?: number;
    top_evidence_score?: number;
    reranked?: boolean;
    latency_ms?: number;
    citations?: CitationItem[];
    attachedFiles?: ParsedFile[];
  };
  attachedFiles?: ParsedFile[];
}

export interface CitationItem {
  number: number;
  documentTitle: string;
  sectionLabel: string;
  vigencia: string;
  relevanceScore: number;
  snippetText: string;
}

export interface Conversation {
  id: string;
  title: string;
  specialization: LegalSpecializationId;
  messages: Message[];
  created_at: number;
  updated_at: number;
  agent_id?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  refresh_token?: string;
}

export interface ChatRequest {
  model: string;
  messages: Array<{ role: 'user' | 'assistant'; content: string }>;
  conversation_id?: string;
}

export interface ChatResponse {
  id?: string;
  model?: string;
  choices: Array<{
    index?: number;
    message: {
      role: 'assistant';
      content: string;
    };
    finish_reason?: string;
  }>;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
  legalia: {
    conversation_id?: string;
    message_id?: string;
    refused_for_lack_of_evidence: boolean;
    verification_status: string;
    retrieval_candidate_count: number;
    context_chunk_count: number;
    top_evidence_score: number;
    reranked: boolean;
    lexical_degraded?: boolean;
    embedding_provider?: string;
    reranker_provider?: string;
    latency_ms?: number;
  };
}

export interface TokenQuota {
  total_tokens: number;
  used_tokens: number;
  remaining_tokens: number;
  remaining_percent: number;
  total_millions: number;
  remaining_millions: number;
  used_millions: number;
  status: string;
  days_remaining?: number;
  requests_remaining?: number;
  request_count_month?: number;
  rpm_limit?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
  cache_read_tokens?: number;
}

// --- Prompts ---

export interface PromptTemplate {
  id: string;
  name: string;
  body: string;
  description?: string;
  category?: string;
  favorite: boolean;
  created_at: number;
  updated_at: number;
}

export interface ParsedVariable {
  name: string;
  value: string;
}

// --- Memories ---

export interface Memory {
  id: string;
  key: string;
  value: string;
  tokens: number;
  created_at: number;
  updated_at: number;
}

export interface MemoriesConfig {
  enabled: boolean;
  maxTokens: number;
}

export interface AgentToolsConfig {
  rag_corpus?: boolean;
  docx_export?: boolean;
  interactive_forms?: boolean;
}

export interface Agent {
  id: string;
  name: string;
  description: string;
  icon?: string;
  avatar?: string;
  model?: string;
  instructions: string;
  specialization: LegalSpecializationId;
  conversation_starters?: string[];
  tools?: AgentToolsConfig;
  is_preset?: boolean;
  created_at: number;
  updated_at: number;
}

export type SidePanelTab =
  | 'chats'
  | 'agents'
  | 'prompts'
  | 'instructions'
  | 'memories'
  | 'bookmarks'
  | 'files';

// --- MarkItDown Document Ingestion Types ---

export interface FileStats {
  raw_bytes: number;
  raw_tokens_est: number;
  markdown_tokens_est: number;
  token_reduction_pct: number;
  word_count: number;
  char_count: number;
}

export interface FileAnalysis {
  doc_type: string;
  jurisdiction: string;
  radicado?: string | null;
  parties: {
    demandante?: string | null;
    demandado?: string | null;
    [key: string]: string | null | undefined;
  };
  key_clauses: Array<{
    title: string;
    summary: string;
  }>;
  filename: string;
}

export interface ParsedFile {
  id: string;
  filename: string;
  content_type: string;
  markdown: string;
  stats: FileStats;
  analysis: FileAnalysis;
  uploaded_at: number;
}
