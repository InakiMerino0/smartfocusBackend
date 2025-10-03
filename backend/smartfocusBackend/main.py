from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from .database import get_db
from .routers import v1_auth, v1_events, v1_nl, v1_subjects, v1_users

# 👇 NUEVO: logging estructurado + request_id
import logging
from .logging_config import setup_logging
from .observability import RequestIDMiddleware, attach_request_id_filter, get_request_id
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

# 1) instalar configuración global de logging (JSON a consola y a archivo)
setup_logging()
# 2) inyectar request_id en todos los logs (app + uvicorn + fastapi)
attach_request_id_filter()

app = FastAPI(
    title="SmartFocus Backend",
    description="Autenticación de usuarios, gestión de eventos y materias con IA",
    version="1.0",
)

# 3) middleware que genera/propaga X-Request-ID por cada request
app.add_middleware(RequestIDMiddleware)

# logger de la app
logger = logging.getLogger("smartfocus")

# CORS (igual que antes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ajustá si necesitás restringir
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rutas (igual que antes)
app.include_router(v1_auth.router)
app.include_router(v1_events.router)
app.include_router(v1_nl.router)
app.include_router(v1_subjects.router)
app.include_router(v1_users.router)

# (opcional) endpoint de salud, útil para healthchecks
@app.get("/health")
def health():
    logger.info("Health check OK", extra={"path": "/health", "method": "GET"})
    return {"status": "ok"}

# ✅ Handlers globales de errores → loguean JSON con request_id y devuelven ese ID al cliente
@app.exception_handler(Exception)
async def unhandled_exc_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception",
        extra={"path": request.url.path, "method": request.method},
        exc_info=True,  # incluye stacktrace en el log
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "internal_error", "request_id": get_request_id()},
    )

@app.exception_handler(RequestValidationError)
async def validation_exc_handler(request: Request, exc: RequestValidationError):
    logger.warning(
        "Validation error",
        extra={"path": request.url.path, "method": request.method, "errors": exc.errors()},
    )
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "request_id": get_request_id()},
    )
