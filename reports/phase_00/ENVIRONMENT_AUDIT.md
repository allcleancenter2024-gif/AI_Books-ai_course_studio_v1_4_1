# Environment Audit — Phase 0

## Configuration model

`studio/config.py` centralizes several defaults: application environment/host/port, public access flag, runtime paths, upload limits, cookie security, local provider enablement/URLs, and web-search enablement. `.env.example` contains placeholders and does not expose an actual credential in the inspected source.

## Safe defaults observed

- `APP_ENV=development`, `APP_HOST=127.0.0.1`, `APP_PORT=8765` by default.
- `PUBLIC_ACCESS=false` and blank public URL by default.
- Ollama and LM Studio default to loopback URLs.
- Max upload size defaults to 500 MB and chunk size to 1 MB.
- Production configuration reports an issue if secure cookies are disabled.
- Test fixtures set a disposable runtime directory and `APP_ENV=test` before application modules are loaded.

## Findings

| Severity | Finding | Recommended later action |
|---|---|---|
| HIGH | Importing configuration creates runtime directories; creating the app initializes SQLite and can alter schema. | Keep static audits import-free; move mutable initialization to an explicit, reviewed startup/migration step in a later phase. |
| MEDIUM | Provider configuration endpoint can change an authenticated server-side provider base URL at runtime. | Define an allowlist/administrative policy in a later security phase. |
| MEDIUM | Actual `.env` values were not inspected to avoid secret exposure. | Conduct a masked, approved configuration validation later. |
| LOW | Public-access validation checks configuration form, not DNS/TLS reachability. | Validate a public gateway only in a separately approved deployment phase. |

No `.env`, environment variable, credential, registry value, or system setting was changed.
