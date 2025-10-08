# Imagen base estable y liviana
FROM python:3.11-slim

# -------- etiquetas/trazabilidad ----------
ARG COMMIT_SHA=unknown
LABEL org.opencontainers.image.revision=$COMMIT_SHA
ENV APP_COMMIT_SHA=$COMMIT_SHA

# -------- optimizaciones Python/pip ----------
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# curl para healthcheck; limpia apt
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

# Usuario no-root
RUN addgroup --system app && adduser --system --ingroup app --uid 10001 app

WORKDIR /app

# Dependencias (contexto = ./backend)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copiar código (contexto = ./backend)
COPY smartfocusBackend ./smartfocusBackend
RUN chown -R app:app /app

USER 10001:10001

EXPOSE 8000

# Healthcheck interno (requiere endpoint /ready)
HEALTHCHECK --interval=15s --timeout=3s --retries=5 \
  CMD curl -fsS http://127.0.0.1:8000/ready || exit 1

# Server ASGI
CMD ["uvicorn","smartfocusBackend.main:app","--host","0.0.0.0","--port","8000"]

# (Opcional multi-core)
# CMD ["gunicorn","-k","uvicorn.workers.UvicornWorker","-w","2","-b","0.0.0.0:8000","smartfocusBackend.main:app"]
