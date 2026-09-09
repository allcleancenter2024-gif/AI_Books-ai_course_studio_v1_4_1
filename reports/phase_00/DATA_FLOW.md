# Data Flow — Phase 0

## Course and generation

```text
Authenticated UI
 -> course/book API route
 -> course/generation service
 -> ProviderManager (Ollama or LM Studio) and optional source context
 -> quality report / approval state
 -> SQLite metadata + Markdown/export files
```

The `.../start` book routes create background thread jobs and persist job state. Direct `/api/ai/week` and `/api/ai/book` routes can run the same work synchronously.

## Source ingestion and retrieval

```text
Authenticated upload / web / video route
 -> source service
 -> parser + upload storage
 -> SQLite source metadata / extracted text
 -> local vector index records
 -> source context for generation
```

Web-source and video paths can contact external endpoints when invoked; none were invoked during this audit.

## Export and publication

```text
Approved lesson state
 -> book/export service
 -> Markdown, PDF, PPTX, HWPX, dashboard files
 -> separate Publisher project consumes reviewed content
```

The code records lesson quality and an approval status. Static inspection did not prove an end-to-end publication gate in a live Publisher deployment.

## Data safety observations

- SQLite is configured with foreign keys, WAL mode, and a 10-second busy timeout.
- `next_service_id()` uses `BEGIN IMMEDIATE` to serialize ID allocation.
- Deletion and cleanup operations exist in source/evidence/job services but were not invoked.
- No MinIO object store or pgvector-backed retrieval flow was found in the current desktop runtime implementation.
