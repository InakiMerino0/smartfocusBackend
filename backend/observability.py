import logging, uuid, contextvars
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

_request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)

class RequestIDFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_ctx.get() or "-"
        return True

def attach_request_id_filter():
    root = logging.getLogger()
    f = RequestIDFilter()
    for h in root.handlers:
        h.addFilter(f)
    for name in ("smartfocus", "uvicorn.error", "uvicorn.access", "fastapi"):
        lg = logging.getLogger(name)
        for h in lg.handlers:
            h.addFilter(f)

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = _request_id_ctx.set(rid)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            _request_id_ctx.reset(token)

def get_request_id() -> str:
    return _request_id_ctx.get() or "-"
