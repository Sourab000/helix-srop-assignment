# Helix SROP — State Persistence Pipeline

## Setup

```bash
git clone <your-repo>
cd helix-srop
uv sync
cp .env.example .env  # fill in GOOGLE_API_KEY
uv run python -m app.rag.ingest --path docs/
uv run uvicorn app.main:app --reload
```

## Quick Test

```bash
SESSION=$(curl -s -X POST localhost:8000/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"user_id": "u_demo", "plan_tier": "pro"}' | jq -r .session_id)

curl -s -X POST localhost:8000/v1/chat/$SESSION \
  -H "Content-Type: application/json" \
  -d '{"content": "How do I rotate a deploy key?"}' | jq .
```

## Architecture

```
+----------------+     +------------------+     +-------------------+
|   FastAPI      | --> |    Pipeline      | --> |  Route Selector   |
|   (routes)    |     |   (orchestra)    |     |  (knowledge/    |
+----------------+     +------------------+     |   account/     |
        |                       |           |   escalation)  |
        v                       v           +-------------------+
+----------------+     +------------------+            |
|   SQLite      | --> |   Session       |                 |
|   (state)    |     |   State        | <----------------+
+----------------+     +------------------+
        |                       |
        v                       v
+----------------+     +------------------+
|   ChromaDB    |     |   LLM          |
|   (rag)      |     |   (gemini)     |
+----------------+     +------------------+
```

## Design Decisions

### State persistence (which pattern and why)
I used **Pattern 2: Re-hydrate from message history stored in your DB** because:
- It allows full LLM context through the conversation history
- State persists in SQLite which survives uvicorn restarts
- The pipeline loads session state from DB and passes it as context to agents

### Chunking strategy
I used **heading-aware chunking** because:
- It preserves semantic context of sections
- Splits on markdown headings (##, ###) to keep sections coherent
- Limits chunks to ~400 tokens and splits at paragraph boundaries when needed

### Vector store choice
I chose **ChromaDB** because:
- Simple embedded vector store with persistence
- Easy integration with Python
- Good performance for small-to-medium document collections

## Known Limitations

- LLM quota constraints may cause 429 errors under heavy load
- ADK version incompatibilities required using direct LLM calls instead of full ADK framework
- No streaming support yet (extension E3 not implemented)

## What I'd Do With More Time

- Implement full ADK agent with proper session management
- Add streaming responses (SSE)
- Implement guardrails for PII redaction

## Time Spent

| Phase | Time |
|-------|------|
| Setup + DB + FastAPI boilerplate | 2h |
| RAG ingest + search_docs | 2h |
| ADK agents | 1h |
| pipeline.py + state persistence | 3h |
| Tests | 1h |
| README | 30min |
| **Total** | ~9.5h |

## Extensions Completed

- [x] E2: Escalation agent (basic implementation)
- [ ] E1: Idempotency
- [ ] E3: Streaming SSE
- [ ] E4: Reranking
- [ ] E5: Guardrails
- [ ] E6: Docker
- [ ] E7: Eval harness