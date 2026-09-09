# Duplication Report — Phase 0

## Observations

- Persistence has two visible concepts: SQLite-authoritative desktop services and an optional PostgreSQL/MongoDB Compose/API stack. The code comments define the distinction, but operator-facing documentation must make it unmistakable.
- Both synchronous and background job variants exist for book generation. This duplicates behavior with different failure/timeout characteristics.
- Web source handling appears across source service, web-search providers and evidence routing. The modules have distinct responsibilities, but end-to-end boundary ownership requires later review.
- Provider behavior is centralized in `ProviderManager`; this is a positive consolidation. The endpoints still expose configure/test/models/auto-connect operations separately.
- Publisher is intentionally separate from Studio rather than a duplicate runtime component.

## Findings

| Severity | Finding | Follow-up |
|---|---|---|
| MEDIUM | Dual synchronous/background generation paths | Decide whether long generation must be job-only without breaking existing clients. |
| MEDIUM | Optional external databases can be confused with runtime authority | Clarify backup, restore, and data ownership before deployment work. |
| LOW | Several web-source layers | Document routing and retry ownership before consolidating any code. |

No code reorganization is proposed or performed in this phase.
