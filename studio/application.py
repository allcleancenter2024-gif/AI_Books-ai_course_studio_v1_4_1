from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from .config import APP_TITLE, VERSION, LAST_UPDATED, STATIC_DIR
from .api.auth_routes import router as public_router
from .api.provider_routes import router as provider_router
from .api.source_routes import router as source_router
from .api.course_routes import router as course_router
from .api.manual_routes import router as manual_router
from .api.hybrid_routes import router as hybrid_router
from .api.github_routes import router as github_router
from .api.routes import router
from .db import init_db


def create_app():
    # Run migrations before the first request so a clean installation works too.
    init_db()
    app = FastAPI(title=APP_TITLE, version=VERSION)
    app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')
    app.include_router(public_router)
    app.include_router(provider_router)
    app.include_router(source_router)
    app.include_router(course_router)
    app.include_router(manual_router)
    app.include_router(hybrid_router)
    app.include_router(github_router)
    app.include_router(router)

    @app.middleware("http")
    async def prevent_stale_ui(request: Request, call_next):
        path = request.url.path
        response = await call_next(request)
        if path == "/" or path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        response.headers["X-AI-Course-Studio-Version"] = VERSION
        return response

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception):
        return JSONResponse(status_code=500, content={'detail': f'서버 내부 오류: {type(exc).__name__}: {exc}'})

    @app.get('/', response_class=HTMLResponse)
    def home():
        html = (STATIC_DIR / 'index.html').read_text(encoding='utf-8')
        return html.replace('{{VERSION}}', VERSION).replace('{{LAST_UPDATED}}', LAST_UPDATED)

    return app
