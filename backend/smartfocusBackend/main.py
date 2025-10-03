import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from .logging_config import setup_logging
from .observability import RequestIDMiddleware, get_request_id

setup_logging()

app = FastAPI(title="SmartFocus Backend", version="1.0")
app.add_middleware(RequestIDMiddleware)

logger = logging.getLogger("smartfocus")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    logger.info("Health check OK", extra={"path": "/health", "method": "GET"})
    return {"status": "ok"}

@app.exception_handler(Exception)
async def unhandled_exc_handler(request: Request, exc: Exception):
    rid = get_request_id()
    logger.error(
        "Unhandled exception",
        extra={"path": request.url.path, "method": request.method},
        exc_info=True  # 🔑 esto imprime el traceback completo
    )
    return JSONResponse(status_code=500, content={"detail": "internal_error", "request_id": rid})

@app.exception_handler(RequestValidationError)
async def validation_exc_handler(request: Request, exc: RequestValidationError):
    rid = get_request_id()
    logger.warning(
        "Validation error",
        extra={"path": request.url.path, "method": request.method, "errors": exc.errors()},
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors(), "request_id": rid})
