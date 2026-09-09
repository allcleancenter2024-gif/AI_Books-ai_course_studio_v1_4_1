# Dependency Map — Phase 0

## Python runtime dependencies

| Area | Evidence | Role |
|---|---|---|
| Web | FastAPI, Uvicorn | Studio HTTP/UI API server |
| HTTP | httpx, BeautifulSoup, trafilatura | Provider, web-source, and extraction clients |
| Persistence | sqlite3 (stdlib), psycopg, pymongo | SQLite is active authority; PostgreSQL/MongoDB are optional integration dependencies |
| Files | pypdf, python-pptx, Pillow, ReportLab | Import/export and file parsing |
| Local AI | Ollama and LM Studio HTTP APIs | Server-side ProviderManager adapters |
| Content/quality | generators, `education_quality`, `evidence_*`, `vector_index` | Course generation, quality checks, local retrieval |

## Service relationships

```text
FastAPI
 ├─ SQLite: courses, books, sources, vectors, job states, auth, evidence
 ├─ local files: uploads, exports, PDFs, logs
 ├─ Ollama (optional, loopback default)
 ├─ LM Studio (optional, loopback default)
 ├─ SearXNG / web extractors (optional; disabled by configuration flag)
 ├─ GitHub API backup (optional; only when explicitly configured and called)
 └─ Docker integration stack (optional, separate Compose)
```

## External dependency controls

- Provider enable flags and base URLs are sourced from configuration.
- `WEB_SEARCH_ENABLED` is a configuration gate; this audit did not call a search provider.
- GitHub backup requires environment configuration and an authenticated request.
- No MinIO, Redis, Celery, RQ, n8n, pgvector runtime implementation, or Tailscale application dependency was found in the inspected code.

## Finding

MEDIUM — the dependency list contains PostgreSQL and MongoDB client libraries while the desktop runtime authority is SQLite. The role separation should be explicit in deployment and backup documentation before any production transition.
