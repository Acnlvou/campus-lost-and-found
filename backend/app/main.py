import hmac
import secrets

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from app.api.router import api_router
from app.core.config import ROOT_DIR, RUNTIME_DIR, settings
from app.core.errors import BusinessError
from app.core.security import new_csrf
from app.db.bootstrap import init_db

MAX_CONTENT_LENGTH = 16384


def _resolve_secret() -> str:
    if settings.secret_key:
        return settings.secret_key
    key_path = RUNTIME_DIR / "session.key"
    key_path.parent.mkdir(parents=True, exist_ok=True)
    if not key_path.exists():
        key_path.write_text(secrets.token_hex(32))
    return key_path.read_text().strip()


def create_app():
    secret_key = _resolve_secret()

    app = FastAPI(
        title=settings.app_name,
        version="v1.0-rc",
        description="校园失物招领系统后端 API",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_middleware(request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > MAX_CONTENT_LENGTH:
            return JSONResponse({"error": "请求内容过长。"}, status_code=413)
        if "csrf" not in request.session:
            request.session["csrf"] = new_csrf()
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            supplied = request.headers.get("X-CSRF-Token", "")
            if not hmac.compare_digest(supplied, request.session["csrf"]):
                return JSONResponse({"error": "页面验证失效，请刷新后重试。"}, status_code=400)
        response = await call_next(request)
        response.headers["X-CSRF-Token"] = request.session.get("csrf", "")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; connect-src 'self'"
        response.headers["Cache-Control"] = "no-store"
        return response

    # SessionMiddleware 最后添加，成为最外层中间件，保证 request.session 在 CSRF 中间件中可用
    app.add_middleware(
        SessionMiddleware,
        secret_key=secret_key,
        session_cookie="session",
        max_age=14 * 24 * 3600,
        same_site="lax",
        https_only=False,
    )

    @app.exception_handler(BusinessError)
    async def business_error_handler(request, exc):
        return JSONResponse({"error": exc.message}, status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request, exc):
        msg = "请求格式错误。"
        errors = exc.errors()
        if errors:
            first = errors[0]
            msg = first.get("msg", msg)
            if msg.startswith("Value error, "):
                msg = msg[len("Value error, "):]
        return JSONResponse({"error": msg}, status_code=400)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request, exc):
        if exc.status_code == 404:
            return JSONResponse({"error": "页面或信息不存在。"}, status_code=404)
        return JSONResponse({"error": "请求格式错误。"}, status_code=exc.status_code)

    @app.exception_handler(SQLAlchemyError)
    async def database_error_handler(request, exc):
        app.logger.exception("Database operation failed")
        return JSONResponse({"error": "操作未完成，数据已回滚，请重试。"}, status_code=503)

    app.include_router(api_router, prefix=settings.api_prefix)

    init_db(settings.seed)

    _mount_spa(app)

    return app


def _mount_spa(app):
    dist = ROOT_DIR / "front" / "dist"
    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        if full_path.startswith("api"):
            raise StarletteHTTPException(status_code=404)
        target = dist / full_path
        if full_path and target.is_file():
            return FileResponse(str(target))
        index = dist / "index.html"
        if index.is_file():
            return FileResponse(str(index))
        return JSONResponse({"error": "页面或信息不存在。"}, status_code=404)


app = create_app()
