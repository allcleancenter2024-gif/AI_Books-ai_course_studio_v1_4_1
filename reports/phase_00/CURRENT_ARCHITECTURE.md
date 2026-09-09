# Current Architecture — Phase 0

Mode: static, read-only audit. Evidence was collected from source, configuration examples, Compose files, test files, and previously recorded host events. No application process, provider, Docker service, database, or web search was started.

## Observed application

- Entry point: `app.py` creates the FastAPI app through `studio.application.create_app()`.
- Web application: FastAPI serves `static/` and mounts API routers for authentication, provider control, sources, courses/books, manual content, hybrid RAG, GitHub backup, and system status.
- UI: static HTML/CSS/JavaScript in `static/`; it calls the FastAPI API rather than SQLite or local AI endpoints directly.
- Authoritative store: `studio/db.py` uses SQLite. `studio/multidb.py` documents PostgreSQL and MongoDB as optional integration/replication targets, not the runtime source of truth.
- Local AI boundary: `providers/engine.py` exposes Ollama and LM Studio through `ProviderManager`; browser code does not call them directly.
- Long work: book generation and source summarization have daemon-thread job paths with state persisted in SQLite. Some synchronous API routes also remain.
- Publisher: `publisher/` is a separate Next.js project. It is not a startup dependency of the FastAPI Studio process.

## Boundaries observed

```text
Browser static UI
  -> FastAPI routers (authenticated except login/health)
  -> service modules
  -> SQLite / local files / ProviderManager / optional web-source services

Docker PostgreSQL + MongoDB + app-api are a separate optional Compose stack.
Publisher is a separate Next.js project.
```

## Architecture findings

| Severity | Finding | Evidence / impact |
|---|---|---|
| HIGH | Runtime schema changes are embedded in `init_db()` | `create_app()` calls `init_db()`; it executes `CREATE`, `ALTER`, index creation and catalog upserts. This is a write side effect on startup and is not a separately versioned migration workflow. |
| MEDIUM | Synchronous generation routes remain | `/api/ai/week` and `/api/ai/book` call `build_book()` directly. Their `.../start` variants use background jobs, but callers can still use the blocking variants. |
| MEDIUM | Docker stack and desktop Studio have different data roles | Compose provisions PostgreSQL/MongoDB/app-api, while Studio is SQLite-authoritative. The distinction is documented in code but needs operational documentation to prevent incorrect assumptions. |
| LOW | Tailscale dependency was not found | Static search found no application startup, authentication, storage, or provider dependency on Tailscale. Runtime ON/OFF was not tested. |

## Scope limits

No runtime health call, import, test execution, database inspection, Docker inspection, provider call, or network call was made. Importing the current configuration/application can create runtime directories or initialize SQLite, so those actions were intentionally excluded.
