"""EasyMeals — Stateless FastAPI Application with Client-Stored Personal Data."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.catalogue_routes import router as catalogue_router
from app.api.ingredient_routes import router as ingredients_router
from app.api.planner_routes import router as planner_router
from app.api.recipe_routes import router as recipes_router
from app.theme import BACKGROUND_COLOR, THEME_COLOR

# 1. Environment & Production Verification
is_production = (
    bool(os.getenv("VERCEL_ENV"))
    or bool(os.getenv("VERCEL"))
    or os.getenv("APP_ENV", "").lower() not in ("development", "dev", "test")
)

# Hard security rule: reject running if service_role key is present in runtime
if os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
    raise RuntimeError(
        "SUPABASE_SERVICE_ROLE_KEY được phát hiện trong runtime environment. "
        "Khoá service_role bị cấm tuyệt đối trên server web."
    )

MAX_BODY_BYTES = 256 * 1024  # 256 KB max payload size for stateless computation

app = FastAPI(
    title="EasyMeals",
    description="Ứng dụng lên lịch bữa ăn theo nguyên liệu có sẵn, dữ liệu cá nhân "
    "lưu trữ cục bộ trên thiết bị và backend tính toán không trạng thái.",
    version="2.0.0",
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc",
    openapi_url=None if is_production else "/openapi.json",
)

# 2. CORS for Capacitor mobile apps (WebView)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "capacitor://localhost",
        "http://localhost",
        "https://localhost",
        "http://127.0.0.1",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "If-None-Match"],
)

# 3. Mount static files & templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
if Path("www").exists():
    app.mount("/mobile", StaticFiles(directory="www", html=True), name="mobile_static")
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["theme_color"] = THEME_COLOR

# 4. Register API routers
app.include_router(catalogue_router)
app.include_router(ingredients_router)
app.include_router(recipes_router)
app.include_router(planner_router)


# 5. Middlewares: Payload Size Limits and Security Headers
@app.middleware("http")
async def payload_size_limit_middleware(request: Request, call_next: Callable) -> Response:
    """Enforce strict 256 KB body size limit on mutating/computation requests."""
    if request.method in ("POST", "PUT", "PATCH"):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_BODY_BYTES:
            return JSONResponse(
                {"detail": "Kích thước dữ liệu vượt quá giới hạn (tối đa 256 KB)."},
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        # In case Chunked Transfer Encoding is used
        body = await request.body()
        if len(body) > MAX_BODY_BYTES:
            return JSONResponse(
                {"detail": "Kích thước dữ liệu vượt quá giới hạn (tối đa 256 KB)."},
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

    return await call_next(request)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next: Callable) -> Response:
    """Apply defense-in-depth security headers without user-tracking analytics."""
    path = request.url.path
    response: Response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "font-src 'self'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "base-uri 'none'; "
        "form-action 'self'; "
        "object-src 'none'; "
        "frame-ancestors 'none';"
    )

    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip().lower()
    if request.url.scheme == "https" or forwarded_proto == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    if not path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"

    return response


# 6. Public Health Check Endpoint
@app.get("/health", include_in_schema=False)
def health() -> JSONResponse:
    """Minimal public liveness check endpoint, never leaks system internals."""
    return JSONResponse(
        {"status": "ok", "service": "easymeals"},
        status_code=200,
    )


# 7. Web App Manifest & Service Worker
@app.get("/manifest.json", include_in_schema=False)
def manifest() -> JSONResponse:
    return JSONResponse(
        {
            "name": "EasyMeals — Sổ Tay Bếp Thông Minh",
            "short_name": "EasyMeals",
            "description": (
                "Lên lịch bữa ăn theo nguyên liệu sẵn có, "
                "dữ liệu cá nhân lưu trữ an toàn trên thiết bị."
            ),
            "start_url": "/",
            "display": "standalone",
            "background_color": BACKGROUND_COLOR,
            "theme_color": THEME_COLOR,
            "icons": [
                {
                    "src": "/static/icon.svg",
                    "sizes": "192x192",
                    "type": "image/svg+xml",
                    "purpose": "any maskable",
                },
                {
                    "src": "/static/icon.svg",
                    "sizes": "512x512",
                    "type": "image/svg+xml",
                    "purpose": "any maskable",
                },
            ],
        }
    )


@app.get("/sw.js", include_in_schema=False)
def service_worker() -> FileResponse:
    return FileResponse(
        "app/static/sw.js",
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"},
    )


# 8. Web Page Views (HTML)
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "index.html", {"title": "EasyMeals — Tủ Lạnh & Nguyên Liệu"}
    )


@app.get("/planner", response_class=HTMLResponse, include_in_schema=False)
def planner_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "planner.html", {"title": "EasyMeals — Kế Hoạch Bữa Ăn"}
    )


@app.get("/recipes", response_class=HTMLResponse, include_in_schema=False)
def recipes_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "recipes.html", {"title": "EasyMeals — Sổ Tay Món Ăn"}
    )


@app.get("/shopping-list", response_class=HTMLResponse, include_in_schema=False)
def shopping_list_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "shopping.html", {"title": "EasyMeals — Danh Sách Đi Chợ"}
    )


@app.get("/settings", response_class=HTMLResponse, include_in_schema=False)
def settings_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "settings.html", {"title": "EasyMeals — Dữ Liệu & Cài Đặt"}
    )
