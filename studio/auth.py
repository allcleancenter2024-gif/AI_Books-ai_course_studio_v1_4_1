"""Local account and session helpers. Passwords are never stored in plain text."""
import hashlib
import hmac
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request

from .db import connect

COOKIE_NAME = "ai_course_studio_session"
SESSION_DAYS = 7
MAX_LOGIN_FAILURES = 5
LOGIN_WINDOW_SECONDS = 5 * 60
_login_attempts: dict[str, list[float]] = {}
_attempt_lock = threading.Lock()


def _now(): return datetime.now(timezone.utc)

def _attempt_key(request: Request, username: str) -> str:
    host = request.client.host if request.client else "unknown"
    return f"{host}:{username.strip().casefold()}"

def login_allowed(request: Request, username: str) -> bool:
    key, now = _attempt_key(request, username), time.monotonic()
    with _attempt_lock:
        attempts = [stamp for stamp in _login_attempts.get(key, []) if now - stamp < LOGIN_WINDOW_SECONDS]
        _login_attempts[key] = attempts
        return len(attempts) < MAX_LOGIN_FAILURES

def record_login_failure(request: Request, username: str) -> None:
    key, now = _attempt_key(request, username), time.monotonic()
    with _attempt_lock:
        attempts = [stamp for stamp in _login_attempts.get(key, []) if now - stamp < LOGIN_WINDOW_SECONDS]
        attempts.append(now)
        _login_attempts[key] = attempts

def clear_login_failures(request: Request, username: str) -> None:
    with _attempt_lock: _login_attempts.pop(_attempt_key(request, username), None)

def _password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${digest.hex()}"

def _password_matches(password: str, stored: str) -> bool:
    try:
        algorithm, salt_hex, _ = stored.split("$", 2)
        return algorithm == "scrypt" and hmac.compare_digest(_password_hash(password, bytes.fromhex(salt_hex)), stored)
    except (TypeError, ValueError): return False

def bootstrap_admin(username: str, password: str) -> None:
    username = username.strip()
    if not username or len(password) < 12: raise ValueError("관리자 이름과 12자 이상의 비밀번호가 필요합니다.")
    with connect() as conn:
        if conn.execute("SELECT 1 FROM app_users LIMIT 1").fetchone(): raise ValueError("초기 관리자 계정이 이미 존재합니다.")
        conn.execute("INSERT INTO app_users(username,password_hash,role,created_at) VALUES(?,?,?,?)", (username, _password_hash(password), "admin", _now().isoformat()))

def authenticate(username: str, password: str) -> dict | None:
    with connect() as conn: row = conn.execute("SELECT username,password_hash,role FROM app_users WHERE username=?", (username.strip(),)).fetchone()
    return {"username": row["username"], "role": row["role"]} if row and _password_matches(password, row["password_hash"]) else None

def create_session(username: str) -> tuple[str, int]:
    token, expires = secrets.token_urlsafe(32), _now() + timedelta(days=SESSION_DAYS)
    with connect() as conn:
        conn.execute("DELETE FROM app_sessions WHERE expires_at<?", (_now().isoformat(),))
        conn.execute("INSERT INTO app_sessions(token_hash,username,expires_at,created_at) VALUES(?,?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), username, expires.isoformat(), _now().isoformat()))
    return token, SESSION_DAYS * 86400

def current_user(token: str | None) -> dict | None:
    if not token: return None
    with connect() as conn: row = conn.execute("SELECT u.username,u.role FROM app_sessions s JOIN app_users u ON u.username=s.username WHERE s.token_hash=? AND s.expires_at>?", (hashlib.sha256(token.encode()).hexdigest(), _now().isoformat())).fetchone()
    return {"username": row["username"], "role": row["role"]} if row else None

def delete_session(token: str | None) -> None:
    if token:
        with connect() as conn: conn.execute("DELETE FROM app_sessions WHERE token_hash=?", (hashlib.sha256(token.encode()).hexdigest(),))

def require_authenticated(request: Request) -> dict:
    user = current_user(request.cookies.get(COOKIE_NAME))
    if not user: raise HTTPException(401, "로그인이 필요합니다.")
    return user
