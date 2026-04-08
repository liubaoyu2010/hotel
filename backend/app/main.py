from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
import redis

from app.config import settings
from app.db import Base, engine
from app.routes import router as api_router

app = FastAPI(title=settings.app_name, version=settings.app_version)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.on_event("startup")
def on_startup() -> None:
    settings.validate()
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": str(exc.detail), "data": {}},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"code": 422, "message": "validation_error", "data": {"errors": exc.errors()}},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, _exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "internal_server_error", "data": {}},
    )


@app.get("/health")
def health() -> dict:
    db_ok = False
    redis_ok = False
    db_error = None
    redis_error = None

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        db_error = str(exc)

    try:
        client = redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1)
        redis_ok = bool(client.ping())
    except Exception as exc:
        redis_error = str(exc)

    overall_ok = db_ok and redis_ok
    status_code = 200 if overall_ok else 503
    return {
        "code": status_code,
        "message": "success" if overall_ok else "degraded",
        "data": {
            "status": "ok" if overall_ok else "degraded",
            "time": datetime.now(timezone.utc).isoformat(),
            "checks": {
                "database": {"ok": db_ok, "error": db_error},
                "redis": {"ok": redis_ok, "error": redis_error},
            },
        },
    }
