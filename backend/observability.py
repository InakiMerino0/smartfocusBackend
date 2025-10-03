import logging, uuid, contextvars
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

_request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)

class RequestIDFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        rid = _request_id_ctx.get() or "-"
        setattr(record, "request_id", rid)
        return True

class EnsureExtrasFilter(logging.Filter):
    """Garantiza que path y method existan aunque el log no los pase en extra."""
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            setattr(record, "request_id", "-")
        if not hasattr(record, "path"):
            setattr(record, "path", "-")
        if not hasattr(record, "method"):
            setattr(record, "method", "-")
        return True

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
