# LegalIA — RAG Pipeline & Legal Intelligence Engine

This document outlines the specialized Retrieval-Augmented Generation (RAG) architecture engineered specifically for the Colombian legal ecosystem.

---

## 1. The Challenge of Legal RAG

Generic RAG systems routinely fail on legal corpora due to:
1. **Arbitrary Text Slicing**: Naive sliding-window chunking divides articles across sentences, detaching qualifiers, exceptions, and procedural conditions from their parent article.
2. **Normative Hierarchy Ignorance**: Colombian jurisprudence relies on a strict hierarchy: Constitution > Statutory Laws > Regulatory Decrees > Jurisprudential Precedent. Chunks must carry their structural lineage.
3. **Implicit Validity (`Vigencia`)**: A repealed norm rarely announces its own invalidity in its text. The system must track and surface normative status explicitly (`VIGENTE` vs `DEROGADA` vs `DESCONOCIDO`).

---

## 2. Ingestion & Hierarchical Legal Splitting (`LegalSplitter`)

Located at `ingestion/processors/legal_splitter.py`, the `LegalSplitter` breaks statutory texts and court rulings into structured nodes without loss of contextual hierarchy:

### 2.1 Recognized Statutory Structures
- **Normative Containers**: `LIBRO`, `PARTE`, `TÍTULO`, `CAPÍTULO`, `SECCIÓN`.
- **Articulated Provisions**: `ARTÍCULO`, `ART.`, `ARTÍCULO TRANSITORIO`, `ARTÍCULO ÚNICO`.
- **Sub-provisions**: `PARÁGRAFO`, `NUMERAL`, `LITERAL`.

### 2.2 Jurisprudential Structures (Judgments / Sentencias)
- **Header & Identification**: Reference code (e.g. `Sentencia C-055/22`, `T-406/92`), magistrate rapporteur (`Magistrado Ponente`).
- **Considerandos**: Legal considerations, ratio decidendi, and constitutional doctrine.
- **Resolutivos**: The operative part of the ruling (`RESUELVE`).

```
Document: Constitución Política de Colombia
 └── TÍTULO II: De los derechos, las garantías y los deberes
      └── CAPÍTULO 1: De los derechos fundamentales
           └── ARTÍCULO 13: Todas las personas nacen libres e iguales ante la ley...
                ├── Hierarchy Path: "TITULO II > CAPITULO 1 > ARTICULO 13"
                ├── Exact Character Offsets: [12450 : 13890]
                └── Normative Status: VIGENTE
```

---

## 3. Hybrid Retrieval Engine

Retrieval balances semantic comprehension with literal statutory citations:

1. **Dense Vector Search**:
   - Computes cosine similarity against 1024-dimensional embeddings (via `pgvector`).
   - Captures conceptual queries (e.g. *"¿Cuándo responde patrimonialmente el Estado por daños a particulares?"* maps to Article 90).
2. **Lexical Full-Text Search**:
   - PostgreSQL `to_tsvector('spanish', content)` indexed via GIN.
   - Preserves exact statutory terms, law numbers, and Latin legal maxims (e.g. *"habeas corpus"*, *"acción de tutela"*, *"non bis in idem"*).
3. **Score Fusion**:
   - Combines normalized dense and lexical scores via configurable weights (`SEMANTIC_WEIGHT = 0.7`, `LEXICAL_WEIGHT = 0.3`).

---

## 4. Cross-Encoder Reranking

Initial candidate retrieval yields `RETRIEVAL_TOP_K` (default: 20) passages. Because dense search can retrieve superficially similar but contextually weak matches, candidates are re-scored using a cross-encoder model:
- Assesses bidirectional cross-attention between query and passage.
- Selects the top `RERANK_TOP_K` (default: 5) most relevant passages.
- Computes `top_evidence_score`.

---

## 5. Strict Grounding: The Verification Pass

If `top_evidence_score < MIN_SIMILARITY_SCORE`, retrieval is deemed insufficient, triggering an immediate refusal:

> *"No se encontró evidencia suficiente en el corpus jurídico disponible para sustentar una respuesta con certeza legal."*

When evidence passes the threshold:
1. **Primary LLM Generation**: Synthesizes the response citing verified articles and judgments.
2. **Independent Verification Pass**: A dedicated verifier model evaluates each factual statement in the draft against the retrieved chunks to confirm:
   - Does chunk $C_i$ explicitly support proposition $P_j$?
   - Are cited article numbers accurate?
   - Is any norm cited as active without verification?
3. **Citation Inspector**: Emits structured citation metadata containing:
   - Source document title and official URL (e.g. SUIN-Juriscol / Corte Constitucional).
   - Exact article or container heading.
   - Text fragment offsets for client-side highlighting.
