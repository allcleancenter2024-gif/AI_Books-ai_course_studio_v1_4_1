"""Portable Windows executable entry point for the Studio BAT-equivalent launcher."""
from pathlib import Path
import shutil
import subprocess
import sys


def _python_command() -> list[str] | None:
    """Return a usable Windows Python command without assuming python.exe exists."""
    if not getattr(sys, "frozen", False):
        return [sys.executable]
    py_launcher = shutil.which("py")
    if py_launcher:
        return [py_launcher, "-3"]
    python = shutil.which("python") or shutil.which("python3")
    return [python] if python else None


if __name__ == "__main__":
    root = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    launcher = root / "launcher.py"
    command = _python_command()
    if not launcher.is_file():
        print(f"[ERROR] launcher.py was not found next to this executable: {launcher}")
        raise SystemExit(21)
    if not command:
        print("[ERROR] Python 3 was not found. Install Python 3.10 or newer, then try again.")
        raise SystemExit(10)
    raise SystemExit(subprocess.call([*command, str(launcher), *sys.argv[1:]], cwd=root))
