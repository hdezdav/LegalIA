# LegalIA — System Architecture

This document details the architectural principles, component responsibilities, and data flow of **LegalIA**, an enterprise RAG assistant specialized in Colombian legal jurisprudence and normative compliance.

---

## 1. Architectural Philosophy

LegalIA is built upon three foundational tenets:

1. **Groundedness Over Hallucination (`NO EVIDENCE → NO ANSWER`)**:
   Legal analysis cannot tolerate probabilistic hallucinations. If the retrieval pipeline fails to find statutory or jurisprudential evidence above the relevance threshold, the system deliberately refuses to synthesize an answer.
2. **Hexagonal Architecture (Ports & Adapters)**:
   All external systems (LLM inference engines, vector stores, embedding providers, rerankers, search engines) are decoupled through strict abstract interfaces (`LLMProvider`, `EmbeddingProvider`, `RerankerProvider`). Swapping providers requires changing an environment variable, not rewriting business logic.
3. **Auditability and Strict Grounding**:
   Every response includes verifiable citations down to the exact article, container heading, and paragraph offsets in official gazettes or court rulings.

---

## 2. High-Level Architecture Diagram

```
                              ┌────────────────────────┐
                              │     User / Client      │
                              └───────────┬────────────┘
                                          │ HTTPS
                                          ▼
                              ┌────────────────────────┐
                              │  Caddy (TLS & Ingress) │
                              └─────┬────────────┬─────┘
                                    │            │
                     /api/* requests│            │ /* (Static assets)
                                    ▼            ▼
                   ┌───────────────────────┐   ┌────────────────────────┐
                   │ LegalIA API (FastAPI) │   │ React SPA (Nginx)      │
                   │ Python 3.12+          │   │ Vite + TypeScript      │
                   └───────────┬───────────┘   └────────────────────────┘
                               │
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
  ┌──────────────────┐ ┌───────────────┐ ┌─────────────────┐
  │ PostgreSQL 16+   │ │ LLM Providers │ │ Ingestion       │
  │ pgvector         │ │ (OpenAI /     │ │ Pipeline        │
  │ Hybrid Indexing  │ │  Anthropic)   │ │ (LegalSplitter) │
  └──────────────────┘ └───────────────┘ └─────────────────┘
```

---

## 3. Core Components

### 3.1 React Frontend (`frontend/`)
- **Technology**: React 18, TypeScript, Vite.
- **Design System**: Tailored dark theme (slate + legal gold), zero bloated CSS frameworks, fluid animations.
- **Features**:
  - Live token streaming with typing effect.
  - Verification telemetry inspector showing citation confidence and grounding status.
  - Interactive citation modal displaying the exact official text snippet.
  - Real-time token quota meter and monthly budget tracking.
  - Document management and case dossier attachment.

### 3.2 FastAPI Backend (`backend/app/`)
- **API Surface (`app/api/routes`)**:
  - `auth.py`: JWT-based authentication (Argon2 / bcrypt password hashing, access/refresh token rotation).
  - `chat.py`: OpenAI-compatible `/chat/completions` endpoint, model discovery, and `/usage/quota` metrics.
  - `health.py`: Live readiness and dependency probes (database connectivity, vector index status).
- **Service Layer (`app/services/`)**:
  - `chat_service.py`: Coordinates the full RAG cycle (query analysis, retrieval, reranking, LLM synthesis, verification).
  - `retrieval_service.py`: Hybrid search executor combining dense vector cosine similarity and lexical matching.
  - `usage_service.py`: Native database telemetry computing monthly token consumption and rate limits.
- **Domain & Database (`app/db/models/`)**:
  - `User`: Accounts, hashed credentials, role assignments.
  - `Conversation` & `Message`: Session continuity and message trees.
  - `Document` & `Chunk`: Ingested statutory norms and court rulings, storing 1024-dim vectors (`pgvector`).
  - `Citation`: Links synthesized answer tokens directly to source chunk IDs and text offsets.
  - `UsageLog`: Content-free operational telemetry (tokens, latency, error status, verification score).

### 3.3 Data Layer (`infrastructure/postgres/`)
- **PostgreSQL 16 with `pgvector`**:
  - `HNSW` or `IVFFlat` index on `chunks.embedding` for sub-10ms approximate nearest neighbor search.
  - GIN indexes on Spanish full-text search vectors (`tsvector`).
  - Internal Docker network isolation (no direct public internet exposure).

---

## 4. Request Lifecycle: Chat & Verification

```
User Query
    │
    ▼
[1] Embed Query (Alibaba text-embedding-v4 / BGE-M3 / Mock)
    │
    ▼
[2] Hybrid Retrieval (pgvector Cosine Search + Lexical Full-Text)
    │ Top-K Candidates (Default: 20)
    ▼
[3] Cross-Encoder Reranking (Alibaba GTE / Semantic Reranker)
    │ Top-N Chunks (Default: 5)
    ▼
[4] Evidence Threshold Check
    ├── Top score < MIN_SIMILARITY_SCORE ──► Return Explicit Refusal (NO EVIDENCE)
    └── Top score >= MIN_SIMILARITY_SCORE
            │
            ▼
[5] Primary LLM Synthesis (Claude 3.5 Sonnet / GPT-4o)
    │
    ▼
[6] Verification Pass (Claude Haiku / Lightweight Verifier)
    │ Check factual propositions against retrieved evidence
    ▼
[7] Persist UsageLog & Stream Response to Client with Citations
```

---

## 5. Security & Isolation

- **Zero Content Leakage in Telemetry**: `usage_logs` strictly tracks counts, model IDs, scores, and execution durations. Prompts and legal documents are never persisted in operational logs.
- **Network Segmentation**: Internal data stores (`legalia-postgres`) reside on an isolated Docker bridge network with no exposed ports to the outside host.
- **Strict Parameterization**: All database queries are executed via SQLAlchemy ORM or bound parameters, eliminating SQL injection vectors.
