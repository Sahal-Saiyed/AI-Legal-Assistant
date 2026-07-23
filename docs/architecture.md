# JuriGPT architecture

## System context

```mermaid
flowchart TB
    User["Authenticated User"] --> Browser["React / Vite Client"]
    Browser -->|HTTPS + JWT| FastAPI["FastAPI Application"]
    FastAPI --> Mongo["MongoDB Atlas"]
    FastAPI --> RAG["RAG Service"]
    RAG --> Intent["Template Intent Detector"]
    Intent --> Templates["Template Service"]
    Templates --> TemplateFiles["Isolated Template Files"]
    RAG --> Chroma["Persistent ChromaDB"]
    RAG --> Gemini["Gemini API"]
    FastAPI --> PDF["Template PDF Service"]
    PDF --> Mongo
```

The React client communicates only with FastAPI. It never accesses MongoDB,
ChromaDB, or Gemini directly.

## Offline ingestion pipeline

```mermaid
flowchart LR
    Files["knowledge_base/ categories"] --> Loader["Document Loader"]
    Templates["knowledge_base/templates/"] -. "excluded" .-> Loader
    Loader -->|"List[Document]"| Chunker["Recursive Chunker"]
    Chunker -->|"Chunks + metadata"| Embedder["E5 Embedder"]
    Embedder -->|"Normalized vectors"| Store["Chroma Vector Store"]
    Store --> Index["vector_dbs/chroma/"]
```

- The loader extracts source text and metadata.
- The loader excludes every file below `knowledge_base/templates/` by default.
- The chunker preserves metadata and produces deterministic chunk identifiers.
- The embedder creates normalized passage vectors.
- The vector store persists chunks and vectors. It does not perform retrieval.

Any stale Chroma result whose category or relative path identifies the template
folder is blocked before context processing. Deployments that previously
embedded templates must rebuild the collection to remove those vectors.

## Online informational-question flow

```mermaid
sequenceDiagram
    participant UI as React Client
    participant API as FastAPI
    participant RAG as RAG Service
    participant ID as Intent Detector
    participant RET as Retriever
    participant CP as Context Processor
    participant PB as Prompt Builder
    participant LLM as Gemini Client

    UI->>API: POST /api/v1/ask/stream
    API->>API: Validate JWT and request
    API->>RAG: stream(question, language, recent turns)
    RAG->>ID: classify semantic intent
    ID-->>RAG: informational
    RAG->>RET: retrieve(question)
    RET-->>RAG: ranked chunks
    RAG->>CP: deduplicate and merge
    CP-->>RAG: processed context
    RAG->>PB: build grounded prompt
    PB-->>RAG: system + user prompts
    RAG->>LLM: stream_generate(...)
    LLM-->>API: text deltas
    API-->>UI: NDJSON delta events
    LLM-->>RAG: final usage metadata
    RAG-->>API: structured completion
    API-->>UI: complete event
```

The API emits retrieval metadata before generation, incremental text deltas
during generation, and one final structured response. Partial deltas are not
written to MongoDB. The completed assistant message is persisted once.

## Legal-document generation

```mermaid
flowchart TD
    Question["Current request + recent turns"] --> Detect["Semantic intent and fact extraction"]
    Detect -->|"Informational"| RAG["Normal RAG path"]
    Detect -->|"Document request"| Catalog["Template catalog"]
    Catalog -->|"No matching template"| Unsupported["Return supported formats"]
    Catalog --> Fields{"All mandatory fields supplied?"}
    Fields -->|"No"| FollowUp["Ask focused follow-up questions"]
    FollowUp --> Question
    Fields -->|"Yes"| Load["Load placeholder template"]
    Load --> Fill["Fill using supplied values only"]
    Fill --> Text["Formatted document text"]
    Text --> Render["Legal-format ReportLab renderer"]
    Render --> Mongo["MongoDB generated_documents"]
    Mongo --> Download["Authenticated download endpoint"]
```

Template selection never queries ChromaDB. Definitions and placeholder Markdown
are read only from `knowledge_base/templates/`. Original source PDFs can remain
there as references without becoming knowledge chunks. Missing mandatory facts
stop generation; the assistant asks for them and recent conversation turns let
the next request continue the same draft. Unsupported document types do not
fall through to RAG.

The completed Markdown document is the canonical formatted text. The PDF
renderer maps headings, clauses, address/date blocks, signatures, witnesses,
page footers, and document spacing into a legal-document layout. PDF bytes are
stored with the authenticated user's ID and the download endpoint enforces the
same ownership check.

## Authentication and persistence

```mermaid
erDiagram
    USERS ||--o{ CONVERSATIONS : owns
    USERS ||--o{ GENERATED_DOCUMENTS : owns
    CONVERSATIONS ||--o{ MESSAGES : contains

    USERS {
        ObjectId _id
        string name
        string email
        string password_hash
    }
    CONVERSATIONS {
        string _id
        ObjectId user_id
        string title
        datetime updated_at
    }
    GENERATED_DOCUMENTS {
        string _id
        ObjectId user_id
        string filename
        binary pdf_data
        datetime created_at
    }
```

Passwords are hashed and never returned. JWT subjects contain the Mongo user
identifier. Every conversation and generated-document query includes the
authenticated user ID.

## Frontend performance boundaries

- Login and workspace pages are route-level lazy chunks.
- React, motion, Markdown, and HTTP dependencies are stable vendor chunks.
- Completed user and assistant messages are memoized, preventing historical
  Markdown responses from re-rendering for every streaming delta.
- Sidebar filtering and sorting are memoized by conversation list and query.
- Streaming text remains local to `ChatWindow`; persistence occurs only after a
  complete response.

## Service responsibilities

| Component | Responsibility |
| --- | --- |
| API routes | HTTP validation, authentication dependencies, response transport |
| RAG Service | Intent routing and orchestration of the selected pipeline |
| Template Service | Field collection, isolated template selection, and filling |
| Template Loader | Safe catalog and source-file loading from the template root |
| Intent Detector | Semantic information-versus-document classification |
| Placeholder Filler | Populate formats using explicit user values only |
| Retriever | Query embedding and Chroma similarity search |
| Context Processor | Deduplication and overlap merging |
| Prompt Builder | Context formatting and legal instructions |
| Gemini Client | Provider-specific generation and streaming |
| Conversation Service | Per-user MongoDB conversation CRUD |
| Document Service | Legal-format PDF rendering, storage, and retrieval |

## Deployment notes

- Serve FastAPI and the frontend over HTTPS.
- Set `VITE_API_BASE_URL` to the public API origin when deployed separately.
- Keep `.env`, Atlas credentials, JWT secrets, and Gemini keys outside source
  control.
- Persist `vector_dbs/chroma/` on durable storage.
- Use a reverse proxy configured not to buffer `application/x-ndjson` streams.
- Rebuild Chroma whenever the embedding model or source corpus changes.
- Rebuild Chroma after removing templates from an older mixed collection.
