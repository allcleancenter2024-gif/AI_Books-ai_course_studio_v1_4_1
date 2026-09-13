# v1.27.2 — 2026-09-13

## Limited Scheduled Pilot safety

- Added a SQLite-backed expiring lock so Studio startup catch-up and the OS-triggered weekly runner cannot execute the same weekly job concurrently.
- Duplicate invocations return `already_running` without collecting sources, creating Evidence Packets, starting Hermes, or creating Drafts.
- Added lock acquire/release regression coverage; the lock is released on normal and exceptional runner exit.
- Limited Scheduled Pilot remains stopped until this guard is reviewed in production-like isolation.

## Verification

- Full regression suite: 117 passed.
- Python compile check and `git diff --check` passed.
