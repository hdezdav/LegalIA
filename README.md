# LegalIA ⚖️

<div align="center">

**Enterprise Retrieval-Augmented Generation (RAG) Platform Specialized in Colombian Jurisprudence**

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg?logo=react&logoColor=black)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-336791.svg?logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/tests-140%2B%20passed-success.svg?logo=pytest&logoColor=white)](backend/tests/)
[![Architecture](https://img.shields.io/badge/architecture-Clean%20%2F%20Hexagonal-orange.svg)](#-system-architecture)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

</div>

---

## 📌 Executive Summary

**LegalIA** is a production-ready, domain-specific AI assistant engineered for legal research and statutory compliance within the Colombian legal framework.

Unlike generic LLM wrappers, LegalIA implements an **evidence-first RAG architecture** guided by a non-negotiable principle:

> ### 🛡️ Fundamental Principle: **`NO EVIDENCE → NO ANSWER`**
> Legal analysis demands zero tolerance for hallucinations. If the retrieval pipeline cannot locate verifiable normative provisions or binding jurisprudential precedent, the system explicitly refuses to synthesize an answer rather than guessing.

---

## 🏛️ System Architecture

LegalIA adheres to **Clean / Hexagonal Architecture** principles, decoupling business rules from external AI providers and data stores.

### End-to-End RAG & Verification Pipeline

```mermaid
flowchart TD
    subgraph Ingestion["Ingestion & Indexing Engine"]
        DOC["Colombian Legal Corpus<br/>(Laws, Codes, Sentencias)"] --> SPLIT["Hierarchical LegalSplitter<br/>(Libro > Título > Capítulo > Artículo)"]
        SPLIT --> EMB["Dense Vector Embeddings<br/>(1024-d via pgvector)"]
        SPLIT --> FTS["Spanish Full-Text Search<br/>(tsvector + GIN Index)"]
    end

    subgraph Retrieval["Hybrid Search & Reranking"]
        QUERY["User Legal Query"] --> VEC["Cosine Vector Search"]
        QUERY --> LEX["Lexical Search (Spanish Stemmer)"]
        VEC --> RRF["Reciprocal Rank Fusion (RRF)"]
        LEX --> RRF
        RRF --> RERANK["Cross-Encoder Reranker<br/>(Contextual Precision Scoring)"]
    end

    subgraph Synthesis["Synthesis & Verification Guardrail"]
        RERANK --> THRESH{Evidence Score<br/>>= Threshold?}
        THRESH -- Refusal --> REFUSE["Explicit Refusal:<br/>'NO EVIDENCE → NO ANSWER'"]
        THRESH -- Pass --> LLM["LLM Synthesis (OpenAI / Anthropic / Mock)"]
        LLM --> VERIFY["Secondary Fact Verification Audit<br/>(Cross-checks tokens against source chunks)"]
        VERIFY --> STREAM["Streaming Response + Interactive Citations"]
    end
```

### Infrastructure Topology

```
                              ┌────────────────────────┐
                              │   Web Client / SPA     │
                              │  (React 18 + TS + Vite)│
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
                   │ Python 3.12+          │   │ Tailored Design System │
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

## ⚡ Key Engineering Highlights

### 1. Hierarchical Legal Splitting (`LegalSplitter`)
- Statutory laws and court rulings cannot be segmented with generic character splitters without destroying normative context.
- LegalIA's structural parser recognizes Colombian normative containers (`LIBRO`, `TÍTULO`, `CAPÍTULO`, `ARTÍCULO`, `PARÁGRAFO`) and court rulings (`Considerandos`, `Resuelve`).
- Preserves exact character offsets and genealogical path hierarchy (e.g. `TÍTULO II > CAPÍTULO 1 > ARTÍCULO 13`).

### 2. Hybrid Search Engine (Dense + Lexical)
- **Dense Vector Search**: Powered by `pgvector` with 1024-dimensional embeddings (Alibaba text-embedding-v4, BGE-M3, or local models).
- **Lexical Search**: PostgreSQL full-text search (`tsvector` / GIN index) in Spanish to match exact law numerals and Latin maxims (*tutela*, *habeas corpus*, *non bis in idem*).
- **Reciprocal Rank Fusion**: Merges scores to ensure both conceptual and verbatim relevance.

### 3. Cross-Encoder Reranking & Verification Pass
- **Semantic Reranking**: Re-scores candidate chunks through a cross-encoder prior to synthesis.
- **Verification Layer**: An independent secondary verification pass audits factual statements against retrieved chunks before streaming output to the user.
- **Citation Tracking**: Emits interactive citations linking each answer token directly to official sources (SUIN-Juriscol, Diario Oficial, Corte Constitucional).

### 4. Enterprise Telemetry & Token Accounting
- Live token quota meter calculating input, output, and verifier token consumption directly from database `UsageLog` records.
- Complete content privacy: operational logs contain zero prompts or legal dossier texts.

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Backend** | Python 3.12+, FastAPI, SQLAlchemy 2, Alembic | Async REST API, Hexagonal domain services |
| **Database** | PostgreSQL 16, pgvector | Relational data, vector embeddings, full-text search |
| **Frontend** | React 18, TypeScript, Vite | Modern SPA, streaming responses, citation modal |
| **LLM Adapters** | OpenAI-compatible, Anthropic SDK, Mock | Dynamic provider switching (Claude, GPT, Gemini) |
| **Embeddings** | Alibaba DashScope, BGE-M3, Mock | Multilingual dense vector generation |
| **Reranking** | Alibaba GTE Reranker, Mock | Cross-encoder contextual precision |
| **Infrastructure** | Docker, Docker Compose, Caddy, Nginx | Containerized deployment, automatic HTTPS |

---

## 📂 Repository Structure

```
LegalIA/
├── backend/                  # FastAPI Application (Clean / Hexagonal Architecture)
│   ├── alembic/              # Database schema migrations (pgvector enabled)
│   ├── app/
│   │   ├── api/routes/       # REST API endpoints & SSE streaming handlers
│   │   ├── core/             # Security (JWT, Argon2), configuration & settings
│   │   ├── db/models/        # SQLAlchemy 2 models (chunks, documents, usage)
│   │   ├── providers/        # LLM, Embedding & Reranking adapters (Hexagonal Ports)
│   │   └── services/         # RAG pipeline orchestration, verification & search
│   └── tests/                # 140+ automated unit & integration test suites
├── frontend/                 # React 18 + TypeScript + Vite SPA
│   └── src/
│       ├── components/       # UI components (SidePanel, CitationsModal, QuotaMeter)
│       └── styles/           # Modern CSS tokens & accessibility-first styling
├── ingestion/                # Document extraction, structural splitters & indexing CLI
├── evaluation/               # Precision/Recall benchmarks & legal retrieval evaluation
├── corpus/                   # Sample Colombian legal corpus (Constitución, Códigos)
├── docs/                     # Comprehensive technical documentation & guides
├── scripts/                  # Administrative tools & deployment automation
├── docker-compose.yml        # Development multi-container orchestration
└── Makefile                  # Developer workflow & automation commands
```

---

## 🚀 Quick Start

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/)
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/hdezdav/LegalIA.git
cd LegalIA
```

### 2. Configure Environment Variables
```bash
cp .env.example .env
```
Edit `.env` to configure your preferred LLM provider (`openai_compatible`, `anthropic`, or `mock` for local offline testing):
```env
# Example using OpenAI or OpenAI-compatible endpoint
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your_api_key_here
LLM_MODEL=gpt-4o

# Database
POSTGRES_DB=legalia
POSTGRES_USER=legalia
POSTGRES_PASSWORD=your_secure_password
```

### 3. Launch Services with Docker Compose
```bash
docker compose up -d --build
```
The stack will spin up 4 optimized containers:
- `legalia-caddy`: Ingress reverse proxy & SSL termination (`http://localhost:80`)
- `legalia-frontend`: Nginx serving the React SPA (`http://localhost/`)
- `legalia-api`: FastAPI backend (`http://localhost:8000/`)
- `legalia-postgres`: PostgreSQL 16 with pgvector

### 4. Run Database Migrations
```bash
docker compose exec legalia-api alembic upgrade head
```

### 5. Ingest Sample Legal Corpus
```bash
docker compose exec legalia-api python -m ingestion.main --file corpus/constitucion_extracto.txt --status VIGENTE
```

---

## 🧪 Testing & Code Quality

LegalIA includes an extensive automated test suite covering authentication, legal chunking, hybrid retrieval, security, and reranking:

```bash
# Run tests inside virtual environment or container
pytest backend/tests -v

# Run with test coverage report
pytest backend/tests --cov=app --cov-report=term-missing
```

Frontend typecheck and build validation:
```bash
cd frontend
npm install
npm run build
```

---

## 📚 Technical Documentation

Explore deep-dive technical guides in the [`docs/`](docs/) directory:

- 🏛️ [**System Architecture**](docs/ARCHITECTURE.md): Structural overview, clean domain boundaries, and data flow.
- 🔬 [**RAG Pipeline & Legal Intelligence**](docs/RAG_PIPELINE.md): Hierarchical chunking, hybrid search, and verification algorithms.
- 🚢 [**Deployment Guide**](docs/DEPLOYMENT.md): Production deployment, SSL configuration, and environment setup.
- 🎨 [**Design System**](docs/DESIGN_SYSTEM.md): Tailored CSS design tokens, typography, and accessibility guidelines.
- ⚖️ [**Corpus Sources**](docs/CORPUS_SOURCES.md): Primary sources for Colombian statutory laws and constitutional jurisprudence.
- 📊 [**Ingestion Status & Corpus Metrics**](docs/INGESTION_STATUS.md): Processing status, corpus coverage, and extraction audit trail.

---

## 🔒 Security & Privacy

- **Data Minimization**: Prompts, answers, and case files are excluded from logging pipelines.
- **Authentication**: JWT tokens signed with HS256, Argon2 password hashing, and role-based access.
- **Network Isolation**: PostgreSQL runs inside an isolated internal Docker bridge network without direct host port exposure in production.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<div align="center">

*Disclaimer: LegalIA is an AI-powered legal intelligence tool designed to assist legal professionals. Outputs do not constitute formal legal counsel.*

</div>
