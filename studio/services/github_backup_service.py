"""Safe, opt-in GitHub repository status and source-backup support."""
from __future__ import annotations
import base64, io, os, re, subprocess, zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import httpx
from ..config import BASE_DIR

_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_BACKUP_PREFIX = "backups/ai-course-studio"
_MAX_BACKUP_BYTES = 90 * 1024 * 1024
_INCLUDED_ROOTS = ("studio", "static", "generators", "providers", "scripts", "services")
_INCLUDED_FILES = ("app.py", "launcher.py", "studio_launcher_entry.py", "requirements.txt", "README.md", "docker-compose.yml", "docker-compose.searxng.yml", ".gitignore", ".env.example", "run_windows.bat", "run_windows_debug.bat", "start_searxng.ps1", "stop_searxng.ps1")
_SKIP_PARTS = {"__pycache__", ".pytest_cache", ".pytest_tmp", "build", "dist", "data", "uploads", "exports", "output", "logs", "backups", "previous_versions", "node_modules"}

def _repository():
    value = os.getenv("GITHUB_REPOSITORY", "").strip()
    return value if _REPOSITORY_RE.fullmatch(value) else None

def _remote_url():
    value = os.getenv("GITHUB_REPOSITORY_URL", "").strip()
    parsed = urlparse(value)
    return value.removesuffix(".git") if parsed.scheme == "https" and parsed.hostname in {"github.com", "www.github.com"} else None

def _git(*args):
    try: return subprocess.run(["git", *args], cwd=BASE_DIR, capture_output=True, text=True, timeout=12, check=False)
    except (OSError, subprocess.TimeoutExpired): return None

def status():
    repository, remote_url = _repository(), _remote_url()
    inside = _git("rev-parse", "--is-inside-work-tree")
    local = bool(inside and inside.returncode == 0 and inside.stdout.strip() == "true")
    remote = _git("remote", "get-url", "origin") if local else None
    origin = remote.stdout.strip() if remote and remote.returncode == 0 else ""
    return {"configured": bool(repository and remote_url), "repository": repository, "remote_url": remote_url, "token_configured": bool(os.getenv("GITHUB_TOKEN", "").strip()), "local_repository": local, "origin_configured": bool(origin), "origin_url": origin or None, "backup_prefix": _BACKUP_PREFIX}

def _iter_backup_paths():
    for name in _INCLUDED_FILES:
        path = BASE_DIR / name
        if path.is_file(): yield path
    for root_name in _INCLUDED_ROOTS:
        root = BASE_DIR / root_name
        if root.is_dir():
            for path in root.rglob("*"):
                if path.is_file() and not any(part in _SKIP_PARTS for part in path.relative_to(BASE_DIR).parts): yield path

def _backup_archive():
    count = 0
    with io.BytesIO() as buffer:
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in _iter_backup_paths():
                try:
                    archive.write(path, path.relative_to(BASE_DIR).as_posix())
                except OSError:
                    # Windows can expose protected pseudo-files in a source
                    # directory.  A best-effort source backup must not fail
                    # because one unreadable, non-source entry is present.
                    continue
                count += 1
        result = buffer.getvalue()
    if len(result) > _MAX_BACKUP_BYTES: raise ValueError("백업 압축 파일이 GitHub 업로드 안전 한도(90MB)를 초과했습니다.")
    return result, count

def _ensure_local_remote(remote_url):
    current = _git("rev-parse", "--is-inside-work-tree")
    if not current or current.returncode != 0:
        initialized = _git("init")
        if not initialized or initialized.returncode != 0: raise RuntimeError("로컬 Git 저장소를 초기화하지 못했습니다.")
    origin = _git("remote", "get-url", "origin")
    if not origin or origin.returncode != 0:
        added = _git("remote", "add", "origin", remote_url + ".git")
        if not added or added.returncode != 0: raise RuntimeError("GitHub 원격 저장소 연결을 추가하지 못했습니다.")
    elif origin.stdout.strip().removesuffix(".git") != remote_url: raise ValueError("기존 origin 주소가 설정한 GITHUB_REPOSITORY_URL과 다릅니다. 기존 연결을 보호하기 위해 중단했습니다.")

def upload_backup():
    info, token = status(), os.getenv("GITHUB_TOKEN", "").strip()
    repository, remote_url = info["repository"], info["remote_url"]
    if not repository or not remote_url: raise ValueError("GITHUB_REPOSITORY 및 GITHUB_REPOSITORY_URL을 환경변수에 설정하세요.")
    if not token: raise ValueError("GITHUB_TOKEN이 설정되지 않았습니다. 토큰은 서버 환경변수에만 저장하세요.")
    _ensure_local_remote(remote_url)
    archive, count = _backup_archive(); stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"); destination = f"{_BACKUP_PREFIX}_{stamp}.zip"
    try: response = httpx.put(f"https://api.github.com/repos/{repository}/contents/{destination}", headers={"Accept":"application/vnd.github+json", "Authorization":f"Bearer {token}", "X-GitHub-Api-Version":"2022-11-28"}, json={"message":f"backup: AI Course Studio source {stamp}", "content":base64.b64encode(archive).decode("ascii")}, timeout=45)
    except httpx.HTTPError as exc: raise RuntimeError("GitHub에 연결하지 못했습니다. 네트워크 연결을 확인하세요.") from exc
    if response.status_code not in {200, 201}: raise RuntimeError(f"GitHub 백업 업로드 실패 (HTTP {response.status_code}). 저장소 권한과 토큰 권한(contents:write)을 확인하세요.")
    return {"uploaded":True, "path":destination, "file_count":count, "size_bytes":len(archive), "html_url":response.json().get("content", {}).get("html_url")}
