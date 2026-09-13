# v1.27.0 — 2026-09-13

## Studio-owned Hermes weekly research

- Added the Studio-owned weekly official-release-note workflow with an explicit source allowlist, safe HTTP collection, change detection, and retained Evidence Packets.
- Added read-only Hermes summarization with atomic `submitted`, `running`, `completed`, `timed_out`, `draft_created`, and `error` result transitions plus bounded telemetry.
- Enforced the 120–300 second weekly Hermes deadline. Timeout and failure retain evidence, create no Draft, and cannot make Hermes a Studio-wide failure.
- Added `SCHEDULER_OWNER=STUDIO` and kept `HERMES_CRON_ENABLED=false`; no external cron or SearXNG dependency is required for official-source collection.
- Added weekly state migration and isolated-runtime cleanup coverage.

## Canary and compatibility

- The exact pinned qwen2.5 Canary was isolated and verified. It failed safely because its 32K context window is below Hermes’ 64K minimum; the original profile was unchanged and optional fallback remains recommended.
- Publisher boundaries and the existing Studio Job/Draft Review Gate remain unchanged.
- Full regression suite: 116 passed (14 existing warnings).
