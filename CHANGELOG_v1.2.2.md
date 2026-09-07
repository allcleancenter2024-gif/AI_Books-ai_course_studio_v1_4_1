# v1.2.2 Windows launcher stabilization

- Replaced the UTF-8/Korean batch + PowerShell launcher chain with an ASCII-only batch bootstrap.
- Added `launcher.py` using Python standard library for port check, dependency check, app import check, server startup, health check, browser launch and logging.
- `startup_error.log` is created by Python before application startup, so launcher failures can be diagnosed reliably.
- Added `run_windows_debug.bat` for a no-server diagnostic test.
- Browser opens only after `/api/health` succeeds.
- Existing Studio instance on port 8765 is detected safely.
- Port conflicts now stop with an explicit message instead of closing silently.
