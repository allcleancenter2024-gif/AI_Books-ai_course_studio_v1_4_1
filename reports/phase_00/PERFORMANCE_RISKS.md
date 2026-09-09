# Performance Risks — Phase 0

| Severity | Risk | Static evidence | Effect / later validation |
|---|---|---|---|
| HIGH | Large source parsing/indexing is not proven to be fully job-only | Upload handling, parsing, storage and indexing are in service paths; source summary has an async job path but an end-to-end 500 MB test was not run. | Validate memory, disk, cancellation and recovery with disposable data only. |
| HIGH | Local inference can be long-running | LM Studio default timeout is 180 s; Ollama default is 900 s. | Verify bounded cancellation, client feedback and capacity behavior later. |
| MEDIUM | LM Studio optional parallelism can be raised to 2 | Default is 1, but `AI_COURSE_STUDIO_LMSTUDIO_PARALLELISM` allows up to 2. | Maintain 1 until measured VRAM/RAM headroom is documented. |
| MEDIUM | Blocking generation API variants exist | `/api/ai/week` and `/api/ai/book` call `build_book()` in-request. | Prefer and later enforce `.../start` job routes for long work. |
| MEDIUM | SQLite write contention is possible under concurrent jobs | WAL and busy timeout exist; multiple job/source/book writes are present. | Stress test with disposable runtime and verify busy/lock handling. |
| LOW | Docker SearXNG has explicit 512 MB / 1.5 CPU limits | Compose declaration only. | No container was started or measured. |

No resource test, provider invocation, browser test, upload, database write, or Docker action was performed in Phase 0.
