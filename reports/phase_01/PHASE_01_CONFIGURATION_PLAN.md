# PHASE 1 — Configuration / Environment Standardization Plan

## Status

PLAN ONLY — NO SOURCE, `.env`, DATABASE, DOCKER, PROVIDER, NETWORK, OR WINDOWS CHANGE

This plan follows the approved Phase 0 result. It is not approval to implement Phase 1.

## Baseline

- Phase 0: PASS.
- Isolated pytest baseline: 63 passed, 2 dependency deprecation warnings, 12.39 s.
- SQLite remains the authoritative desktop data store. Docker PostgreSQL/MongoDB are optional integration/replication services.
- Studio and local providers default to loopback addresses. Tailscale remains independent and optional.
- Existing uncommitted changes already introduce configuration values in `.env.example`, `studio/config.py`, `launcher.py`, `providers/engine.py`, `studio/services/web_search.py`, and tests. They are treated as user-owned baseline changes, not as Phase 1 changes.

## Evidence-based gaps

| Priority | Gap | Evidence |
|---|---|---|
| HIGH | Static manual facts can drift from runtime configuration | `studio/services/manual_service.py` still contains `v1.24.0` and `http://127.0.0.1:8765` literals while `studio/config.py` has version/config values. |
| MEDIUM | Web-search configuration is distributed | `studio/services/web_search.py` reads provider, timeout, cache, Firecrawl and extractor settings directly from environment. |
| MEDIUM | Provider timeouts are not configuration constants | `providers/engine.py` has fixed default timeouts, including a 900-second Ollama timeout. |
| MEDIUM | Local-provider parallelism is read directly in generation service | `AI_COURSE_STUDIO_LMSTUDIO_PARALLELISM` is bounded in `generation_service.py`, outside the central config module. |
| LOW | UI contains intentional localhost links | `static/index.html` has local pgAdmin, Mongo Express and Publisher links. These are user-interface links, not Studio server binding. Any change requires separate UX/security review. |

## Minimal implementation proposal

### 1. Preserve and complete a single configuration boundary

Target: `studio/config.py`.

- Keep existing environment parsing helpers and bounded numeric parsing.
- Add only settings already consumed in code and necessary for safe operation:
  - local-provider request timeout defaults and bounded maximums;
  - LM Studio concurrency maximum, constrained to `1` unless a later, measured-capacity decision approves more;
  - SearXNG/local extractor timeout and cache limits where centralization does not expand behavior.
- Retain local-first defaults: Studio, Ollama, LM Studio and optional web-RAG stay loopback by default.
- Do not add Tailscale settings, Docker routing settings, public bindings, credentials, or a new framework.

### 2. Replace safe duplicate runtime facts only

Potential targets: `studio/services/manual_service.py`, `providers/engine.py`, `studio/services/generation_service.py`, `studio/services/web_search.py`.

- Replace duplicated Studio version/base URL facts in operational metadata with already-existing configuration values.
- Replace only timeout/parallelism literals with validated configuration values.
- Do not alter provider request semantics, auto-connect behavior, model choice, or fallback policy in this phase.
- Do not change localhost-only UI links without a separate decision about the administrative access model.

### 3. Update `.env.example` only as a contract

- Document every newly centralized non-secret setting with its safe default.
- Preserve placeholders for credentials; never copy an actual `.env` value.
- Keep `PUBLIC_ACCESS=false`, blank `PUBLIC_BASE_URL`, and loopback provider defaults.
- Do not create, edit, or read the real `.env` file.

### 4. Tests

- Extend configuration unit tests to cover bounded values, safe defaults, production-cookie validation, and provider-disable behavior.
- Use the existing disposable test runtime only.
- Do not call a real provider, Docker, SearXNG, GitHub, or browser.
- Run the full pytest baseline and compare Git status before/after.

## Planned file scope

| File | Planned change | Risk |
|---|---|---|
| `studio/config.py` | Add/centralize only existing operational settings and validation | Medium; import has current filesystem side effects |
| `providers/engine.py` | Consume central timeout settings | Medium; affects local AI wait behavior |
| `studio/services/generation_service.py` | Consume central concurrency setting, retain safe maximum 1 | Medium; affects local AI scheduling |
| `studio/services/web_search.py` | Consume selected central web-search limits | Medium; must not cause a network call during tests |
| `studio/services/manual_service.py` | Remove stale version/base URL literals | Low |
| `.env.example` | Document the configuration contract, no secrets | Low |
| `tests/test_configuration.py` | Add isolated configuration assertions | Low |

No Docker file, database model, migration, runtime `.env`, static UI link, provider model, firewall, Tailscale configuration, or Windows setting is in the planned write scope.

## Acceptance criteria

- No secret value introduced or printed.
- Default Studio/provider bindings remain loopback.
- Tailscale remains absent from application control flow.
- SQLite remains authoritative; no database/migration change occurs.
- Real `.env` remains untouched.
- Real providers, Docker, web search, and server remain unstarted during tests.
- Full isolated pytest passes.
- Git diff is limited to the approved files; existing user modifications are not overwritten.
- Rollback is file-level reversal of Phase 1-only hunks; no data rollback is needed.

## Human review decision required

Before implementation, approve or amend:

1. Centralize the listed timeout/concurrency values with LM Studio concurrency capped at 1.
2. Replace stale manual-service Studio URL/version literals with central configuration values.
3. Keep static UI localhost management links unchanged for this phase.
4. Permit only the planned files and isolated pytest verification.

## Result

PHASE 1 PLAN: READY FOR HUMAN REVIEW

