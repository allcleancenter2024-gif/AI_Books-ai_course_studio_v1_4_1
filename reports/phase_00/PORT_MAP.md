# Port Map — Phase 0

Values below are configuration/source facts only; listening sockets were not probed in this phase.

| Service | Port / binding evidence | Classification | Notes |
|---|---|---|---|
| Studio FastAPI | `APP_HOST` default `127.0.0.1`, `APP_PORT` default `8765` | LOCALHOST ONLY by default | Launcher passes those values to Uvicorn. |
| Ollama | default `127.0.0.1:11434/v1` | LOCALHOST ONLY by default | Provider-side only. |
| LM Studio | default `127.0.0.1:12345/v1` | LOCALHOST ONLY by default | Provider-side only. |
| PostgreSQL Compose | `127.0.0.1:${POSTGRES_HOST_PORT:-5434}:5432` | LOCALHOST ONLY | Docker optional stack. |
| MongoDB Compose | `127.0.0.1:${MONGO_HOST_PORT:-27018}:27017` | LOCALHOST ONLY | Docker optional stack. |
| pgAdmin Compose | `127.0.0.1:${PGADMIN_HOST_PORT:-5051}:80` | LOCALHOST ONLY | Administrative UI. |
| Mongo Express Compose | `127.0.0.1:${MONGO_EXPRESS_HOST_PORT:-8082}:8081` | LOCALHOST ONLY | Administrative UI. |
| app-api Compose | `127.0.0.1:${APP_API_HOST_PORT:-3001}:3000` | LOCALHOST ONLY | Separate Node/Prisma service. |
| SearXNG Compose | `127.0.0.1:${SEARXNG_HOST_PORT:-8888}:8080` | LOCALHOST ONLY | Separate optional web-RAG stack. |
| Publisher preview | no authoritative runtime binding confirmed | UNKNOWN | Separate Next.js project; no process was inspected. |

## Findings

- PASS — inspected Compose mappings use loopback publication, not public `0.0.0.0` publication.
- MEDIUM — runtime overrides in `.env` or process arguments were intentionally not read because they may contain secrets. Actual bindings must be verified in a separately approved runtime audit.
- PASS — no Tailscale-specific listening or routing configuration was found in application/Compose source.
