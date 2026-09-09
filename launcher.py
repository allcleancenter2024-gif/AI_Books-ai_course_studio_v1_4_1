from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
import traceback
import urllib.request
import webbrowser

from studio.config import APP_HOST, APP_PORT, LOGS_DIR, VERSION, APP_TITLE

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = LOGS_DIR
STARTUP_LOG = LOG_DIR / "startup_error.log"
SERVER_OUT = LOG_DIR / "server_stdout.log"
SERVER_ERR = LOG_DIR / "server_stderr.log"
HOST = APP_HOST
PORT = APP_PORT
BASE_URL = f"http://{HOST}:{PORT}"
REQUIRED = {
    "fastapi": "fastapi>=0.110",
    "uvicorn": "uvicorn[standard]>=0.27",
    "httpx": "httpx>=0.27",
    "multipart": "python-multipart>=0.0.9",
    "bs4": "beautifulsoup4>=4.12",
    "pypdf": "pypdf>=5.0",
    "pptx": "python-pptx>=1.0",
    "PIL": "Pillow>=10.0",
    "reportlab": "reportlab>=4.0",
    "youtube_transcript_api": "youtube-transcript-api>=1.2",
    "pymongo": "pymongo>=4.10",
    "psycopg": "psycopg[binary]>=3.2",
}


def ensure_log_dir() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def write_log(message: str, *, append: bool = True) -> None:
    ensure_log_dir()
    mode = "a" if append else "w"
    with STARTUP_LOG.open(mode, encoding="utf-8") as f:
        f.write(message.rstrip() + "\n")


def fail(message: str, code: int = 1) -> int:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    write_log(f"[{stamp}] {message}")
    print("\n[ERROR] " + message)
    print(f"[LOG] {STARTUP_LOG}")
    if SERVER_ERR.exists():
        try:
            lines = SERVER_ERR.read_text(encoding="utf-8", errors="replace").splitlines()[-30:]
            if lines:
                print("\n--- server_stderr.log (last 30 lines) ---")
                print("\n".join(lines))
                print("--- end log ---")
        except Exception:
            pass
    return code


def python_info() -> str:
    return f"{sys.version.split()[0]} | {sys.executable}"


def port_is_listening() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.6)
        return s.connect_ex((HOST, PORT)) == 0


def fetch_json(path: str, timeout: float = 1.5) -> dict | None:
    try:
        req = urllib.request.Request(
            BASE_URL + path,
            headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))
    except Exception:
        return None


def health_info(timeout: float = 1.5) -> dict | None:
    data = fetch_json("/api/health", timeout)
    return data if data and data.get("ok") else None


def health_ok(timeout: float = 1.5, expected_version: str | None = None) -> bool:
    data = health_info(timeout)
    if not data:
        return False
    if expected_version is not None:
        return str(data.get("version")) == str(expected_version)
    return True


def existing_app_identity() -> tuple[bool, str, str]:
    health = health_info()
    if not health:
        return False, "", ""
    version = str(health.get("version", ""))
    openapi = fetch_json("/openapi.json") or {}
    title = str((openapi.get("info") or {}).get("title", ""))
    is_studio = title.startswith("AI 강의 활용 Studio") or title.startswith("AI Course Studio")
    return is_studio, version, title


def windows_listening_pids(port: int) -> list[int]:
    if os.name != "nt":
        return []
    try:
        result = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
        )
        pids: set[int] = set()
        pattern = re.compile(rf"^\s*TCP\s+\S+:{port}\s+\S+\s+LISTENING\s+(\d+)\s*$", re.I)
        for line in result.stdout.splitlines():
            m = pattern.match(line)
            if m:
                pids.add(int(m.group(1)))
        return sorted(pids)
    except Exception:
        return []


def stop_previous_studio() -> tuple[bool, str]:
    """Stop an older Studio only after its HTTP identity has been verified."""
    is_studio, old_version, title = existing_app_identity()
    if not is_studio:
        return False, "The process on port 8765 is not identifiable as AI Course Studio."
    if os.name != "nt":
        return False, f"Older Studio {old_version} is running. Automatic replacement is Windows-only."
    pids = windows_listening_pids(PORT)
    if not pids:
        return False, f"Older Studio {old_version} was detected, but its Windows PID could not be found."
    print(f"[INFO] Older Studio detected: {title} (version {old_version})")
    print(f"[INFO] Replacing old server on port {PORT}. PID(s): {', '.join(map(str, pids))}")
    for pid in pids:
        result = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            write_log(f"taskkill failed for PID {pid}: {result.stdout}\n{result.stderr}")
            return False, f"Could not stop older Studio PID {pid}. Try closing its old command window."
    deadline = time.time() + 8
    while time.time() < deadline:
        if not port_is_listening():
            return True, f"Older Studio {old_version} stopped."
        time.sleep(0.25)
    return False, "Older Studio did not release port 8765 after termination."


def browser_url() -> str:
    return f"{BASE_URL}/?v={VERSION}&ts={int(time.time())}"


def missing_packages() -> list[str]:
    return [pkg for module, pkg in REQUIRED.items() if importlib.util.find_spec(module) is None]


def install_packages(packages: list[str]) -> bool:
    if not packages:
        return True
    print("[SETUP] Missing packages detected. Installing only what is needed...")
    cmd = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", *packages]
    result = subprocess.run(cmd, cwd=BASE_DIR)
    return result.returncode == 0


def preflight_import() -> tuple[bool, str]:
    try:
        os.environ["PYTHONPATH"] = str(BASE_DIR)
        if str(BASE_DIR) not in sys.path:
            sys.path.insert(0, str(BASE_DIR))
        from app import app  # noqa: F401
        return True, "APP_IMPORT_OK"
    except Exception:
        return False, traceback.format_exc()


def start_server() -> subprocess.Popen:
    ensure_log_dir()
    SERVER_OUT.write_text("", encoding="utf-8")
    SERVER_ERR.write_text("", encoding="utf-8")
    out = SERVER_OUT.open("a", encoding="utf-8")
    err = SERVER_ERR.open("a", encoding="utf-8")
    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    cmd = [sys.executable, "-m", "uvicorn", "app:app", "--host", HOST, "--port", str(PORT)]
    proc = subprocess.Popen(
        cmd,
        cwd=BASE_DIR,
        stdout=out,
        stderr=err,
        creationflags=creationflags,
    )
    proc._studio_out = out  # type: ignore[attr-defined]
    proc._studio_err = err  # type: ignore[attr-defined]
    return proc


def close_server_streams(proc: subprocess.Popen) -> None:
    for attr in ("_studio_out", "_studio_err"):
        f = getattr(proc, attr, None)
        if f:
            try:
                f.close()
            except Exception:
                pass


def wait_until_ready(proc: subprocess.Popen, seconds: int = 30) -> bool:
    deadline = time.time() + seconds
    last_print = -1
    while time.time() < deadline:
        if proc.poll() is not None:
            return False
        if health_ok(expected_version=VERSION):
            return True
        elapsed = int(seconds - max(0, deadline - time.time()))
        if elapsed >= last_print + 2:
            print(f"[WAIT] Server starting... {elapsed}s")
            last_print = elapsed
        time.sleep(0.5)
    return False


def diagnose() -> int:
    ensure_log_dir()
    STARTUP_LOG.write_text("", encoding="utf-8")
    print(f"AI Course Studio v{VERSION} launcher diagnostics")
    print(f"[PYTHON] {python_info()}")
    print(f"[FOLDER] {BASE_DIR}")
    listening = port_is_listening()
    print(f"[PORT] {PORT} listening={listening}")
    if listening:
        is_studio, v, title = existing_app_identity()
        print(f"[PORT OWNER] studio={is_studio} version={v or '?'} title={title or '?'}")
    missing = missing_packages()
    print(f"[PACKAGES] missing={missing if missing else 'none'}")
    ok, detail = preflight_import() if not missing else (False, "Skipped import because packages are missing")
    print(f"[APP IMPORT] {'OK' if ok else 'FAILED'}")
    if not ok:
        print(detail)
        write_log(detail)
        return 2
    print(f"[TARGET VERSION] {VERSION}")
    print("[DIAGNOSE] PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--diagnose", action="store_true")
    args = parser.parse_args()

    if args.diagnose:
        return diagnose()

    ensure_log_dir()
    STARTUP_LOG.write_text("", encoding="utf-8")
    print("============================================================")
    print(f" AI Course Studio v{VERSION} - Version-safe Windows Launcher")
    print(f" URL: {BASE_URL}")
    print(" LOGIN: Use the local administrator account on the opening screen.")
    print("============================================================")
    print(f"[1/5] Python: {python_info()}")

    print(f"[2/5] Checking port {PORT} and running version...")
    if port_is_listening():
        is_studio, running_version, title = existing_app_identity()
        if is_studio and running_version == VERSION:
            print(f"[OK] Studio v{VERSION} is already running. Opening current version.")
            webbrowser.open(browser_url())
            return 0
        if is_studio:
            ok, message = stop_previous_studio()
            print("[INFO] " + message)
            if not ok:
                return fail(
                    f"An older Studio ({running_version or '?'}) is still using port {PORT}. "
                    "Close the old Studio command window, then run this file again.",
                    11,
                )
        else:
            return fail(
                f"Port {PORT} is used by another program ({title or 'unknown service'}). "
                "This launcher will not terminate unrelated programs.",
                11,
            )
    print("[OK] Port is available for the current Studio.")

    print("[3/5] Checking required packages...")
    missing = missing_packages()
    if missing:
        print("[INFO] Missing: " + ", ".join(missing))
        if not install_packages(missing):
            return fail("Package installation failed. Check internet access and pip output above.", 12)
        still_missing = missing_packages()
        if still_missing:
            return fail("Packages are still missing after installation: " + ", ".join(still_missing), 13)
    print("[OK] Required packages are available.")

    print("[4/5] Checking application import...")
    ok, detail = preflight_import()
    if not ok:
        write_log(detail)
        return fail("Application import failed. See startup_error.log.", 14)
    print("[OK] Application import passed.")

    print("[5/5] Starting web server...")
    proc = None
    try:
        proc = start_server()
        if not wait_until_ready(proc, 30):
            rc = proc.poll()
            if rc is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
            running = health_info()
            extra = f" Running health: {running}" if running else ""
            return fail(f"Server did not become healthy as version {VERSION} within 30 seconds.{extra}", 15)

        print("\n[READY] Current Studio is running.")
        print(f"[VERSION] {VERSION}")
        print(f"[OPEN] {BASE_URL}")
        print("[LOGIN] The Studio login screen verifies your account before opening program data.")
        print("[INFO] Keep this window open while using Studio.")
        print("[INFO] Press Ctrl+C here to stop the server.\n")
        webbrowser.open(browser_url())

        while True:
            rc = proc.poll()
            if rc is not None:
                if rc != 0:
                    return fail(f"Web server exited unexpectedly with code {rc}.", 16)
                print("[STOPPED] Web server stopped.")
                return 0
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[STOP] Closing Studio...")
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        return 0
    except Exception:
        detail = traceback.format_exc()
        write_log(detail)
        return fail("Unexpected launcher error. See startup_error.log.", 99)
    finally:
        if proc:
            close_server_streams(proc)


if __name__ == "__main__":
    rc = main()
    if rc != 0 and "--diagnose" not in sys.argv:
        print("\nLauncher stopped with an error.")
        print("Press Enter to close this window.")
        try:
            input()
        except Exception:
            pass
    raise SystemExit(rc)
