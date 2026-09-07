# v1.2.1 Windows launcher stabilization

- Replaced fragile batch-only startup flow with a PowerShell preflight launcher.
- Detects Python via `py -3`, `python`, or `python3` and resolves the actual executable.
- Checks port 8765 before launching; detects an already-running Studio separately from a foreign process.
- Checks/imports dependencies and installs only when missing.
- Imports the FastAPI app before background launch to expose module/import errors early.
- Starts uvicorn first, polls `/api/health`, and opens the browser only after the app is actually ready.
- Keeps startup/server logs under `logs/`.
- On failure, returns a non-zero code to the BAT wrapper, which keeps the console open with `pause`.
- Keeps the launcher window alive while the server process is running, so crashes are visible rather than disappearing.
