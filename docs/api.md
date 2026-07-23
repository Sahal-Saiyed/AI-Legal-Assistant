# JuriGPT API

Base URL during local development:

```text
http://127.0.0.1:8000
```

Interactive OpenAPI documentation:

- Swagger UI: `/docs`
- OpenAPI JSON: `/openapi.json`

Except for `/health`, registration, and login, endpoints require:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

## Health

### `GET /health`

Returns process health without checking Gemini, MongoDB, or ChromaDB.

```json
{ "status": "healthy" }
```

## Authentication

### `POST /api/v1/auth/register`

```json
{
  "name": "Asha Verma",
  "email": "asha@example.com",
  "password": "minimum-8-characters"
}
```

Returns HTTP `201` with a bearer token and user profile.

### `POST /api/v1/auth/login`

```json
{
  "email": "asha@example.com",
  "password": "minimum-8-characters"
}
```

### `GET /api/v1/auth/me`

Returns the authenticated user:

```json
{
  "id": "MongoObjectId",
  "name": "Asha Verma",
  "email": "asha@example.com"
}
```

## Legal answers

Supported language codes:

| Code | Language |
| --- | --- |
| `en` | English |
| `hi` | Hindi |
| `bn` | Bengali |
| `ta` | Tamil |
| `te` | Telugu |
| `mr` | Marathi |
| `gu` | Gujarati |
| `kn` | Kannada |
| `ml` | Malayalam |
| `pa` | Punjabi |
| `ur` | Urdu |

### `POST /api/v1/ask`

Non-streaming compatibility endpoint.

```json
{
  "question": "How do I file an FIR?",
  "language": "en",
  "conversation_context": []
}
```

`conversation_context` is optional and backward compatible. The frontend sends
at most the last 20 user and assistant turns so a user can answer template
follow-up questions:

```json
{
  "question": "The monthly rent is Rs. 20,000.",
  "language": "en",
  "conversation_context": [
    {"role": "user", "content": "Prepare a rent agreement for me."},
    {
      "role": "assistant",
      "content": "Please provide the landlord, tenant, property, dates, rent, and deposit."
    }
  ]
}
```

Conversation context is used only for document intent and explicit field
collection. It is not legal evidence and is never stored in ChromaDB.

Response:

```json
{
  "question": "How do I file an FIR?",
  "language": "en",
  "answer": "Grounded answer...",
  "sources": ["FIR Guide"],
  "generation_time": 1.42,
  "model_name": "gemini-2.5-flash",
  "input_token_count": 1200,
  "output_token_count": 280,
  "finish_reason": "STOP",
  "retrieved_chunks_count": 5,
  "processed_chunks_count": 3,
  "document": null,
  "document_error": null
}
```

### `POST /api/v1/ask/stream`

Uses the same request body and returns newline-delimited JSON:

```http
Content-Type: application/x-ndjson
Cache-Control: no-cache, no-transform
```

Events arrive in this order:

```json
{"type":"metadata","question":"How do I file an FIR?","language":"en","retrieved_chunks_count":5,"processed_chunks_count":3}
{"type":"delta","delta":"An FIR"}
{"type":"delta","delta":" may be filed..."}
{"type":"complete","response":{"question":"How do I file an FIR?","answer":"..."}}
```

If generation fails after streaming begins:

```json
{"type":"error","message":"Failed to generate a legal response"}
```

Reverse proxies must disable response buffering for this route.

## Conversations

All conversation endpoints are scoped to the authenticated user.

### `GET /api/v1/conversations`

Returns up to 200 conversations ordered by most recently updated.

### `PUT /api/v1/conversations/{conversation_id}`

Creates or replaces a conversation using a client-generated UUID.

```json
{
  "title": "FIR registration",
  "title_customized": false,
  "messages": [
    {
      "id": "message-uuid",
      "role": "user",
      "content": "How do I file an FIR?",
      "timestamp": "2026-07-23T12:00:00Z"
    }
  ],
  "updated_at": "2026-07-23T12:00:00Z"
}
```

Assistant messages additionally contain `answer`, `sources`, `disclaimer`,
`generation_time`, `language`, and optional generated-document metadata.

### `PATCH /api/v1/conversations/{conversation_id}`

```json
{ "title": "My FIR questions" }
```

### `DELETE /api/v1/conversations/{conversation_id}`

Returns HTTP `204`. Deletion is idempotent and restricted to the owner.

## Generated documents

Document requests are classified before retrieval. They never use template
chunks from ChromaDB:

- Missing mandatory information returns a focused follow-up and `document: null`.
- An unavailable format returns the supported template list and `document: null`.
- A complete, supported English request returns formatted document text and
  populates the `document` field.

Current catalog entries include Agreement to Sell, Exchange Deed, Gift Deed,
Lease Deed (including rent-agreement intent), Power of Attorney, Sale Deed,
Simple Mortgage Deed, and Will.

Example document metadata:

```json
{
  "id": "document-uuid",
  "filename": "complaint-ab12cd34.pdf",
  "document_type": "Complaint",
  "media_type": "application/pdf",
  "size_bytes": 4821,
  "created_at": "2026-07-23T12:05:00Z",
  "download_url": "/api/v1/documents/document-uuid"
}
```

### `GET /api/v1/documents/{document_id}`

Returns the PDF as an authenticated attachment. A user cannot download another
user's document.

## Error responses

Validation errors use FastAPI's HTTP `422` schema. Other errors use:

```json
{ "detail": "Human-readable error message" }
```

Common statuses:

| Status | Meaning |
| --- | --- |
| `400` | Invalid RAG request |
| `401` | Missing, invalid, or expired token |
| `404` | Conversation or document not found |
| `409` | Duplicate registration or identifier conflict |
| `422` | Request schema validation failed |
| `502` | Upstream model generation failed |
| `503` | MongoDB-backed persistence unavailable |
