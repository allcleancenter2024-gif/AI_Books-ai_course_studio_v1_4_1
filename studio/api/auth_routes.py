"""Public authentication and health endpoints kept separate from protected APIs."""
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, Response

from ..auth import COOKIE_NAME, authenticate, clear_login_failures, create_session, current_user, delete_session, login_allowed, record_login_failure
from ..config import AUTH_COOKIE_SECURE, LAST_UPDATED, VERSION
from ..schemas import LoginRequest

router = APIRouter(prefix="/api")

@router.post("/auth/login")
def login(req: LoginRequest, response: Response, request: Request):
    if not login_allowed(request, req.username):
        raise HTTPException(429, "로그인 시도가 너무 많습니다. 5분 뒤 다시 시도하세요.")
    user = authenticate(req.username, req.password)
    if not user:
        record_login_failure(request, req.username)
        raise HTTPException(401, "이름 또는 접속 암호를 확인하세요.")
    clear_login_failures(request, req.username)
    token, max_age = create_session(user["username"])
    response.set_cookie(COOKIE_NAME, token, max_age=max_age if req.remember else None, httponly=True, samesite="strict", secure=AUTH_COOKIE_SECURE, path="/")
    return {"ok": True, "user": user}

@router.get("/auth/session")
def session(request: Request):
    user = current_user(request.cookies.get(COOKIE_NAME))
    if not user: raise HTTPException(401, "로그인이 필요합니다.")
    return {"authenticated": True, "user": user}

@router.post("/auth/logout")
def logout(request: Request, response: Response):
    delete_session(request.cookies.get(COOKIE_NAME))
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}

@router.get("/health")
def health():
    return {"ok": True, "version": VERSION, "last_updated": LAST_UPDATED, "time": datetime.now().isoformat(timespec="seconds")}
