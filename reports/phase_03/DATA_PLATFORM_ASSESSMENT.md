# PHASE 3 — Data Platform Safety Assessment

## Confirmed current topology

```text
Studio FastAPI
  └─ SQLite (RUNTIME_DIR/data/studio.db) — authoritative runtime store
       ├─ courses, books, lesson units, users, sessions, jobs
       ├─ source metadata, extracted text, evidence packs
       └─ source vectors (SQLite BLOB)

Optional Docker stack (not in the Studio request path)
  ├─ PostgreSQL — ServiceRecord replication target for app-api
  └─ MongoDB — raw source replication target for app-api
```

There is no MinIO/S3 client, MinIO Compose service, pgvector extension, or
PostgreSQL data-access path in the Studio FastAPI application. These components
must not be inferred as deployed.

## Safety properties confirmed

| Property | Evidence | Status |
|---|---|---|
| Desktop Studio survives optional stack absence | `studio/multidb.py` performs SQLite-only persistence; mirror hook is a no-op | PASS |
| Studio database is local and explicit | `DB_PATH = RUNTIME_DIR / data / studio.db` | PASS |
| Test runtime is isolated | `tests/conftest.py` sets a unique temporary `AI_COURSE_STUDIO_RUNTIME_DIR` before imports | PASS |
| Docker administration interfaces are private by default | Compose publishes PostgreSQL, MongoDB, pgAdmin, Mongo Express, and app-api only through `127.0.0.1` | PASS |
| Existing transfer is one-way | `scripts/sync_sqlite_to_multidb.py` documents SQLite as unchanged and uses PostgreSQL/Mongo upserts | PASS, static only |
| Public object storage is absent | No MinIO/S3 configuration or client found | PASS — not deployed |

## Constraints and risks

### HIGH — no approved production migration contract

The sync script has no environment namespace/prefix, checksum ledger,
transaction/object compensation protocol, or restore verification. It is an
optional legacy migration utility, not an approved production data plane.
Do not run it against production data until a dedicated migration plan is
reviewed.

### MEDIUM — pgvector and MinIO acceptance criteria are not applicable yet

Current vector storage uses SQLite BLOBs. There is no pgvector schema or MinIO
object prefix to test. Introducing either requires an explicit architecture
decision, new dependencies, migrations, data-copy/rollback procedure, and
separate development/test/staging/production namespaces.

### LOW — original uploads are intentionally ephemeral

`studio/services/upload.py` writes to the local uploads directory; the README
states that originals are removed after extraction. This is a product retention
choice, not a MinIO-backed asset workflow. Any retention-policy change needs a
separate user decision.

## Preconditions for a later PostgreSQL/pgvector/MinIO implementation

1. Approve the target role of each system and the authoritative write source.
2. Define distinct database names and object prefixes for development, test,
   staging, and production; tests must never use production credentials/prefixes.
3. Add migrations for relational schema and pgvector only after backup and
   rollback procedures are reviewed.
4. Add object checksum, idempotency key, orphan detection, and compensation for
   DB/object partial failures.
5. Verify backup and restore using non-production data before any cutover.
6. Keep PostgreSQL, MinIO, Redis, Ollama, and LM Studio off the public Internet.

## Non-actions in this phase

- No Docker Compose change
- No database migration or sync execution
- No MinIO/pgvector package or service addition
- No actual `.env` read/change
- No production/test data access
