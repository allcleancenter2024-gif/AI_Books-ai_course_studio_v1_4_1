# Security Findings — Phase 0

Static-only assessment. A finding is not a confirmed exploit; no penetration test, endpoint request, credential inspection, or runtime scan was performed.

## Application findings

| Severity | Finding | Evidence / impact |
|---|---|---|
| HIGH | Startup can mutate the authoritative SQLite schema/data | `create_app()` invokes `init_db()`; this includes DDL, `ALTER`, indexes, and catalog upserts. Startup must not be treated as read-only. |
| MEDIUM | Provider endpoint configuration accepts an authenticated base URL | Later security review should restrict destinations to approved local endpoints or a documented allowlist. |
| MEDIUM | Some export and AI routes perform work synchronously | A slow authenticated request can occupy a server worker; route-level timeouts and job-only enforcement require later review. |
| MEDIUM | Production cookie safety is validation-only | Configuration identifies insecure production cookies, but static analysis did not prove boot-time enforcement. |
| LOW | Authentication protection is present on provider, source, course, hybrid, manual and GitHub routes | `require_authenticated` is router-level; login/session/health are intentionally public. Runtime authorization behavior was not tested. |
| LOW | Static scan found path normalization and upload size/type controls | Their complete bypass resistance was not tested. |

## Host-level findings requiring separate review

These are **not recorded as confirmed Studio failure causes**.

| Severity | Finding | Evidence recorded during read-only host review |
|---|---|---|
| HIGH | Windows Update servicing error | KB5124008 / build 26200.9445 was recorded with error `0x80070002`. User-supplied elevated DISM and SFC checks later reported no component-store or protected-file corruption. |
| HIGH | IObit Uninstaller service crash | `IUService.exe` recorded `0xc0000005` access violation around the restart sequence. |
| MEDIUM | Dangling kernel driver service | `PRI-Driver` is configured to reference missing `C:\Windows\System32\drivers\PRI-Driver.sys` and fails to start. |
| MEDIUM | Shutdown delay/veto record | TopDesk had Windows shutdown delay/veto records. |

The above host findings require separate Windows/vendor review. This phase did not alter Windows Update, registry, drivers, services, IObit, or TopDesk.
