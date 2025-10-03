from logging.config import dictConfig

def setup_logging():
    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "ensure_extras": {
                "()": "smartfocusBackend.observability.EnsureExtrasFilter"
            }
        },
        "formatters": {
            "plain": {
                "format": "[%(asctime)s] %(levelname)s %(name)s [rid=%(request_id)s] %(message)s (path=%(path)s, method=%(method)s)"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "plain",
                "level": "INFO",
                "filters": ["ensure_extras"]
            }
        },
        "loggers": {
            "smartfocus":     {"handlers": ["console"], "level": "INFO", "propagate": False},
            "uvicorn.error":  {"handlers": ["console"], "level": "INFO", "propagate": False},
            "uvicorn.access": {"handlers": ["console"], "level": "INFO", "propagate": False},
            "fastapi":        {"handlers": ["console"], "level": "INFO", "propagate": False},
        },
        "root": {"handlers": ["console"], "level": "INFO"}
    })
