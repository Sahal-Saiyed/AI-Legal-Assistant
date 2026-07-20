# Ingestion Pipeline

## Overview

The ingestion pipeline is responsible for converting the legal knowledge base into a searchable vector database.

This process runs offline whenever new documents are added or existing documents are updated.

The pipeline does NOT involve the LLM. Its only responsibility is preparing the knowledge base for semantic search.

---

# Input

Supported file types:

- PDF
- Markdown (.md)
- Text (.txt)

Location:

knowledge_base/

---

# Output

Persistent ChromaDB vector database stored inside:

vector_dbs/chroma/

Each stored record contains:

- Chunk text
- Embedding vector
- Metadata

---

# Pipeline Flow

Knowledge Base

↓

Document Loader

↓

Metadata Extraction

↓

Chunking

↓

Embedding Generation

↓

ChromaDB Storage

---

# Components

## 1. Document Loader

Responsibilities:

- Traverse knowledge_base recursively.
- Detect supported document types.
- Read document contents.
- Convert documents into LangChain Document objects.
- Attach document-level metadata.

Output:

List[Document]

---

## 2. Metadata Extraction

Every document must contain metadata before chunking.

Example:

{
    "category": "...",
    "document_name": "...",
    "file_type": "...",
    "source": "official",
    "relative_path": "..."
}

Metadata must remain attached throughout the pipeline.

---

## 3. Chunking

Responsibilities:

- Split large documents into manageable chunks.
- Preserve semantic meaning.
- Maintain overlap between chunks.
- Preserve metadata.

Chunk metadata should additionally include:

{
    "chunk_index": ...
}

---

## 4. Embedding Generation

Embedding model:

intfloat/e5-base-v2

Responsibilities:

- Convert every chunk into a vector.
- Preserve metadata.
- Produce one embedding per chunk.

No LLM is involved.

---

## 5. Vector Storage

Vector Database:

ChromaDB

Responsibilities:

- Store embeddings
- Store original chunk text
- Store metadata

The vector database acts as the retrieval index for the chatbot.

---

# Retrieval Flow

User Question

↓

Embedding Model

↓

ChromaDB Similarity Search

↓

Relevant Chunks

↓

LLM

↓

Final Answer

---

# Metadata Schema

Every stored chunk should contain:

- category
- document_name
- file_type
- source
- relative_path
- chunk_index

---

# Development Order

1. Document Loader
2. Metadata Extraction
3. Chunking
4. Embedding Generation
5. ChromaDB Storage
6. Retrieval Testing

Do not move to the next stage until the current stage is fully tested.

---

# Success Criteria

The ingestion pipeline is complete when:

- All documents are successfully loaded.
- Metadata is correctly attached.
- Documents are chunked.
- Embeddings are generated.
- Chunks are stored in ChromaDB.
- Similarity search returns relevant chunks.